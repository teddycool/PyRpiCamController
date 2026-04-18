# This software-file was created by Pär Sundbäck and is part of the PyRpiCamController project
# The complete project is available at: https://github.com/teddycool/PyRpiCamController
# The project is licensed under GNU GPLv3, check the LICENSE file for details.

__author__ = 'teddycool'

# Import pipeline subpackage - this makes Vision.pipeline accessible
from . import pipeline

# Import VisionManager and DetectedObject from pipeline
try:
    from .VisionManager import VisionManager
    from .pipeline.processors.ObjectDetectionProcessor import DetectedObject
    __all__ = ['pipeline', 'VisionManager', 'DetectedObject']
except ImportError as e:
    # Some components might have issues, just expose pipeline for now
    print(f"Warning: Could not import all Vision components: {e}")
    __all__ = ['pipeline']
