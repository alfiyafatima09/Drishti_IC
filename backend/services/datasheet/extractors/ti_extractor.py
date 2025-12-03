"""
Texas Instruments PDF datasheet extractor.
Extracts IC specification data from TI PDF datasheets.
A single PDF can contain multiple IC variants (e.g., LM317DCY, LM317KCS).
"""
import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

from .base import DatasheetExtractor
from ..exceptions import DatasheetExtractionException

logger = logging.getLogger(__name__)


class TIExtractor(DatasheetExtractor):
    """Extractor for Texas Instruments PDF datasheets."""
    
    def extract(self, pdf_path: Path) -> List[Dict]:
        """
        Extract IC specification data from TI PDF datasheet.
        Extracts all IC variants found in package dimension tables.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of dictionaries, each containing data for one IC variant
            
        Raises:
            DatasheetExtractionException: If extraction fails
        """
        if not PDFPLUMBER_AVAILABLE:
            logger.warning("pdfplumber not available, skipping PDF extraction")
            return []
        
        try:
            logger.debug(f"Extracting data from TI PDF: {pdf_path}")
            
            ic_variants = []
            voltage_specs = {}  # Extract once, apply to all variants
            temp_specs = {}     # Extract once, apply to all variants
            
            with pdfplumber.open(pdf_path) as pdf:
                # First pass: Extract voltage and temperature specs from "Recommended Operating Conditions"
                voltage_specs, temp_specs = self._extract_operating_conditions(pdf)
                
                # Second pass: Extract IC variants from package dimension tables
                for page_num, page in enumerate(pdf.pages, 1):
                    tables = page.extract_tables()
                    
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                        
                        header_row = table[0] if table else []
                        header_text = " ".join(str(cell) if cell else "" for cell in header_row).lower()
                        
                        # Check if this is a package dimension table
                        if any(keyword in header_text for keyword in ["device", "package", "pins", "package type"]):
                            variants = self._extract_from_table(table, header_row, voltage_specs, temp_specs)
                            ic_variants.extend(variants)
            
            if not ic_variants:
                logger.debug(f"No IC variants found in PDF: {pdf_path}")
                return [self._create_basic_entry(pdf_path, voltage_specs, temp_specs)]
            
            logger.info(f"Extracted {len(ic_variants)} IC variants from TI PDF")
            return ic_variants
            
        except Exception as e:
            logger.error(f"Failed to extract data from TI PDF {pdf_path}: {e}")
            raise DatasheetExtractionException(
                f"Failed to extract data from TI PDF: {str(e)}"
            )
    
    def _extract_operating_conditions(self, pdf) -> Tuple[Dict, Dict]:
        """
        Extract voltage and temperature specs from "Recommended Operating Conditions" table.
        Returns once per PDF, applies to all variants.
        
        Returns:
            Tuple of (voltage_specs, temp_specs) dictionaries
        """
        voltage_specs = {}
        temp_specs = {}
        
        for page in pdf.pages:
            tables = page.extract_tables()
            
            for table in tables:
                if not table or len(table) < 2:
                    continue
                
                header_row = table[0] if table else []
                header_text = " ".join(str(cell) if cell else "" for cell in header_row).lower()
                
                # Look for "Recommended Operating Conditions" table
                if "recommended operating" in header_text or "operating conditions" in header_text:
                    for row in table[1:]:
                        if not row or len(row) < 2:
                            continue
                        
                        # Look for voltage and temperature rows
                        first_cell = str(row[0] if row[0] else "").lower()
                        
                        if "supply voltage" in first_cell or "voltage" in first_cell:
                            # Extract voltage range
                            for cell in row[1:]:
                                if cell:
                                    voltage_range = self._extract_voltage_range(str(cell))
                                    if voltage_range:
                                        voltage_specs.update(voltage_range)
                        
                        if "temperature" in first_cell and "operating" in first_cell:
                            # Extract temperature range
                            for cell in row[1:]:
                                if cell:
                                    temp_range = self._extract_temperature_range(str(cell))
                                    if temp_range:
                                        temp_specs.update(temp_range)
        
        return voltage_specs, temp_specs
    
    def _extract_voltage_range(self, text: str) -> Optional[Dict]:
        """Extract voltage min/max from text like '4.5 V to 18 V' or '4.5V to 18V'."""
        if not text:
            return None
        
        # Pattern: "X to Y" or "X-Y" or "X V to Y V"
        pattern = r'(\d+\.?\d*)\s*V?\s*(?:to|-)\s*(\d+\.?\d*)\s*V?'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            try:
                min_v = float(match.group(1))
                max_v = float(match.group(2))
                return {"voltage_min": min_v, "voltage_max": max_v}
            except ValueError:
                pass
        
        return None
    
    def _extract_temperature_range(self, text: str) -> Optional[Dict]:
        """Extract temperature min/max from text like '-40°C to 125°C'."""
        if not text:
            return None
        
        # Pattern: "X°C to Y°C" or "X to Y"
        pattern = r'(-?\d+\.?\d*)\s*°?\s*C?\s*(?:to|-)\s*(-?\d+\.?\d*)\s*°?\s*C?'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            try:
                min_t = float(match.group(1))
                max_t = float(match.group(2))
                return {"operating_temp_min": min_t, "operating_temp_max": max_t}
            except ValueError:
                pass
        
        return None
    
    def _extract_from_table(
        self, 
        table: List[List], 
        header_row: List,
        voltage_specs: Dict,
        temp_specs: Dict
    ) -> List[Dict]:
        """
        Extract IC variants from a package dimension table.
        
        Args:
            table: Table data (list of rows)
            header_row: First row containing column headers
            voltage_specs: Voltage specs extracted from operating conditions
            temp_specs: Temperature specs extracted from operating conditions
            
        Returns:
            List of IC variant dictionaries
        """
        variants = []
        
        # Find column indices
        col_indices = self._find_column_indices(header_row)
        if not col_indices:
            return variants
        
        # Process data rows (skip header row)
        for row in table[1:]:
            if not row or len(row) < 2:
                continue
            
            # Extract device/part number
            device = self._get_cell_value(row, col_indices.get("device"))
            if not device or not device.strip():
                continue
            
            # Clean device name
            device = self._clean_part_number(device)
            if not device:
                continue
            
            # Extract package information - improved logic
            package_name = self._get_cell_value(row, col_indices.get("package_name"))
            package_type = self._get_cell_value(row, col_indices.get("package_type"))
            
            # If package_type is empty, try to get from package_name or description
            if not package_type and package_name:
                # Package name might be the code (e.g., "D", "P", "DCY")
                # Look for package type in other columns or use package_name as fallback
                package_type = package_name
            
            # Extract pin count
            pins = self._extract_pin_count(row, col_indices.get("pins"))
            
            # Extract dimensions
            dimension_length = None
            dimension_width = None
            dimension_height = None
            
            dimensions = {}
            if col_indices.get("length"):
                dimension_length = self._extract_float(row, col_indices.get("length"))
                dimensions["length_mm"] = dimension_length
            if col_indices.get("width"):
                dimension_width = self._extract_float(row, col_indices.get("width"))
                dimensions["width_mm"] = dimension_width
            if col_indices.get("thickness"):
                dimensions["thickness_um"] = self._extract_float(row, col_indices.get("thickness"))
            if col_indices.get("height"):
                dimension_height = self._extract_float(row, col_indices.get("height"))
                dimensions["height_mm"] = dimension_height
            
            # Create IC specification entry with voltage and temp specs
            variant = {
                "part_number": device,
                "manufacturer": "TI",
                "pin_count": pins or 0,
                "package_type": package_type or None,
                "description": f"TI {device} - {package_type or package_name or 'Unknown Package'}",
                "voltage_min": voltage_specs.get("voltage_min"),
                "voltage_max": voltage_specs.get("voltage_max"),
                "operating_temp_min": temp_specs.get("operating_temp_min"),
                "operating_temp_max": temp_specs.get("operating_temp_max"),
                "dimension_length": dimension_length,
                "dimension_width": dimension_width,
                "dimension_height": dimension_height,
                "electrical_specs": {
                    "package_name": package_name,
                    "dimensions": dimensions,
                }
            }
            
            variants.append(variant)
        
        return variants
    
    def _find_column_indices(self, header_row: List) -> Dict[str, int]:
        """
        Find column indices for key fields in the table.
        Improved matching for package type.
        """
        indices = {}
        
        for idx, cell in enumerate(header_row):
            if not cell:
                continue
            
            cell_lower = str(cell).lower().strip()
            
            # Device/Part number column
            if "device" in cell_lower and "device" not in indices:
                indices["device"] = idx
            
            # Package name column
            if ("package name" in cell_lower or "package_name" in cell_lower) and "package_name" not in indices:
                indices["package_name"] = idx
            
            # Package type column - improved matching
            # Look for "Package Type" or "Package Drawing" or just "Package" (if not "Package Name")
            if (("package type" in cell_lower or "package_type" in cell_lower or 
                 "package drawing" in cell_lower) and "package_type" not in indices):
                indices["package_type"] = idx
            elif ("package" in cell_lower and "name" not in cell_lower and 
                  "drawing" not in cell_lower and "package_type" not in indices and
                  "package_name" not in indices):
                # Sometimes "Package" column contains the type (check it's not already package_name)
                indices["package_type"] = idx
            
            # Pins column
            if "pin" in cell_lower and "pins" not in indices:
                indices["pins"] = idx
            
            # Dimension columns
            if ("length" in cell_lower or cell_lower in ["l", "l (mm)"]) and "length" not in indices:
                indices["length"] = idx
            if ("width" in cell_lower or cell_lower in ["w", "w (mm)"]) and "width" not in indices:
                indices["width"] = idx
            if ("thickness" in cell_lower or cell_lower in ["t", "t (µm)", "t (um)"]) and "thickness" not in indices:
                indices["thickness"] = idx
            if ("height" in cell_lower or cell_lower in ["b", "b (mm)", "h", "h (mm)"]) and "height" not in indices:
                indices["height"] = idx
        
        return indices
    
    def _get_cell_value(self, row: List, col_index: Optional[int]) -> Optional[str]:
        """Get cell value from row, handling None indices."""
        if col_index is None or col_index >= len(row):
            return None
        value = row[col_index]
        return str(value).strip() if value else None
    
    def _clean_part_number(self, device: str) -> str:
        """Clean and normalize part number."""
        if not device:
            return ""
        device = " ".join(device.split())
        return device.upper().strip()
    
    def _extract_pin_count(self, row: List, col_index: Optional[int]) -> Optional[int]:
        """Extract pin count from cell."""
        if col_index is None:
            return None
        
        value = self._get_cell_value(row, col_index)
        if not value:
            return None
        
        match = re.search(r'\d+', str(value))
        if match:
            try:
                return int(match.group())
            except ValueError:
                pass
        
        return None
    
    def _extract_float(self, row: List, col_index: Optional[int]) -> Optional[float]:
        """Extract float value from cell."""
        if col_index is None:
            return None
        
        value = self._get_cell_value(row, col_index)
        if not value:
            return None
        
        match = re.search(r'[\d.]+', str(value))
        if match:
            try:
                return float(match.group())
            except ValueError:
                pass
        
        return None
    
    def _create_basic_entry(self, pdf_path: Path, voltage_specs: Dict, temp_specs: Dict) -> Dict:
        """Create a basic entry when no table data is found."""
        part_number = pdf_path.stem.upper()
        
        return {
            "part_number": part_number,
            "manufacturer": "TI",
            "pin_count": 0,
            "package_type": None,
            "description": f"TI {part_number}",
            "voltage_min": voltage_specs.get("voltage_min"),
            "voltage_max": voltage_specs.get("voltage_max"),
            "operating_temp_min": temp_specs.get("operating_temp_min"),
            "operating_temp_max": temp_specs.get("operating_temp_max"),
            "dimension_length": None,
            "dimension_width": None,
            "dimension_height": None,
            "electrical_specs": {},
        }
