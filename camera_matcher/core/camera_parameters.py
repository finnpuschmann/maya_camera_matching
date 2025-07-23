"""
CameraParameters class for managing camera settings and optimization constraints.
"""

from typing import Dict, Tuple, Optional, Any
import maya.cmds as cmds
from dataclasses import dataclass, field


@dataclass
class ParameterConstraints:
    """Constraints for a camera parameter during optimization."""
    is_locked: bool = False
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    
    def clamp_value(self, value: float) -> float:
        """Clamp a value to the constraint bounds."""
        if self.min_value is not None:
            value = max(value, self.min_value)
        if self.max_value is not None:
            value = min(value, self.max_value)
        return value


class CameraParameters:
    """
    Manages camera parameters and their optimization constraints.
    """
    
    def __init__(self, camera_name: str):
        """
        Initialize camera parameters from a Maya camera.
        
        Args:
            camera_name: Name of the camera transform or shape in Maya
        """
        self.camera_name: str = camera_name
        self._camera_shape: Optional[str] = None
        self._camera_transform: Optional[str] = None
        
        # Initialize parameter values
        self._translation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._focal_length: float = 35.0
        self._film_offset_x: float = 0.0
        self._film_offset_y: float = 0.0
        self._film_aperture_h: float = 36.0
        self._film_aperture_v: float = 24.0
        
        # Initialize constraints
        self._constraints: Dict[str, ParameterConstraints] = {
            'translate_x': ParameterConstraints(),
            'translate_y': ParameterConstraints(),
            'translate_z': ParameterConstraints(),
            'rotate_x': ParameterConstraints(),
            'rotate_y': ParameterConstraints(),
            'rotate_z': ParameterConstraints(),
            'focal_length': ParameterConstraints(min_value=1.0, max_value=1000.0),
            'film_offset_x': ParameterConstraints(min_value=-50.0, max_value=50.0),
            'film_offset_y': ParameterConstraints(min_value=-50.0, max_value=50.0),
        }
        
        # Load current values from Maya camera
        self._update_from_maya()
    
    def _update_from_maya(self) -> None:
        """Update parameter values from the Maya camera."""
        if not cmds.objExists(self.camera_name):
            raise RuntimeError(f"Camera '{self.camera_name}' does not exist in scene")
        
        # Determine camera transform and shape
        if cmds.nodeType(self.camera_name) == 'camera':
            self._camera_shape = self.camera_name
            camera_transforms = cmds.listRelatives(self.camera_name, parent=True, type='transform')
            if camera_transforms:
                self._camera_transform = camera_transforms[0]
            else:
                raise RuntimeError(f"Camera shape '{self.camera_name}' has no transform parent")
        else:
            self._camera_transform = self.camera_name
            camera_shapes = cmds.listRelatives(self.camera_name, shapes=True, type='camera')
            if camera_shapes:
                self._camera_shape = camera_shapes[0]
            else:
                raise RuntimeError(f"Transform '{self.camera_name}' has no camera shape")
        
        # Get transform values
        translation = cmds.xform(self._camera_transform, query=True, worldSpace=True, translation=True)
        rotation = cmds.xform(self._camera_transform, query=True, worldSpace=True, rotation=True)
        
        self._translation = (translation[0], translation[1], translation[2])
        self._rotation = (rotation[0], rotation[1], rotation[2])
        
        # Get camera shape values
        self._focal_length = cmds.getAttr(f"{self._camera_shape}.focalLength")
        self._film_offset_x = cmds.getAttr(f"{self._camera_shape}.horizontalFilmOffset") * 25.4  # Convert to mm
        self._film_offset_y = cmds.getAttr(f"{self._camera_shape}.verticalFilmOffset") * 25.4   # Convert to mm
        self._film_aperture_h = cmds.getAttr(f"{self._camera_shape}.horizontalFilmAperture") * 25.4
        self._film_aperture_v = cmds.getAttr(f"{self._camera_shape}.verticalFilmAperture") * 25.4
    
    @property
    def camera_transform(self) -> str:
        """Get the camera transform name."""
        return self._camera_transform or self.camera_name
    
    @property
    def camera_shape(self) -> str:
        """Get the camera shape name."""
        return self._camera_shape or self.camera_name
    
    @property
    def translation(self) -> Tuple[float, float, float]:
        """Get camera translation."""
        return self._translation
    
    @translation.setter
    def translation(self, value: Tuple[float, float, float]) -> None:
        """Set camera translation."""
        self._translation = value
    
    @property
    def rotation(self) -> Tuple[float, float, float]:
        """Get camera rotation."""
        return self._rotation
    
    @rotation.setter
    def rotation(self, value: Tuple[float, float, float]) -> None:
        """Set camera rotation."""
        self._rotation = value
    
    @property
    def focal_length(self) -> float:
        """Get camera focal length."""
        return self._focal_length
    
    @focal_length.setter
    def focal_length(self, value: float) -> None:
        """Set camera focal length."""
        constrained_value = self._constraints['focal_length'].clamp_value(value)
        self._focal_length = constrained_value
    
    @property
    def film_offset_x(self) -> float:
        """Get camera horizontal film offset."""
        return self._film_offset_x
    
    @film_offset_x.setter
    def film_offset_x(self, value: float) -> None:
        """Set camera horizontal film offset."""
        constrained_value = self._constraints['film_offset_x'].clamp_value(value)
        self._film_offset_x = constrained_value
    
    @property
    def film_offset_y(self) -> float:
        """Get camera vertical film offset."""
        return self._film_offset_y
    
    @film_offset_y.setter
    def film_offset_y(self, value: float) -> None:
        """Set camera vertical film offset."""
        constrained_value = self._constraints['film_offset_y'].clamp_value(value)
        self._film_offset_y = constrained_value
    
    @property
    def film_aperture_h(self) -> float:
        """Get camera horizontal film aperture."""
        return self._film_aperture_h
    
    @property
    def film_aperture_v(self) -> float:
        """Get camera vertical film aperture."""
        return self._film_aperture_v
    
    def get_parameter_value(self, param_name: str) -> float:
        """
        Get the value of a specific parameter.
        
        Args:
            param_name: Name of the parameter
            
        Returns:
            Parameter value
        """
        if param_name == 'translate_x':
            return self._translation[0]
        elif param_name == 'translate_y':
            return self._translation[1]
        elif param_name == 'translate_z':
            return self._translation[2]
        elif param_name == 'rotate_x':
            return self._rotation[0]
        elif param_name == 'rotate_y':
            return self._rotation[1]
        elif param_name == 'rotate_z':
            return self._rotation[2]
        elif param_name == 'focal_length':
            return self._focal_length
        elif param_name == 'film_offset_x':
            return self._film_offset_x
        elif param_name == 'film_offset_y':
            return self._film_offset_y
        else:
            raise ValueError(f"Unknown parameter: {param_name}")
    
    def set_parameter_value(self, param_name: str, value: float) -> None:
        """
        Set the value of a specific parameter.
        
        Args:
            param_name: Name of the parameter
            value: New value
        """
        # Apply constraints
        if param_name in self._constraints:
            value = self._constraints[param_name].clamp_value(value)
        
        if param_name == 'translate_x':
            self._translation = (value, self._translation[1], self._translation[2])
        elif param_name == 'translate_y':
            self._translation = (self._translation[0], value, self._translation[2])
        elif param_name == 'translate_z':
            self._translation = (self._translation[0], self._translation[1], value)
        elif param_name == 'rotate_x':
            self._rotation = (value, self._rotation[1], self._rotation[2])
        elif param_name == 'rotate_y':
            self._rotation = (self._rotation[0], value, self._rotation[2])
        elif param_name == 'rotate_z':
            self._rotation = (self._rotation[0], self._rotation[1], value)
        elif param_name == 'focal_length':
            self._focal_length = value
        elif param_name == 'film_offset_x':
            self._film_offset_x = value
        elif param_name == 'film_offset_y':
            self._film_offset_y = value
        else:
            raise ValueError(f"Unknown parameter: {param_name}")
    
    def get_constraints(self, param_name: str) -> ParameterConstraints:
        """
        Get constraints for a parameter.
        
        Args:
            param_name: Name of the parameter
            
        Returns:
            Parameter constraints
        """
        return self._constraints.get(param_name, ParameterConstraints())
    
    def set_constraints(self, param_name: str, constraints: ParameterConstraints) -> None:
        """
        Set constraints for a parameter.
        
        Args:
            param_name: Name of the parameter
            constraints: New constraints
        """
        self._constraints[param_name] = constraints
        
        # Re-apply constraints to current value
        current_value = self.get_parameter_value(param_name)
        constrained_value = constraints.clamp_value(current_value)
        if constrained_value != current_value:
            self.set_parameter_value(param_name, constrained_value)
    
    def is_parameter_locked(self, param_name: str) -> bool:
        """
        Check if a parameter is locked for optimization.
        
        Args:
            param_name: Name of the parameter
            
        Returns:
            True if locked, False otherwise
        """
        return self._constraints.get(param_name, ParameterConstraints()).is_locked
    
    def lock_parameter(self, param_name: str, locked: bool = True) -> None:
        """
        Lock or unlock a parameter for optimization.
        
        Args:
            param_name: Name of the parameter
            locked: Whether to lock the parameter
        """
        if param_name not in self._constraints:
            self._constraints[param_name] = ParameterConstraints()
        self._constraints[param_name].is_locked = locked
    
    def apply_to_maya(self) -> None:
        """Apply current parameter values to the Maya camera."""
        if not cmds.objExists(self.camera_name):
            raise RuntimeError(f"Camera '{self.camera_name}' does not exist in scene")
        
        # Apply transform values
        cmds.xform(self._camera_transform, worldSpace=True, translation=self._translation)
        cmds.xform(self._camera_transform, worldSpace=True, rotation=self._rotation)
        
        # Apply camera shape values
        cmds.setAttr(f"{self._camera_shape}.focalLength", self._focal_length)
        cmds.setAttr(f"{self._camera_shape}.horizontalFilmOffset", self._film_offset_x / 25.4)  # Convert from mm
        cmds.setAttr(f"{self._camera_shape}.verticalFilmOffset", self._film_offset_y / 25.4)   # Convert from mm
    
    def get_parameter_vector(self) -> list[float]:
        """
        Get all unlocked parameters as a vector for optimization.
        
        Returns:
            List of parameter values for unlocked parameters
        """
        params = []
        param_names = [
            'translate_x', 'translate_y', 'translate_z',
            'rotate_x', 'rotate_y', 'rotate_z',
            'focal_length', 'film_offset_x', 'film_offset_y'
        ]
        
        for param_name in param_names:
            if not self.is_parameter_locked(param_name):
                params.append(self.get_parameter_value(param_name))
        
        return params
    
    def set_parameter_vector(self, values: list[float]) -> None:
        """
        Set all unlocked parameters from a vector.
        
        Args:
            values: List of parameter values for unlocked parameters
        """
        param_names = [
            'translate_x', 'translate_y', 'translate_z',
            'rotate_x', 'rotate_y', 'rotate_z',
            'focal_length', 'film_offset_x', 'film_offset_y'
        ]
        
        unlocked_params = [name for name in param_names if not self.is_parameter_locked(name)]
        
        if len(values) != len(unlocked_params):
            raise ValueError(f"Expected {len(unlocked_params)} values, got {len(values)}")
        
        for i, param_name in enumerate(unlocked_params):
            self.set_parameter_value(param_name, values[i])
    
    def get_unlocked_parameter_names(self) -> list[str]:
        """
        Get names of all unlocked parameters.
        
        Returns:
            List of parameter names that are not locked
        """
        param_names = [
            'translate_x', 'translate_y', 'translate_z',
            'rotate_x', 'rotate_y', 'rotate_z',
            'focal_length', 'film_offset_x', 'film_offset_y'
        ]
        
        return [name for name in param_names if not self.is_parameter_locked(name)]
    
    def __str__(self) -> str:
        """String representation of camera parameters."""
        return (f"CameraParameters(camera='{self.camera_name}', "
                f"translation={self._translation}, rotation={self._rotation}, "
                f"focal_length={self._focal_length}, "
                f"film_offset=({self._film_offset_x}, {self._film_offset_y}))")
    
    def __repr__(self) -> str:
        """Detailed string representation of camera parameters."""
        return str(self)