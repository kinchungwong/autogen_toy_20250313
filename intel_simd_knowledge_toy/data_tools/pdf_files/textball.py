from pathlib import Path
from typing import Final, Union

from intel_simd_knowledge_toy.data_tools.pdf_files.text_data_model import (
    PdfPageSequence,
)
from intel_simd_knowledge_toy.data_tools.pdf_files.internal_data_model import (
    FileResource,
)
from intel_simd_knowledge_toy.data_tools.pdf_files.pdftotext_subprocess import (
    PdfToTextSubprocess,
)


class TextBall:
    """Represents a text resource that can be loaded from a PDF file, a text file, or a tarball file.
    """
    _res_pdf: FileResource
    _res_text: FileResource
    _res_tarball: FileResource
    _text: str
    _data_model: PdfPageSequence

    _ENCODING: Final[str] = "utf-8"

    def __init__(
        self,
        *,
        pdf_path: Union[str, Path, None] = None,
        text_path: Union[str, Path, None] = None,
        tarball_path: Union[str, Path, None] = None,
    ):
        self._res_pdf = FileResource(pdf_path)
        self._res_text = FileResource(text_path)
        self._res_tarball = FileResource(tarball_path)
        all_res = (self._res_pdf, self._res_text, self._res_tarball)
        if all(not r.was_specified for r in all_res):
            raise ValueError("At least one of the PDF file, the text file, or the tarball file must be specified.")
        if all(not r.was_present for r in all_res):
            raise FileNotFoundError("Neither the PDF file, the text file, nor the tarball file exists.")
        self._text = ""
        self._data_model = PdfPageSequence(tuple[int](), self._text)

    def get_pages(self) -> PdfPageSequence:
        self._ensure_loaded()
        return self._data_model

    def get_full_text(self) -> str:
        self._ensure_loaded()
        return self._text
    
    def _ensure_loaded(self) -> None: 
        if self._text:
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
            data: bytes = f.read()
        self._text = data.decode(self._ENCODING)
        self._post_load()
    
    def _load_pdf_bytes(self) -> None:
        assert self._res_pdf.is_present
        pdf_to_text = PdfToTextSubprocess(self._res_pdf.path)
        pdf_to_text.run()
        data: bytes = pdf_to_text.data
        if self._res_text.was_specified and not self._res_text.is_present:
            try:
                with self._res_text.path.open("wb") as f:
                    f.write(data)
            except Exception as e:
                print(f"Failed to write PDF text to file: {self._res_text.path}. Error: {e}")
        self._text = data.decode(self._ENCODING)
        self._post_load()

    def _load_tarball_bytes(self) -> None:
        assert self._res_tarball.is_present
        raise NotImplementedError("Loading from tarball is not implemented yet.")

    def _post_load(self) -> None:
        if not self._text:
            return
        self._init_data_model()
        self._save_tarball_if_specified()

    def _init_data_model(self) -> None:
        ### TODO 
        # Currently this class does not allow selecting a page range for pdftotext.
        # If this feature is ever implemented, set this value accordingly.
        ###
        pdf_first_pagenum = 1
        self._data_model = PdfPageSequence(
            pdf_first_pagenum=pdf_first_pagenum,
            full_text=self._text,
        )

    def _save_tarball_if_specified(self) -> None:
        if not self._res_tarball.was_specified:
            return
        if self._res_tarball.is_present:
            return
        ### Not implemented yet
        pass
