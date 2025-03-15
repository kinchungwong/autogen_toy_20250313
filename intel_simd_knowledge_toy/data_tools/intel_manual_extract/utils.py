from dataclasses import dataclass

@dataclass(frozen=True)
class PdfPageRange:
    """Represents a range of pages in a PDF file as first and last page numbers, both inclusive.
    Note that PDF allows page numbers to start from any integer value.
    """
    first: int
    last: int
    def __post_init__(self):
        if not isinstance(self.first, int):
            raise TypeError("The 'first' attribute must be an integer.")
        if not isinstance(self.last, int):
            raise TypeError("The 'last' attribute must be an integer.")
