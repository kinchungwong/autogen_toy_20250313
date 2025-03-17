from pathlib import Path
from typing import Optional, Union
import tempfile
import subprocess
import shutil

from intel_simd_knowledge_toy.data_tools.pdf_files.text_data_model import (
    PdfPageRange,
)


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
