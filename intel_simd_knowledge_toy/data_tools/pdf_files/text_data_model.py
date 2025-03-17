from collections.abc import Sequence
from dataclasses import dataclass
from functools import cached_property

from intel_simd_knowledge_toy.data_tools.pdf_files.strdelim import (
    StrDelim,
)

all = [
    "PdfPageRange",
    "PdfPageLine",
    "PdfPageText",
    "PdfPageSequence",
]


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


@dataclass(frozen=True)
class PdfPageLine:
    """Represents a text line found on a PDF page.
    Members:
        page_idx (int) : The zero-based index of the page, relative to the start of the page range.
        pdf_pagenum (int) : The page number in the PDF file. This number is usually one-based.
        line_idx (int) : The zero-based index of the line on the page.
        char_start (int) : The starting char index of the line within the concatenated page text.
        char_stop (int) : The ending char index of the line within the concatenated page text.
        text (str) : The text content of the line, without the newline character.
    """
    page_idx: int
    pdf_pagenum: int
    line_idx: int
    char_start: int
    char_stop: int
    text: str

    def __str__(self) -> str:
        return self.text
    
    def __repr__(self) -> str:
        return f"PdfPageLine(page_idx={self.page_idx}, pdf_pagenum={self.pdf_pagenum}, line_idx={self.line_idx}, text='{self.text}')"


@dataclass(frozen=True)
class PdfPageText(Sequence[PdfPageLine]):
    """Represents the text content of a PDF page.
    Attributes:
        page_idx (int) : The zero-based index of the page, relative to the start of the page range.
        pdf_pagenum (int) : The page number in the PDF file. This number is usually one-based.
        page_text (str) : The concatenated text content of the page.
        line_spans (Sequence[tuple[int, int]], computed) : A tuple of char index ranges for each line in the page text.
    """
    page_idx: int
    pdf_pagenum: int
    page_text: str

    def __len__(self) -> int:
        return len(self.line_spans)

    def __getitem__(self, line_idx: int) -> PdfPageLine:
        char_start, char_stop = self.line_spans[line_idx]
        return PdfPageLine(
            page_idx=self.page_idx,
            pdf_pagenum=self.pdf_pagenum,
            line_idx=line_idx,
            char_start=char_start,
            char_stop=char_stop,
            text=self.page_text[char_start:char_stop],
        )
    
    @cached_property
    def line_spans(self) -> Sequence[tuple[int, int]]:
        return tuple(StrDelim.get_line_spans(self.page_text))


@dataclass(frozen=True)
class PdfPageSequence(Sequence[PdfPageText]):
    """Represents the text content of a sequence of PDF pages.
    """
    pdf_first_pagenum: int
    full_text: str

    def __len__(self) -> int:
        return len(self.page_spans)

    def __getitem__(self, page_idx: int) -> PdfPageLine:
        char_start, char_stop = self.page_spans[page_idx]
        page_text = self.full_text[char_start:char_stop]
        pdf_pagenum = self.pdf_first_pagenum + page_idx
        return PdfPageText(
            page_idx=page_idx,
            pdf_pagenum=pdf_pagenum,
            page_text=page_text,
        )
    
    @cached_property
    def page_spans(self) -> Sequence[tuple[int, int]]:
        return tuple(StrDelim.get_page_spans(self.full_text))
