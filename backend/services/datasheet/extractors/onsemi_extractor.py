"""
OnSemi (onsemi) PDF datasheet extractor.
Extracts IC specification data from OnSemi PDF datasheets.
A single PDF can contain multiple IC variants.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

from .base import DatasheetExtractor
from ..exceptions import DatasheetExtractionException

import logging

logger = logging.getLogger(__name__)


class OnSemiExtractor(DatasheetExtractor):
    """Extractor for OnSemi PDF datasheets."""
    
    def extract(self, pdf_path: Path) -> List[Dict]:
        """
        Extract IC specification data from OnSemi PDF datasheet.
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
            logger.debug(f"Extracting data from OnSemi PDF: {pdf_path}")
            
            ic_variants = []
            voltage_specs = {}  # Extract once, apply to all variants
            temp_specs = {}     # Extract once, apply to all variants
            
            with pdfplumber.open(pdf_path) as pdf:
                # First pass: Extract voltage and temperature specs from operating conditions
                voltage_specs, temp_specs = self._extract_operating_conditions(pdf)
                
                # Second pass: Extract IC variants from package/ordering information tables
                for page_num, page in enumerate(pdf.pages, 1):
                    tables = page.extract_tables()
                    
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                        
                        header_row = table[0] if table else []
                        header_text = " ".join(str(cell) if cell else "" for cell in header_row).lower()
                        
                        # Check if this is a package/ordering information table
                        if any(keyword in header_text for keyword in [
                            "order", "ordering", "part number", "package", 
                            "device", "ordering information", "marking"
                        ]):
                            variants = self._extract_from_table(table, header_row, voltage_specs, temp_specs)
                            ic_variants.extend(variants)
            
            if not ic_variants:
                logger.debug(f"No IC variants found in PDF: {pdf_path}")
                return [self._create_basic_entry(pdf_path, voltage_specs, temp_specs)]
            
            logger.info(f"Extracted {len(ic_variants)} IC variants from OnSemi PDF")
            return ic_variants
            
        except Exception as e:
            logger.error(f"Failed to extract data from OnSemi PDF {pdf_path}: {e}")
            raise DatasheetExtractionException(
                f"Failed to extract data from OnSemi PDF: {str(e)}"
            )
    
    def _extract_operating_conditions(self, pdf) -> Tuple[Dict, Dict]:
        """
        Extract voltage and temperature specs from operating conditions tables.
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
                
                # Look for operating conditions or electrical characteristics table
                if any(keyword in header_text for keyword in [
                    "operating conditions", "electrical characteristics", 
                    "absolute maximum ratings", "recommended operating"
                ]):
                    for row in table[1:]:
                        if not row or len(row) < 2:
                            continue
                        
                        # Look for voltage and temperature rows
                        first_cell = str(row[0] if row[0] else "").lower()
                        
                        # Extract voltage range
                        if any(keyword in first_cell for keyword in ["supply voltage", "vcc", "vdd", "voltage"]):
                            for cell in row[1:]:
                                if cell:
                                    voltage_range = self._extract_voltage_range(str(cell))
                                    if voltage_range:
                                        voltage_specs.update(voltage_range)
                        
                        # Extract temperature range
                        if "temperature" in first_cell and ("operating" in first_cell or "range" in first_cell):
                            for cell in row[1:]:
                                if cell:
                                    temp_range = self._extract_temperature_range(str(cell))
                                    if temp_range:
                                        temp_specs.update(temp_range)
        
        return voltage_specs, temp_specs
    
    def _extract_voltage_range(self, text: str) -> Optional[Dict]:
        """Extract voltage min/max from text like '3 to 32' or '3V to 32V'."""
        if not text:
            return None
        
        # Pattern: "X to Y" or "X-Y" or "X V to Y V"
        pattern = r'(\d+\.?\d*)\s*V?\s*(?:to|-|–)\s*(\d+\.?\d*)\s*V?'
        match = re.search(pattern, text, re.IGNORECASE)
        
        if match:
            try:
                min_v = float(match.group(1))
                max_v = float(match.group(2))
                return {"voltage_min": min_v, "voltage_max": max_v}
            except ValueError:
                pass
        
        # Single value pattern (e.g., "32" for max voltage)
        pattern_single = r'(\d+\.?\d*)\s*V?'
        match_single = re.search(pattern_single, text)
        if match_single:
            try:
                val = float(match_single.group(1))
                if val > 1:
                    return {"voltage_max": val}
            except ValueError:
                pass
        
        return None
    
    def _extract_temperature_range(self, text: str) -> Optional[Dict]:
        """Extract temperature min/max from text like '0 to 70°C' or '-40 to 125'."""
        if not text:
            return None
        
        # Pattern: "X°C to Y°C" or "X to Y"
        pattern = r'(-?\d+\.?\d*)\s*°?\s*C?\s*(?:to|-|–)\s*(-?\d+\.?\d*)\s*°?\s*C?'
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
        Extract IC variants from a package/ordering information table.
        
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
            
            # Extract part number/device
            part_number = self._get_cell_value(row, col_indices.get("part_number"))
            if not part_number or not part_number.strip():
                continue
            
            # Clean part number
            part_number = self._clean_part_number(part_number)
            if not part_number:
                continue
            
            # Extract package information
            package_type = self._get_cell_value(row, col_indices.get("package"))
            
            # Extract pin count
            pins = self._extract_pin_count(row, col_indices.get("pins"))
            
            # Extract marking code
            marking = self._get_cell_value(row, col_indices.get("marking"))
            
            # Create IC specification entry with voltage and temp specs
            variant = {
                "part_number": part_number,
                "manufacturer": "ONSEMI",
                "pin_count": pins or 0,
                "package_type": package_type or None,
                "description": f"OnSemi {part_number} - {package_type or 'Unknown Package'}",
                "voltage_min": voltage_specs.get("voltage_min"),
                "voltage_max": voltage_specs.get("voltage_max"),
                "operating_temp_min": temp_specs.get("operating_temp_min"),
                "operating_temp_max": temp_specs.get("operating_temp_max"),
                "dimension_length": None,
                "dimension_width": None,
                "dimension_height": None,
                "electrical_specs": {
                    "marking": marking,
                }
            }
            
            variants.append(variant)
        
        return variants
    
    def _find_column_indices(self, header_row: List) -> Dict[str, int]:
        """
        Find column indices for key fields in the table.
        OnSemi datasheets typically use "Device", "Package", "Marking" columns.
        """
        indices = {}
        
        for idx, cell in enumerate(header_row):
            if not cell:
                continue
            
            cell_lower = str(cell).lower().strip()
            
            # Part number/Device column
            if any(keyword in cell_lower for keyword in ["device", "part number", "type", "order"]) and "part_number" not in indices:
                indices["part_number"] = idx
            
            # Package column
            if "package" in cell_lower and "package" not in indices:
                indices["package"] = idx
            
            # Pins column
            if "pin" in cell_lower and "pins" not in indices:
                indices["pins"] = idx
            
            # Marking column
            if "marking" in cell_lower and "marking" not in indices:
                indices["marking"] = idx
        
        return indices
    
    def _get_cell_value(self, row: List, col_index: Optional[int]) -> Optional[str]:
        """Get cell value from row, handling None indices."""
        if col_index is None or col_index >= len(row):
            return None
        value = row[col_index]
        return str(value).strip() if value else None
    
    def _clean_part_number(self, part_number: str) -> str:
        """Clean and normalize part number."""
        if not part_number:
            return ""
        part_number = " ".join(part_number.split())
        return part_number.upper().strip()
    
    def _extract_pin_count(self, row: List, col_index: Optional[int]) -> Optional[int]:
        """Extract pin count from cell or infer from package name."""
        # First try dedicated pins column
        if col_index is not None:
            value = self._get_cell_value(row, col_index)
            if value:
                match = re.search(r'\d+', str(value))
                if match:
                    try:
                        return int(match.group())
                    except ValueError:
                        pass
        
        # Try to extract from package name (e.g., "SOIC8", "DIP14", "TO92")
        for cell in row:
            if cell:
                cell_str = str(cell).upper()
                # Look for patterns like SOIC8, DIP14, etc.
                match = re.search(r'(SO|SOIC|TSSOP|DIP|QFP|LQFP|SSOP|MSOP|VSSOP|PDIP)(\d+)', cell_str)
                if match:
                    try:
                        return int(match.group(2))
                    except ValueError:
                        pass
        
        return None
    
    def _create_basic_entry(self, pdf_path: Path, voltage_specs: Dict, temp_specs: Dict) -> Dict:
        """Create a basic entry when no table data is found."""
        part_number = pdf_path.stem.upper()
        
        return {
            "part_number": part_number,
            "manufacturer": "ONSEMI",
            "pin_count": 0,
            "package_type": None,
            "description": f"OnSemi {part_number}",
            "voltage_min": voltage_specs.get("voltage_min"),
            "voltage_max": voltage_specs.get("voltage_max"),
            "operating_temp_min": temp_specs.get("operating_temp_min"),
            "operating_temp_max": temp_specs.get("operating_temp_max"),
            "dimension_length": None,
            "dimension_width": None,
            "dimension_height": None,
            "electrical_specs": {},
        }
