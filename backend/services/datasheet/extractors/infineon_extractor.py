"""
Infineon Technologies PDF datasheet extractor.
Extracts IC specification data from Infineon PDF datasheets using regex-based text parsing.
Supports XMC series microcontrollers and other Infineon products.
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


class InfineonExtractor(DatasheetExtractor):
    """Extractor for Infineon Technologies PDF datasheets."""

    # Infineon part number patterns
    # XMC series: XMC1100-T016F0008, XMC1100-Q024F0016, etc.
    # Format: XMC<DDD>-<Z><PPP><T><FFFF>
    PART_NUMBER_PATTERNS = [
        # XMC1000/2000/4000 series microcontrollers
        r'\b(XMC\d{4}-[TQ]\d{3}[FX]\d{4})\b',
        # Generic XMC pattern (less specific)
        r'\b(XMC\d{4}[A-Z0-9\-]+)\b',
        # IFX series
        r'\b(IFX\d{4,5}[A-Z]*\d*)\b',
        # TLE series (automotive)
        r'\b(TLE\d{4,5}[A-Z]*)\b',
        # IRF/IRFP series (power MOSFETs)
        r'\b(IRF[PZ]?\d{3,4}[A-Z]*)\b',
        # BTS series (smart switches)
        r'\b(BTS\d{3,5}[A-Z]*)\b',
    ]

    # Package type patterns with pin counts
    PACKAGE_PATTERNS = [
        (r'\bPG-TSSOP-(\d+)-\d+\b', 'TSSOP'),
        (r'\bPG-VQFN-(\d+)-\d+\b', 'VQFN'),
        (r'\bTSSOP-?(\d+)\b', 'TSSOP'),
        (r'\bVQFN-?(\d+)\b', 'VQFN'),
        (r'\bQFN-?(\d+)\b', 'QFN'),
        (r'\bLQFP-?(\d+)\b', 'LQFP'),
        (r'\bBGA-?(\d+)\b', 'BGA'),
        (r'\bSOIC-?(\d+)\b', 'SOIC'),
        (r'\bTO-?(\d+)\b', 'TO'),
        (r'(\d+)[\s-]?(?:pin|lead)s?\b', None),
    ]

    # XMC package to pin count mapping from datasheet
    XMC_PACKAGE_PIN_MAP = {
        'T016': ('TSSOP', 16),
        'T038': ('TSSOP', 38),
        'Q024': ('VQFN', 24),
        'Q040': ('VQFN', 40),
    }

    # Temperature range mapping
    TEMP_RANGE_MAP = {
        'F': (-40.0, 85.0),   # Industrial
        'X': (-40.0, 105.0),  # Extended
    }

    def extract(self, pdf_path: Path) -> List[Dict]:
        """
        Extract IC specification data from Infineon PDF datasheet.

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
            logger.debug(f"Extracting data from Infineon PDF: {pdf_path}")

            with pdfplumber.open(pdf_path) as pdf:
                # Extract text from first 15 pages (device info usually in first pages)
                full_text = self._extract_text_from_pages(pdf, max_pages=15)

                # Extract dimension pages
                dimension_text = self._extract_dimension_pages(pdf)

                # Extract voltage specs
                voltage_specs = self._extract_voltage_from_text(full_text)

                # Extract dimension specs
                dimension_specs = self._extract_dimensions_from_text(dimension_text)

                # Extract variants from device types table
                ic_variants = self._extract_variants_from_text(full_text, voltage_specs, dimension_specs)

            if not ic_variants:
                logger.debug(f"No IC variants found in PDF: {pdf_path}")
                return [self._create_basic_entry(pdf_path, voltage_specs)]

            logger.info(f"Extracted {len(ic_variants)} IC variants from Infineon PDF")
            return ic_variants

        except Exception as e:
            logger.error(f"Failed to extract data from Infineon PDF {pdf_path}: {e}")
            raise DatasheetExtractionException(
                f"Failed to extract data from Infineon PDF: {str(e)}"
            )

    def _extract_text_from_pages(self, pdf, max_pages: int = 15) -> str:
        """Extract text from first N pages of PDF."""
        text_parts = []
        for i, page in enumerate(pdf.pages):
            if i >= max_pages:
                break
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)

    def _extract_dimension_pages(self, pdf) -> str:
        """Extract text from pages containing package dimensions."""
        text_parts = []
        for i in range(max(0, len(pdf.pages) - 15), len(pdf.pages)):
            page_text = pdf.pages[i].extract_text()
            if page_text and any(kw in page_text.lower() for kw in
                ['package outline', 'package dimension', 'mechanical', 'outline dimension', 'body size']):
                text_parts.append(page_text)
        return "\n".join(text_parts)

    def _extract_dimensions_from_text(self, text: str) -> Dict[str, Dict]:
        """
        Extract package dimensions from PDF text.

        Returns:
            Dictionary mapping package type to dimensions
        """
        dimensions = {}

        # Pattern for package dimensions like "TSSOP16 - 4.4 × 5.0 mm"
        pkg_dim_pattern = r'\b([A-Z]{2,6})[\-]?(\d+)\b[^\n]*?(\d+\.?\d*)\s*[×xX]\s*(\d+\.?\d*)\s*mm'
        for match in re.finditer(pkg_dim_pattern, text, re.IGNORECASE):
            try:
                pkg_type = match.group(1).upper()
                pin_count = int(match.group(2))
                length = float(match.group(3))
                width = float(match.group(4))

                if 1.0 <= length <= 50.0 and 1.0 <= width <= 50.0:
                    package_key = f"{pkg_type}-{pin_count}"
                    if package_key not in dimensions:
                        dimensions[package_key] = {
                            "length": length,
                            "width": width,
                            "height": None
                        }
                        logger.debug(f"Found dimensions for {package_key}: {length}x{width} mm")
            except (ValueError, IndexError):
                continue

        return dimensions

    def _extract_voltage_from_text(self, text: str) -> Dict:
        """Extract voltage specs from PDF text."""
        voltage_specs = {}

        patterns = [
            # VDDP range pattern (common in Infineon datasheets)
            r'V[Dd][Dd][Pp]?\s*(?:SR)?\s*(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*V',
            # Digital supply voltage
            r'[Dd]igital\s+supply\s+voltage[^\d]*(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*V',
            # Supply voltage range
            r'[Ss]upply\s+[Vv]oltage[^\d]*(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*V',
            # Operating voltage
            r'[Oo]perating\s+[Vv]oltage[^\d]*(\d+\.?\d*)\s*[-–]\s*(\d+\.?\d*)\s*V',
            # VDD range
            r'V[Dd][Dd]\s*[=:]\s*(\d+\.?\d*)\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    min_v = float(match.group(1))
                    max_v = float(match.group(2))
                    # Sanity check
                    if 0.5 <= min_v <= 10.0 and 0.5 <= max_v <= 10.0 and min_v < max_v:
                        voltage_specs = {"voltage_min": min_v, "voltage_max": max_v}
                        logger.debug(f"Found voltage range: {min_v}V to {max_v}V")
                        break
                except (ValueError, IndexError):
                    continue

        return voltage_specs

    def _extract_variants_from_text(
        self,
        text: str,
        voltage_specs: Dict,
        dimension_specs: Optional[Dict[str, Dict]] = None
    ) -> List[Dict]:
        """Extract IC variants from text using regex patterns."""
        variants = []
        seen_parts = set()
        dimension_specs = dimension_specs or {}

        # Find device types section (Table 1 in XMC datasheets)
        device_section = self._find_device_types_section(text)
        # Use more text for search - device types often in first 15000 chars
        search_text = device_section if device_section else text[:15000]

        # Extract XMC-style part numbers with full decoding
        xmc_variants = self._extract_xmc_variants(search_text, voltage_specs, dimension_specs)
        for v in xmc_variants:
            if v["part_number"] not in seen_parts:
                seen_parts.add(v["part_number"])
                variants.append(v)

        # If no XMC variants found, try generic patterns
        if not variants:
            for pattern in self.PART_NUMBER_PATTERNS:
                matches = re.finditer(pattern, search_text, re.IGNORECASE)
                for match in matches:
                    part_number = match.group(1).upper()

                    if part_number in seen_parts or len(part_number) < 5:
                        continue

                    # Skip false positives
                    if part_number in ['TABLE', 'DEVICE', 'PACKAGE', 'FIGURE']:
                        continue

                    seen_parts.add(part_number)

                    # Get context for package info
                    start = max(0, match.start() - 10)
                    end = min(len(search_text), match.end() + 200)
                    context = search_text[start:end]

                    package_type, pin_count = self._extract_package_from_context(context)

                    # Look up dimensions
                    dim_length = None
                    dim_width = None
                    dim_height = None

                    if package_type and dimension_specs:
                        if package_type in dimension_specs:
                            dims = dimension_specs[package_type]
                            dim_length = dims.get("length")
                            dim_width = dims.get("width")
                            dim_height = dims.get("height")

                    variant = {
                        "part_number": part_number,
                        "manufacturer": "INFINEON",
                        "pin_count": pin_count or 0,
                        "package_type": package_type,
                        "description": f"Infineon {part_number}" + (f" - {package_type}" if package_type else ""),
                        "voltage_min": voltage_specs.get("voltage_min"),
                        "voltage_max": voltage_specs.get("voltage_max"),
                        "operating_temp_min": None,
                        "operating_temp_max": None,
                        "dimension_length": dim_length,
                        "dimension_width": dim_width,
                        "dimension_height": dim_height,
                        "electrical_specs": {}
                    }
                    variants.append(variant)

        return variants

    def _extract_xmc_variants(self, text: str, voltage_specs: Dict, dimension_specs: Optional[Dict[str, Dict]] = None) -> List[Dict]:
        """
        Extract XMC series variants with decoded package and temperature info.
        XMC format: XMC<DDD>-<Z><PPP><T><FFFF>
        - DDD: derivative (e.g., 1100)
        - Z: package (T=TSSOP, Q=VQFN)
        - PPP: pin count (016, 024, 038, 040)
        - T: temp range (F=-40 to 85°C, X=-40 to 105°C)
        - FFFF: flash size in KB
        """
        variants = []
        dimension_specs = dimension_specs or {}

        # Pattern for XMC part numbers with full format
        xmc_pattern = r'\b(XMC\d{4})-([TQ])(\d{3})([FX])(\d{4})\b'

        matches = re.finditer(xmc_pattern, text, re.IGNORECASE)
        seen = set()

        for match in matches:
            base = match.group(1).upper()
            pkg_code = match.group(2).upper()
            pin_code = match.group(3)
            temp_code = match.group(4).upper()
            flash_code = match.group(5)

            part_number = f"{base}-{pkg_code}{pin_code}{temp_code}{flash_code}"

            if part_number in seen:
                continue
            seen.add(part_number)

            # Decode package type
            pkg_key = f"{pkg_code}{pin_code}"
            if pkg_key in self.XMC_PACKAGE_PIN_MAP:
                package_type, pin_count = self.XMC_PACKAGE_PIN_MAP[pkg_key]
                package_type = f"PG-{package_type}-{pin_count}"
            else:
                package_type = "TSSOP" if pkg_code == 'T' else "VQFN"
                try:
                    pin_count = int(pin_code)
                except ValueError:
                    pin_count = 0

            # Decode temperature range
            temp_min, temp_max = self.TEMP_RANGE_MAP.get(temp_code, (-40.0, 85.0))

            # Decode flash size
            try:
                flash_kb = int(flash_code)
            except ValueError:
                flash_kb = 0

            # Look up dimensions
            dim_length = None
            dim_width = None
            dim_height = None

            if package_type and dimension_specs:
                if package_type in dimension_specs:
                    dims = dimension_specs[package_type]
                    dim_length = dims.get("length")
                    dim_width = dims.get("width")
                    dim_height = dims.get("height")

            description = f"Infineon {base} Microcontroller, {flash_kb}KB Flash, {package_type}"

            variant = {
                "part_number": part_number,
                "manufacturer": "INFINEON",
                "pin_count": pin_count,
                "package_type": package_type,
                "description": description,
                "voltage_min": voltage_specs.get("voltage_min", 1.8),
                "voltage_max": voltage_specs.get("voltage_max", 5.5),
                "operating_temp_min": temp_min,
                "operating_temp_max": temp_max,
                "dimension_length": dim_length,
                "dimension_width": dim_width,
                "dimension_height": dim_height,
                "electrical_specs": {
                    "flash_kb": flash_kb,
                    "sram_kb": 16,  # XMC1100 has 16KB SRAM
                }
            }
            variants.append(variant)

        return variants

    def _find_device_types_section(self, text: str) -> Optional[str]:
        """Find and extract the device types section from text."""
        patterns = [
            # Match "Table N Synopsis of XMC..." and capture following content
            r'(Table\s+\d+\s+Synopsis\s+of\s+XMC\d+\s+Device\s+Types.{500,5000})',
            # Match "Derivative Package Flash" table header
            r'(Derivative\s+Package\s+Flash.{500,5000})',
            r'(?:Ordering\s+Information)(.{500,3000})',
            r'(?:Available\s+Derivatives)(.{500,3000})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                logger.debug(f"Found device types section")
                return match.group(0)

        return None

    def _extract_package_from_context(self, context: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract package type and pin count from text context."""
        package_type = None
        pin_count = None

        for pattern, pkg_name in self.PACKAGE_PATTERNS:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                if pkg_name:
                    try:
                        pin_count = int(match.group(1))
                        package_type = f"{pkg_name}-{pin_count}"
                    except (ValueError, IndexError):
                        package_type = pkg_name
                else:
                    try:
                        pin_count = int(match.group(1))
                    except (ValueError, IndexError):
                        pass
                break

        return package_type, pin_count

    def _create_basic_entry(self, pdf_path: Path, voltage_specs: Dict) -> Dict:
        """Create a basic entry when no detailed data is found."""
        # Try to extract part number from filename
        filename = pdf_path.stem.upper()

        # Remove common prefixes
        for prefix in ["INFINEON_", "INFINEON-", "IFX_", "IFX-"]:
            if filename.startswith(prefix):
                filename = filename[len(prefix):]
                break

        # Try to find XMC or other Infineon pattern in filename
        part_match = re.search(r'(XMC\d{4}[A-Z0-9\-]*)', filename)
        if part_match:
            part_number = part_match.group(1)
        else:
            part_number = filename.split('_')[0].split('-')[0]

        return {
            "part_number": part_number,
            "manufacturer": "INFINEON",
            "pin_count": 0,
            "package_type": None,
            "description": f"Infineon {part_number}",
            "voltage_min": voltage_specs.get("voltage_min"),
            "voltage_max": voltage_specs.get("voltage_max"),
            "operating_temp_min": None,
            "operating_temp_max": None,
            "dimension_length": None,
            "dimension_width": None,
            "dimension_height": None,
            "electrical_specs": {},
        }
