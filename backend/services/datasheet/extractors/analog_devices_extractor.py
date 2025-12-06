"""
Analog Devices PDF datasheet extractor.
Extracts IC specification data from Analog Devices PDF datasheets using regex-based text parsing.
Supports ADuC series microconverters, AD series converters, and other Analog Devices products.
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


class AnalogDevicesExtractor(DatasheetExtractor):
    """Extractor for Analog Devices PDF datasheets."""

    # Analog Devices part number patterns
    PART_NUMBER_PATTERNS = [
        # ADuC series microconverters: ADuC7060BCPZ32, ADuC7061BSTZ32-RL, etc.
        r'\b(ADuC\d{4}[A-Z]{1,4}Z?\d*(?:-RL)?)\b',
        # AD series converters: AD7124-8, AD5940, AD9833, etc.
        r'\b(AD\d{4,5}[A-Z]*-?\d*[A-Z]*)\b',
        # ADP series power: ADP5090, ADP1720, etc.
        r'\b(ADP\d{4}[A-Z]*)\b',
        # ADM series interface: ADM3053, ADM485, etc.
        r'\b(ADM\d{3,4}[A-Z]*)\b',
        # ADXL series accelerometers: ADXL345, ADXL355, etc.
        r'\b(ADXL\d{3}[A-Z]*)\b',
        # ADF series RF: ADF4351, ADF7021, etc.
        r'\b(ADF\d{4}[A-Z]*)\b',
        # ADUM series isolators: ADUM1201, ADUM4160, etc.
        r'\b(ADUM\d{4}[A-Z]*)\b',
        # LT series (Linear Tech): LT1234, LTC2000, etc.
        r'\b(LT[C]?\d{4}[A-Z]*)\b',
        # MAX series: MAX232, MAX485, etc. (acquired from Maxim)
        r'\b(MAX\d{3,4}[A-Z]*)\b',
    ]

    # Package patterns with pin counts
    PACKAGE_PATTERNS = [
        (r'\b(\d+)-?[Ll]ead\s+LFCSP\b', 'LFCSP'),
        (r'\b(\d+)-?[Ll]ead\s+LQFP\b', 'LQFP'),
        (r'\b(\d+)-?[Ll]ead\s+TSSOP\b', 'TSSOP'),
        (r'\b(\d+)-?[Ll]ead\s+SOIC\b', 'SOIC'),
        (r'\b(\d+)-?[Ll]ead\s+QFN\b', 'QFN'),
        (r'\b(\d+)-?[Ll]ead\s+MSOP\b', 'MSOP'),
        (r'\b(\d+)-?[Ll]ead\s+WLCSP\b', 'WLCSP'),
        (r'\bLFCSP[_-]?(\d+)\b', 'LFCSP'),
        (r'\bLQFP[_-]?(\d+)\b', 'LQFP'),
        (r'\bTSSOP[_-]?(\d+)\b', 'TSSOP'),
        (r'\bSOIC[_-]?(\d+)\b', 'SOIC'),
        (r'\bQFN[_-]?(\d+)\b', 'QFN'),
        (r'\bCP-(\d+)-\d+\b', 'LFCSP'),  # CP-48-5 = 48-lead LFCSP
        (r'\bST-(\d+)\b', 'LQFP'),  # ST-48 = 48-lead LQFP
        (r'(\d+)[- ]?(?:pin|lead)s?\b', None),
    ]

    # ADuC package code mapping
    ADUC_PACKAGE_MAP = {
        'CPZ': ('LFCSP', None),
        'BCPZ': ('LFCSP', None),
        'STZ': ('LQFP', None),
        'BSTZ': ('LQFP', None),
    }

    def extract(self, pdf_path: Path) -> List[Dict]:
        """
        Extract IC specification data from Analog Devices PDF datasheet.

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
            logger.debug(f"Extracting data from Analog Devices PDF: {pdf_path}")

            with pdfplumber.open(pdf_path) as pdf:
                # Extract text from first and last pages (specs at start, ordering at end)
                full_text = self._extract_text_from_pages(pdf, max_pages=15)

                # Also get ordering guide from last few pages
                ordering_text = self._extract_ordering_guide(pdf)

                # Extract voltage specs
                voltage_specs = self._extract_voltage_from_text(full_text)

                # Extract temperature specs
                temp_specs = self._extract_temperature_from_text(full_text)

                # Extract variants from ordering guide and main text
                ic_variants = self._extract_variants_from_text(
                    full_text + "\n" + ordering_text,
                    voltage_specs,
                    temp_specs
                )

            if not ic_variants:
                logger.debug(f"No IC variants found in PDF: {pdf_path}")
                return [self._create_basic_entry(pdf_path, voltage_specs, temp_specs)]

            logger.info(f"Extracted {len(ic_variants)} IC variants from Analog Devices PDF")
            return ic_variants

        except Exception as e:
            logger.error(f"Failed to extract data from Analog Devices PDF {pdf_path}: {e}")
            raise DatasheetExtractionException(
                f"Failed to extract data from Analog Devices PDF: {str(e)}"
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

    def _extract_ordering_guide(self, pdf) -> str:
        """Extract ordering guide from last few pages."""
        text_parts = []
        # Check last 5 pages for ordering guide
        for i in range(max(0, len(pdf.pages) - 5), len(pdf.pages)):
            page_text = pdf.pages[i].extract_text()
            if page_text and ('ordering' in page_text.lower() or 'order' in page_text.lower()):
                text_parts.append(page_text)
        return "\n".join(text_parts)

    def _extract_voltage_from_text(self, text: str) -> Dict:
        """Extract voltage specs from PDF text."""
        voltage_specs = {}

        patterns = [
            # VDD with tolerance: "VDD = 2.5 V ± 5%" -> 2.375 to 2.625
            r'V[Dd][Dd]\s*[=:]\s*(\d+\.?\d*)\s*V\s*[±]\s*(\d+)%',
            # AVDD/DVDD range
            r'[AD]VDD\s*[=:]\s*(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # Supply voltage range
            r'[Ss]upply\s+[Vv]oltage[^\\d]*(\\d+\\.?\\d*)\\s*V?\\s*(?:to|[-–~])\\s*(\\d+\\.?\\d*)\\s*V',
            # Operating voltage
            r'[Oo]perating\s+[Vv]oltage[^\\d]*(\\d+\\.?\\d*)\\s*V?\\s*(?:to|[-–~])\\s*(\\d+\\.?\\d*)\\s*V',
            # Generic "X.X V to Y.Y V"
            r'(\d+\.?\d*)\s*V\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V(?:\s|,|$)',
        ]

        # First try the VDD with tolerance pattern
        tolerance_match = re.search(patterns[0], text)
        if tolerance_match:
            try:
                vdd = float(tolerance_match.group(1))
                tolerance = float(tolerance_match.group(2)) / 100.0
                voltage_specs = {
                    "voltage_min": round(vdd * (1 - tolerance), 3),
                    "voltage_max": round(vdd * (1 + tolerance), 3)
                }
                logger.debug(f"Found voltage with tolerance: {vdd}V ± {tolerance*100}%")
                return voltage_specs
            except (ValueError, IndexError):
                pass

        # Try other patterns
        for pattern in patterns[1:]:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    min_v = float(match.group(1))
                    max_v = float(match.group(2))
                    # Sanity check
                    if 0.5 <= min_v <= 20.0 and 0.5 <= max_v <= 20.0 and min_v < max_v:
                        voltage_specs = {"voltage_min": min_v, "voltage_max": max_v}
                        logger.debug(f"Found voltage range: {min_v}V to {max_v}V")
                        break
                except (ValueError, IndexError):
                    continue

        return voltage_specs

    def _extract_temperature_from_text(self, text: str) -> Dict:
        """Extract temperature specs from PDF text."""
        temp_specs = {}

        # Normalize unicode minus signs to regular hyphens
        normalized_text = text.replace('−', '-').replace('–', '-')

        patterns = [
            # Standard format: "-40°C to +125°C"
            r'(-?\d+)\s*°?\s*C\s*(?:to|[-~])\s*\+?(\d+)\s*°?\s*C',
            # Temperature range in specifications
            r'[Tt]emperature\s+[Rr]ange[:\s]+(-?\d+)\s*°?\s*C?\s*(?:to|[-~])\s*\+?(\d+)',
            # Operating temperature
            r'[Oo]perating\s+[Tt]emperature[:\s]+(-?\d+)\s*°?\s*C?\s*(?:to|[-~])\s*\+?(\d+)',
            # Specified for temperature range
            r'[Ss]pecified\s+for\s+(-?\d+)\s*°?\s*C?\s*(?:to|[-~])\s*\+?(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, normalized_text, re.IGNORECASE)
            if match:
                try:
                    min_t = float(match.group(1))
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
        """Extract IC variants from text using regex patterns."""
        variants = []
        seen_parts = set()

        # Find ordering section
        ordering_section = self._find_ordering_section(text)
        search_text = ordering_section if ordering_section else text

        # Try each part number pattern
        for pattern in self.PART_NUMBER_PATTERNS:
            matches = re.finditer(pattern, search_text, re.IGNORECASE)

            for match in matches:
                part_number = match.group(1).upper()

                # Skip if already seen or too short
                if part_number in seen_parts or len(part_number) < 4:
                    continue

                # Skip common false positives and eval kits
                if any(x in part_number for x in ['EVAL', 'TABLE', 'FIGURE', 'PAGE', 'QSPZ', 'MKZ']):
                    continue

                # Skip reel versions if base part exists
                base_part = part_number.replace('-RL', '')
                if '-RL' in part_number and base_part in seen_parts:
                    continue

                seen_parts.add(part_number)

                # Get context around match to extract package info
                start = max(0, match.start() - 50)
                end = min(len(search_text), match.end() + 300)
                context = search_text[start:end]

                # Extract package and pin count
                package_type, pin_count = self._extract_package_from_context(context, part_number)

                # Build description
                description = f"Analog Devices {part_number}"
                if package_type:
                    description += f" - {package_type}"

                variant = {
                    "part_number": part_number,
                    "manufacturer": "ANALOG_DEVICES",
                    "pin_count": pin_count or 0,
                    "package_type": package_type,
                    "description": description,
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
            # Look for ORDERING GUIDE followed by table content (Model/Temperature/Package)
            r'(ORDERING\s+GUIDE\s*\n[^\n]*(?:Model|Temperature|Package).{200,5000})',
            r'(ORDER(?:ING)?\s+INFORMATION\s*\n.{200,3000})',
            r'(Model\d?\s+Temperature\s+Range\s+Package.{200,3000})',
        ]

        for pattern in patterns:
            # Find ALL matches and take the LAST one (actual table, not TOC reference)
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.DOTALL))
            if matches:
                # Use the last match (likely the actual ordering table, not TOC)
                last_match = matches[-1]
                logger.debug(f"Found ordering section at position {last_match.start()}")
                return last_match.group(0)

        return None

    def _extract_package_from_context(
        self,
        context: str,
        part_number: str
    ) -> Tuple[Optional[str], Optional[int]]:
        """Extract package type and pin count from text context."""
        package_type = None
        pin_count = None

        # Check if ADuC part - decode from part number
        # Format: ADuC7060BCPZ32 or ADuC7061BSTZ32
        # B = temperature grade, CPZ = LFCSP package, STZ = LQFP package
        aduc_match = re.match(r'ADuC\d{4}B?(CPZ|STZ|CP|ST)(\d*)', part_number, re.IGNORECASE)
        if aduc_match:
            pkg_code = aduc_match.group(1).upper()
            if 'ST' in pkg_code:
                package_type = 'LQFP'
            elif 'CP' in pkg_code:
                package_type = 'LFCSP'

        # Try package patterns from context to get pin count
        for pattern, pkg_name in self.PACKAGE_PATTERNS:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                try:
                    pins = int(match.group(1))
                    if pkg_name:
                        # If we already have package type from part number, just add pin count
                        if package_type:
                            package_type = f"{package_type}{pins}"
                        else:
                            package_type = f"{pkg_name}{pins}"
                        pin_count = pins
                    else:
                        pin_count = pins
                        if package_type:
                            package_type = f"{package_type}{pins}"
                    break
                except (ValueError, IndexError):
                    if pkg_name and not package_type:
                        package_type = pkg_name

        return package_type, pin_count

    def _create_basic_entry(self, pdf_path: Path, voltage_specs: Dict, temp_specs: Dict) -> Dict:
        """Create a basic entry when no detailed data is found."""
        # Try to extract part number from filename
        filename = pdf_path.stem.upper()

        # Remove manufacturer prefix if present
        for prefix in ["ANALOG_DEVICES_", "ANALOG-DEVICES_", "ADI_", "ADI-"]:
            if filename.startswith(prefix):
                filename = filename[len(prefix):]
                break

        # Try to find AD/ADuC pattern in filename
        part_match = re.search(r'(AD[A-Z]*\d{4}[A-Z0-9]*)', filename)
        if part_match:
            part_number = part_match.group(1)
        else:
            part_number = filename.split('_')[0].split('-')[0]

        return {
            "part_number": part_number,
            "manufacturer": "ANALOG_DEVICES",
            "pin_count": 0,
            "package_type": None,
            "description": f"Analog Devices {part_number}",
            "voltage_min": voltage_specs.get("voltage_min"),
            "voltage_max": voltage_specs.get("voltage_max"),
            "operating_temp_min": temp_specs.get("operating_temp_min"),
            "operating_temp_max": temp_specs.get("operating_temp_max"),
            "dimension_length": None,
            "dimension_width": None,
            "dimension_height": None,
            "electrical_specs": {},
        }
