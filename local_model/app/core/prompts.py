# Prompt templates for IC analysis

IC_ANALYSIS_PROMPT = """Analyze the attached IC image and return ONLY a valid JSON object with the following structure:

{
  "texts": ["text1", "text2", ...],  // Array of exact text strings visible on the IC (reading order)
  "num_pins": 0,                     // Integer count of visible pins
  "logo": "Company Name"             // Company name if visible, else "unknown"
}

Constraints:
- Return ONLY the JSON object.
- No markdown formatting.
- No explanations.
"""
