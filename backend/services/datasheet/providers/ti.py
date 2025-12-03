"""
Texas Instruments datasheet provider.
"""
from .base import DatasheetProvider


class TIProvider(DatasheetProvider):
    """Texas Instruments datasheet provider."""
    
    def construct_url(self, part_number: str) -> str:
        """
        Construct TI datasheet URL.
        Format: https://www.ti.com/lit/ds/symlink/{part_number}.pdf
        
        Args:
            part_number: IC part number (e.g., 'lm555', 'lm358')
            
        Returns:
            Full URL to the datasheet PDF
        """
        part_number_clean = part_number.lower().strip()
        return f"https://www.ti.com/lit/ds/symlink/{part_number_clean}.pdf"

