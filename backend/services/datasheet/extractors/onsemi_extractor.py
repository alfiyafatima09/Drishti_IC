# """
# OnSemi (onsemi) PDF datasheet extractor.
# Extracts IC specification data from OnSemi PDF datasheets.
# A single PDF can contain multiple IC variants.
# """
# import re
# from pathlib import Path
# from typing import Dict, List, Optional, Tuple

# try:
#     import pdfplumber
#     PDFPLUMBER_AVAILABLE = True
# except ImportError:
#     PDFPLUMBER_AVAILABLE = False

# from .base import DatasheetExtractor
# from ..exceptions import DatasheetExtractionException

# import logging

# logger = logging.getLogger(__name__)


# class OnSemiExtractor(DatasheetExtractor):
#     """Extractor for OnSemi PDF datasheets."""
    
#     def extract(self, pdf_path: Path) -> List[Dict]:
#         """
#         Extract IC specification data from OnSemi PDF datasheet.
#         Extracts all IC variants found in package dimension tables.
        
#         Args:
#             pdf_path: Path to the PDF file
            
#         Returns:
#             List of dictionaries, each containing data for one IC variant
            
#         Raises:
#             DatasheetExtractionException: If extraction fails
#         """
#         if not PDFPLUMBER_AVAILABLE:
#             logger.warning("pdfplumber not available, skipping PDF extraction")
#             return []
        
#         try:
#             logger.debug(f"Extracting data from OnSemi PDF: {pdf_path}")
            
#             ic_variants = []
#             voltage_specs = {}  # Extract once, apply to all variants
#             temp_specs = {}     # Extract once, apply to all variants
            
#             with pdfplumber.open(pdf_path) as pdf:
#                 # First pass: Extract voltage and temperature specs from operating conditions
#                 voltage_specs, temp_specs = self._extract_operating_conditions(pdf)
                
#                 # Second pass: Extract IC variants from package/ordering information tables
#                 for page_num, page in enumerate(pdf.pages, 1):
#                     tables = page.extract_tables()
                    
#                     for table in tables:
#                         if not table or len(table) < 2:
#                             continue
                        
#                         header_row = table[0] if table else []
#                         header_text = " ".join(str(cell) if cell else "" for cell in header_row).lower()
                        
#                         # Check if this is a package/ordering information table
#                         if any(keyword in header_text for keyword in [
#                             "order", "ordering", "part number", "package", 
#                             "device", "ordering information", "marking"
#                         ]):
#                             variants = self._extract_from_table(table, header_row, voltage_specs, temp_specs)
#                             ic_variants.extend(variants)
            
#             if not ic_variants:
#                 logger.debug(f"No IC variants found in PDF: {pdf_path}")
#                 return [self._create_basic_entry(pdf_path, voltage_specs, temp_specs)]
            
#             logger.info(f"Extracted {len(ic_variants)} IC variants from OnSemi PDF")
#             return ic_variants
            
#         except Exception as e:
#             logger.error(f"Failed to extract data from OnSemi PDF {pdf_path}: {e}")
#             raise DatasheetExtractionException(
#                 f"Failed to extract data from OnSemi PDF: {str(e)}"
#             )
    
#     def _extract_operating_conditions(self, pdf) -> Tuple[Dict, Dict]:
#         """
#         Extract voltage and temperature specs from operating conditions tables.
#         Returns once per PDF, applies to all variants.
        
#         Returns:
#             Tuple of (voltage_specs, temp_specs) dictionaries
#         """
#         voltage_specs = {}
#         temp_specs = {}
        
#         for page in pdf.pages:
#             tables = page.extract_tables()
            
#             for table in tables:
#                 if not table or len(table) < 2:
#                     continue
                
#                 header_row = table[0] if table else []
#                 header_text = " ".join(str(cell) if cell else "" for cell in header_row).lower()
                
#                 # Look for operating conditions or electrical characteristics table
#                 if any(keyword in header_text for keyword in [
#                     "operating conditions", "electrical characteristics", 
#                     "absolute maximum ratings", "recommended operating"
#                 ]):
#                     for row in table[1:]:
#                         if not row or len(row) < 2:
#                             continue
                        
#                         # Look for voltage and temperature rows
#                         first_cell = str(row[0] if row[0] else "").lower()
                        
#                         # Extract voltage range
#                         if any(keyword in first_cell for keyword in ["supply voltage", "vcc", "vdd", "voltage"]):
#                             for cell in row[1:]:
#                                 if cell:
#                                     voltage_range = self._extract_voltage_range(str(cell))
#                                     if voltage_range:
#                                         voltage_specs.update(voltage_range)
                        
#                         # Extract temperature range
#                         if "temperature" in first_cell and ("operating" in first_cell or "range" in first_cell):
#                             for cell in row[1:]:
#                                 if cell:
#                                     temp_range = self._extract_temperature_range(str(cell))
#                                     if temp_range:
#                                         temp_specs.update(temp_range)
        
#         return voltage_specs, temp_specs
    
#     def _extract_voltage_range(self, text: str) -> Optional[Dict]:
#         """Extract voltage min/max from text like '3 to 32' or '3V to 32V'."""
#         if not text:
#             return None
        
#         # Pattern: "X to Y" or "X-Y" or "X V to Y V"
#         pattern = r'(\d+\.?\d*)\s*V?\s*(?:to|-|–)\s*(\d+\.?\d*)\s*V?'
#         match = re.search(pattern, text, re.IGNORECASE)
        
#         if match:
#             try:
#                 min_v = float(match.group(1))
#                 max_v = float(match.group(2))
#                 return {"voltage_min": min_v, "voltage_max": max_v}
#             except ValueError:
#                 pass
        
#         # Single value pattern (e.g., "32" for max voltage)
#         pattern_single = r'(\d+\.?\d*)\s*V?'
#         match_single = re.search(pattern_single, text)
#         if match_single:
#             try:
#                 val = float(match_single.group(1))
#                 if val > 1:
#                     return {"voltage_max": val}
#             except ValueError:
#                 pass
        
#         return None
    
#     def _extract_temperature_range(self, text: str) -> Optional[Dict]:
#         """Extract temperature min/max from text like '0 to 70°C' or '-40 to 125'."""
#         if not text:
#             return None
        
#         # Pattern: "X°C to Y°C" or "X to Y"
#         pattern = r'(-?\d+\.?\d*)\s*°?\s*C?\s*(?:to|-|–)\s*(-?\d+\.?\d*)\s*°?\s*C?'
#         match = re.search(pattern, text, re.IGNORECASE)
        
#         if match:
#             try:
#                 min_t = float(match.group(1))
#                 max_t = float(match.group(2))
#                 return {"operating_temp_min": min_t, "operating_temp_max": max_t}
#             except ValueError:
#                 pass
        
#         return None
    
#     def _extract_from_table(
#         self, 
#         table: List[List], 
#         header_row: List,
#         voltage_specs: Dict,
#         temp_specs: Dict
#     ) -> List[Dict]:
#         """
#         Extract IC variants from a package/ordering information table.
        
#         Args:
#             table: Table data (list of rows)
#             header_row: First row containing column headers
#             voltage_specs: Voltage specs extracted from operating conditions
#             temp_specs: Temperature specs extracted from operating conditions
            
#         Returns:
#             List of IC variant dictionaries
#         """
#         variants = []
        
#         # Find column indices
#         col_indices = self._find_column_indices(header_row)
#         if not col_indices:
#             return variants
        
#         # Process data rows (skip header row)
#         for row in table[1:]:
#             if not row or len(row) < 2:
#                 continue
            
#             # Extract part number/device
#             part_number = self._get_cell_value(row, col_indices.get("part_number"))
#             if not part_number or not part_number.strip():
#                 continue
            
#             # Clean part number
#             part_number = self._clean_part_number(part_number)
#             if not part_number:
#                 continue
            
#             # Extract package information
#             package_type = self._get_cell_value(row, col_indices.get("package"))
            
#             # Extract pin count
#             pins = self._extract_pin_count(row, col_indices.get("pins"))
            
#             # Extract marking code
#             marking = self._get_cell_value(row, col_indices.get("marking"))
            
#             # Create IC specification entry with voltage and temp specs
#             variant = {
#                 "part_number": part_number,
#                 "manufacturer": "ONSEMI",
#                 "pin_count": pins or 0,
#                 "package_type": package_type or None,
#                 "description": f"OnSemi {part_number} - {package_type or 'Unknown Package'}",
#                 "voltage_min": voltage_specs.get("voltage_min"),
#                 "voltage_max": voltage_specs.get("voltage_max"),
#                 "operating_temp_min": temp_specs.get("operating_temp_min"),
#                 "operating_temp_max": temp_specs.get("operating_temp_max"),
#                 "dimension_length": None,
#                 "dimension_width": None,
#                 "dimension_height": None,
#                 "electrical_specs": {
#                     "marking": marking,
#                 }
#             }
            
#             variants.append(variant)
        
#         return variants
    
#     def _find_column_indices(self, header_row: List) -> Dict[str, int]:
#         """
#         Find column indices for key fields in the table.
#         OnSemi datasheets typically use "Device", "Package", "Marking" columns.
#         """
#         indices = {}
        
#         for idx, cell in enumerate(header_row):
#             if not cell:
#                 continue
            
#             cell_lower = str(cell).lower().strip()
            
#             # Part number/Device column
#             if any(keyword in cell_lower for keyword in ["device", "part number", "type", "order"]) and "part_number" not in indices:
#                 indices["part_number"] = idx
            
#             # Package column
#             if "package" in cell_lower and "package" not in indices:
#                 indices["package"] = idx
            
#             # Pins column
#             if "pin" in cell_lower and "pins" not in indices:
#                 indices["pins"] = idx
            
#             # Marking column
#             if "marking" in cell_lower and "marking" not in indices:
#                 indices["marking"] = idx
        
#         return indices
    
#     def _get_cell_value(self, row: List, col_index: Optional[int]) -> Optional[str]:
#         """Get cell value from row, handling None indices."""
#         if col_index is None or col_index >= len(row):
#             return None
#         value = row[col_index]
#         return str(value).strip() if value else None
    
#     def _clean_part_number(self, part_number: str) -> str:
#         """Clean and normalize part number."""
#         if not part_number:
#             return ""
#         part_number = " ".join(part_number.split())
#         return part_number.upper().strip()
    
#     def _extract_pin_count(self, row: List, col_index: Optional[int]) -> Optional[int]:
#         """Extract pin count from cell or infer from package name."""
#         # First try dedicated pins column
#         if col_index is not None:
#             value = self._get_cell_value(row, col_index)
#             if value:
#                 match = re.search(r'\d+', str(value))
#                 if match:
#                     try:
#                         return int(match.group())
#                     except ValueError:
#                         pass
        
#         # Try to extract from package name (e.g., "SOIC8", "DIP14", "TO92")
#         for cell in row:
#             if cell:
#                 cell_str = str(cell).upper()
#                 # Look for patterns like SOIC8, DIP14, etc.
#                 match = re.search(r'(SO|SOIC|TSSOP|DIP|QFP|LQFP|SSOP|MSOP|VSSOP|PDIP)(\d+)', cell_str)
#                 if match:
#                     try:
#                         return int(match.group(2))
#                     except ValueError:
#                         pass
        
#         return None
    
#     def _create_basic_entry(self, pdf_path: Path, voltage_specs: Dict, temp_specs: Dict) -> Dict:
#         """Create a basic entry when no table data is found."""
#         part_number = pdf_path.stem.upper()
        
#         return {
#             "part_number": part_number,
#             "manufacturer": "ONSEMI",
#             "pin_count": 0,
#             "package_type": None,
#             "description": f"OnSemi {part_number}",
#             "voltage_min": voltage_specs.get("voltage_min"),
#             "voltage_max": voltage_specs.get("voltage_max"),
#             "operating_temp_min": temp_specs.get("operating_temp_min"),
#             "operating_temp_max": temp_specs.get("operating_temp_max"),
#             "dimension_length": None,
#             "dimension_width": None,
#             "dimension_height": None,
#             "electrical_specs": {},
#         }
"""
ON Semiconductor (onsemi) PDF datasheet extractor.
Extracts IC specification data from onsemi PDF datasheets.
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

# Assuming these imports exist in your project structure
from .base import DatasheetExtractor
from ..exceptions import DatasheetExtractionException

logger = logging.getLogger(__name__)


class OnSemiExtractor(DatasheetExtractor):
    """
    Extractor for ON Semiconductor (onsemi) PDF datasheets.
    Specific focus on parsing "ORDERING INFORMATION" tables where 
    Pin counts are often embedded in the Package Name (e.g., 'SOIC-8 NB').
    """
    
    def extract(self, pdf_path: Path) -> List[Dict]:
        """
        Extract IC specification data from OnSemi PDF datasheet.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            List of dictionaries, each containing data for one IC variant
        """
        if not PDFPLUMBER_AVAILABLE:
            logger.warning("pdfplumber not available, skipping PDF extraction")
            return []
        
        try:
            logger.debug(f"Extracting data from OnSemi PDF: {pdf_path}")
            
            ic_variants = []
            # Extract global specs (Voltage/Temp) usually found in "Maximum Ratings" or "Attributes"
            voltage_specs, temp_specs = self._extract_global_specs(pdf_path)
            
            # Try to find the base part number from the PDF
            base_part_number = self._extract_base_part_number(pdf_path)
            
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    tables = page.extract_tables()
                    
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                        
                        # Normalize header for comparison
                        header_row = table[0]
                        header_text = " ".join(str(cell) if cell else "" for cell in header_row).lower()
                        
                        # Target the "ORDERING INFORMATION" table
                        # This table typically contains: Device | Package | Shipping
                        if "ordering information" in header_text or ("device" in header_text and "package" in header_text and "shipping" in header_text):
                            variants = self._extract_from_ordering_table(
                                table, 
                                header_row, 
                                voltage_specs, 
                                temp_specs
                            )
                            ic_variants.extend(variants)
                        
                        # Also handle "Package | Programming Boards" table format
                        elif "package" in header_text and ("programming" in header_text or "board" in header_text):
                            variants = self._extract_from_package_table(
                                table,
                                header_row,
                                base_part_number,
                                voltage_specs,
                                temp_specs
                            )
                            ic_variants.extend(variants)
            
            # De-duplicate variants (sometimes tables span pages or are repeated)
            unique_variants = {v['part_number']: v for v in ic_variants}.values()
            
            if not unique_variants:
                logger.debug(f"No IC variants found in PDF: {pdf_path}")
                return [self._create_basic_entry(pdf_path, voltage_specs, temp_specs)]
            
            logger.info(f"Extracted {len(unique_variants)} IC variants from OnSemi PDF")
            return list(unique_variants)
            
        except Exception as e:
            logger.error(f"Failed to extract data from OnSemi PDF {pdf_path}: {e}")
            raise DatasheetExtractionException(
                f"Failed to extract data from OnSemi PDF: {str(e)}"
            )

    def _extract_global_specs(self, pdf_path: Path) -> Tuple[Dict, Dict]:
        """
        Scans specific tables (Maximum Ratings, Attributes) to find Voltage and Temp ranges.
        OnSemi often puts these in a "Maximum Ratings" table on Page 2 or 3.
        """
        voltage_specs = {}
        temp_specs = {}
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:5]:  # Check first 5 pages
                text = page.extract_text() or ""
                
                # Look for operating temperature in text
                if 'operating temperature' in text.lower():
                    temp_match = re.search(r'(-?\d+)°?C?\s+to\s+([+-]?\d+)°?C?', text, re.IGNORECASE)
                    if temp_match:
                        temp_specs['operating_temp_min'] = float(temp_match.group(1))
                        temp_specs['operating_temp_max'] = float(temp_match.group(2))
                
                tables = page.extract_tables()
                for table in tables:
                    if not table: continue
                    
                    header_text = " ".join(str(c) for c in table[0]).lower()
                    
                    # 1. Look for Temperature in "Attributes" or "Maximum Ratings"
                    # OnSemi often lists "Operating Temperature Range"
                    if "ratings" in header_text or "attributes" in header_text or "characteristics" in header_text:
                        for row in table:
                            row_text = " ".join(str(c) for c in row).lower()
                            
                            # Extract Temperature
                            if "operating temperature" in row_text or "ambient temperature" in row_text:
                                min_t, max_t = self._parse_min_max(row_text)
                                if min_t is not None: temp_specs['operating_temp_min'] = min_t
                                if max_t is not None: temp_specs['operating_temp_max'] = max_t
                            
                            # Extract Voltage (VCC / VEE)
                            if "power supply" in row_text and "voltage" in row_text:
                                min_v, max_v = self._parse_min_max(row_text)
                                if min_v is not None: voltage_specs['voltage_min'] = min_v
                                if max_v is not None: voltage_specs['voltage_max'] = max_v
                                
        return voltage_specs, temp_specs
    
    def _extract_base_part_number(self, pdf_path: Path) -> Optional[str]:
        """
        Extract the base part number from the PDF (usually on first page).
        For OnSemi, this is often like LC87F7932B, MC34063, etc.
        """
        with pdfplumber.open(pdf_path) as pdf:
            if len(pdf.pages) > 0:
                text = pdf.pages[0].extract_text() or ""
                
                # Look for common OnSemi part number patterns
                # LC87FXXXX, MCXXXXX, NSVXXXXX, etc.
                patterns = [
                    r'(LC87F[0-9A-Z]+)',
                    r'(MC[0-9]{5}[A-Z]*)',
                    r'(NSV[0-9]{4}[A-Z]*)',
                    r'(NCV[0-9]{4,5}[A-Z]*)',
                    r'([A-Z]{2,4}[0-9]{4,5}[A-Z]*)'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, text)
                    if match:
                        part = match.group(1)
                        logger.info(f"Found base part number: {part}")
                        return part
        
        return None

    def _extract_from_ordering_table(
        self, 
        table: List[List], 
        header_row: List, 
        voltage_specs: Dict, 
        temp_specs: Dict
    ) -> List[Dict]:
        """
        Parses the Ordering Information table.
        Columns are usually: Device | Package | Shipping
        """
        variants = []
        
        # Identify columns
        col_indices = self._find_column_indices(header_row)
        if "device" not in col_indices or "package" not in col_indices:
            return variants
            
        for row in table[1:]:
            if not row or len(row) < 2: continue
            
            # 1. Extract Part Number
            part_number = str(row[col_indices["device"]]).strip()
            if not part_number or part_number.lower() == "none": continue
            
            # 2. Extract Package String (e.g., "SOIC-8 NB")
            package_raw = str(row[col_indices["package"]]).strip()
            package_raw = package_raw.replace('\n', ' ') # Fix multiline cells
            
            # 3. Parse Pin Count and Clean Package Type from string
            # This is the key requirement for OnSemi
            package_type, pin_count = self._parse_package_string(package_raw)
            
            variant = {
                "part_number": part_number,
                "manufacturer": "ONSEMI",
                "pin_count": pin_count,
                "package_type": package_type,
                "description": f"OnSemi {part_number} - {package_type}",
                "voltage_min": voltage_specs.get("voltage_min"),
                "voltage_max": voltage_specs.get("voltage_max"),
                "operating_temp_min": temp_specs.get("operating_temp_min"),
                "operating_temp_max": temp_specs.get("operating_temp_max"),
                "dimension_length": None,
                "dimension_width": None,
                "dimension_height": None,
                "electrical_specs": {
                    "raw_package_string": package_raw
                }
            }
            variants.append(variant)
            
        return variants
    
    def _extract_from_package_table(
        self,
        table: List[List],
        header_row: List,
        base_part_number: Optional[str],
        voltage_specs: Dict,
        temp_specs: Dict
    ) -> List[Dict]:
        """
        Extracts IC variants from "Package | Programming Boards" style table.
        Used when the datasheet doesn't have a full ordering table.
        
        Args:
            table: Table data
            header_row: Header row
            base_part_number: Base part number from PDF
            voltage_specs: Voltage specifications
            temp_specs: Temperature specifications
            
        Returns:
            List of IC variant dictionaries
        """
        variants = []
        
        if not base_part_number:
            logger.warning("No base part number found, cannot extract from package table")
            return variants
        
        # Find package column (should be first column)
        package_col = None
        for idx, cell in enumerate(header_row):
            if cell and 'package' in str(cell).lower():
                package_col = idx
                break
        
        if package_col is None:
            logger.warning("No package column found in table")
            return variants
        
        # Process each row to create variants
        for row in table[1:]:  # Skip header
            if not row or len(row) <= package_col:
                continue
            
            package_str = str(row[package_col]).strip()
            if not package_str or package_str.lower() in ['none', 'n/a', '']:
                continue
            
            # Parse package string like "QIP64E (14×14)" or "TQFP64J (7×7)"
            package_type, pin_count = self._parse_package_string(package_str)
            
            # Create part number variant: use base part number
            # e.g., LC87F7932B (base part number applies to all package variants)
            part_number = base_part_number
            
            variant = {
                "part_number": part_number,
                "manufacturer": "ONSEMI",
                "pin_count": pin_count,
                "package_type": package_type,
                "description": f"OnSemi {part_number} - {package_type}",
                "voltage_min": voltage_specs.get("voltage_min"),
                "voltage_max": voltage_specs.get("voltage_max"),
                "operating_temp_min": temp_specs.get("operating_temp_min"),
                "operating_temp_max": temp_specs.get("operating_temp_max"),
                "dimension_length": None,
                "dimension_width": None,
                "dimension_height": None,
                "electrical_specs": {
                    "raw_package_string": package_str
                }
            }
            
            variants.append(variant)
        
        return variants

    def _parse_package_string(self, package_str: str) -> Tuple[str, int]:
        """
        Extracts package type and pin count from strings like:
        "SOIC-8 NB", "TSSOP-8", "DFN-8", "SOIC-8 NB (Pb-Free)"
        
        Returns:
            (package_type, pin_count)
        """
        if not package_str:
            return ("Unknown", 0)
            
        # 1. Try to find the pin count (number attached to package code or isolated)
        # Regex looks for patterns like "-8", " 8", or "8 NB"
        # Common OnSemi patterns: SOIC-8, TSSOP-8, DFN8
        pins = 0
        
        # Look for explicit digit after hyphen or space, often followed by non-digit or end
        # Example match: "-8" in "SOIC-8"
        pin_match = re.search(r'(?:-|−|\s)(\d+)(?:\s|$|[A-Za-z])', package_str)
        
        if pin_match:
            pins = int(pin_match.group(1))
        else:
            # Fallback: look for any sequence of digits inside the string
            # dangerous if package has other numbers, but OnSemi usually strictly formats like "Type-Pin"
            digits = re.findall(r'\d+', package_str)
            if digits:
                # Take the first number found as likely pin count
                pins = int(digits[0])
                
        # 2. Clean up package type (remove Pb-Free notes, etc)
        clean_pkg = package_str
        # Remove (Pb-Free), (Halogen Free), etc.
        clean_pkg = re.sub(r'\(.*?\)', '', clean_pkg)
        # Remove "Suffix" text if present
        clean_pkg = clean_pkg.replace("SUFFIX", "")
        
        return clean_pkg.strip(), pins

    def _find_column_indices(self, header_row: List) -> Dict[str, int]:
        """Find index of Device and Package columns."""
        indices = {}
        for idx, cell in enumerate(header_row):
            if not cell: continue
            text = str(cell).lower()
            
            if "device" in text or "part number" in text:
                indices["device"] = idx
            elif "package" in text:
                indices["package"] = idx
            elif "shipping" in text or "qty" in text:
                indices["shipping"] = idx
                
        return indices

    def _parse_min_max(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Helper to find min/max numbers in text. 
        Matches patterns like "3.0 V to 5.5 V" or "-40 to 85".
        """
        # Find all floats
        nums = re.findall(r'-?\d+\.?\d*', text)
        if len(nums) >= 2:
            try:
                # Assuming first is min, second is max
                vals = [float(n) for n in nums]
                return min(vals), max(vals)
            except ValueError:
                pass
        return None, None

    def _create_basic_entry(self, pdf_path: Path, voltage_specs: Dict, temp_specs: Dict) -> Dict:
        """Fallback entry."""
        return {
            "part_number": pdf_path.stem.upper(),
            "manufacturer": "ONSEMI",
            "pin_count": 0,
            "package_type": "Unknown",
            "description": "Extraction Failed - Manual Review Required",
            "voltage_min": voltage_specs.get("voltage_min"),
            "voltage_max": voltage_specs.get("voltage_max"),
            "operating_temp_min": temp_specs.get("operating_temp_min"),
            "operating_temp_max": temp_specs.get("operating_temp_max"),
            "dimension_length": None,
            "dimension_width": None,
            "dimension_height": None,
            "electrical_specs": {}
        }