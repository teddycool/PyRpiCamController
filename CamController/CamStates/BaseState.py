# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

"""Common lifecycle contract for camera-controller states."""

from abc import ABC, abstractmethod
from typing import Any


class BaseState(ABC):
    """Base class for states managed by :class:`MainLoop`."""

    def __init__(self) -> None:
        self._settings: dict[str, Any] = {}

    @abstractmethod
    def initialize(self, settings: dict[str, Any]) -> None:
        """Allocate state resources using one consistent settings snapshot."""
        self._settings = settings

    @abstractmethod
    def update(self, context: Any) -> None:
        """Perform one state update."""

    @abstractmethod
    def cleanup(self) -> None:
        """Release resources when leaving or reloading the state."""

    @abstractmethod
    def dispose(self) -> None:
        """Release resources during final shutdown."""

    def get_runtime_status(self) -> dict[str, Any]:
        """Return state-owned runtime status for the generic status writer."""
        return {}
