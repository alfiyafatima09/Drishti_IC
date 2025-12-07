"""
Raspberry Pi PDF datasheet extractor.
Extracts IC specification data from Raspberry Pi PDF datasheets using hybrid approach:
- Regex-based text parsing for RP2040, RP2350, and other Raspberry Pi silicon
- Table-based extraction for package specifications
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


class RaspberryPiExtractor(DatasheetExtractor):
    """Extractor for Raspberry Pi PDF datasheets."""

    # Raspberry Pi silicon part number patterns
    PART_NUMBER_PATTERNS = [
        # RP2040 series
        r'\b(RP2040)\b',
        # RP2350 series: RP2350A, RP2350B, RP2354A, RP2354B
        r'\b(RP235[04][AB]?)\b',
        # Future RP parts
        r'\b(RP\d{4}[A-Z]?)\b',
    ]

    # Package patterns with pin counts
    PACKAGE_PATTERNS = [
        (r'\b(QFN)[\s-]?(\d+)\b', 'QFN'),
        (r'\b(\d+)[\s-]?QFN\b', 'QFN'),
        (r'\bQFN[\s-]?(\d+)\b', 'QFN'),
        # Pattern for "60-pin" or "60 pins"
        (r'(\d+)[\s-]?(?:pin|lead)s?', None),
    ]

    # RP2350 variant specifications (from the datasheet)
    RP2350_VARIANTS = {
        "RP2350A": {"package": "QFN60", "pin_count": 60, "gpio": 30, "adc": 4, "flash": None},
        "RP2350B": {"package": "QFN80", "pin_count": 80, "gpio": 48, "adc": 8, "flash": None},
        "RP2354A": {"package": "QFN60", "pin_count": 60, "gpio": 30, "adc": 4, "flash": "2MB"},
        "RP2354B": {"package": "QFN80", "pin_count": 80, "gpio": 48, "adc": 8, "flash": "2MB"},
    }

    # RP2040 specifications
    RP2040_SPECS = {
        "package": "QFN56",
        "pin_count": 56,
        "gpio": 30,
        "sram_kb": 264,
        "flash": None,  # External
    }

    def extract(self, pdf_path: Path) -> List[Dict]:
        """
        Extract IC specification data from Raspberry Pi PDF datasheet.
        Uses hybrid approach: regex text parsing + known variant data.

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
            logger.debug(f"Extracting data from Raspberry Pi PDF: {pdf_path}")

            with pdfplumber.open(pdf_path) as pdf:
                # Extract full text for regex-based parsing
                full_text = self._extract_full_text(pdf)

                # Extract dimension pages
                dimension_text = self._extract_dimension_pages(pdf)

                # Extract voltage and temperature from text
                voltage_specs = self._extract_voltage_from_text(full_text)
                temp_specs = self._extract_temperature_from_text(full_text)

                # Extract memory specs (SRAM, Flash)
                memory_specs = self._extract_memory_specs(full_text)

                # Extract peripheral specs
                peripheral_specs = self._extract_peripheral_specs(full_text)

                # Extract dimension specs
                dimension_specs = self._extract_dimensions_from_text(dimension_text)

                logger.debug(f"Extracted voltage specs: {voltage_specs}")
                logger.debug(f"Extracted temp specs: {temp_specs}")
                logger.debug(f"Extracted memory specs: {memory_specs}")
                logger.debug(f"Extracted dimension specs: {dimension_specs}")

                # Try regex-based variant extraction
                ic_variants = self._extract_variants_from_text(
                    full_text, voltage_specs, temp_specs, dimension_specs,
                    memory_specs, peripheral_specs
                )

            if not ic_variants:
                logger.debug(f"No IC variants found in PDF: {pdf_path}")
                return [self._create_basic_entry(pdf_path, voltage_specs, temp_specs)]

            logger.info(f"Extracted {len(ic_variants)} IC variants from Raspberry Pi PDF")
            return ic_variants

        except Exception as e:
            logger.error(f"Failed to extract data from Raspberry Pi PDF {pdf_path}: {e}")
            raise DatasheetExtractionException(
                f"Failed to extract data from Raspberry Pi PDF: {str(e)}"
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
        for i in range(max(0, len(pdf.pages) - 10), len(pdf.pages)):
            page_text = pdf.pages[i].extract_text()
            if page_text and any(kw in page_text.lower() for kw in
                ['physical specification', 'package dimension', 'mechanical',
                 'qfn pinout', 'qfn physical', 'millimetre']):
                text_parts.append(page_text)
        return "\n".join(text_parts)

    def _extract_dimensions_from_text(self, text: str) -> Dict[str, Dict]:
        """
        Extract package dimensions from PDF text.

        Returns:
            Dictionary mapping package type to dimensions
        """
        dimensions = {}

        # Pattern for QFN dimensions from Raspberry Pi datasheets
        # Look for D and E dimensions (package body size)
        # QFN-60: 7mm x 7mm, QFN-80: 10mm x 10mm

        # Pattern for "D 7 BSC" or "E 10 BSC" (body size)
        d_match = re.search(r'\bD\s+(\d+)\s*BSC\b', text)
        e_match = re.search(r'\bE\s+(\d+)\s*BSC\b', text)

        if d_match and e_match:
            try:
                d_val = float(d_match.group(1))
                e_val = float(e_match.group(1))
                if 5.0 <= d_val <= 15.0 and 5.0 <= e_val <= 15.0:
                    # Determine package type based on dimensions
                    if d_val == 7.0:
                        pkg_key = "QFN60"
                    elif d_val == 10.0:
                        pkg_key = "QFN80"
                    else:
                        pkg_key = "QFN"

                    dimensions[pkg_key] = {
                        "length": d_val,
                        "width": e_val,
                        "height": 0.85  # Typical QFN height
                    }
                    logger.debug(f"Found dimensions for {pkg_key}: {d_val}x{e_val} mm")
            except ValueError:
                pass

        # Also look for explicit mm dimensions
        dim_pattern = r'(\d+\.?\d*)\s*[×xX]\s*(\d+\.?\d*)\s*(?:mm|×)'
        for match in re.finditer(dim_pattern, text):
            try:
                length = float(match.group(1))
                width = float(match.group(2))
                if 5.0 <= length <= 15.0 and 5.0 <= width <= 15.0:
                    if length == 7.0 and width == 7.0:
                        dimensions["QFN60"] = {"length": 7.0, "width": 7.0, "height": 0.85}
                    elif length == 10.0 and width == 10.0:
                        dimensions["QFN80"] = {"length": 10.0, "width": 10.0, "height": 0.85}
            except ValueError:
                continue

        return dimensions

    def _extract_voltage_from_text(self, text: str) -> Dict:
        """Extract voltage specs from full PDF text using regex."""
        voltage_specs = {}

        patterns = [
            # IOVDD range (1.8V to 3.3V for Raspberry Pi silicon)
            r'IOVDD[^,\n]*(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # VREG_VIN range
            r'VREG_VIN[^,\n]*(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # Nominal voltage patterns
            r'[Nn]ominal\s+[Vv]oltage\s+(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # Power supply voltage
            r'[Pp]ower\s+[Ss]upply[^,\n]*(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # Generic voltage range
            r'(\d+\.?\d*)\s*V\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    min_v = float(match.group(1))
                    max_v = float(match.group(2))
                    # Sanity check for typical MCU voltage ranges
                    if 0.5 <= min_v <= 6.0 and 1.0 <= max_v <= 6.0 and min_v < max_v:
                        voltage_specs = {"voltage_min": min_v, "voltage_max": max_v}
                        logger.debug(f"Found voltage range: {min_v}V to {max_v}V")
                        break
                except (ValueError, IndexError):
                    continue

        # Default to typical RP2350/RP2040 IOVDD range if not found
        if not voltage_specs:
            voltage_specs = {"voltage_min": 1.8, "voltage_max": 3.3}

        return voltage_specs

    def _extract_temperature_from_text(self, text: str) -> Dict:
        """Extract temperature specs from full PDF text using regex."""
        temp_specs = {}

        # Normalize PDF encoding issues
        normalized_text = text.replace('(cid:176)', '°').replace('°', '°')

        patterns = [
            # Industrial range: -40°C to +85°C
            r'[-–]\s*(\d+)\s*°?\s*C?\s*to\s*\+?(\d+)\s*°?\s*C',
            # Temperature range with degree symbol
            r'(-?\d+)\s*°?\s*C\s*(?:to|[-–~])\s*\+?(\d+)\s*°?\s*C',
            # Operating temperature
            r'[Oo]perating\s+[Tt]emperature[:\s]+(-?\d+)\s*(?:°C)?\s*(?:to|[-–~])\s*\+?(\d+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, normalized_text, re.IGNORECASE)
            if match:
                try:
                    min_t = float(match.group(1))
                    max_t = float(match.group(2))
                    # Handle negative temperature
                    if min_t > 0 and min_t == 40:  # Likely -40
                        min_t = -40
                    # Sanity check
                    if -65 <= min_t <= 25 and 50 <= max_t <= 150:
                        temp_specs = {"operating_temp_min": min_t, "operating_temp_max": max_t}
                        logger.debug(f"Found temperature range: {min_t}°C to {max_t}°C")
                        break
                except (ValueError, IndexError):
                    continue

        # Default to industrial temp range for Raspberry Pi silicon
        if not temp_specs:
            temp_specs = {"operating_temp_min": -20, "operating_temp_max": 85}

        return temp_specs

    def _extract_memory_specs(self, text: str) -> Dict:
        """Extract SRAM and flash specs from PDF text."""
        memory_specs = {}

        # SRAM patterns
        sram_patterns = [
            r'(\d+)\s*KB?\s*(?:on-chip\s+)?SRAM',
            r'SRAM[:\s]+(\d+)\s*KB?',
            r'(\d+)\s*KB?\s*SRAM',
        ]

        for pattern in sram_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    sram_kb = int(match.group(1))
                    if 64 <= sram_kb <= 1024:  # Reasonable range for MCU SRAM
                        memory_specs["sram_kb"] = sram_kb
                        logger.debug(f"Found SRAM: {sram_kb}KB")
                        break
                except (ValueError, IndexError):
                    continue

        # External flash patterns
        flash_patterns = [
            r'(\d+)\s*MB?\s*(?:stacked\s+)?[Ff]lash',
            r'[Ff]lash[:\s]+(\d+)\s*MB?',
            r'(\d+)\s*MB?\s*external\s+(?:QSPI\s+)?[Ff]lash',
        ]

        for pattern in flash_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    flash_mb = int(match.group(1))
                    if 1 <= flash_mb <= 32:
                        memory_specs["flash_mb"] = flash_mb
                        logger.debug(f"Found Flash: {flash_mb}MB")
                        break
                except (ValueError, IndexError):
                    continue

        return memory_specs

    def _extract_peripheral_specs(self, text: str) -> Dict:
        """Extract peripheral specifications from PDF text."""
        peripheral_specs = {}

        # CPU clock speed
        clock_match = re.search(r'@?\s*(\d+)\s*MHz', text)
        if clock_match:
            try:
                peripheral_specs["clock_mhz"] = int(clock_match.group(1))
            except ValueError:
                pass

        # GPIO count
        gpio_patterns = [
            r'(\d+)\s*GPIO\s*pins?',
            r'(\d+)/\d+\s*GPIO',
            r'GPIO[:\s]+(\d+)',
        ]
        for pattern in gpio_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    gpio_count = int(match.group(1))
                    if 10 <= gpio_count <= 100:
                        peripheral_specs["gpio_count"] = gpio_count
                        break
                except ValueError:
                    pass

        # UART count
        uart_match = re.search(r'(\d+)\s*[×x]?\s*UART', text, re.IGNORECASE)
        if uart_match:
            try:
                peripheral_specs["uart_count"] = int(uart_match.group(1))
            except ValueError:
                pass

        # SPI count
        spi_match = re.search(r'(\d+)\s*[×x]?\s*SPI\s*controllers?', text, re.IGNORECASE)
        if spi_match:
            try:
                peripheral_specs["spi_count"] = int(spi_match.group(1))
            except ValueError:
                pass

        # I2C count
        i2c_match = re.search(r'(\d+)\s*[×x]?\s*I2C\s*controllers?', text, re.IGNORECASE)
        if i2c_match:
            try:
                peripheral_specs["i2c_count"] = int(i2c_match.group(1))
            except ValueError:
                pass

        # ADC channels
        adc_match = re.search(r'(\d+)/?\d*\s*[×x]?\s*ADC\s*channels?', text, re.IGNORECASE)
        if adc_match:
            try:
                peripheral_specs["adc_channels"] = int(adc_match.group(1))
            except ValueError:
                pass

        # PWM channels
        pwm_match = re.search(r'(\d+)\s*[×x]?\s*PWM\s*channels?', text, re.IGNORECASE)
        if pwm_match:
            try:
                peripheral_specs["pwm_channels"] = int(pwm_match.group(1))
            except ValueError:
                pass

        # PIO state machines
        pio_match = re.search(r'(\d+)\s*[×x]?\s*PIO\s*state\s*machines?', text, re.IGNORECASE)
        if pio_match:
            try:
                peripheral_specs["pio_state_machines"] = int(pio_match.group(1))
            except ValueError:
                pass

        # USB support
        if re.search(r'USB\s*1\.1', text, re.IGNORECASE):
            peripheral_specs["usb"] = "USB 1.1"

        # Dual-core
        if re.search(r'[Dd]ual[- ][Cc]ore|[Dd]ual\s+(?:Arm|RISC)', text):
            peripheral_specs["cores"] = 2

        # ARM Cortex-M33 or RISC-V
        if re.search(r'Cortex-M33', text):
            peripheral_specs["cpu_type"] = "ARM Cortex-M33"
        elif re.search(r'Hazard3\s*RISC-V', text):
            peripheral_specs["cpu_type"] = "Hazard3 RISC-V"
        elif re.search(r'Cortex-M0\+', text):
            peripheral_specs["cpu_type"] = "ARM Cortex-M0+"

        return peripheral_specs

    def _extract_variants_from_text(
        self,
        text: str,
        voltage_specs: Dict,
        temp_specs: Dict,
        dimension_specs: Optional[Dict[str, Dict]] = None,
        memory_specs: Optional[Dict] = None,
        peripheral_specs: Optional[Dict] = None
    ) -> List[Dict]:
        """Extract IC variants from text using regex."""
        variants = []
        seen_parts = set()
        dimension_specs = dimension_specs or {}
        memory_specs = memory_specs or {}
        peripheral_specs = peripheral_specs or {}

        # Search the full text for part numbers
        search_text = text

        # Try each part number pattern
        for pattern in self.PART_NUMBER_PATTERNS:
            matches = re.finditer(pattern, search_text, re.IGNORECASE)

            for match in matches:
                part_number = match.group(1).upper()

                # Skip if already seen
                if part_number in seen_parts:
                    continue

                seen_parts.add(part_number)

                # Get known variant info
                variant_info = self.RP2350_VARIANTS.get(part_number, {})

                # Determine package and pin count
                package_type = variant_info.get("package")
                pin_count = variant_info.get("pin_count", 0)

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

                # Build description
                description_parts = [f"Raspberry Pi {part_number}"]
                if peripheral_specs.get("cpu_type"):
                    description_parts.append(f"Dual {peripheral_specs['cpu_type']}")
                if peripheral_specs.get("clock_mhz"):
                    description_parts.append(f"@ {peripheral_specs['clock_mhz']}MHz")
                if memory_specs.get("sram_kb"):
                    description_parts.append(f"{memory_specs['sram_kb']}KB SRAM")
                if variant_info.get("flash"):
                    description_parts.append(f"{variant_info['flash']} Flash")

                # Build electrical specs
                electrical_specs = {}
                electrical_specs.update(memory_specs)
                electrical_specs.update(peripheral_specs)
                if variant_info.get("gpio"):
                    electrical_specs["gpio_count"] = variant_info["gpio"]
                if variant_info.get("adc"):
                    electrical_specs["adc_channels"] = variant_info["adc"]
                if variant_info.get("flash"):
                    electrical_specs["internal_flash"] = variant_info["flash"]

                variant = {
                    "part_number": part_number,
                    "manufacturer": "RASPBERRY_PI",
                    "pin_count": pin_count,
                    "package_type": package_type,
                    "description": " - ".join(description_parts),
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

    def _create_basic_entry(self, pdf_path: Path, voltage_specs: Dict, temp_specs: Dict) -> Dict:
        """Create a basic entry when no detailed data is found."""
        part_number = pdf_path.stem.upper()

        # Clean up part number
        part_number = re.sub(r'[-_]?product[-_]?brief', '', part_number, flags=re.IGNORECASE)
        part_number = re.sub(r'[-_]?datasheet', '', part_number, flags=re.IGNORECASE)
        part_number = part_number.strip('-_').upper()

        return {
            "part_number": part_number,
            "manufacturer": "RASPBERRY_PI",
            "pin_count": 0,
            "package_type": None,
            "description": f"Raspberry Pi {part_number}",
            "voltage_min": voltage_specs.get("voltage_min"),
            "voltage_max": voltage_specs.get("voltage_max"),
            "operating_temp_min": temp_specs.get("operating_temp_min"),
            "operating_temp_max": temp_specs.get("operating_temp_max"),
            "dimension_length": None,
            "dimension_width": None,
            "dimension_height": None,
            "electrical_specs": {},
        }
