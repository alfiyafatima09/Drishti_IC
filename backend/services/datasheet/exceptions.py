"""
Custom exceptions for datasheet operations.
"""


class DatasheetDownloadException(Exception):
    """Exception raised when datasheet download fails."""
    pass


class UnsupportedManufacturerException(Exception):
    """Exception raised when manufacturer is not supported."""
    pass


class DatasheetExtractionException(Exception):
    """Exception raised when PDF data extraction fails."""
    pass

