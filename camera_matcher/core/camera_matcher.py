"""
Main CameraMatcher class that coordinates camera matching functionality.
"""

from typing import List, Optional, Tuple, Dict, Any
import os
import maya.cmds as cmds
from .locator_pair import LocatorPair
from .camera_parameters import CameraParameters
from .optimization import CameraOptimizer


class CameraMatcher:
    """
    Main class for camera matching functionality.
    """
    
    def __init__(self):
        """Initialize the camera matcher."""
        self.locator_pairs: List[LocatorPair] = []
        self.camera_params: Optional[CameraParameters] = None
        self.optimizer: Optional[CameraOptimizer] = None
        
        # Image properties
        self.image_path: Optional[str] = None
        self.image_width: int = 0
        self.image_height: int = 0
        
        # Auto-incrementing ID for locator pairs
        self._next_pair_id: int = 1
        
        # Settings
        self.locator_size: float = 1.0
        self.locator_prefix: str = "cam_match_loc"
    
    def set_image(self, image_path: str, width: int, height: int) -> None:
        """
        Set the reference image for camera matching.
        
        Args:
            image_path: Path to the image file
            width: Image width in pixels
            height: Image height in pixels
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        self.image_path = image_path
        self.image_width = width
        self.image_height = height
        
        # Update optimizer if it exists
        if self.optimizer and self.camera_params:
            self.optimizer = CameraOptimizer(
                self.camera_params, 
                self.locator_pairs,
                self.image_width, 
                self.image_height
            )
    
    def set_camera(self, camera_name: str) -> None:
        """
        Set the camera to be matched.
        
        Args:
            camera_name: Name of the camera in Maya scene
        """
        if not cmds.objExists(camera_name):
            raise RuntimeError(f"Camera '{camera_name}' does not exist in scene")
        
        self.camera_params = CameraParameters(camera_name)
        
        # Update optimizer if image is set
        if self.image_width > 0 and self.image_height > 0:
            self.optimizer = CameraOptimizer(
                self.camera_params,
                self.locator_pairs,
                self.image_width,
                self.image_height
            )
    
    def create_locator_pair(self, pixel_x: float, pixel_y: float, 
                           world_pos: Optional[Tuple[float, float, float]] = None) -> LocatorPair:
        """
        Create a new 3D-2D locator pair.
        
        Args:
            pixel_x: X pixel coordinate in image
            pixel_y: Y pixel coordinate in image
            world_pos: Optional 3D world position, defaults to origin
            
        Returns:
            The created locator pair
        """
        if world_pos is None:
            world_pos = (0.0, 0.0, 0.0)
        
        # Create unique locator name
        locator_name = f"{self.locator_prefix}_{self._next_pair_id:03d}"
        while cmds.objExists(locator_name):
            self._next_pair_id += 1
            locator_name = f"{self.locator_prefix}_{self._next_pair_id:03d}"
        
        # Create locator in Maya
        locator = cmds.spaceLocator(name=locator_name)[0]
        cmds.xform(locator, worldSpace=True, translation=world_pos)
        
        # Set locator display properties
        cmds.setAttr(f"{locator}.localScaleX", self.locator_size)
        cmds.setAttr(f"{locator}.localScaleY", self.locator_size)
        cmds.setAttr(f"{locator}.localScaleZ", self.locator_size)
        
        # Create locator pair
        pair = LocatorPair(locator_name, (pixel_x, pixel_y), self._next_pair_id)
        self.locator_pairs.append(pair)
        
        self._next_pair_id += 1
        
        # Update optimizer
        self._update_optimizer()
        
        return pair
    
    def remove_locator_pair(self, pair_id: int) -> bool:
        """
        Remove a locator pair by ID.
        
        Args:
            pair_id: ID of the pair to remove
            
        Returns:
            True if pair was found and removed, False otherwise
        """
        for i, pair in enumerate(self.locator_pairs):
            if pair.pair_id == pair_id:
                # Delete the locator from Maya
                pair.delete_locator()
                # Remove from list
                del self.locator_pairs[i]
                self._update_optimizer()
                return True
        return False
    
    def get_locator_pair(self, pair_id: int) -> Optional[LocatorPair]:
        """
        Get a locator pair by ID.
        
        Args:
            pair_id: ID of the pair to find
            
        Returns:
            The locator pair if found, None otherwise
        """
        for pair in self.locator_pairs:
            if pair.pair_id == pair_id:
                return pair
        return None
    
    def update_locator_pixel_coords(self, pair_id: int, pixel_x: float, pixel_y: float) -> bool:
        """
        Update the pixel coordinates of a locator pair.
        
        Args:
            pair_id: ID of the pair to update
            pixel_x: New X pixel coordinate
            pixel_y: New Y pixel coordinate
            
        Returns:
            True if pair was found and updated, False otherwise
        """
        pair = self.get_locator_pair(pair_id)
        if pair:
            pair.update_pixel_coords((pixel_x, pixel_y))
            return True
        return False
    
    def update_locator_world_pos(self, pair_id: int, x: float, y: float, z: float) -> bool:
        """
        Update the world position of a locator pair.
        
        Args:
            pair_id: ID of the pair to update
            x: New X world coordinate
            y: New Y world coordinate
            z: New Z world coordinate
            
        Returns:
            True if pair was found and updated, False otherwise
        """
        pair = self.get_locator_pair(pair_id)
        if pair:
            try:
                pair.update_locator_position((x, y, z))
                return True
            except Exception:
                return False
        return False
    
    def clear_all_pairs(self) -> None:
        """Remove all locator pairs."""
        for pair in self.locator_pairs:
            pair.delete_locator()
        self.locator_pairs.clear()
        self._update_optimizer()
    
    def get_valid_pairs(self) -> List[LocatorPair]:
        """
        Get all valid locator pairs.
        
        Returns:
            List of valid locator pairs
        """
        return [pair for pair in self.locator_pairs if pair.is_valid]
    
    def get_pair_count(self) -> int:
        """Get the total number of locator pairs."""
        return len(self.locator_pairs)
    
    def get_valid_pair_count(self) -> int:
        """Get the number of valid locator pairs."""
        return len(self.get_valid_pairs())
    
    def optimize_camera(self, method: Optional[str] = None) -> Tuple[bool, float, int]:
        """
        Perform camera optimization.
        
        Args:
            method: Optimization method to use
            
        Returns:
            Tuple of (success, final_error, iterations)
        """
        if not self.optimizer:
            raise RuntimeError("Optimizer not initialized. Set camera and image first.")
        
        # Validate setup
        is_valid, error_msg = self.optimizer.validate_setup()
        if not is_valid:
            raise RuntimeError(f"Optimization setup invalid: {error_msg}")
        
        # Perform optimization
        success, final_error, iterations = self.optimizer.optimize(method)
        
        # Apply results to Maya camera
        if success and self.camera_params:
            self.camera_params.apply_to_maya()
        
        return success, final_error, iterations
    
    def calculate_current_error(self) -> float:
        """
        Calculate current RMS reprojection error.
        
        Returns:
            RMS error in pixels
        """
        if not self.optimizer:
            return float('inf')
        
        return self.optimizer.calculate_rms_error()
    
    def get_individual_errors(self) -> List[Tuple[int, float]]:
        """
        Get individual reprojection errors for each pair.
        
        Returns:
            List of (pair_id, error) tuples
        """
        if not self.optimizer:
            return []
        
        return self.optimizer.get_individual_errors()
    
    def project_locators_to_pixels(self) -> Dict[int, Tuple[float, float]]:
        """
        Project all locators to pixel coordinates using current camera.
        
        Returns:
            Dictionary mapping pair_id to (pixel_x, pixel_y)
        """
        if not self.camera_params:
            return {}
        
        projections = {}
        
        for pair in self.locator_pairs:
            if not pair.is_valid:
                continue
                
            try:
                # Get NDC coordinates
                ndc_coords = pair.get_projected_coords(self.camera_params.camera_transform)
                
                # Convert to pixel coordinates
                pixel_x = (ndc_coords[0] + 1.0) * 0.5 * self.image_width
                pixel_y = (1.0 - ndc_coords[1]) * 0.5 * self.image_height  # Flip Y
                
                projections[pair.pair_id] = (pixel_x, pixel_y)
                
            except Exception:
                continue
        
        return projections
    
    def _update_optimizer(self) -> None:
        """Update the optimizer with current state."""
        if self.camera_params and self.image_width > 0 and self.image_height > 0:
            self.optimizer = CameraOptimizer(
                self.camera_params,
                self.locator_pairs,
                self.image_width,
                self.image_height
            )
    
    def export_data(self, file_path: str) -> None:
        """
        Export camera matcher data to a file.
        
        Args:
            file_path: Path to save the data
        """
        import json
        
        data = {
            'image_path': self.image_path,
            'image_width': self.image_width,
            'image_height': self.image_height,
            'camera_name': self.camera_params.camera_name if self.camera_params else None,
            'locator_pairs': []
        }
        
        for pair in self.locator_pairs:
            if pair.is_valid:
                try:
                    world_pos = pair.world_position
                    pair_data = {
                        'pair_id': pair.pair_id,
                        'locator_name': pair.locator_name,
                        'pixel_coords': pair.pixel_coords,
                        'world_position': world_pos
                    }
                    data['locator_pairs'].append(pair_data)
                except Exception:
                    continue
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def import_data(self, file_path: str) -> None:
        """
        Import camera matcher data from a file.
        
        Args:
            file_path: Path to load the data from
        """
        import json
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Data file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Clear current data
        self.clear_all_pairs()
        
        # Load image info
        if data.get('image_path') and data.get('image_width') and data.get('image_height'):
            self.image_path = data['image_path']
            self.image_width = data['image_width']
            self.image_height = data['image_height']
        
        # Load camera
        if data.get('camera_name'):
            try:
                self.set_camera(data['camera_name'])
            except Exception:
                pass  # Camera might not exist in current scene
        
        # Load locator pairs
        for pair_data in data.get('locator_pairs', []):
            try:
                # Create locator pair without creating new locator if it exists
                locator_name = pair_data['locator_name']
                pixel_coords = tuple(pair_data['pixel_coords'])
                world_pos = tuple(pair_data['world_position'])
                pair_id = pair_data['pair_id']
                
                # Create or update locator
                if not cmds.objExists(locator_name):
                    locator = cmds.spaceLocator(name=locator_name)[0]
                    cmds.xform(locator, worldSpace=True, translation=world_pos)
                else:
                    cmds.xform(locator_name, worldSpace=True, translation=world_pos)
                
                # Create pair object
                pair = LocatorPair(locator_name, pixel_coords, pair_id)
                self.locator_pairs.append(pair)
                
                # Update next ID
                if pair_id >= self._next_pair_id:
                    self._next_pair_id = pair_id + 1
                    
            except Exception:
                continue
        
        # Update optimizer
        self._update_optimizer()
    
    def __str__(self) -> str:
        """String representation of the camera matcher."""
        return (f"CameraMatcher(image='{self.image_path}', "
                f"camera='{self.camera_params.camera_name if self.camera_params else None}', "
                f"pairs={len(self.locator_pairs)})")
    
    def __repr__(self) -> str:
        """Detailed string representation of the camera matcher."""
        return str(self)