"""
STMicroelectronics datasheet provider.
"""
from .base import DatasheetProvider


class STMProvider(DatasheetProvider):
    """STMicroelectronics datasheet provider."""
    
    def construct_url(self, part_number: str) -> str:
        """
        Construct STM datasheet URL.
        Format: https://www.st.com/resource/en/datasheet/{part_number}.pdf
        
        Args:
            part_number: IC part number (e.g., 'stm32l031k6')
            
        Returns:
            Full URL to the datasheet PDF
        """
        part_number_clean = part_number.lower().strip()
        return f"https://www.st.com/resource/en/datasheet/{part_number_clean}.pdf"

