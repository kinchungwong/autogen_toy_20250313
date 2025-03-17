from pathlib import Path
from typing import Final, Optional, Union

class FileResource:
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
