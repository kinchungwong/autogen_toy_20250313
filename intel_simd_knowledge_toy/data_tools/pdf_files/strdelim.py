from functools import lru_cache
import re

__all__ = [
    "StrDelim",
]


class StrDelim:
    @classmethod
    def get_line_spans(cls, text: str) -> list[tuple[int, int]]:
        return cls.get_spans(text, cls.get_linebreak_regex())

    @classmethod
    def get_page_spans(cls, text: str) ->   list[tuple[int, int]]:
        return cls.get_spans(text, cls.get_pagebreak_regex())
    
    @classmethod
    def get_spans(cls, text: str, pattern: re.Pattern) -> list[tuple[int, int]]:
        if not isinstance(pattern, re.Pattern):
            raise TypeError("pattern must be a compiled regex pattern")
        char_count = len(text)
        delim_spans = list[tuple[int, int]]()
        delim_spans.append((0, 0))
        delim_spans.extend((m.start(), m.end()) for m in pattern.finditer(text))
        delim_spans.append((char_count, char_count))
        content_spans = [
            (delim_spans[i-1][1], delim_spans[i][0])
            for i in range(1, len(delim_spans))
        ]
        return content_spans

    @classmethod
    @lru_cache(maxsize=1)
    def get_linebreak_regex(cls) -> re.Pattern:
        ### NOTE 
        #   Form-feed ("\f") is redundant; already used as page break by pdftotext.
        #   Included because it is part of "universal newlines" per Python docs.
        ###
        _UNIVERSAL_NEWLINES = [
            r"\n",
            r"\r",
            r"\r\n",
            r"\v",
            r"\f",
            r"\x1c",
            r"\x1d",
            r"\x1e",
            r"\x85",
            r"\u2028",
            r"\u2029",
        ]
        s = '|'.join(_UNIVERSAL_NEWLINES)
        return re.compile(s, flags=re.NOFLAG)

    @classmethod
    @lru_cache(maxsize=1)
    def get_pagebreak_regex(cls) -> re.Pattern:
        _PAGE_BREAKS = [
            r"\f",
            r"\x1a",
            r"\x00",
            r"\x03",
            r"\x04",
        ]
        s = '|'.join(_PAGE_BREAKS)
        return re.compile(s, flags=re.NOFLAG)
