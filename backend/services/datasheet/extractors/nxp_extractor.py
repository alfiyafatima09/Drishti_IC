"""
NXP Semiconductors PDF datasheet extractor.
Extracts IC specification data from NXP PDF datasheets using regex-based text parsing.
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


class NXPExtractor(DatasheetExtractor):
    """Extractor for NXP Semiconductors PDF datasheets using regex-based text parsing."""

    # Common NXP part number patterns (more specific first)
    PART_NUMBER_PATTERNS = [
        # P89LPC series with package suffix: P89LPC920FDH, P89LPC921FDH, etc.
        r'\b(P89LPC\d{3,4}[A-Z]{2,3})\b',
        # LPC series: LPC1768, LPC1114, LPC55S69, etc.
        r'\b(LPC\d{2,4}[A-Z]?\d*[A-Z]*)\b',
        # S32K series: S32K144, S32K148, etc.
        r'\b(S32K\d{3}[A-Z]*)\b',
        # i.MX series: i.MX6, i.MX8, MIMX8, etc.
        r'\b(i\.?MX\d+[A-Z]*\d*[A-Z]*)\b',
        r'\b(MIMX\d+[A-Z]*)\b',
        # MC series: MC9S08, MC56F, etc.
        r'\b(MC\d{1,2}[A-Z]\d+[A-Z]*)\b',
        # MK series: MKL25Z, MK64F, etc.
        r'\b(MK[A-Z]?\d+[A-Z]+\d*)\b',
    ]

    # Package code patterns to exclude from part numbers
    PACKAGE_CODES = {'SOT', 'DIP', 'TSSOP', 'SOIC', 'QFP', 'LQFP', 'QFN', 'BGA', 'SSOP', 'MSOP'}

    # Package patterns with pin counts
    PACKAGE_PATTERNS = [
        (r'\b(TSSOP)(\d+)\b', 'TSSOP'),
        (r'\b(DIP)(\d+)\b', 'DIP'),
        (r'\b(SOIC)(\d+)\b', 'SOIC'),
        (r'\b(QFP)(\d+)\b', 'QFP'),
        (r'\b(LQFP)(\d+)\b', 'LQFP'),
        (r'\b(QFN)(\d+)\b', 'QFN'),
        (r'\b(HVQFN)(\d+)\b', 'HVQFN'),
        (r'\b(VQFN)(\d+)\b', 'VQFN'),
        (r'\b(BGA)(\d+)\b', 'BGA'),
        (r'\b(LFBGA)(\d+)\b', 'LFBGA'),
        (r'\b(SSOP)(\d+)\b', 'SSOP'),
        (r'\b(MSOP)(\d+)\b', 'MSOP'),
        (r'\b(SO)(\d+)\b', 'SO'),
        # Pattern for "20-pin TSSOP" or "20 leads"
        (r'(\d+)[\s-]?(?:pin|lead)', None),
    ]

    def extract(self, pdf_path: Path) -> List[Dict]:
        """
        Extract IC specification data from NXP PDF datasheet using regex text parsing.

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
            logger.debug(f"Extracting data from NXP PDF: {pdf_path}")

            # Extract all text from PDF
            full_text = self._extract_full_text(pdf_path)

            if not full_text:
                logger.warning(f"No text extracted from PDF: {pdf_path}")
                return [self._create_basic_entry(pdf_path, {}, {})]

            # Extract operating conditions (voltage, temperature)
            voltage_specs = self._extract_voltage_from_text(full_text)
            temp_specs = self._extract_temperature_from_text(full_text)

            logger.debug(f"Extracted voltage specs: {voltage_specs}")
            logger.debug(f"Extracted temp specs: {temp_specs}")

            # Extract IC variants from ordering information section
            ic_variants = self._extract_variants_from_text(full_text, voltage_specs, temp_specs)

            if not ic_variants:
                logger.debug(f"No IC variants found via regex, creating basic entry")
                return [self._create_basic_entry(pdf_path, voltage_specs, temp_specs)]

            logger.info(f"Extracted {len(ic_variants)} IC variants from NXP PDF")
            return ic_variants

        except Exception as e:
            logger.error(f"Failed to extract data from NXP PDF {pdf_path}: {e}")
            raise DatasheetExtractionException(
                f"Failed to extract data from NXP PDF: {str(e)}"
            )

    def _extract_full_text(self, pdf_path: Path) -> str:
        """Extract all text from PDF."""
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
        return "\n".join(text_parts)

    def _extract_voltage_from_text(self, text: str) -> Dict:
        """
        Extract voltage specs from full PDF text using regex.
        Looks for patterns like:
        - VDD = 2.4V to 3.6V
        - Supply voltage: 2.4 to 3.6 V
        - Vcc/Vdd: 2.95V ~ 5.5V
        """
        voltage_specs = {}

        # Pattern 1: "VDD = X.X V to Y.Y V" or "VDD = X.XV to Y.YV"
        patterns = [
            # VDD/VCC followed by range
            r'V[Dd][Dd]\s*[=:]\s*(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            r'V[Cc][Cc]\s*[=:]\s*(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # Supply voltage range
            r'[Ss]upply\s+[Vv]oltage[:\s]+(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # Operating voltage
            r'[Oo]perating\s+[Vv]oltage[:\s]+(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # Voltage range in specs (e.g., "2.4V ~ 3.6V")
            r'(\d+\.?\d*)\s*V\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V(?:\s|$|,)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    min_v = float(match.group(1))
                    max_v = float(match.group(2))
                    # Sanity check: voltage should be between 1V and 60V
                    if 1.0 <= min_v <= 60.0 and 1.0 <= max_v <= 60.0 and min_v < max_v:
                        voltage_specs = {"voltage_min": min_v, "voltage_max": max_v}
                        logger.debug(f"Found voltage range: {min_v}V to {max_v}V")
                        break
                except (ValueError, IndexError):
                    continue

        return voltage_specs

    def _extract_temperature_from_text(self, text: str) -> Dict:
        """
        Extract temperature specs from full PDF text using regex.
        Looks for patterns like:
        - -40°C to +85°C
        - Operating temperature: -40 to 85°C
        - Tamb = -40°C to +85°C
        - -40(cid:176)C to +85(cid:176)C (PDF encoding issue)
        """
        temp_specs = {}

        # Normalize common PDF encoding issues for degree symbol
        # (cid:176) is a common encoding for ° in some PDFs
        normalized_text = text.replace('(cid:176)', '°')

        patterns = [
            # Pattern for "- 40°C to +85°C" with various separators (common in NXP datasheets)
            r'[-–]\s*(\d+)\s*°?\s*C?\s*to\s*\+?(\d+)\s*°?\s*C',
            # Temperature range with degree symbol
            r'(-?\d+)\s*°?\s*C\s*(?:to|[-–~])\s*\+?(\d+)\s*°?\s*C',
            # Operating/ambient temperature
            r'[Oo]perating\s+[Tt]emperature[:\s]+(-?\d+)\s*(?:°C)?\s*(?:to|[-–~])\s*\+?(\d+)',
            r'[Aa]mbient\s+[Tt]emperature[:\s]+(-?\d+)\s*(?:°C)?\s*(?:to|[-–~])\s*\+?(\d+)',
            r'T[_]?amb[:\s=]+[-–]?\s*(\d+)\s*(?:°C)?\s*(?:to|[-–~])\s*\+?(\d+)',
            # Industrial temperature range pattern (very specific)
            r'[-–]\s*(40)\s*°?\s*C?\s*to\s*\+?(85|125)\s*°?\s*C',
        ]

        for pattern in patterns:
            match = re.search(pattern, normalized_text, re.IGNORECASE)
            if match:
                try:
                    # Handle negative temperature (first group might not have minus sign)
                    min_t_str = match.group(1)
                    min_t = float(min_t_str)
                    # If pattern matched "- 40" without minus in capture group, negate it
                    if min_t > 0 and '- ' + min_t_str in normalized_text:
                        min_t = -min_t
                    max_t = float(match.group(2))
                    # Sanity check: temperature should be reasonable
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
        """
        Extract IC variants from ordering information section using regex.

        Looks for patterns like:
        P89LPC920FDH TSSOP20 plastic thin shrink...
        P89LPC921FDH TSSOP20 plastic thin shrink...
        """
        variants = []
        seen_parts = set()

        # Find the ordering information section
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
                if part_number in ['TABLE', 'FLASH', 'PACKAGE', 'ORDER']:
                    continue

                # Skip if it looks like a package code (e.g., SOT360, DIP20)
                if any(part_number.startswith(pkg) for pkg in self.PACKAGE_CODES):
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
                    "manufacturer": "NXP",
                    "pin_count": pin_count or 0,
                    "package_type": package_type,
                    "description": f"NXP {part_number}" + (f" - {package_type}" if package_type else ""),
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
        # Look for ordering section headers
        patterns = [
            r'(?:ordering\s+information|order\s+information|ordering\s+options)(.{500,3000})',
            r'(?:type\s+number.*?package)(.{200,2000})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(0)

        return None

    def _extract_package_from_context(self, context: str) -> Tuple[Optional[str], Optional[int]]:
        """Extract package type and pin count from text context."""
        package_type = None
        pin_count = None

        # Try package patterns
        for pattern, pkg_name in self.PACKAGE_PATTERNS:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                if pkg_name:
                    # Pattern like TSSOP20
                    package_type = f"{pkg_name}{match.group(2)}"
                    try:
                        pin_count = int(match.group(2))
                    except (ValueError, IndexError):
                        pass
                else:
                    # Pattern like "20-pin"
                    try:
                        pin_count = int(match.group(1))
                    except (ValueError, IndexError):
                        pass
                break

        # Also look for "X leads" pattern
        if not pin_count:
            leads_match = re.search(r'(\d+)\s*leads?', context, re.IGNORECASE)
            if leads_match:
                try:
                    pin_count = int(leads_match.group(1))
                except ValueError:
                    pass

        return package_type, pin_count

    def _create_basic_entry(self, pdf_path: Path, voltage_specs: Dict, temp_specs: Dict) -> Dict:
        """Create a basic entry when no detailed data is found."""
        part_number = pdf_path.stem.upper()

        # Remove manufacturer prefix if present
        for prefix in ["NXP_", "NXP-"]:
            if part_number.startswith(prefix):
                part_number = part_number[len(prefix):]
                break

        return {
            "part_number": part_number,
            "manufacturer": "NXP",
            "pin_count": 0,
            "package_type": None,
            "description": f"NXP {part_number}",
            "voltage_min": voltage_specs.get("voltage_min"),
            "voltage_max": voltage_specs.get("voltage_max"),
            "operating_temp_min": temp_specs.get("operating_temp_min"),
            "operating_temp_max": temp_specs.get("operating_temp_max"),
            "dimension_length": None,
            "dimension_width": None,
            "dimension_height": None,
            "electrical_specs": {},
        }
