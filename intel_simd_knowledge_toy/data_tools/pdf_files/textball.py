from pathlib import Path
from typing import Final, Optional, Union
from dataclasses import dataclass
import os
from os.path import join as _pathjoin
import tempfile
import subprocess
import shutil


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


class PdfToTextSubprocess:
    _pdf_path: Path
    _page_range: Optional[PdfPageRange]
    _keep_layout: bool
    _data: bytes

    def __init__(
        self,
        pdf_path: Union[str, Path],
        *,
        page_range: Optional[PdfPageRange] = None,
        keep_layout: bool = True,
    ):
        if not self._check_pdftotext_exist():
            raise RuntimeError("The 'pdftotext' utility from Poppler is not available.")
        pdf_path = Path(pdf_path)
        if not pdf_path.is_file():
            raise FileNotFoundError(f"The file '{pdf_path}' does not exist.")
        if not isinstance(page_range, (PdfPageRange, type(None))):
            raise TypeError("The 'page_range' argument must be a PdfPageRange object or otherwise None.")
        self._pdf_path = pdf_path
        self._page_range = page_range
        self._keep_layout = keep_layout
        self._data = b''

    @property
    def pdf_path(self) -> Path:
        return self._pdf_path

    @property
    def data(self) -> bytes:
        return self._data

    def run(self):
        with tempfile.TemporaryDirectory(suffix="_pdf") as temp_dir:
            pdf_orig_path = self._pdf_path
            pdf_copy_path = Path(temp_dir) / pdf_orig_path.name
            text_path = Path(temp_dir) / f"{pdf_orig_path.stem}.txt"
            shutil.copy(pdf_orig_path, pdf_copy_path)
            self._run_pdftotext(pdf_copy_path, text_path)
            self._data = self._load_text_bytes(text_path)

    def _run_pdftotext(self, pdf_path: Path, text_path: Path):
        cmd_args = ["pdftotext"]
        if self._keep_layout:
            cmd_args.append("-layout")
        if self._page_range:
            cmd_args.extend(["-f", str(self._page_range.first)])
            cmd_args.extend(["-l", str(self._page_range.last)])
        cmd_args.extend([str(pdf_path), str(text_path)])
        subprocess.run(cmd_args, check=True)

    def _load_text_bytes(self, text_path: Path) -> bytes:
        with text_path.open("rb") as f:
            return f.read()
    
    def _check_pdftotext_exist(self) -> bool:
        return shutil.which("pdftotext") is not None


class _FileResource:
    """Represents a file resource that may or may not be specified and may or may not be present.

    Attributes:
        path ([Path|None], mutable) : The path to the file resource. Can be None. Can be assigned after initialization.
        was_specified (Final[bool]) : Whether the path was specified at initialization.
        was_present (Final[bool]) : Whether the file resource was present at initialization.
        is_specified (bool, @property) : Whether the path is specified.
        is_present (bool, @property) : Whether the file resource is present.
    """
    path: Optional[Path]
    was_specified: Final[bool]
    was_present: Final[bool]

    def __init__(self, path: Optional[Union[str, Path]]):
        self.path = Path(path) if path else None
        self.was_specified = self.path is not None
        self.was_present = self.was_specified and self.path.is_file()

    @property
    def is_specified(self) -> bool:
        return self.path is not None

    @property
    def is_present(self) -> bool:
        return self.path is not None and self.path.is_file()


class TextBall:
    """Represents a text resource that can be loaded from a PDF file, a text file, or a tarball file.
    """
    _res_pdf: _FileResource
    _res_text: _FileResource
    _res_tarball: _FileResource
    _bytes: bytes
    _page_breaks: list[int]

    def __init__(
        self,
        *,
        pdf_path: Union[str, Path, None] = None,
        text_path: Union[str, Path, None] = None,
        tarball_path: Union[str, Path, None] = None,
    ):
        self._res_pdf = _FileResource(pdf_path)
        self._res_text = _FileResource(text_path)
        self._res_tarball = _FileResource(tarball_path)
        if all(not r.was_specified for r in (self._res_pdf, self._res_text, self._res_tarball)):
            raise ValueError("At least one of the PDF file, the text file, or the tarball file must be specified.")
        if all(not r.was_present for r in (self._res_pdf, self._res_text, self._res_tarball)):
            raise FileNotFoundError("Neither the PDF file, the text file, nor the tarball file exists.")
        self._bytes = b''
        self._page_breaks = list[int]()

    def get_bytes(self) -> bytes:
        self._ensure_bytes_loaded()
        return self._bytes
    
    def _ensure_bytes_loaded(self) -> None: 
        if self._bytes:
            return
        if self._res_text.is_present:
            self._load_text_bytes()
            return
        elif self._res_pdf.is_present:
            self._load_pdf_bytes()
            return
        # elif self._res_tarball.is_present:
        raise NotImplementedError("Loading from tarball is not implemented yet.")
        
    def _load_text_bytes(self) -> None:
        assert self._res_text.is_present
        with self._res_text.path.open("rb") as f:
            self._bytes = f.read()
        self._fetch_pagebreaks()
    
    def _load_pdf_bytes(self) -> None:
        assert self._res_pdf.is_present
        pdf_to_text = PdfToTextSubprocess(self._res_pdf.path)
        pdf_to_text.run()
        self._bytes = pdf_to_text.data
        self._fetch_pagebreaks()

    def _fetch_pagebreaks(self):
        ### NOTE: we only use form-feed (\x0c) because it is the default page break character used by pdftotext
        _FORM_FEED: Final[bytes] = b"\f"
        bs = self._bytes
        if not bs:
            return
        pb = list[int]()
        idx_start = 0
        idx_end = len(bs)
        while idx_start < idx_end:
            idx = bs.find(_FORM_FEED, idx_start, idx_end)
            if idx == -1:
                break
            pb.append(idx)
            idx_start = idx + 1
        self._page_breaks.clear()
        self._page_breaks.extend(pb)

    def get_page_count(self) -> int:
        self._ensure_bytes_loaded()
        if len(self._bytes) == 0:
            return 0
        return len(self._page_breaks) + 1

    def get_page_bytes(self, page_idx: int) -> bytes:
        self._ensure_bytes_loaded()
        page_count = self.get_page_count()
        if not (0 <= page_idx < page_count):
            raise ValueError(f"Page index {page_idx} (zero-based) is out of range. Page count: {page_count}")
        bs = self._bytes
        pb = self._page_breaks
        page_count = len(pb) + 1
        pb_start = 0 if page_idx == 0 else pb[page_idx - 1] + 1
        pb_end = pb[page_idx] if page_idx < len(pb) else len(bs)
        return bs[pb_start:pb_end]

    def get_page_lines(self, page_idx: int) -> list[str]:
        ### TODO: find out what encoding is used by pdftotext
        _ENCODING: Final[str] = "utf-8"
        self._ensure_bytes_loaded()
        return self.get_page_bytes(page_idx).decode(_ENCODING).splitlines()
