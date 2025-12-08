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

    # TI Package Drawing code to package type mapping
    PACKAGE_DRAWING_MAP = {
        'D': 'SOIC',
        'DB': 'SSOP',
        'PW': 'TSSOP',
        'NS': 'SOP',
        'N': 'PDIP',
        'P': 'PDIP',
        'RTE': 'WQFN',
        'RGE': 'VQFN',
        'RSE': 'VQFN',
        'DGK': 'MSOP',
        'DGS': 'MSOP',
        'DCU': 'SOT',
        'DBV': 'SOT',
        'FK': 'LCCC',
        'W': 'CFP',
        'J': 'CDIP',
    }

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
            package_outline_dims = {}  # Package drawing code -> dimensions

            with pdfplumber.open(pdf_path) as pdf:
                # First pass: Extract voltage and temperature specs from "Recommended Operating Conditions"
                voltage_specs, temp_specs = self._extract_operating_conditions(pdf)

                # Second pass: Extract package outline dimensions from PACKAGE OUTLINE pages
                package_outline_dims = self._extract_package_outline_dimensions(pdf)
                logger.debug(f"Extracted package outline dimensions: {package_outline_dims}")

                # Third pass: Extract IC variants from package dimension tables
                for page_num, page in enumerate(pdf.pages, 1):
                    tables = page.extract_tables()

                    for table in tables:
                        if not table or len(table) < 2:
                            continue

                        header_row = table[0] if table else []
                        header_text = " ".join(str(cell) if cell else "" for cell in header_row).lower()

                        # Skip PACKAGE MATERIALS / TAPE AND REEL tables - they have reel dimensions, not IC body dims
                        if "reel" in header_text or "spq" in header_text or "a0" in header_text or "b0" in header_text:
                            continue

                        # Check if this is a package dimension table
                        if any(keyword in header_text for keyword in ["device", "package", "pins", "package type", "body size", "package size"]):
                            variants = self._extract_from_table(table, header_row, voltage_specs, temp_specs, package_outline_dims)
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

    def _extract_package_outline_dimensions(self, pdf) -> Dict[str, Dict]:
        """
        Extract package body dimensions from PACKAGE OUTLINE pages.

        TI datasheets have "PACKAGE OUTLINE" sections with actual IC body dimensions,
        separate from "PACKAGE MATERIALS" sections which have tape/reel dimensions.

        The PACKAGE OUTLINE pages typically contain:
        - Package drawing code (e.g., D0014A for SOIC 14-pin)
        - Package type and max height in header (e.g., "SOIC - 1.75 mm max height")
        - Body length and width dimensions in the drawing

        Returns:
            Dict mapping package drawing code to dimensions:
            {
                "D": {"length": 6.0, "width": 3.9, "height": 1.75, "pins": 14},
                "PW": {"length": 6.4, "width": 4.4, "height": 1.2, "pins": 14},
            }
        """
        dimensions = {}

        for page in pdf.pages:
            text = page.extract_text() or ""

            # Skip PACKAGE MATERIALS pages (these have reel dimensions)
            if "TAPE AND REEL" in text or "PACKAGE MATERIALS" in text:
                continue

            # Look for PACKAGE OUTLINE header
            if "PACKAGE OUTLINE" not in text:
                continue

            # Pattern to extract package info from header like:
            # "D0014A SOIC - 1.75 mm max height"
            # "PW0014A TSSOP - 1.2 mm max height"
            # "RTE0016C WQFN - 0.8 mm max height"
            header_pattern = r'([A-Z]+)(\d{4})[A-Z]?\s+([A-Z]+)\s*[-–]\s*(\d+\.?\d*)\s*mm\s*max\s*height'
            header_match = re.search(header_pattern, text, re.IGNORECASE)

            if not header_match:
                continue

            drawing_code = header_match.group(1).upper()  # e.g., "D", "PW", "RTE"
            pin_count = int(header_match.group(2))  # e.g., 14 from "0014"
            package_type = header_match.group(3).upper()  # e.g., "SOIC", "TSSOP"
            max_height = float(header_match.group(4))  # e.g., 1.75

            logger.debug(f"Found PACKAGE OUTLINE: {drawing_code} {package_type} {pin_count}-pin, height={max_height}mm")

            # Extract body dimensions from the outline drawing text
            # TI datasheets show body dimensions in drawings with max/min pairs
            # Body dimensions are SMALLER than overall dimensions (which include leads)
            # Example for D0014A SOIC: body = 6.0x3.9mm, overall = 8.65mm with leads

            length = None
            width = None

            # Extract numbers in order of appearance
            numbers = re.findall(r'(\d+\.?\d+)', text)

            # Convert to floats, filtering reasonable dimension range
            # Exclude common non-dimension numbers (pin counts like 14, 16, 20)
            common_pin_counts = {8, 10, 12, 14, 16, 18, 20, 24, 28, 32, 44, 48, 64}
            float_nums = []
            for n in numbers:
                try:
                    f = float(n)
                    # Dimension range: 2-15mm, exclude exact pin count matches
                    if 2.0 <= f <= 15.0 and int(f) not in common_pin_counts:
                        float_nums.append(f)
                    # Also include if it has decimal part (e.g., 14.5 is valid dimension)
                    elif 2.0 <= f <= 15.0 and f != int(f):
                        float_nums.append(f)
                except ValueError:
                    continue

            # Find ALL valid dimension pairs (max/min with small difference)
            all_pairs = []
            used_indices = set()
            for i in range(len(float_nums)):
                if i in used_indices:
                    continue
                curr = float_nums[i]

                for j in range(i + 1, min(i + 5, len(float_nums))):
                    if j in used_indices:
                        continue
                    next_val = float_nums[j]
                    diff = curr - next_val

                    # Valid max/min pair: difference 0.1-0.8mm
                    if 0.1 <= diff <= 0.8:
                        all_pairs.append((round(curr, 2), i))
                        used_indices.add(i)
                        used_indices.add(j)
                        break

            # Select the two smallest dimension pairs as body dimensions
            # Body dimensions are smaller than overall dimensions
            # Sort pairs by value to get the smallest ones
            all_pairs.sort(key=lambda x: x[0])

            # For SOIC/TSSOP/SSOP: need two different dimensions (length and width)
            if package_type in ['WQFN', 'VQFN', 'QFN']:
                # Square packages - use smallest dimension
                if all_pairs:
                    length = all_pairs[0][0]
                    width = all_pairs[0][0]
            else:
                # Rectangular packages - use two smallest distinct dimensions
                if len(all_pairs) >= 2:
                    # The smaller value is width, larger is length
                    width = all_pairs[0][0]
                    length = all_pairs[1][0]
                    # Ensure length >= width
                    if length < width:
                        length, width = width, length
                elif len(all_pairs) == 1:
                    length = all_pairs[0][0]

            # Store dimensions for this package drawing code
            if drawing_code not in dimensions:
                dimensions[drawing_code] = {
                    "length": length,
                    "width": width,
                    "height": max_height,
                    "pins": pin_count,
                    "package_type": package_type
                }
                logger.debug(f"Package {drawing_code}: {length}x{width}x{max_height}mm, {pin_count} pins")

        return dimensions

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
        temp_specs: Dict,
        package_outline_dims: Optional[Dict[str, Dict]] = None
    ) -> List[Dict]:
        """
        Extract IC variants from a package dimension table.

        Args:
            table: Table data (list of rows)
            header_row: First row containing column headers
            voltage_specs: Voltage specs extracted from operating conditions
            temp_specs: Temperature specs extracted from operating conditions
            package_outline_dims: Package outline dimensions from PACKAGE OUTLINE pages

        Returns:
            List of IC variant dictionaries
        """
        variants = []
        package_outline_dims = package_outline_dims or {}

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
            package_drawing = self._get_cell_value(row, col_indices.get("package_drawing"))

            # If package_type is empty, try to get from package_name or description
            if not package_type and package_name:
                # Package name might be the code (e.g., "D", "P", "DCY")
                package_type = package_name

            # Extract package drawing code from package_type string like "D (SOIC, 14)" or "PW (TSSOP, 14)"
            drawing_code = package_drawing
            if not drawing_code and package_type:
                # Try to extract drawing code from package type string
                drawing_match = re.match(r'^([A-Z]{1,3})\s*[\(\[]', package_type)
                if drawing_match:
                    drawing_code = drawing_match.group(1)

            # If still no drawing code, try extracting from part number
            if not drawing_code:
                drawing_code = self._extract_drawing_code_from_part(device)

            # Extract pin count
            pins = self._extract_pin_count(row, col_indices.get("pins"))

            # Extract dimensions - prioritize PACKAGE OUTLINE data over table columns
            dimension_length = None
            dimension_width = None
            dimension_height = None

            # First try to get dimensions from PACKAGE OUTLINE (actual IC body dimensions)
            if drawing_code and drawing_code in package_outline_dims:
                outline_dims = package_outline_dims[drawing_code]
                dimension_length = outline_dims.get("length")
                dimension_width = outline_dims.get("width")
                dimension_height = outline_dims.get("height")
                logger.debug(f"Using PACKAGE OUTLINE dims for {device} ({drawing_code}): {dimension_length}x{dimension_width}x{dimension_height}mm")

            dimensions = {}

            # If PACKAGE OUTLINE didn't have dimensions, try table columns
            # But skip if we suspect these are reel/tape dimensions
            if dimension_length is None and col_indices.get("length"):
                table_length = self._extract_float(row, col_indices.get("length"))
                # Sanity check: IC body length should be < 25mm typically
                if table_length and table_length < 25:
                    dimension_length = table_length

            if dimension_width is None and col_indices.get("width"):
                table_width = self._extract_float(row, col_indices.get("width"))
                if table_width and table_width < 25:
                    dimension_width = table_width

            # If explicit columns failed, try combined "size" column
            if (dimension_length is None or dimension_width is None) and col_indices.get("size"):
                size_str = self._get_cell_value(row, col_indices.get("size"))
                l, w = self._parse_combined_dimensions(size_str)
                if l is not None and l < 25:
                    dimension_length = l
                if w is not None and w < 25:
                    dimension_width = w

            if dimension_length:
                dimensions["length_mm"] = dimension_length
            if dimension_width:
                dimensions["width_mm"] = dimension_width

            if col_indices.get("thickness"):
                dimensions["thickness_um"] = self._extract_float(row, col_indices.get("thickness"))
            if dimension_height is None and col_indices.get("height"):
                table_height = self._extract_float(row, col_indices.get("height"))
                if table_height and table_height < 10:  # IC height < 10mm
                    dimension_height = table_height
                    dimensions["height_mm"] = dimension_height
            elif dimension_height:
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
                    "package_drawing": drawing_code,
                    "dimensions": dimensions,
                }
            }

            variants.append(variant)

        return variants

    def _extract_drawing_code_from_part(self, part_number: str) -> Optional[str]:
        """
        Extract TI package drawing code from part number.

        TI part numbers typically encode the package type:
        - LM324DR -> D (SOIC)
        - LM324PWR -> PW (TSSOP)
        - LM324N -> N (PDIP)
        - LM324ADBR -> DB (SSOP)

        The pattern is usually: <base part><package code><suffix>
        where suffix is often R (reel), G4 (green), etc.
        """
        if not part_number:
            return None

        part = part_number.upper()

        # Remove common suffixes
        for suffix in ['G4', 'G3', '-Q1', '/NOPB', 'E4']:
            part = part.replace(suffix, '')

        # Try to match known package codes at the end (before R suffix)
        # Order matters - longer codes first
        for code in ['RTE', 'RGE', 'RSE', 'DGK', 'DGS', 'DCU', 'DBV', 'DB', 'PW', 'NS', 'FK', 'D', 'N', 'P', 'W', 'J']:
            # Check if code appears near end of part number
            if part.endswith(code + 'R') or part.endswith(code):
                return code
            # Also check for pattern like LM324DR where D is the package
            if code + 'R' in part[-5:] or (len(code) == 1 and part[-2:-1] == code):
                return code

        return None
    
    def _find_column_indices(self, header_row: List) -> Dict[str, int]:
        """
        Find column indices for key fields in the table.
        Improved matching for dimension columns.
        """
        indices = {}

        for idx, cell in enumerate(header_row):
            if not cell:
                continue

            cell_lower = str(cell).lower().strip()

            # Device/Part number column
            if "device" in cell_lower and "device" not in indices:
                indices["device"] = idx
            elif "part number" in cell_lower and "device" not in indices:
                indices["device"] = idx

            # Package name column
            if ("package name" in cell_lower or "package_name" in cell_lower) and "package_name" not in indices:
                indices["package_name"] = idx

            # Package drawing column (e.g., "Package Drawing" containing D, PW, DB codes)
            if ("package drawing" in cell_lower or "drawing" in cell_lower) and "package_drawing" not in indices:
                indices["package_drawing"] = idx

            # Package type column
            if (("package type" in cell_lower or "package_type" in cell_lower) and "package_type" not in indices):
                indices["package_type"] = idx
            elif ("package" in cell_lower and "name" not in cell_lower and
                  "drawing" not in cell_lower and "size" not in cell_lower and
                  "package_type" not in indices and "package_name" not in indices):
                # Sometimes "Package" column contains the type/code
                indices["package_type"] = idx

            # Pins column
            if "pin" in cell_lower and "pins" not in indices:
                indices["pins"] = idx

            # Dimension columns (explicit)
            if ("length" in cell_lower or cell_lower in ["l", "l (mm)"]) and "length" not in indices:
                indices["length"] = idx
            if ("width" in cell_lower or cell_lower in ["w", "w (mm)"]) and "width" not in indices:
                indices["width"] = idx

            # Combined dimension columns (e.g., "Body Size", "Package Size")
            if (("body size" in cell_lower or "package size" in cell_lower or "body size (nom)" in cell_lower)
                and "size" not in indices):
                indices["size"] = idx

            if ("thickness" in cell_lower or cell_lower in ["t", "t (µm)", "t (um)"]) and "thickness" not in indices:
                indices["thickness"] = idx
            if ("height" in cell_lower or cell_lower in ["b", "b (mm)", "h", "h (mm)"]) and "height" not in indices:
                indices["height"] = idx

        return indices
    
    def _parse_combined_dimensions(self, text: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
        """
        Parse combined dimensions from string like '3.00 mm x 3.00 mm' or '4.90mm x 3.91mm'.
        Returns (length, width) tuple.
        """
        if not text:
            return None, None
            
        # Common patterns:
        # 3.00 mm x 3.00 mm
        # 3.00mm x 3.00mm
        # 3 x 3
        # 4.90mm \u00d7 3.91mm  (using multiplication symbol)
        
        # Normalized regex: Number, optional space, optional unit, space, separator (x, X, *), space, Number
        pattern = r'(\d+\.?\d*)\s*(?:mm)?\s*[\sxX*×]+\s*(\d+\.?\d*)'
        
        match = re.search(pattern, text)
        if match:
            try:
                l = float(match.group(1))
                w = float(match.group(2))
                return l, w
            except ValueError:
                pass
                
        return None, None

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
        # Remove footnotes like (1) or [1] often found in part numbers
        device = re.sub(r'[\(\[\{]\d+[\)\]\}]', '', device)
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
        
        # Remove non-numeric start chars if any, but keep decimal points
        match = re.search(r'(\d+\.?\d*)', str(value))
        if match:
            try:
                return float(match.group(1))
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