"""
Maya command for the camera matcher plugin.
"""

import maya.api.OpenMaya as om
import maya.cmds as cmds
from typing import Any


class CameraMatcherCommand(om.MPxCommand):
    """
    Maya command for camera matcher functionality.
    """
    
    kPluginCmdName = "cameraMatcher"
    
    def __init__(self):
        """Initialize the command."""
        om.MPxCommand.__init__(self)
    
    @staticmethod
    def cmdCreator():
        """Create an instance of the command."""
        return CameraMatcherCommand()
    
    @staticmethod
    def newSyntax():
        """Define the command syntax."""
        syntax = om.MSyntax()
        
        # Add flags
        syntax.addFlag("-ui", "-userInterface", om.MSyntax.kNoArg)
        syntax.addFlag("-v", "-version", om.MSyntax.kNoArg)
        syntax.addFlag("-h", "-help", om.MSyntax.kNoArg)
        
        return syntax
    
    def doIt(self, args: Any) -> None:
        """Execute the command."""
        try:
            # Parse arguments
            arg_db = om.MArgDatabase(self.syntax(), args)
            
            if arg_db.isFlagSet("-help"):
                self._print_help()
                return
            
            if arg_db.isFlagSet("-version"):
                self._print_version()
                return
            
            if arg_db.isFlagSet("-userInterface"):
                self._open_ui()
                return
            
            # Default action - open UI
            self._open_ui()
            
        except Exception as e:
            om.MGlobal.displayError(f"Camera Matcher command failed: {str(e)}")
            raise
    
    def _print_help(self) -> None:
        """Print help information."""
        help_text = """
Camera Matcher Command

Usage: cameraMatcher [flags]

Flags:
    -ui, -userInterface    Open the Camera Matcher user interface
    -v,  -version         Print version information
    -h,  -help            Print this help message

Examples:
    cameraMatcher -ui      # Open the UI
    cameraMatcher          # Open the UI (default)
    cameraMatcher -help    # Show help
"""
        print(help_text)
    
    def _print_version(self) -> None:
        """Print version information."""
        from camera_matcher import __version__, __author__
        print(f"Camera Matcher Plugin v{__version__} by {__author__}")
    
    def _open_ui(self) -> None:
        """Open the camera matcher UI."""
        try:
            from camera_matcher.ui.main_window import CameraMatcherUI
            ui = CameraMatcherUI()
            ui.show()
        except Exception as e:
            om.MGlobal.displayError(f"Failed to open Camera Matcher UI: {str(e)}")
            raise