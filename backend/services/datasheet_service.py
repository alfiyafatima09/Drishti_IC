"""
Datasheet retrieval and parsing service
"""
import requests
import os
import re
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime
import hashlib
from urllib.parse import urljoin, urlparse
import time
import io
import pdfplumber
import PyPDF2
from bs4 import BeautifulSoup
import cv2
import numpy as np

from config.settings import settings
from models.database import DatasheetCache

logger = logging.getLogger(__name__)


class DatasheetService:
    """Service for retrieving and parsing IC datasheets"""

    def __init__(self):
        os.makedirs(settings.datasheet_cache_dir, exist_ok=True)

    async def fetch_datasheet(
        self,
        part_number: str,
        manufacturer: Optional[str] = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """Fetch datasheet for an IC part number"""

        try:
            start_time = datetime.utcnow()

            # Determine manufacturer if not provided
            if not manufacturer:
                manufacturer = self._identify_manufacturer(part_number)

            if not manufacturer or manufacturer not in settings.supported_manufacturers:
                return {
                    "success": False,
                    "error": f"Unsupported manufacturer: {manufacturer}",
                    "part_number": part_number
                }

            # Check cache first
            if not force_refresh:
                cached_result = self._check_cache(part_number, manufacturer)
                if cached_result:
                    return cached_result

            # Generate datasheet URL
            datasheet_url = self._generate_datasheet_url(part_number, manufacturer)

            if not datasheet_url:
                return {
                    "success": False,
                    "error": "Could not generate datasheet URL",
                    "part_number": part_number,
                    "manufacturer": manufacturer
                }

            # Download datasheet
            download_result = await self._download_datasheet(datasheet_url, part_number)

            if not download_result["success"]:
                # Try alternative search methods
                alternative_result = await self._search_alternative_sources(part_number, manufacturer)
                if alternative_result["success"]:
                    download_result = alternative_result

            processing_time = (datetime.utcnow() - start_time).total_seconds()

            result = {
                "success": download_result["success"],
                "part_number": part_number,
                "manufacturer": manufacturer,
                "url": download_result.get("url"),
                "local_path": download_result.get("local_path"),
                "downloaded_at": datetime.utcnow().isoformat(),
                "processing_time_seconds": processing_time
            }

            if download_result["success"]:
                # Cache the result
                await self._cache_datasheet(result)
            else:
                result["error"] = download_result.get("error", "Download failed")

            return result

        except Exception as e:
            logger.error(f"Error fetching datasheet for {part_number}: {e}")
            return {
                "success": False,
                "error": str(e),
                "part_number": part_number
            }

    def _identify_manufacturer(self, part_number: str) -> Optional[str]:
        """Identify manufacturer from part number"""

        # Simple heuristics based on part number patterns
        part_upper = part_number.upper()

        # Common manufacturer prefixes
        manufacturer_patterns = {
            "STMicroelectronics": [r'^STM', r'^L78', r'^LD1117'],
            "Texas Instruments": [r'^LM', r'^TL0', r'^SN74', r'^TPS', r'^DRV'],
            "NXP": [r'^PCA', r'^LPC', r'^MC9S12', r'^PN5'],
            "Microchip": [r'^PIC', r'^ATMEGA', r'^ATTINY', r'^MCP'],
            "Infineon": [r'^IRF', r'^BTS', r'^TLE'],
            "Analog Devices": [r'^AD', r'^ADA', r'^ADP', r'^ADR'],
            "ON Semiconductor": [r'^MC78', r'^LM78', r'^NCP']
        }

        for manufacturer, patterns in manufacturer_patterns.items():
            for pattern in patterns:
                if re.match(pattern, part_upper):
                    return manufacturer

        return None

    def _generate_datasheet_url(self, part_number: str, manufacturer: str) -> Optional[str]:
        """Generate datasheet URL based on manufacturer and part number"""

        manufacturer_config = settings.supported_manufacturers.get(manufacturer)
        if not manufacturer_config:
            return None

        base_url = manufacturer_config["datasheet_base_url"]

        # Manufacturer-specific URL generation logic
        if manufacturer == "STMicroelectronics":
            # Example: https://www.st.com/resource/en/datasheet/stm32f103c8.pdf
            return f"{base_url}{part_number.lower()}.pdf"

        elif manufacturer == "Texas Instruments":
            # Example: https://www.ti.com/lit/ds/symlink/lm358.pdf
            return f"{base_url}{part_number.lower()}.pdf"

        elif manufacturer == "NXP":
            # Example: https://www.nxp.com/docs/en/data-sheet/PCA9685.pdf
            return f"{base_url}{part_number.upper()}.pdf"

        elif manufacturer == "Microchip":
            # Example: https://ww1.microchip.com/downloads/en/DeviceDoc/40001811A.pdf
            # This might need more complex logic
            return f"{base_url}40001811A.pdf"  # Placeholder

        elif manufacturer == "Infineon":
            # Example: https://www.infineon.com/dgdl/irf540.pdf
            return f"{base_url}{part_number.lower()}.pdf"

        elif manufacturer == "Analog Devices":
            # Example: https://www.analog.com/media/en/technical-documentation/data-sheets/ADXL355.pdf
            return f"{base_url}{part_number.upper()}.pdf"

        elif manufacturer == "ON Semiconductor":
            # Example: https://www.onsemi.com/pub/Collateral/MC78M05-D.PDF
            return f"{base_url}{part_number.upper()}-D.PDF"

        return None

    async def _download_datasheet(self, url: str, part_number: str) -> Dict[str, Any]:
        """Download datasheet from URL"""

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }

            response = requests.get(url, headers=headers, timeout=settings.datasheet_timeout)

            if response.status_code == 200:
                # Generate local path
                filename = f"{part_number.lower().replace('/', '_')}.pdf"
                local_path = os.path.join(settings.datasheet_cache_dir, filename)

                # Save file
                with open(local_path, 'wb') as f:
                    f.write(response.content)

                # Calculate checksum
                checksum = hashlib.sha256(response.content).hexdigest()

                return {
                    "success": True,
                    "url": url,
                    "local_path": local_path,
                    "file_size": len(response.content),
                    "checksum": checksum
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}",
                    "url": url
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "url": url
            }

    async def _search_alternative_sources(self, part_number: str, manufacturer: str) -> Dict[str, Any]:
        """Search for datasheet from alternative sources"""

        # Try web search approach (simplified)
        search_queries = [
            f'"{part_number}" datasheet pdf',
            f'"{part_number}" {manufacturer} datasheet',
            f'{manufacturer} {part_number} pdf'
        ]

        # This is a placeholder - real implementation would use search APIs
        # For now, return failure
        return {
            "success": False,
            "error": "Alternative search not implemented",
            "part_number": part_number
        }

    def _check_cache(self, part_number: str, manufacturer: str) -> Optional[Dict[str, Any]]:
        """Check if datasheet is cached in database and filesystem"""

        from models.database import SessionLocal
        
        try:
            db = SessionLocal()
            
            # Check database cache first
            cache_entry = db.query(DatasheetCache).filter(
                DatasheetCache.url.contains(part_number.lower())
            ).order_by(DatasheetCache.last_accessed.desc()).first()
            
            if cache_entry and os.path.exists(cache_entry.local_path):
                # Update last accessed time
                cache_entry.last_accessed = datetime.utcnow()
                db.commit()
                
                return {
                    "success": True,
                    "part_number": part_number,
                    "manufacturer": manufacturer,
                    "local_path": cache_entry.local_path,
                    "url": cache_entry.url,
                    "cached": True,
                    "file_size": cache_entry.file_size_bytes,
                    "downloaded_at": cache_entry.downloaded_at.isoformat(),
                    "last_accessed": cache_entry.last_accessed.isoformat()
                }
            
            # Fallback to filesystem check
            filename = f"{part_number.lower().replace('/', '_')}.pdf"
            local_path = os.path.join(settings.datasheet_cache_dir, filename)

            if os.path.exists(local_path):
                return {
                    "success": True,
                    "part_number": part_number,
                    "manufacturer": manufacturer,
                    "local_path": local_path,
                    "cached": True,
                    "file_size": os.path.getsize(local_path)
                }

            return None
            
        except Exception as e:
            logger.error(f"Error checking cache: {e}")
            return None
        finally:
            db.close()

    async def _cache_datasheet(self, datasheet_info: Dict[str, Any]):
        """Cache datasheet information in database"""

        from models.database import SessionLocal
        
        try:
            db = SessionLocal()
            
            url = datasheet_info.get("url")
            local_path = datasheet_info.get("local_path")
            
            if not url or not local_path:
                return
            
            # Check if already cached
            existing = db.query(DatasheetCache).filter_by(url=url).first()
            
            if existing:
                # Update existing entry
                existing.last_accessed = datetime.utcnow()
                if os.path.exists(local_path):
                    existing.file_size_bytes = os.path.getsize(local_path)
                db.commit()
            else:
                # Create new cache entry
                file_size = os.path.getsize(local_path) if os.path.exists(local_path) else 0
                
                # Calculate checksum
                checksum = None
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as f:
                        checksum = hashlib.sha256(f.read()).hexdigest()
                
                cache_entry = DatasheetCache(
                    url=url,
                    local_path=local_path,
                    file_size_bytes=file_size,
                    checksum=checksum,
                    downloaded_at=datetime.utcnow(),
                    last_accessed=datetime.utcnow()
                )
                
                db.add(cache_entry)
                db.commit()
                
            logger.info(f"Cached datasheet: {url}")
            
        except Exception as e:
            logger.error(f"Error caching datasheet: {e}")
        finally:
            db.close()

    async def parse_datasheet(self, content: bytes) -> Dict[str, Any]:
        """Parse datasheet content and extract specifications"""

        try:
            # Try multiple parsing approaches
            specs = {}

            # Method 1: PyPDF2 for text extraction
            try:
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
                text_content = ""
                for page in pdf_reader.pages[:10]:  # First 10 pages usually contain specs
                    text_content += page.extract_text() + "\n"

                specs.update(self._extract_specs_from_text(text_content))
            except Exception as e:
                logger.warning(f"PyPDF2 parsing failed: {e}")

            # Method 2: pdfplumber for table extraction
            try:
                with pdfplumber.open(io.BytesIO(content)) as pdf:
                    for page in pdf.pages[:5]:
                        tables = page.extract_tables()
                        for table in tables:
                            table_specs = self._extract_specs_from_table(table)
                            specs.update(table_specs)
            except Exception as e:
                logger.warning(f"pdfplumber parsing failed: {e}")

            # Method 3: OCR fallback for image-based PDFs
            try:
                ocr_specs = await self._extract_specs_with_ocr(content)
                specs.update(ocr_specs)
            except Exception as e:
                logger.warning(f"OCR parsing failed: {e}")

            validated_specs = self._validate_and_clean_specs(specs)

            return {
                "parsing_success": True,
                "extracted_specs": validated_specs,
                "confidence": self._calculate_parsing_confidence(validated_specs)
            }

        except Exception as e:
            logger.error(f"Error parsing datasheet: {e}")
            return {
                "parsing_success": False,
                "error": str(e),
                "extracted_specs": {}
            }

    def _extract_specs_from_text(self, text: str) -> Dict[str, Any]:
        """Extract specifications from plain text"""

        specs = {}

        # Common patterns for IC specifications
        patterns = {
            "operating_voltage_min": [
                r'operating.*voltage.*?(\d+\.?\d*)\s*V',
                r'VCC.*?(\d+\.?\d*)\s*V.*?min',
                r'supply.*voltage.*?(\d+\.?\d*)\s*V'
            ],
            "operating_voltage_max": [
                r'operating.*voltage.*?(\d+\.?\d*)\s*V.*?max',
                r'VCC.*?(\d+\.?\d*)\s*V.*?max'
            ],
            "current_rating": [
                r'output.*current.*?(\d+\.?\d*)\s*(mA|A)',
                r'IOUT.*?(\d+\.?\d*)\s*(mA|A)'
            ],
            "temperature_min": [
                r'operating.*temp.*?(-?\d+)\s*°?C.*?min',
                r'TA.*?(-?\d+)\s*°?C'
            ],
            "temperature_max": [
                r'operating.*temp.*?(\d+)\s*°?C.*?max',
                r'TA.*?(\d+)\s*°?C'
            ],
            "pin_count": [
                r'(\d+)\s*(?:pin|lead)',
                r'package.*?(\d+)\s*pin'
            ]
        }

        for spec_name, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    value = match.group(1)
                    unit = match.group(2) if len(match.groups()) > 1 else None

                    if spec_name in ["operating_voltage_min", "operating_voltage_max",
                                   "current_rating", "temperature_min", "temperature_max"]:
                        try:
                            specs[spec_name] = float(value)
                            if unit:
                                specs[f"{spec_name}_unit"] = unit
                        except ValueError:
                            pass
                    elif spec_name == "pin_count":
                        try:
                            specs[spec_name] = int(value)
                        except ValueError:
                            pass
                    break

        return specs

    def _extract_specs_from_table(self, table: List[List[str]]) -> Dict[str, Any]:
        """Extract specifications from table data"""

        specs = {}

        if not table:
            return specs

        table_text = "\n".join(["\t".join([str(cell) for cell in row if cell]) for row in table])

        # Look for common specification tables
        spec_keywords = {
            "operating_voltage": ["operating voltage", "supply voltage", "vcc", "vdd"],
            "current": ["output current", "iout", "current"],
            "temperature": ["operating temperature", "temperature range", "ta"],
            "pin_count": ["pins", "package"]
        }

        for spec_type, keywords in spec_keywords.items():
            for keyword in keywords:
                if keyword.lower() in table_text.lower():
                    values = self._extract_values_near_keyword(table_text, keyword)
                    if values:
                        specs.update(values)
                        break

        return specs

    def _extract_values_near_keyword(self, text: str, keyword: str) -> Dict[str, Any]:
        """Extract numerical values near a keyword"""

        keyword_pos = text.lower().find(keyword.lower())
        if keyword_pos == -1:
            return {}

        start = max(0, keyword_pos - 100)
        end = min(len(text), keyword_pos + 100)
        context = text[start:end]

        numbers = re.findall(r'(\d+\.?\d*)\s*(V|mA|A|°C|C)', context, re.IGNORECASE)

        specs = {}
        for value, unit in numbers:
            try:
                num_value = float(value)
                if unit.upper() in ['V', 'MV']:
                    if 'min' in context.lower() or 'minimum' in context.lower():
                        specs["operating_voltage_min"] = num_value
                    elif 'max' in context.lower() or 'maximum' in context.lower():
                        specs["operating_voltage_max"] = num_value
                elif unit.upper() in ['MA', 'A']:
                    specs["current_rating"] = num_value
                    specs["current_unit"] = unit
                elif unit.upper() in ['°C', 'C']:
                    if 'min' in context.lower():
                        specs["temperature_min"] = num_value
                    elif 'max' in context.lower():
                        specs["temperature_max"] = num_value
            except ValueError:
                pass

        return specs

    async def _extract_specs_with_ocr(self, content: bytes) -> Dict[str, Any]:
        """Extract specifications using OCR for image-based PDFs"""

        try:
            # Convert PDF pages to images and run OCR
            import pdf2image
            from services.ocr_service import OCRService
            
            ocr_service = OCRService()
            specs = {}
            
            # Convert first 5 pages to images
            try:
                images = pdf2image.convert_from_bytes(
                    content,
                    first_page=1,
                    last_page=5,
                    dpi=300
                )
            except Exception as e:
                logger.warning(f"PDF to image conversion failed: {e}")
                return {}
            
            # Run OCR on each page
            for idx, img in enumerate(images):
                # Convert PIL image to numpy array
                img_array = np.array(img)
                
                # Convert RGB to BGR for OpenCV
                if len(img_array.shape) == 3 and img_array.shape[2] == 3:
                    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
                
                # Extract text using OCR service
                ocr_result = await ocr_service.extract_text(img_array, preprocess=True)
                
                if ocr_result.get("extracted_text"):
                    # Combine all extracted text
                    page_text = " ".join([
                        item.get("text", "") 
                        for item in ocr_result["extracted_text"]
                    ])
                    
                    # Extract specs from OCR text
                    page_specs = self._extract_specs_from_text(page_text)
                    specs.update(page_specs)
            
            return specs
            
        except ImportError:
            logger.warning("pdf2image not installed, skipping OCR extraction")
            return {}
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return {}

    def _validate_and_clean_specs(self, specs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean extracted specifications"""

        validated = {}

        v_min = specs.get("operating_voltage_min")
        v_max = specs.get("operating_voltage_max")

        if v_min is not None and v_max is not None:
            if v_min <= v_max and 0 <= v_min <= 100 and 0 <= v_max <= 100:
                validated["operating_voltage_min"] = v_min
                validated["operating_voltage_max"] = v_max
                validated["operating_voltage_unit"] = specs.get("operating_voltage_unit", "V")

        # Current rating validation
        current = specs.get("current_rating")
        if current is not None and 0 <= current <= 10000: 
            validated["current_rating"] = current
            validated["current_unit"] = specs.get("current_unit", "A")

        # Temperature validation
        t_min = specs.get("temperature_min")
        t_max = specs.get("temperature_max")

        if t_min is not None and t_max is not None:
            if t_min <= t_max and -100 <= t_min <= 200 and -100 <= t_max <= 200:
                validated["temperature_min"] = t_min
                validated["temperature_max"] = t_max
                validated["temperature_unit"] = specs.get("temperature_unit", "°C")

        # Pin count validation
        pins = specs.get("pin_count")
        if pins is not None and 2 <= pins <= 1000:  # Reasonable pin count range
            validated["pin_count"] = pins

        return validated

    def _calculate_parsing_confidence(self, specs: Dict[str, Any]) -> float:
        """Calculate confidence score for parsed specifications"""

        # Count extracted specifications
        spec_count = len(specs)

        # Base confidence
        confidence = min(spec_count / 10, 0.8)  # Max 80% from spec count

        # Bonus for having key specifications
        key_specs = ["operating_voltage_min", "operating_voltage_max", "pin_count"]
        key_spec_count = sum(1 for spec in key_specs if spec in specs)

        confidence += (key_spec_count / len(key_specs)) * 0.2

        return min(confidence, 1.0)

    async def search_ic_database(self, query: str, manufacturer: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        """Search IC database for specifications"""

        from models.database import SessionLocal, IC, Manufacturer
        from sqlalchemy import or_
        
        try:
            db = SessionLocal()
            
            # Build query
            ic_query = db.query(IC).join(Manufacturer)
            
            # Filter by manufacturer if provided
            if manufacturer:
                ic_query = ic_query.filter(Manufacturer.name == manufacturer)
            
            # Search by part number or other fields
            search_term = f"%{query}%"
            ic_query = ic_query.filter(
                or_(
                    IC.part_number.ilike(search_term),
                    IC.package_type.ilike(search_term),
                    Manufacturer.name.ilike(search_term)
                )
            )
            
            # Limit results
            results = ic_query.limit(limit).all()
            
            # Convert to dict
            ic_list = []
            for ic in results:
                ic_dict = {
                    "id": ic.id,
                    "part_number": ic.part_number,
                    "manufacturer": ic.manufacturer.name if ic.manufacturer else None,
                    "manufacturer_short_name": ic.manufacturer.short_name if ic.manufacturer else None,
                    "operating_voltage_min": ic.operating_voltage_min,
                    "operating_voltage_max": ic.operating_voltage_max,
                    "operating_voltage_unit": ic.operating_voltage_unit,
                    "current_rating": ic.current_rating,
                    "current_unit": ic.current_unit,
                    "temperature_min": ic.temperature_min,
                    "temperature_max": ic.temperature_max,
                    "temperature_unit": ic.temperature_unit,
                    "pin_count": ic.pin_count,
                    "package_type": ic.package_type,
                    "datasheet_url": ic.datasheet_url,
                    "marking_specifications": ic.marking_specifications,
                    "font_specifications": ic.font_specifications,
                    "logo_requirements": ic.logo_requirements
                }
                ic_list.append(ic_dict)
            
            return ic_list
            
        except Exception as e:
            logger.error(f"Error searching IC database: {e}")
            return []
        finally:
            db.close()

    def generate_datasheet_url(self, part_number: str) -> str:
        """Generate datasheet URL for a part number"""

        manufacturer = self._identify_manufacturer(part_number)
        if manufacturer:
            return self._generate_datasheet_url(part_number, manufacturer)

        return ""
