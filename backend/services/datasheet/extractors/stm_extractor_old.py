"""
STMicroelectronics PDF datasheet extractor.
Extracts IC specification data from STM PDF datasheets.
A single PDF can contain multiple IC variants (e.g., LM358D, LM358DT).
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


class STMExtractor(DatasheetExtractor):
    """Extractor for STMicroelectronics PDF datasheets."""
    
    # STM32 part number patterns (more specific first)
    PART_NUMBER_PATTERNS = [
        # STM32 series: STM32F103C8, STM32L476RG, STM32H743ZI, etc.
        r'\b(STM32[A-Z]\d{2,3}[A-Z]{1,2}\d{1,2}[A-Z]?)\b',
        # STM8 series: STM8S105C6, STM8L152C6, etc.
        r'\b(STM8[A-Z]\d{3}[A-Z]\d)\b',
        # Legacy STM parts
        r'\b(L\d{3,4}[A-Z]?)\b',  # L293, L298, etc.
        r'\b(LM\d{3,4}[A-Z]*)\b',  # LM358, LM324, etc.
    ]
    
    # Package patterns with pin counts
    PACKAGE_PATTERNS = [
        (r'\b(LQFP)(\d+)\b', 'LQFP'),
        (r'\b(UFQFPN)(\d+)\b', 'UFQFPN'),
        (r'\b(WLCSP)(\d+)\b', 'WLCSP'),
        (r'\b(TFBGA)(\d+)\b', 'TFBGA'),
        (r'\b(TSSOP)(\d+)\b', 'TSSOP'),
        (r'\b(SOIC)(\d+)\b', 'SOIC'),
        (r'\b(SO)(\d+)\b', 'SO'),
        (r'\b(DIP)(\d+)\b', 'DIP'),
        (r'\b(QFN)(\d+)\b', 'QFN'),
        (r'\b(QFP)(\d+)\b', 'QFP'),
        (r'\b(UFBGA)(\d+)\b', 'UFBGA'),
        # Pattern for "48-pin" or "48 pins"
        (r'(\d+)[\s-]?(?:pin|lead)', None),
    ]
    
    def extract(self, pdf_path: Path) -> List[Dict]:
        """
        Extract IC specification data from STM PDF datasheet.
        Uses hybrid approach: regex text parsing + table extraction.
        
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
            logger.debug(f"Extracting data from STM PDF: {pdf_path}")
            
            ic_variants = []
            voltage_specs = {}
            temp_specs = {}
            
            with pdfplumber.open(pdf_path) as pdf:
                # Extract full text for regex-based parsing
                full_text = self._extract_full_text(pdf)
                
                # Extract voltage and temperature from text (more reliable)
                voltage_specs = self._extract_voltage_from_text(full_text)
                temp_specs = self._extract_temperature_from_text(full_text)
                
                logger.debug(f"Extracted voltage specs: {voltage_specs}")
                logger.debug(f"Extracted temp specs: {temp_specs}")
                
                # Try regex-based variant extraction first (works for STM32)
                regex_variants = self._extract_variants_from_text(full_text, voltage_specs, temp_specs)
                ic_variants.extend(regex_variants)
                
                # Also try table-based extraction (works for older analog parts)
                table_variants = self._extract_from_tables(pdf, voltage_specs, temp_specs)
                
                # Merge variants (avoid duplicates)
                seen_parts = {v["part_number"] for v in ic_variants}
                for variant in table_variants:
                    if variant["part_number"] not in seen_parts:
                        ic_variants.append(variant)
                        seen_parts.add(variant["part_number"])
            
            if not ic_variants:
                logger.debug(f"No IC variants found in PDF: {pdf_path}")
                return [self._create_basic_entry(pdf_path, voltage_specs, temp_specs)]
            
            logger.info(f"Extracted {len(ic_variants)} IC variants from STM PDF")
            return ic_variants
            
        except Exception as e:
            logger.error(f"Failed to extract data from STM PDF {pdf_path}: {e}")
            raise DatasheetExtractionException(
                f"Failed to extract data from STM PDF: {str(e)}"
            )
    
    def _extract_full_text(self, pdf) -> str:
        """Extract all text from PDF."""
        text_parts = []
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)
    
    def _extract_voltage_from_text(self, text: str) -> Dict:
        """Extract voltage specs from full PDF text using regex (like NXP extractor)."""
        voltage_specs = {}
        
        patterns = [
            # VDD/VCC range
            r'V[Dd][Dd][A-Z]?\s*[=:]\s*(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            r'V[Cc][Cc]\s*[=:]\s*(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # Supply voltage range
            r'[Ss]upply\s+[Vv]oltage[:\s]+(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            r'[Oo]perating\s+[Vv]oltage[:\s]+(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # Generic voltage range
            r'(\d+\.?\d*)\s*V\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V(?:\s|$|,)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    min_v = float(match.group(1))
                    max_v = float(match.group(2))
                    if 1.0 <= min_v <= 60.0 and 1.0 <= max_v <= 60.0 and min_v < max_v:
                        voltage_specs = {"voltage_min": min_v, "voltage_max": max_v}
                        logger.debug(f"Found voltage range: {min_v}V to {max_v}V")
                        break
                except (ValueError, IndexError):
                    continue
        
        return voltage_specs
    
    def _extract_temperature_from_text(self, text: str) -> Dict:
        """Extract temperature specs from full PDF text using regex (like NXP extractor)."""
        temp_specs = {}
        
        # Normalize PDF encoding issues
        normalized_text = text.replace('(cid:176)', '°').replace('(cid:176)', '°')
        
        patterns = [
            # Pattern for "-40°C to +85°C" with various separators
            r'[-–]\s*(\d+)\s*°?\s*C?\s*to\s*\+?(\d+)\s*°?\s*C',
            # Temperature range with degree symbol
            r'(-?\d+)\s*°?\s*C\s*(?:to|[-–~])\s*\+?(\d+)\s*°?\s*C',
            # Operating/ambient temperature
            r'[Oo]perating\s+[Tt]emperature[:\s]+(-?\d+)\s*(?:°C)?\s*(?:to|[-–~])\s*\+?(\d+)',
            r'[Aa]mbient\s+[Tt]emperature[:\s]+(-?\d+)\s*(?:°C)?\s*(?:to|[-–~])\s*\+?(\d+)',
            # Industrial temperature range pattern
            r'[-–]\s*(40)\s*°?\s*C?\s*to\s*\+?(85|125)\s*°?\s*C',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, normalized_text, re.IGNORECASE)
            if match:
                try:
                    min_t_str = match.group(1)
                    min_t = float(min_t_str)
                    # Handle negative temperature
                    if min_t > 0 and '- ' + min_t_str in normalized_text:
                        min_t = -min_t
                    max_t = float(match.group(2))
                    # Sanity check
                    if -65 <= min_t <= 25 and 50 <= max_t <= 200:
                        temp_specs = {"operating_temp_min": min_t, "operating_temp_max": max_t}
                        logger.debug(f"Found temperature range: {min_t}°C to {max_t}°C")
                        break
                except (ValueError, IndexError):
                    continue
        
        return temp_specs
    
    def _extract_variants_from_text(
        self,
        text: str,
        voltage_specs: Dict,
        temp_specs: Dict
    ) -> List[Dict]:
        """Extract IC variants from text using regex (STM32 focused)."""
        variants = []
        seen_parts = set()
        
        # Find ordering/device summary section
        ordering_section = self._find_ordering_section(text)
        search_text = ordering_section if ordering_section else text
        
        # Try each part number pattern
        for pattern in self.PART_NUMBER_PATTERNS:
            matches = re.finditer(pattern, search_text, re.IGNORECASE)
            
            for match in matches:
                part_number = match.group(1).upper()
                
                # Skip if already seen or too short
                if part_number in seen_parts or len(part_number) < 5:
                    continue
                
                # Skip common false positives
                if part_number in ['TABLE', 'FLASH', 'PACKAGE', 'ORDER', 'LQFP']:
                    continue
                
                seen_parts.add(part_number)
                
                # Get context around match to extract package info
                start = max(0, match.start() - 10)
                end = min(len(search_text), match.end() + 200)
                context = search_text[start:end]
                
                # Extract package and pin count from context
                package_type, pin_count = self._extract_package_from_context(context)
                
                variant = {
                    "part_number": part_number,
                    "manufacturer": "STM",
                    "pin_count": pin_count or 0,
                    "package_type": package_type,
                    "description": f"STM {part_number}" + (f" - {package_type}" if package_type else ""),
                    "voltage_min": voltage_specs.get("voltage_min"),
                    "voltage_max": voltage_specs.get("voltage_max"),
                    "operating_temp_min": temp_specs.get("operating_temp_min"),
                    "operating_temp_max": temp_specs.get("operating_temp_max"),
                    "dimension_length": None,
                    "dimension_width": None,
                    "dimension_height": None,
                    "electrical_specs": {}
                }
                
                variants.append(variant)
        
        return variants
    
    def _find_ordering_section(self, text: str) -> Optional[str]:
        """Find and extract the ordering information section from text."""
        patterns = [
            r'(?:ordering\s+information|order\s+information|device\s+summary)(.{500,3000})',
            r'(?:part\s+numbering.*?package)(.{200,2000})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(0)
        
        return None
    
    def _extract_package_from_context(self, context: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract package type and pin count from text context (like NXP)."""
        package_type = None
        pin_count = None
        
        # Try package patterns
        for pattern, pkg_name in self.PACKAGE_PATTERNS:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                if pkg_name:
                    # Pattern like LQFP48
                    package_type = f"{pkg_name}{match.group(2)}"
                    try:
                        pin_count = int(match.group(2))
                    except (ValueError, IndexError):
                        pass
                else:
                    # Pattern like "48-pin"
                    try:
                        pin_count = int(match.group(1))
                    except (ValueError, IndexError):
                        pass
                break
        
        return package_type, pin_count
    
    def _extract_from_tables(
        self,
        pdf,
        voltage_specs: Dict,
        temp_specs: Dict
    ) -> List[Dict]:
        """Extract IC variants from tables (fallback for older parts)."""
        ic_variants = []
        
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            
            for table_idx, table in enumerate(tables):
                if not table or len(table) < 2:
                    continue
                
                header_row = table[0] if table else []
                header_text = " ".join(str(cell) if cell else "" for cell in header_row).lower()
                
                # Check if this is an ordering table
                if any(keyword in header_text for keyword in [
                    "order code", "ordering", "part number", "package", 
                    "device summary", "ordering information", "packing",
                    "temperature range", "sales type"
                ]):
                    logger.debug(f"Found potential ordering table on page {page_num}")
                    variants = self._extract_from_table(table, header_row, voltage_specs, temp_specs)
                    if variants:
                        logger.info(f"Extracted {len(variants)} variants from page {page_num}, table {table_idx}")
                    ic_variants.extend(variants)
        
        return ic_variants
    
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
        """Extract voltage min/max from text like '3 to 30' or '3V to 30V'."""
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
        
        # Single value pattern (e.g., "30" for max voltage)
        pattern_single = r'(\d+\.?\d*)\s*V?'
        match_single = re.search(pattern_single, text)
        if match_single:
            try:
                val = float(match_single.group(1))
                # Assume it's max voltage if single value
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
    
    def _extract_stm32_device_summary(
        self,
        table: List[List],
        header_row: List,
        voltage_specs: Dict,
        temp_specs: Dict
    ) -> List[Dict]:
        """
        Extract STM32 variants from device summary table (usually on first pages).
        These tables list all part numbers with their memory/package info.
        
        Example table structure:
        | Part number | Flash (KB) | Package | Pins |
        | STM32C071C8 | 64        | LQFP48  | 48   |
        """
        variants = []
        
        # Find column indices
        part_num_idx = None
        package_idx = None
        pins_idx = None
        flash_idx = None
        
        for idx, cell in enumerate(header_row):
            if not cell:
                continue
            cell_lower = str(cell).lower().strip()
            
            if "part" in cell_lower and "number" in cell_lower:
                part_num_idx = idx
            elif "package" in cell_lower:
                package_idx = idx
            elif "pin" in cell_lower:
                pins_idx = idx
            elif "flash" in cell_lower or "memory" in cell_lower:
                flash_idx = idx
        
        # Need at least part number column
        if part_num_idx is None:
            return variants
        
        logger.debug(f"STM32 summary - part_num:{part_num_idx}, package:{package_idx}, pins:{pins_idx}")
        
        # Process data rows
        for row in table[1:]:
            if not row or len(row) <= part_num_idx:
                continue
            
            part_number = self._get_cell_value(row, part_num_idx)
            if not part_number or not part_number.strip():
                continue
            
            # Skip header-like rows
            if "part" in part_number.lower() and "number" in part_number.lower():
                continue
            
            # Clean and validate part number
            part_number = self._clean_part_number(part_number)
            if not part_number or len(part_number) < 5:
                continue
            
            # Split if multiple part numbers in one cell (comma or space separated)
            # Example: "STM32C071C8, STM32C071R8" -> ["STM32C071C8", "STM32C071R8"]
            part_numbers = re.split(r'[,\s]+', part_number)
            
            for pn in part_numbers:
                pn = pn.strip()
                if len(pn) < 5:  # Skip short fragments
                    continue
                
                # Extract package and pins
                package_type = self._get_cell_value(row, package_idx) if package_idx is not None else None
                pin_count = None
                
                if pins_idx is not None:
                    pin_val = self._get_cell_value(row, pins_idx)
                    if pin_val:
                        match = re.search(r'(\d+)', pin_val)
                        if match:
                            pin_count = int(match.group(1))
                
                # Try to extract pin count from package name if not found
                if pin_count is None and package_type:
                    match = re.search(r'(\d+)', package_type)
                    if match:
                        pin_count = int(match.group(1))
                
                # Extract flash size if available
                flash_size = None
                if flash_idx is not None:
                    flash_val = self._get_cell_value(row, flash_idx)
                    if flash_val:
                        match = re.search(r'(\d+)', flash_val)
                        if match:
                            flash_size = int(match.group(1))
                
                # Create variant entry
                variant = {
                    "part_number": pn,
                    "manufacturer": "STM",
                    "pin_count": pin_count or 0,
                    "package_type": package_type,
                    "description": f"STM {pn}" + (f" - {package_type}" if package_type else ""),
                    "voltage_min": voltage_specs.get("voltage_min"),
                    "voltage_max": voltage_specs.get("voltage_max"),
                    "operating_temp_min": temp_specs.get("operating_temp_min"),
                    "operating_temp_max": temp_specs.get("operating_temp_max"),
                    "dimension_length": None,
                    "dimension_width": None,
                    "dimension_height": None,
                    "electrical_specs": {
                        "flash_kb": flash_size,
                    }
                }
                
                variants.append(variant)
        
        return variants
    
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
            
            # Extract part number/order code
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
            
            # Extract temperature grade if available
            temp_grade = self._get_cell_value(row, col_indices.get("temp_grade"))
            temp_override = self._parse_temperature_grade(temp_grade) if temp_grade else {}
            
            # Extract packing/marking info
            packing = self._get_cell_value(row, col_indices.get("packing"))
            marking = self._get_cell_value(row, col_indices.get("marking"))
            
            # Create IC specification entry with voltage and temp specs
            variant = {
                "part_number": part_number,
                "manufacturer": "STM",
                "pin_count": pins or 0,
                "package_type": package_type or None,
                "description": f"STM {part_number} - {package_type or 'Unknown Package'}",
                "voltage_min": voltage_specs.get("voltage_min"),
                "voltage_max": voltage_specs.get("voltage_max"),
                "operating_temp_min": temp_override.get("operating_temp_min") or temp_specs.get("operating_temp_min"),
                "operating_temp_max": temp_override.get("operating_temp_max") or temp_specs.get("operating_temp_max"),
                "dimension_length": None,
                "dimension_width": None,
                "dimension_height": None,
                "electrical_specs": {
                    "packing": packing,
                    "marking": marking,
                    "temperature_grade": temp_grade,
                }
            }
            
            variants.append(variant)
        
        return variants
    
    def _find_column_indices(self, header_row: List) -> Dict[str, int]:
        """
        Find column indices for key fields in the table.
        STM datasheets typically use "Order code", "Package", "Packing" columns.
        """
        indices = {}
        
        for idx, cell in enumerate(header_row):
            if not cell:
                continue
            
            cell_lower = str(cell).lower().strip()
            
            # Part number/Order code column - be very flexible
            if any(keyword in cell_lower for keyword in [
                "order code", "order_code", "ordercode",
                "part number", "part_number", "partnumber",
                "type", "device", "sales type"
            ]) and "part_number" not in indices:
                indices["part_number"] = idx
                logger.debug(f"Found part_number column at index {idx}: '{cell}'")
            
            # Package column
            if "package" in cell_lower and "package" not in indices:
                indices["package"] = idx
                logger.debug(f"Found package column at index {idx}: '{cell}'")
            
            # Pins column
            if "pin" in cell_lower and "pins" not in indices:
                indices["pins"] = idx
                logger.debug(f"Found pins column at index {idx}: '{cell}'")
            
            # Temperature grade/range column
            if any(keyword in cell_lower for keyword in [
                "temp", "temperature grade", "temperature range", "grade"
            ]) and "temp_grade" not in indices:
                indices["temp_grade"] = idx
                logger.debug(f"Found temp_grade column at index {idx}: '{cell}'")
            
            # Packing column
            if "packing" in cell_lower and "packing" not in indices:
                indices["packing"] = idx
                logger.debug(f"Found packing column at index {idx}: '{cell}'")
            
            # Marking column
            if "marking" in cell_lower and "marking" not in indices:
                indices["marking"] = idx
                logger.debug(f"Found marking column at index {idx}: '{cell}'")
        
        logger.debug(f"Column indices found: {indices}")
        return indices
    
    def _get_cell_value(self, row: List, col_index: Optional[int]) -> Optional[str]:
        """Get cell value from row, handling None indices and sparse tables.
        
        STM PDFs often have merged cells, so we look for non-None values
        around col_index. The header might be offset from actual data due to
        merged cells, so we check both before and after the index.
        """
        if col_index is None or col_index >= len(row):
            return None
        
        # First try the exact column
        value = row[col_index]
        if value and str(value).strip():
            return str(value).strip()
        
        # Check one column before (header might be offset by 1)
        if col_index > 0:
            value = row[col_index - 1]
            if value and str(value).strip():
                return str(value).strip()
        
        # If still None, check next few columns for merged cell data (up to 3 columns ahead)
        for offset in range(1, 4):
            if col_index + offset < len(row):
                value = row[col_index + offset]
                if value and str(value).strip():
                    return str(value).strip()
        
        return None
    
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
        
        # Try to extract from package name (e.g., "SO8", "TSSOP8", "DIP14")
        for cell in row:
            if cell:
                cell_str = str(cell).upper()
                # Look for patterns like SO8, SOIC8, TSSOP8, DIP14, etc.
                match = re.search(r'(SO|SOIC|TSSOP|DIP|QFP|LQFP|SSOP|MSOP|VSSOP)(\d+)', cell_str)
                if match:
                    try:
                        return int(match.group(2))
                    except ValueError:
                        pass
        
        return None
    
    def _parse_temperature_grade(self, temp_grade: str) -> Dict:
        """
        Parse temperature grade codes like '0 to 70°C', 'Industrial', 'Automotive'.
        Common STM temperature grades:
        - Commercial: 0°C to 70°C
        - Industrial: -40°C to 85°C
        - Automotive: -40°C to 125°C or -40°C to 150°C
        """
        if not temp_grade:
            return {}
        
        temp_grade_lower = temp_grade.lower()
        
        # Direct range extraction
        temp_range = self._extract_temperature_range(temp_grade)
        if temp_range:
            return temp_range
        
        # Named grades
        if "commercial" in temp_grade_lower or "0" in temp_grade_lower and "70" in temp_grade_lower:
            return {"operating_temp_min": 0, "operating_temp_max": 70}
        elif "industrial" in temp_grade_lower:
            return {"operating_temp_min": -40, "operating_temp_max": 85}
        elif "automotive" in temp_grade_lower:
            # Default automotive range
            return {"operating_temp_min": -40, "operating_temp_max": 125}
        elif "extended" in temp_grade_lower:
            return {"operating_temp_min": -40, "operating_temp_max": 125}
        
        return {}
    
    def _create_basic_entry(self, pdf_path: Path, voltage_specs: Dict, temp_specs: Dict) -> Dict:
        """Create a basic entry when no table data is found."""
        part_number = pdf_path.stem.upper()
        
        return {
            "part_number": part_number,
            "manufacturer": "STM",
            "pin_count": 0,
            "package_type": None,
            "description": f"STM {part_number}",
            "voltage_min": voltage_specs.get("voltage_min"),
            "voltage_max": voltage_specs.get("voltage_max"),
            "operating_temp_min": temp_specs.get("operating_temp_min"),
            "operating_temp_max": temp_specs.get("operating_temp_max"),
            "dimension_length": None,
            "dimension_width": None,
            "dimension_height": None,
            "electrical_specs": {},
        }

