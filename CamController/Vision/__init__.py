# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

# Import pipeline subpackage - this makes Vision.pipeline accessible
from . import pipeline

# Import MotionDetector if needed
try:
    from .MotionDetector import MotionDetector
    __all__ = ['pipeline', 'MotionDetector']
except ImportError:
    # MotionDetector might have issues, just expose pipeline for now
    __all__ = ['pipeline']
