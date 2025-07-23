"""
Camera Matcher Package

A Maya plugin for matching cameras to images using 3D-2D locator correspondences.
"""

__version__ = "1.0.0"
__author__ = "Camera Matching Tool"

# Import main classes for easy access
from .core.camera_matcher import CameraMatcher
from .core.locator_pair import LocatorPair
from .core.camera_parameters import CameraParameters

__all__ = [
    "CameraMatcher",
    "LocatorPair", 
    "CameraParameters"
]