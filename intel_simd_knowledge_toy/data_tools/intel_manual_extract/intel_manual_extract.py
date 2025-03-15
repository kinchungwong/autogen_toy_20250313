from typing import Optional
import os
import tempfile
import subprocess
import itertools

from intel_simd_knowledge_toy.data_tools.intel_manual_extract.utils import PdfPageRange
from intel_simd_knowledge_toy.data_tools.intel_manual_extract.text_cleanup import (
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
        pdf_path: str, 
        data_dir: str, 
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
        self._pdf_path = pdf_path
        self._data_dir = data_dir
        self._page_range = page_range
        self._toc_range = toc_range
        self._toc_profile = toc_profile or self._TOC_PROFILE
        self._pages_profile = pages_profile or self._PAGES_PROFILE
        self._pdfpage_filenames = None
        self._cleanpage_filenames = None

    def _run_toc_bash(self):
        """Creates a bash script which extracts the TOC page range into a single text file.
        """
        ntf_args = {
            "mode": "wt",
            "delete": True, 
            "delete_on_close": False,
        }
        toc_first = self._toc_range.first
        toc_last = self._toc_range.last
        pdf_path = self._pdf_path
        toc_txt_path = os.path.join(self._data_dir, "toc.txt")
        bash_lines = [
            '''#!/bin/bash -ex''',
            f"pdftotext -layout -f {toc_first} -l {toc_last} {pdf_path} {toc_txt_path}",
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            ntf_args["dir"] = tmpdir
            with tempfile.NamedTemporaryFile(**ntf_args) as bashfile:
                bashfile.write("\n".join(bash_lines))
                bashfile.close()
                subprocess.run(["chmod", "u+x", bashfile.name])
                subprocess.run(["bash", bashfile.name])

    def _run_toc_clean(self):
        toc_txt_path = os.path.join(self._data_dir, "toc.txt")
        toc_clean_path = os.path.join(self._data_dir, "toc_clean.txt")
        with open(toc_txt_path, "rt") as f:
            text = f.read().splitlines()
        cleanup = TextCleanup(text, self._toc_profile)
        cleanup.run_profile()
        with open(toc_clean_path, "wt") as f:
            f.write("\n".join(cleanup.text))
        return cleanup

    def _run_pages_bash(self):
        """Creates a bash script which extracts the remaining pages range into single page text files.
        """
        ntf_args = {
            "mode": "wt",
            "delete": True, 
            "delete_on_close": False,
        }
        pdf_path = self._pdf_path
        bash_lines = [
            '''#!/bin/bash -ex''',
        ]
        page_first = self._toc_range.last + 1
        page_last = self._page_range.last
        pdfpage_filenames = list[str]()
        for pdf_pagenum in range(page_first, page_last + 1):
            txt_path = os.path.join(self._data_dir, f"page_{pdf_pagenum:04d}.txt")
            pdfpage_filenames.append(txt_path)
            bash_lines.append(f"pdftotext -layout -f {pdf_pagenum} -l {pdf_pagenum} {pdf_path} {txt_path}")
        with tempfile.TemporaryDirectory() as tmpdir:
            ntf_args["dir"] = tmpdir
            with tempfile.NamedTemporaryFile(**ntf_args) as bashfile:
                bashfile.write("\n".join(bash_lines))
                bashfile.close()
                subprocess.run(["chmod", "u+x", bashfile.name])
                subprocess.run(["bash", bashfile.name])
        self._pdfpage_filenames = pdfpage_filenames

    def _run_pages_clean(self):
        cleanpage_filenames = list[str]()
        for txt_path in self._pdfpage_filenames:
            with open(txt_path, "rt") as f:
                text = f.read().splitlines()
            cleanup = TextCleanup(text, self._pages_profile)
            cleanup.run_profile()
            lines = cleanup.text
            if cleanup.page_id is None:
                raise ValueError(f"Page ID not found in {txt_path}")
            cleanpage_filename = os.path.join(self._data_dir, f"clean_{cleanup.page_id}.txt")
            cleanpage_filenames.append(cleanpage_filename)
            cleanpage_header = [
                "Page ID: " + cleanup.page_id,
                "Page title: " + cleanup.page_title,
                "",
                "---",
                "",
            ]
            with open(cleanpage_filename, "wt") as f:
                f.write("\n".join(itertools.chain(cleanpage_header, lines)))
