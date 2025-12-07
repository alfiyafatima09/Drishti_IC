# Prompt templates for IC analysis

IC_ANALYSIS_PROMPT = (
    "Analyze the attached IC image and return ONLY a valid JSON object"
    " with the following structure:\n\n"
    "{\n"
    '  "texts": ["t1", "t2"],             // Array of exact visible text strings\n'
    '  "num_pins": 0,                     // Integer count of visible pins\n'
    '  "logo": "Company Name"             // Company name if visible, else "unknown"\n'
    "}\n\n"
    "Constraints:\n"
    "- Return ONLY the JSON object.\n"
    "- No markdown formatting.\n"
    "- No explanations.\n"
)
