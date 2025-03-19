from collections.abc import Collection, Iterable
from typing import overload, Union
import re
import functools

class SimdSpellcheck(Collection[str]):
    _FILENAME = "intel_simd_knowledge_toy/data/simd_spellcheck_list.txt"
    _keyword_list: list[str]
    _keyword_set: set[str]
    _keyword_lookup: dict[str, int]
    _morpheme_list: list[str]
    _morpheme_set: set[str]
    _morpheme_lookup: dict[str, int]

    def __init__(self):
        with open(self._FILENAME, "rt") as f:
            text = f.read()
        self._keyword_list = text.splitlines()
        self._keyword_set = set(self._keyword_list)
        self._keyword_lookup = {
            keyword: idx for idx, keyword in enumerate(self._keyword_list)
        }
        self._morpheme_list = []
        self._morpheme_set = set()
        self._morpheme_lookup = {}
        for keyword in self._keyword_list:
            for morpheme in keyword.split('_'):
                if morpheme:
                    self._add_morpheme(morpheme)

    def __len__(self) -> int:
        return len(self._keyword_list)

    def __contains__(self, keyword: str) -> bool:
        return keyword in self._keyword_set

    @overload
    def __getitem__(self, index: int) -> str:...

    @overload
    def __getitem__(self, slc: slice) -> list[str]:...

    def __getitem__(self, arg: Union[int, slice, range, Iterable[int]]) -> str:
        if isinstance(arg, (int, slice)):
            return self._keyword_list[arg]
        elif isinstance(arg, (range, Iterable)):
            return [self._keyword_list[i] for i in arg]
        else:
            raise TypeError("Only int, slice, range, and Iterable[int] are supported")

    def __iter__(self) -> Iterable[str]:
        return iter(self._keyword_list)

    def _as_list(self) -> list[str]:
        return self._keyword_list
    
    def _as_set(self) -> set[str]:
        return self._keyword_set
    
    def _as_lookup(self) -> dict[str, int]:
        return self._keyword_lookup

    def wildcard(self, spec: str) -> list[str]:
        p0 = self._re_compile("[0-9a-zA-Z_?*]+")
        if not p0.fullmatch(spec):
            raise ValueError("The spec must be a string of alphanumeric characters, underscores, question marks (each matching a single character), and asterisks (each matching a sequence of characters).")
        if '?' in spec:
            spec = spec.replace('?', '.')
        if '*' in spec:
            spec = spec.replace('*', '.*')
        p = self._re_compile(".*" + spec + ".*")
        return [keyword for keyword in self._keyword_list if p.fullmatch(keyword)]

    @classmethod
    @functools.lru_cache
    def _re_compile(cls, pattern: str) -> re.Pattern:
        return re.compile(pattern)

    def _add_morpheme(self, morpheme: str) -> int:
        idx = self._morpheme_lookup.get(morpheme, None)
        if idx is not None:
            return idx
        idx = len(self._morpheme_list)
        self._morpheme_list.append(morpheme)
        self._morpheme_set.add(morpheme)
        self._morpheme_lookup[morpheme] = idx
        return idx
    
    def list_morphemes(self) -> list[str]:
        return self._morpheme_list
