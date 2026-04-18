# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

from .CropProcessor import CropProcessor
from .MotionDetectionProcessor import MotionDetectionProcessor
from .ObjectDetectionProcessor import ObjectDetectionProcessor, DetectedObject

__all__ = ['CropProcessor', 'MotionDetectionProcessor', 'ObjectDetectionProcessor', 'DetectedObject']