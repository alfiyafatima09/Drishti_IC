# Prompt templates for IC analysis

IC_ANALYSIS_PROMPT = """
Analyze this IC chip image and identify:
1. The manufacturer (company name)
2. The total number of pins visible on the chip

Look for:
- Manufacturer logos or markings (TI, STM, ATMEL, etc.)
- Physical pins around the edges of the chip

Return ONLY valid JSON:
{"manufacturer": "Texas Instruments", "pin_count": 8}
"""
