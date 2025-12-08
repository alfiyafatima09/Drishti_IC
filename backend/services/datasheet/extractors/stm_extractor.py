"""
STMicroelectronics PDF datasheet extractor.
Extracts IC specification data from STM PDF datasheets using hybrid approach:
- Regex-based text parsing (like NXP) for STM32 microcontrollers
- Table-based extraction for older analog parts
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
        (r'(\d+)[\s-]?(?:pin|lead)s?', None),
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
            
            with pdfplumber.open(pdf_path) as pdf:
                # Extract full text for regex-based parsing
                full_text = self._extract_full_text(pdf)
                
                # Extract voltage and temperature from text (more reliable than tables)
                voltage_specs = self._extract_voltage_from_text(full_text)
                temp_specs = self._extract_temperature_from_text(full_text)
                
                logger.debug(f"Extracted voltage specs: {voltage_specs}")
                logger.debug(f"Extracted temp specs: {temp_specs}")
                
                # Try regex-based variant extraction (works well for STM32)
                ic_variants = self._extract_variants_from_text(full_text, voltage_specs, temp_specs)
            
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
        """Extract voltage specs from full PDF text using regex."""
        voltage_specs = {}
        
        patterns = [
            # VDD/VCC range
            r'V[Dd][Dd][A-Z]?\s*[=:]\s*(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            r'V[Cc][Cc]\s*[=:]\s*(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # Supply voltage range
            r'[Ss]upply\s+[Vv]oltage[:\s]+(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            r'[Oo]perating\s+[Vv]oltage[:\s]+(\d+\.?\d*)\s*V?\s*(?:to|[-–~])\s*(\d+\.?\d*)\s*V',
            # Generic voltage range (e.g., "2.0V to 3.6V")
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
            # Pattern for "-40°C to +85°C" with various separators
            r'[-–]\s*(\d+)\s*°?\s*C?\s*to\s*\+?(\d+)\s*°?\s*C',
            # Temperature range with degree symbol
            r'(-?\d+)\s*°?\s*C\s*(?:to|[-–~])\s*\+?(\d+)\s*°?\s*C',
            # Operating/ambient temperature
            r'[Oo]perating\s+[Tt]emperature[:\s]+(-?\d+)\s*(?:°C)?\s*(?:to|[-–~])\s*\+?(\d+)',
            r'[Aa]mbient\s+[Tt]emperature[:\s]+(-?\d+)\s*(?:°C)?\s*(?:to|[-–~])\s*\+?(\d+)',
            # Industrial temperature range pattern
            r'[-–]\s*(40)\s*°?\s*C?\s*to\s*\+?(85|125|150)\s*°?\s*C',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, normalized_text, re.IGNORECASE)
            if match:
                try:
                    min_t_str = match.group(1)
                    min_t = float(min_t_str)
                    # Handle negative temperature (check if there's a minus before)
                    if min_t > 0 and ('- ' + min_t_str in normalized_text or '–' + min_t_str in normalized_text):
                        min_t = -min_t
                    max_t = float(match.group(2))
                    # Sanity check: reasonable temperature range
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
        
        # Find ordering/device summary section (first 5000 chars usually contain summary)
        ordering_section = self._find_ordering_section(text)
        search_text = ordering_section if ordering_section else text[:5000]
        
        # Try each part number pattern
        for pattern in self.PART_NUMBER_PATTERNS:
            matches = re.finditer(pattern, search_text, re.IGNORECASE)
            
            for match in matches:
                part_number = match.group(1).upper()
                
                # Skip if already seen or too short
                if part_number in seen_parts or len(part_number) < 5:
                    continue
                
                # Skip common false positives
                if part_number in ['TABLE', 'FLASH', 'PACKAGE', 'ORDER', 'LQFP', 'TSSOP']:
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
            r'(?:table\s+\d+\..*?device\s+summary)(.{200,2000})',
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
        for prefix in ["STM_", "STM-", "ST_", "ST-"]:
            if part_number.startswith(prefix):
                part_number = part_number[len(prefix):]
                break
        
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
