"""Contains generic data class for assigning to :class:`AntInterface`."""

from dataclasses import dataclass
from threading import Lock


@dataclass
class Data:
    """Generic data class for assigning to :class:`AntInterface`."""

    lock = Lock()
