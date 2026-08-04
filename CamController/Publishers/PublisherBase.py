# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

"""Common lifecycle contract for image publishers."""

from abc import ABC, abstractmethod
from typing import Any


class PublisherBase(ABC):
    """Interface implemented by all image publishers."""

    @abstractmethod
    def initialize(self, settings: dict[str, Any]) -> None:
        """Initialize the publisher from a settings snapshot."""

    @abstractmethod
    def publish(self, jpgimagedata: Any, metadata: dict[str, Any] | None = None) -> bool:
        """Publish an image and return whether it succeeded."""

    @abstractmethod
    def cleanup(self) -> None:
        """Release publisher resources."""
