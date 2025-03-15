from collections.abc import Iterable
from typing import Any, ForwardRef, Optional
import re
from dataclasses import dataclass
from dataclasses import asdict as _dtc_asdict

TextCleanup = ForwardRef("TextCleanup")
_Self = TextCleanup

@dataclass
class TextCleanupProfile():
    """A dataclass to store the enabled status of text cleanup methods."""
    strip: bool = True
    remove_ignored: bool = True
    scan_page_id: bool = True
    remove_vol_roman: bool = True
    replace_spacetab: bool = True
    replace_dotspace: bool = True
    reformat_pageid: bool = True


class TextCleanup:
    """Reduce noise and clean up text lines from the Intel 64 and IA-32 Architectures Software Developer's Manual.

    Attributes:
        text (list[str], mutable): The list of text lines at the current state of processing.
        profile (TextCleanupProfile): The profile of enabled processing methods to use.
        page_title (Optional[str]): The title of the current set of text lines, if found.
        page_id (Optional[str]): The page identifier for the current set of text lines, if found.
    """
    text: list[str]
    profile: TextCleanupProfile
    page_title: Optional[str]
    page_id: Optional[str]

    _LINE_IGNORED = (
        "", 
        "CONTENTS", 
        "PAGE",
    )

    _RE_VOL_ROMAN = re.compile(r"^([ivx]*)\s*\bVol\. (2[A-D])\s*([ivx]*)$")
    _RE_VOL_PAGEID = re.compile(r"^(.+)\bVol\. (2[A-D])\s*([1-9A-Z]-\d{1,3})?$")
    _RE_SPACETAB = re.compile(r"(\t|\s\s\s\s)(?:\t{1,}+|\s{4,}+)")
    _REPL_SPACETAB = r"    "
    _RE_DOTSPACE = re.compile(r"(?:\.\s){8,}+\.{0,}+")
    _REPL_DOTSPACE = r"  ...  "
    _RE_PAGEID = re.compile(r"(\b[1-9A-Z]-\d{1,3}\b)$")
    _REPL_PAGEID = r"page-\1"

    def __init__(
        self, 
        text: Iterable[str], 
        profile: Optional[TextCleanupProfile] = None,
    ):
        """Initializes with a list of text lines, and sets all processing methods to enabled by default.

        Args:
            text (Iterable[str]): The input list of text lines to process.
            profile (Optional[TextCleanupProfile]): The profile of enabled processing methods to use.
        """
        ### validations
        if profile is None:
            profile = TextCleanupProfile()
        if not isinstance(profile, TextCleanupProfile):
            raise TypeError(f"Expected a TextCleanupProfile object, got {type(profile).__name__}.")
        self._validate_profile(profile)
        ### init
        if isinstance(text, str):
            self.text = text.splitlines()
        else:
            self.text = list[str](text)
        self.profile = profile
        self.page_title = None
        self.page_id = None

    def get_profile(self) -> TextCleanupProfile:
        return self.profile
    
    def set_profile(self, profile: TextCleanupProfile) -> _Self:
        if not isinstance(profile, TextCleanupProfile):
            raise TypeError(f"Expected a TextCleanupProfile object, got {type(profile).__name__}.")
        self._validate_profile(profile)
        self.profile = profile
        return self
    
    def run_profile(self) -> dict[str, Any]:
        """Runs all profile enabled methods. For methods that have meaningful return values, the results are stored in the returned dictionary.
        """
        results = dict[str, Any]()
        for method, enabled in _dtc_asdict(self.profile).items():
            if not enabled:
                continue
            fn = getattr(self, method)
            result = fn()
            if result is not None and result is not self:
                results[method] = result
        return results

    def strip(self):
        """Strips leading and trailing whitespace from each line."""
        self.text = [line.strip() for line in self.text]
        return self

    def remove_ignored(self):
        """Removes lines that are ignored, such as empty lines and table of contents headers."""
        self.text = [line for line in self.text if line not in self._LINE_IGNORED]
        return self

    def scan_page_id(self) -> tuple[Optional[str], Optional[str]]:
        """Scans the text lines for a page identifier and page title, return both if found.
        """
        if self.page_title or self.page_id:
            return self.page_id, self.page_title
        for line in reversed(self.text):
            match = self._RE_VOL_PAGEID.search(line)
            if match:
                page_title = match.group(1).strip()
                page_id = match.group(3)
                if not page_id:
                    match2 = self._RE_PAGEID.search(page_title)
                    if match2:
                        page_id = match2.group(1)
                if page_id:
                    page_id = self._RE_PAGEID.sub(self._REPL_PAGEID, page_id)
                    self.page_id = page_id
                    self.page_title = page_title
                    break
        return self.page_id, self.page_title

    def remove_vol_roman(self):
        """Removes lines that contain volume numbers in Roman numerals."""
        self.text = [line for line in self.text if not self._RE_VOL_ROMAN.findall(line)]
        return self
    
    def replace_spacetab(self):
        """Removes excessively long sequences of spaces and tabs, replacing them with four spaces."""
        self.text = [self._RE_SPACETAB.sub(self._REPL_SPACETAB, line) for line in self.text]
        return self
    
    def replace_dotspace(self):
        """Replaces excessively long sequences of alternating dots and spaces with an ellipsis."""
        self.text = [self._RE_DOTSPACE.sub(self._REPL_DOTSPACE, line) for line in self.text]
        return self
    
    def reformat_pageid(self):
        """Reformats page identifiers for easier parsing."""
        self.text = [self._RE_PAGEID.sub(self._REPL_PAGEID, line) for line in self.text]
        return self

    def _validate_profile(self, profile: TextCleanupProfile):
        """Validates that all fields have corresponding methods, and values are bool."""
        for name, value in _dtc_asdict(profile).items():
            if not isinstance(name, str):
                raise TypeError(f"Expected a string for profile field name, got {type(name).__name__}.")
            if not name:
                raise ValueError("Profile field name cannot be an empty string.")
            if name.startswith("_"):
                raise ValueError(f"Profile field name '{name}' cannot start with an underscore.")
            fn = getattr(self, name, None)
            if not callable(fn):
                raise AttributeError(f"No method found for profile field '{name}'.")
            if not isinstance(value, bool):
                raise TypeError(f"Expected a boolean value for '{name}', got {type(value).__name__}.")
