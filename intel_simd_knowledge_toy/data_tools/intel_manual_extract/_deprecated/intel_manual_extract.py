from typing import Optional, Union
from pathlib import Path
import os
from os.path import join as _pathjoin
import tempfile
import subprocess
import itertools
import shutil
from dataclasses import dataclass


from intel_simd_knowledge_toy.data_tools.intel_manual_extract._deprecated.utils import (
    PdfPageRange,
    DirtyPage,
    CleanedPage,
)

from intel_simd_knowledge_toy.data_tools.intel_manual_extract._deprecated.text_cleanup import (
    TextCleanup, 
    TextCleanupProfile,
)

class PdfManualExtract:
    """Extracts information from the Intel 64 and IA-32 Architectures Software Developer's Manual.

    This class uses the command-line utility pdftotext, which requires the poppler-utils to be installed.
    """

    _TOC_PROFILE = TextCleanupProfile(
        strip=True,
        remove_ignored=True,
        scan_page_id=True,
        remove_vol_roman=True,
        replace_spacetab=True,
        replace_dotspace=True,
        reformat_pageid=True,
    )

    _PAGES_PROFILE = TextCleanupProfile(
        strip=False,
        remove_ignored=False,
        scan_page_id=True,
        remove_vol_roman=False,
        replace_spacetab=False,
        replace_dotspace=False,
        reformat_pageid=True,
    )

    def __init__(
        self, 
        pdf_path: Union[str, Path], 
        data_dir: Union[str, Path], 
        page_range: PdfPageRange,
        toc_range: PdfPageRange,
        toc_profile: Optional[TextCleanupProfile] = None,
        pages_profile: Optional[TextCleanupProfile] = None,
    ):
        """Initializes the PdfManualExtract object.

        Args:
            pdf_path (str): The path to the PDF file to extract information from.
            data_dir (str): The path to the directory where extracted data will be stored.
            page_range (PdfPageRange): The first and last page number of the PDF file.
            toc_range (PdfPageRange): The first and last page number of the table of contents (TOC).
        """
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        if not os.path.isdir(data_dir):
            raise NotADirectoryError(f"Data directory not found: {data_dir}")
        self._pdf_path = str(pdf_path)
        self._data_dir = str(data_dir)
        self._page_range = page_range
        self._toc_range = toc_range
        self._toc_profile = toc_profile or self._TOC_PROFILE
        self._pages_profile = pages_profile or self._PAGES_PROFILE
        self._pdfpage_filenames = None
        self._cleanpage_filenames = None
        self._temp_src = tempfile.TemporaryDirectory(suffix="_src")
        self._temp_bin = tempfile.TemporaryDirectory(suffix="_bin")
        self._temp_txt = tempfile.TemporaryDirectory(suffix="_txt")
        self._temp_out = tempfile.TemporaryDirectory(suffix="_out")

    def run(self):
        """Runs the extraction process.
        """
        with self._temp_src as temp_src, self._temp_bin as temp_bin, self._temp_txt as temp_txt, self._temp_out as temp_out:
            pdf_copy_path = _pathjoin(temp_src, "input.pdf")
            toc_bash_path = _pathjoin(temp_bin, "toc.sh")
            toc_dirty_path = _pathjoin(temp_txt, "toc.txt")
            toc_clean_path = _pathjoin(temp_txt, "toc_clean.txt")
            pages_bash_path = _pathjoin(temp_bin, "pages.sh")
            dirty_pages = list[DirtyPage]()
            clean_pages = list[CleanedPage]()
            self._copy_pdf(self._pdf_path, pdf_copy_path)
            self._create_toc_bash(toc_bash_path, pdf_copy_path, self._toc_range, toc_dirty_path)
            self._run_toc_bash(toc_bash_path)
            self._clean_toc(toc_dirty_path, toc_clean_path)
            self._create_pages_bash(pages_bash_path, pdf_copy_path, self._page_range, temp_txt, dirty_pages)
            self._run_pages_bash(pages_bash_path)
            self._clean_pages(dirty_pages, temp_txt, clean_pages)
            self._extract_intrinsics(clean_pages)
            self._remove_dirty_files(toc_dirty_path, dirty_pages)
            self._move_clean_files(toc_clean_path, clean_pages, self._data_dir)
            pass
        pass

    def _copy_pdf(self, pdf_path: str, pdf_copy_path: str) -> None:
        """Copies the PDF file to the temporary source directory.
        """
        os.link(pdf_path, pdf_copy_path)
        
    def _create_toc_bash(
        self, 
        toc_bash_path: str, 
        pdf_input_path: str, 
        toc_range: PdfPageRange, 
    toc_dirty_path: str) -> None:
        """Creates a bash script which extracts the TOC page range into a single text file.
        """
        toc_first = toc_range.first
        toc_last = toc_range.last
        bash_lines = [
            '''#!/bin/bash -ex''',
            f"pdftotext -layout -f {toc_first} -l {toc_last} {pdf_input_path} {toc_dirty_path}",
        ]
        with open(toc_bash_path, "wt") as f:
            f.write("\n".join(bash_lines))

    def _run_toc_bash(self, toc_bash_path: str) -> None:
        """Runs the TOC bash script.
        """
        os.chmod(toc_bash_path, 0o700)
        subprocess.run(toc_bash_path, shell=True, check=True)

    def _clean_toc(self, toc_dirty_path: str, toc_clean_path: str) -> None:
        """Cleans the TOC text file.
        """
        with open(toc_dirty_path, "rt") as f:
            text = f.read().splitlines()
        cleanup = TextCleanup(text, self._toc_profile)
        cleanup.run_profile()
        with open(toc_clean_path, "wt") as f:
            f.write("\n".join(cleanup.text))

    def _create_pages_bash(
        self, 
        pages_bash_path: str, 
        pdf_input_path: str, 
        page_range: PdfPageRange, 
        temp_txt: str,
        dirty_pages: list[DirtyPage],
    ) -> None:
        """Creates a bash script which extracts the remaining pages range into single page text files.
        Args:
            temp_txt: The temporary text directory.
            pages_dirty_paths (list[DirtyPage], mutable): List for collecting the paths of extracted text files.
        """
        page_first = page_range.first
        page_last = page_range.last
        bash_lines = [
            '''#!/bin/bash -ex''',
        ]
        for pdf_pagenum in range(page_first, page_last + 1):
            page_txt_path = _pathjoin(temp_txt, f"page_{pdf_pagenum:05d}.txt")
            dirty_pages.append(DirtyPage(
                pdf_pagenum=pdf_pagenum,
                dirty_filename=page_txt_path,
            ))
            bash_lines.append(f"pdftotext -layout -f {pdf_pagenum} -l {pdf_pagenum} {pdf_input_path} {page_txt_path}")
        with open(pages_bash_path, "wt") as f:
            f.write("\n".join(bash_lines))

    def _run_pages_bash(self, pages_bash_path: str):
        """Runs the pages bash script.
        """
        os.chmod(pages_bash_path, 0o700)
        subprocess.run(pages_bash_path, shell=True, check=True)

    def _clean_pages(
        self, 
        dirty_pages: list[DirtyPage], 
        temp_txt: str, 
        clean_pages: list[CleanedPage],
    ) -> None:
        """Cleans the page text files.
        Args:
            pages_dirty_paths (list[str]): List of paths to the extracted text files.
            temp_txt (str): The temporary text directory for writing cleaned files.
            clean_pages (list[CleanedPage], mutable): List for collecting the cleaned page information.
        """
        for dirty_page in dirty_pages:
            pdf_pagenum = dirty_page.pdf_pagenum
            pdf_pagenum_str = f"{pdf_pagenum:05d}"
            page_dirty_path = dirty_page.dirty_filename
            with open(page_dirty_path, "rt") as f:
                text = f.read().splitlines()
            cleanup = TextCleanup(text, self._pages_profile)
            cleanup.run_profile()
            lines = cleanup.text
            ### NOTE: extracted page_id is not guaranteed to be unique or even present
            ### NOTE: output filenames must be unique
            page_id = cleanup.page_id
            page_title = cleanup.page_title
            if page_id is None:
                print(f"Unable to extract page ID from {page_dirty_path}, pdf page {pdf_pagenum}")
                page_id = pdf_pagenum_str
            if page_title is None:
                page_title = f"Page {pdf_pagenum}"
            page_id = self._fs_safe_str(page_id)
            page_clean_path = _pathjoin(temp_txt, f"clean_{pdf_pagenum_str}_{page_id}.txt")
            cleanpage_header = [
                "Page ID: " + page_id,
                "Page title: " + page_title,
                "",
                "---",
                "",
            ]
            with open(page_clean_path, "wt") as f:
                f.write("\n".join(itertools.chain(
                    cleanpage_header, 
                    lines,
                )))
            clean_pages.append(CleanedPage(
                pdf_pagenum=pdf_pagenum,
                page_id=page_id,
                page_title=page_title,
                header=cleanpage_header,
                text=lines,
                dirty_filename=page_dirty_path,
                clean_filename=page_clean_path,
            ))

    def _extract_intrinsics(self, clean_pages: list[CleanedPage]) -> None:
        """Extracts intrinsic information from the cleaned pages.
        Args:
            clean_pages (list[CleanedPage]): List of cleaned page information.
        """
        _PATTERN = '''Intel C/C++ Compiler Intrinsic Equivalent'''
        for clean_page in clean_pages:
            pdf_pagenum = clean_page.pdf_pagenum
            page_id = clean_page.page_id
            page_title = clean_page.page_title
            text = clean_page.text
            is_selected = False
            for idx, line in enumerate(text):
                if _PATTERN in line:
                    is_selected = True
                    continue
                if is_selected:
                    if not all(c in line for c in ('(', ')', '_', 'm')):
                        is_selected = False
                        continue
                    print(f"Page {pdf_pagenum} ({page_id}): {line}")

    def _remove_dirty_files(self, toc_dirty_path: str, dirty_pages: list[DirtyPage]) -> None:
        """Removes the dirty text files.
        Args:
            toc_dirty_path (str): The path to the TOC dirty text file.
            dirty_pages (list[DirtyPage]): List of paths to the extracted text files.
        """
        os.remove(toc_dirty_path)
        for dirty_page in dirty_pages:
            os.remove(dirty_page.dirty_filename)

    def _move_clean_files(
        self, 
        toc_clean_path: str, 
        clean_pages: list[CleanedPage], 
        data_dir: str,
    ) -> None:
        """Moves the cleaned text files to the user-specified data directory.
        Args:
            toc_clean_path (str): The path to the cleaned TOC text file.
            clean_pages (list[CleanedPage]): List of cleaned page information.
            data_dir (str): The path to the data directory.
        """
        toc_final_path = _pathjoin(data_dir, "toc.txt")
        shutil.move(toc_clean_path, toc_final_path)
        for clean_page in clean_pages:
            pdf_pagenum = clean_page.pdf_pagenum
            page_id = clean_page.page_id
            page_final_path = _pathjoin(data_dir, f"{pdf_pagenum}_{page_id}.txt")
            shutil.move(clean_page.clean_filename, page_final_path)

    @staticmethod
    def _fs_safe_str(s: str) -> str:
        """Returns a filesystem-safe version of the input string.
        """
        return "".join((
            c if any((c.isalnum(), c in ('-', '_'))) else "_" 
            for c in (s or "_")
        ))
