"""
Maya Camera Matcher Plugin

A Maya plugin for matching cameras to images using 3D-2D locator correspondences.
"""

import maya.api.OpenMaya as om
import maya.cmds as cmds
import maya.mel as mel
from typing import Any

# Plugin information
kPluginName = "CameraMatcher"
kVersion = "1.0.0"
kAuthor = "Camera Matching Tool"
kRequiredAPIVersion = "Any"

def maya_useNewAPI():
    """
    The presence of this function tells Maya that the plugin produces, and
    expects to be passed, objects created using the Maya Python API 2.0.
    """
    pass

def initializePlugin(mobject: Any) -> None:
    """Initialize the plugin when Maya loads it."""
    mplugin = om.MFnPlugin(mobject, kAuthor, kVersion, kRequiredAPIVersion)
    
    try:
        # Import and register the camera matcher command
        from camera_matcher.commands import CameraMatcherCommand
        mplugin.registerCommand(
            CameraMatcherCommand.kPluginCmdName,
            CameraMatcherCommand.cmdCreator,
            CameraMatcherCommand.newSyntax
        )
        
        # Add menu item
        _add_menu_item()
        
        print(f"Successfully loaded {kPluginName} v{kVersion}")
        
    except Exception as e:
        om.MGlobal.displayError(f"Failed to register {kPluginName}: {str(e)}")
        raise

def uninitializePlugin(mobject: Any) -> None:
    """Uninitialize the plugin when Maya unloads it."""
    mplugin = om.MFnPlugin(mobject)
    
    try:
        # Remove menu item
        _remove_menu_item()
        
        # Deregister the command
        from camera_matcher.commands import CameraMatcherCommand
        mplugin.deregisterCommand(CameraMatcherCommand.kPluginCmdName)
        
        print(f"Successfully unloaded {kPluginName}")
        
    except Exception as e:
        om.MGlobal.displayError(f"Failed to unregister {kPluginName}: {str(e)}")
        raise

def _add_menu_item() -> None:
    """Add the Camera Matcher menu item to Maya's main menu."""
    try:
        # Check if the menu already exists
        if cmds.menu("cameraMatcherMenu", exists=True):
            cmds.deleteUI("cameraMatcherMenu")
        
        # Get the main Maya window
        main_window = mel.eval('$temp1=$gMainWindow')
        
        # Create the Camera Matcher menu
        cmds.menu(
            "cameraMatcherMenu",
            label="Camera Matcher",
            parent=main_window,
            tearOff=True
        )
        
        # Add menu items
        cmds.menuItem(
            label="Open Camera Matcher",
            command="from camera_matcher.ui.main_window import CameraMatcherUI; CameraMatcherUI().show()",
            parent="cameraMatcherMenu"
        )
        
        cmds.menuItem(divider=True, parent="cameraMatcherMenu")
        
        cmds.menuItem(
            label="About",
            command=f"cmds.confirmDialog(title='About', message='{kPluginName} v{kVersion}\\n{kAuthor}', button=['OK'])",
            parent="cameraMatcherMenu"
        )
        
    except Exception as e:
        print(f"Warning: Could not create menu item: {str(e)}")

def _remove_menu_item() -> None:
    """Remove the Camera Matcher menu item from Maya's main menu."""
    try:
        if cmds.menu("cameraMatcherMenu", exists=True):
            cmds.deleteUI("cameraMatcherMenu")
    except Exception as e:
        print(f"Warning: Could not remove menu item: {str(e)}")