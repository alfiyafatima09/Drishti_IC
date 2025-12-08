"""
Atmel PDF datasheet extractor.
Extracts IC specification data from Atmel PDF datasheets using hybrid approach:
- Regex-based text parsing for AVR, SAM, AT91, and other microcontrollers
- Table-based extraction for memory and peripheral ICs
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


class AtmelExtractor(DatasheetExtractor):
    """Extractor for Atmel PDF datasheets."""

    # Atmel part number patterns (more specific first)
    PART_NUMBER_PATTERNS = [
        # AVR series: ATmega328P, ATmega2560, ATmega32U4, etc.
        r'\b(ATMEGA\d{2,4}[A-Z]*\d*[A-Z]*)\b',
        # ATtiny series: ATtiny85, ATtiny2313, ATtiny44A, etc.
        r'\b(ATTINY\d{2,4}[A-Z]*)\b',
        # ATxmega series: ATxmega128A1, ATxmega256A3BU, etc.
        r'\b(ATXMEGA\d{2,4}[A-Z]\d[A-Z]*)\b',
        # SAM series (ARM): ATSAM3X8E, ATSAMD21G18A, ATSAME70Q21, etc.
        r'\b(ATSAM[A-Z]?\d{1,2}[A-Z]\d{1,2}[A-Z]?\d?[A-Z]?)\b',
        # SAM series without AT prefix: SAMD21G18A, SAME70Q21, etc.
        r'\b(SAM[A-Z]?\d{1,2}[A-Z]\d{1,2}[A-Z]?)\b',
        # AT91 series: AT91SAM7S256, AT91SAM9G20, etc.
        r'\b(AT91SAM\d{1,2}[A-Z]\d{2,3}[A-Z]?)\b',
        # AT91 generic: AT91RM9200, AT91M55800A, etc.
        r'\b(AT91[A-Z]{2}\d{4,5}[A-Z]*)\b',
        # ATA series (automotive): ATA6614Q, ATA5831, etc.
        r'\b(ATA\d{4}[A-Z]*)\b',
        # AT24 EEPROM series: AT24C02, AT24C256, etc.
        r'\b(AT24C\d{2,4}[A-Z]*)\b',
        # AT25 SPI EEPROM/Flash: AT25SF041, AT25DF321A, etc.
        r'\b(AT25[A-Z]{2}\d{3,4}[A-Z]*)\b',
        # AT45 DataFlash: AT45DB321E, AT45DB641E, etc.
        r'\b(AT45DB\d{3,4}[A-Z]*)\b',
        # ATF CPLD/FPGA series: ATF1502AS, ATF22V10C, etc.
        r'\b(ATF\d{3,5}[A-Z]*)\b',
        # Generic AT prefix parts
        r'\b(AT\d{2}[A-Z]{1,4}\d{2,5}[A-Z]*)\b',
    ]

    # Package patterns with pin counts
    PACKAGE_PATTERNS = [
        (r'\b(SOIC)[\s-]?(\d+)\b', 'SOIC'),
        (r'\b(TSSOP)[\s-]?(\d+)\b', 'TSSOP'),
        (r'\b(QFN)[\s-]?(\d+)\b', 'QFN'),
        (r'\b(QFP)[\s-]?(\d+)\b', 'QFP'),
        (r'\b(TQFP)[\s-]?(\d+)\b', 'TQFP'),
        (r'\b(LQFP)[\s-]?(\d+)\b', 'LQFP'),
        (r'\b(VQFP)[\s-]?(\d+)\b', 'VQFP'),
        (r'\b(DIP)[\s-]?(\d+)\b', 'DIP'),
        (r'\b(PDIP)[\s-]?(\d+)\b', 'PDIP'),
        (r'\b(PLCC)[\s-]?(\d+)\b', 'PLCC'),
        (r'\b(MLF)[\s-]?(\d+)\b', 'MLF'),
        (r'\b(VQFN)[\s-]?(\d+)\b', 'VQFN'),
        (r'\b(UQFN)[\s-]?(\d+)\b', 'UQFN'),
        (r'\b(SSOP)[\s-]?(\d+)\b', 'SSOP'),
        (r'\b(CBGA)[\s-]?(\d+)\b', 'CBGA'),
        (r'\b(BGA)[\s-]?(\d+)\b', 'BGA'),
        (r'\b(UFBGA)[\s-]?(\d+)\b', 'UFBGA'),
        # Pattern for "8-pin" or "8 pins"
        (r'(\d+)[\s-]?(?:pin|lead)s?', None),
    ]

    def extract(self, pdf_path: Path) -> List[Dict]:
        """
        Extract IC specification data from Atmel PDF datasheet.
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
            logger.debug(f"Extracting data from Atmel PDF: {pdf_path}")

            with pdfplumber.open(pdf_path) as pdf:
                # Extract full text for regex-based parsing
                full_text = self._extract_full_text(pdf)

                # Extract dimension pages
                dimension_text = self._extract_dimension_pages(pdf)

                # Extract voltage and temperature from text
                voltage_specs = self._extract_voltage_from_text(full_text)
                temp_specs = self._extract_temperature_from_text(full_text)

                # Extract dimension specs
                dimension_specs = self._extract_dimensions_from_text(dimension_text)

                # Extract memory/flash specs (important for Atmel MCUs)
                memory_specs = self._extract_memory_specs(full_text)

                logger.debug(f"Extracted voltage specs: {voltage_specs}")
                logger.debug(f"Extracted temp specs: {temp_specs}")
                logger.debug(f"Extracted dimension specs: {dimension_specs}")
                logger.debug(f"Extracted memory specs: {memory_specs}")

                # Try regex-based variant extraction
                ic_variants = self._extract_variants_from_text(
                    full_text, voltage_specs, temp_specs, dimension_specs, memory_specs
                )

            if not ic_variants:
                logger.debug(f"No IC variants found in PDF: {pdf_path}")
                return [self._create_basic_entry(pdf_path, voltage_specs, temp_specs)]

            logger.info(f"Extracted {len(ic_variants)} IC variants from Atmel PDF")
            return ic_variants

        except Exception as e:
            logger.error(f"Failed to extract data from Atmel PDF {pdf_path}: {e}")
            raise DatasheetExtractionException(
                f"Failed to extract data from Atmel PDF: {str(e)}"
            )

    def _extract_full_text(self, pdf) -> str:
        """Extract all text from PDF."""
        text_parts = []
        for page in pdf.pages:
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
                ['package outline', 'package dimension', 'mechanical',
                 'outline dimension', 'package marking', 'package drawing',
                 'physical dimension', 'package information']):
                text_parts.append(page_text)
        return "\n".join(text_parts)

    def _extract_dimensions_from_text(self, text: str) -> Dict[str, Dict]:
        """
        Extract package dimensions from PDF text.

        Returns:
            Dictionary mapping package type to dimensions
        """
        dimensions = {}

        # Pattern for Atmel package dimensions like "TQFP32 - 7.0 × 7.0 mm"
        pkg_dim_pattern = r'\b([A-Z]{2,6})[\-]?(\d+)\b[^\n]*?(\d+\.?\d*)\s*[×xX]\s*(\d+\.?\d*)\s*mm'
        for match in re.finditer(pkg_dim_pattern, text, re.IGNORECASE):
            try:
                pkg_type = match.group(1).upper()
                pin_count = int(match.group(2))
                length = float(match.group(3))
                width = float(match.group(4))

                if 1.0 <= length <= 50.0 and 1.0 <= width <= 50.0:
                    package_key = f"{pkg_type}{pin_count}"
                    if package_key not in dimensions:
                        dimensions[package_key] = {
                            "length": length,
                            "width": width,
                            "height": None
                        }
                        logger.debug(f"Found dimensions for {package_key}: {length}x{width} mm")
            except (ValueError, IndexError):
                continue

        # Pattern for dimension tables: D (length) x E (width)
        d_match = re.search(r'\bD\d?\s*[=:]\s*(\d+\.?\d*)', text)
        e_match = re.search(r'\bE\d?\s*[=:]\s*(\d+\.?\d*)', text)

        if d_match and e_match:
            try:
                d_val = float(d_match.group(1))
                e_val = float(e_match.group(1))
                if 1.0 <= d_val <= 50.0 and 1.0 <= e_val <= 50.0:
                    dimensions["GENERIC"] = {
                        "length": d_val,
                        "width": e_val,
                        "height": None
                    }
            except ValueError:
                pass

        return dimensions

    def _extract_voltage_from_text(self, text: str) -> Dict:
        """Extract voltage specs from full PDF text using regex."""
        voltage_specs = {}

        patterns = [
            # VCC range (common in Atmel datasheets)
            r'V[Cc][Cc]\s*[=:]\s*(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # VDD range
            r'V[Dd][Dd][A-Z]?\s*[=:]\s*(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # Operating Voltage
            r'[Oo]perating\s+[Vv]oltage[:\s]+(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # Power Supply Voltage
            r'[Pp]ower\s+[Ss]upply[:\s]+(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # Supply voltage range
            r'[Ss]upply\s+[Vv]oltage[:\s]+(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # AVR specific: "1.8V - 5.5V operation"
            r'(\d+\.?\d*)\s*V\s*[-–~]\s*(\d+\.?\d*)\s*V\s*(?:operation|range)',
            # Generic voltage range
            r'(\d+\.?\d*)\s*V\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V(?:\s|$|,)',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    min_v = float(match.group(1))
                    max_v = float(match.group(2))
                    # Sanity check: voltage should be between 0.5V and 60V
                    if 0.5 <= min_v <= 60.0 and 0.5 <= max_v <= 60.0 and min_v < max_v:
                        voltage_specs = {"voltage_min": min_v, "voltage_max": max_v}
                        logger.debug(f"Found voltage range: {min_v}V to {max_v}V")
                        break
                except (ValueError, IndexError):
                    continue

        return voltage_specs

    def _extract_temperature_from_text(self, text: str) -> Dict:
        """Extract temperature specs from full PDF text using regex."""
        temp_specs = {}

        # Normalize PDF encoding issues
        normalized_text = text.replace('(cid:176)', '°').replace('°', '°')

        patterns = [
            # Pattern for "-40°C to +85°C" (Industrial)
            r'[-–]\s*(\d+)\s*°?\s*C?\s*to\s*\+?(\d+)\s*°?\s*C',
            # Temperature range with degree symbol
            r'(-?\d+)\s*°?\s*C\s*(?:to|[-–~])\s*\+?(\d+)\s*°?\s*C',
            # Operating/ambient temperature
            r'[Oo]perating\s+[Tt]emperature[:\s]+(-?\d+)\s*(?:°C)?\s*(?:to|[-–~])\s*\+?(\d+)',
            r'[Aa]mbient\s+[Tt]emperature[:\s]+(-?\d+)\s*(?:°C)?\s*(?:to|[-–~])\s*\+?(\d+)',
            # Industrial temperature range (common for Atmel)
            r'[-–]\s*(40)\s*°?\s*C?\s*to\s*\+?(85|105|125|150)\s*°?\s*C',
            # Extended temperature
            r'[Ee]xtended\s+[Tt]emperature[:\s]+(-?\d+)\s*(?:°C)?\s*(?:to|[-–~])\s*\+?(\d+)',
            # Commercial temperature (0 to 70)
            r'(0)\s*°?\s*C?\s*to\s*\+?(70)\s*°?\s*C',
        ]

        for pattern in patterns:
            match = re.search(pattern, normalized_text, re.IGNORECASE)
            if match:
                try:
                    min_t_str = match.group(1)
                    min_t = float(min_t_str)
                    # Handle negative temperature
                    if min_t > 0 and ('- ' + min_t_str in normalized_text or '–' + min_t_str in normalized_text):
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

    def _extract_memory_specs(self, text: str) -> Dict:
        """Extract flash/SRAM/EEPROM specs common in Atmel MCU datasheets."""
        memory_specs = {}

        # Flash memory patterns
        flash_patterns = [
            r'(\d+)\s*[Kk][Bb](?:ytes?)?\s*(?:of\s+)?(?:[Ii]n-[Ss]ystem\s+)?(?:[Ss]elf-)?[Pp]rogramm?able?\s*[Ff]lash',
            r'[Ff]lash[:\s]+(\d+)\s*[Kk][Bb]',
            r'[Pp]rogram\s+[Mm]emory[:\s]+(\d+)\s*[Kk][Bb]',
            r'(\d+)\s*[Kk][Bb]\s*[Ff]lash',
        ]

        for pattern in flash_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    flash_kb = int(match.group(1))
                    if 1 <= flash_kb <= 4096:  # Reasonable range
                        memory_specs["flash_kb"] = flash_kb
                        logger.debug(f"Found flash memory: {flash_kb}KB")
                        break
                except (ValueError, IndexError):
                    continue

        # SRAM patterns
        sram_patterns = [
            r'(\d+)\s*[Kk]?[Bb](?:ytes?)?\s*(?:of\s+)?(?:[Ii]nternal\s+)?SRAM',
            r'SRAM[:\s]+(\d+)\s*[Kk]?[Bb]',
            r'[Dd]ata\s+[Mm]emory[:\s]+(\d+)\s*[Bb]ytes?',
        ]

        for pattern in sram_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    sram_val = int(match.group(1))
                    # Determine if bytes or KB
                    if 'K' in text[match.start():match.end()].upper():
                        memory_specs["sram_kb"] = sram_val
                    else:
                        memory_specs["sram_bytes"] = sram_val
                    logger.debug(f"Found SRAM: {sram_val}")
                    break
                except (ValueError, IndexError):
                    continue

        # EEPROM patterns
        eeprom_patterns = [
            r'(\d+)\s*[Bb]ytes?\s*(?:of\s+)?EEPROM',
            r'EEPROM[:\s]+(\d+)\s*[Bb]ytes?',
            r'(\d+)\s*[Kk][Bb]\s*EEPROM',
        ]

        for pattern in eeprom_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    eeprom_val = int(match.group(1))
                    if 'K' in text[match.start():match.end()].upper():
                        memory_specs["eeprom_kb"] = eeprom_val
                    else:
                        memory_specs["eeprom_bytes"] = eeprom_val
                    logger.debug(f"Found EEPROM: {eeprom_val}")
                    break
                except (ValueError, IndexError):
                    continue

        return memory_specs

    def _extract_variants_from_text(
        self,
        text: str,
        voltage_specs: Dict,
        temp_specs: Dict,
        dimension_specs: Optional[Dict[str, Dict]] = None,
        memory_specs: Optional[Dict] = None
    ) -> List[Dict]:
        """Extract IC variants from text using regex."""
        variants = []
        seen_parts = set()
        dimension_specs = dimension_specs or {}
        memory_specs = memory_specs or {}

        # Find ordering/device summary section
        ordering_section = self._find_ordering_section(text)
        search_text = ordering_section if ordering_section else text[:8000]

        # Try each part number pattern
        for pattern in self.PART_NUMBER_PATTERNS:
            matches = re.finditer(pattern, search_text, re.IGNORECASE)

            for match in matches:
                part_number = match.group(1).upper()

                # Skip if already seen or too short
                if part_number in seen_parts or len(part_number) < 5:
                    continue

                # Skip common false positives
                if part_number in ['TABLE', 'DEVICE', 'PACKAGE', 'ORDER', 'SOIC',
                                   'TSSOP', 'TQFP', 'FLASH', 'SRAM', 'EEPROM']:
                    continue

                seen_parts.add(part_number)

                # Get context around match to extract package info
                start = max(0, match.start() - 10)
                end = min(len(search_text), match.end() + 200)
                context = search_text[start:end]

                # Extract package and pin count from context
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
                    elif "GENERIC" in dimension_specs:
                        dims = dimension_specs["GENERIC"]
                        dim_length = dims.get("length")
                        dim_width = dims.get("width")
                        dim_height = dims.get("height")

                # Build description
                description_parts = [f"Atmel {part_number}"]
                if package_type:
                    description_parts.append(f"- {package_type}")
                if memory_specs.get("flash_kb"):
                    description_parts.append(f"- {memory_specs['flash_kb']}KB Flash")

                # Build electrical specs
                electrical_specs = {}
                if memory_specs:
                    electrical_specs.update(memory_specs)

                variant = {
                    "part_number": part_number,
                    "manufacturer": "ATMEL",
                    "pin_count": pin_count or 0,
                    "package_type": package_type,
                    "description": " ".join(description_parts),
                    "voltage_min": voltage_specs.get("voltage_min"),
                    "voltage_max": voltage_specs.get("voltage_max"),
                    "operating_temp_min": temp_specs.get("operating_temp_min"),
                    "operating_temp_max": temp_specs.get("operating_temp_max"),
                    "dimension_length": dim_length,
                    "dimension_width": dim_width,
                    "dimension_height": dim_height,
                    "electrical_specs": electrical_specs
                }

                variants.append(variant)

        return variants

    def _find_ordering_section(self, text: str) -> Optional[str]:
        """Find and extract the ordering information section from text."""
        patterns = [
            r'(?:ordering\s+information|order\s+information|ordering\s+code)(.{500,3000})',
            r'(?:device\s+summary|product\s+summary)(.{200,2000})',
            r'(?:part\s+numbering.*?package)(.{200,2000})',
            r'(?:table\s+\d+\..*?device\s+variants)(.{200,2000})',
            r'(?:device\s+selection|part\s+selection)(.{200,2000})',
            r'(?:package\s+and\s+pin\s+information)(.{200,2000})',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                logger.debug(f"Found ordering section: {match.group(0)[:100]}...")
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
                    # Pattern like TQFP32
                    package_type = f"{pkg_name}{match.group(2)}"
                    try:
                        pin_count = int(match.group(2))
                    except (ValueError, IndexError):
                        pass
                else:
                    # Pattern like "32-pin"
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

        # Look for MLF/QFN packages (common in Atmel)
        if not package_type:
            mlf_match = re.search(r'(\d+)[\s-]?(?:MLF|QFN)', context, re.IGNORECASE)
            if mlf_match:
                try:
                    pin_count = int(mlf_match.group(1))
                    package_type = f"MLF{pin_count}"
                except ValueError:
                    pass

        return package_type, pin_count

    def _create_basic_entry(self, pdf_path: Path, voltage_specs: Dict, temp_specs: Dict) -> Dict:
        """Create a basic entry when no detailed data is found."""
        part_number = pdf_path.stem.upper()

        # Remove manufacturer prefix if present
        for prefix in ["ATMEL_", "ATMEL-", "AT_", "AT-"]:
            if part_number.startswith(prefix):
                part_number = part_number[len(prefix):]
                break

        return {
            "part_number": part_number,
            "manufacturer": "ATMEL",
            "pin_count": 0,
            "package_type": None,
            "description": f"Atmel {part_number}",
            "voltage_min": voltage_specs.get("voltage_min"),
            "voltage_max": voltage_specs.get("voltage_max"),
            "operating_temp_min": temp_specs.get("operating_temp_min"),
            "operating_temp_max": temp_specs.get("operating_temp_max"),
            "dimension_length": None,
            "dimension_width": None,
            "dimension_height": None,
            "electrical_specs": {},
        }
