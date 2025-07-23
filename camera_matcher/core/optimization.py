"""
Camera optimization module using scipy optimization algorithms.
"""

from typing import List, Callable, Optional, Tuple
import numpy as np
from .camera_parameters import CameraParameters
from .locator_pair import LocatorPair

try:
    from scipy.optimize import minimize, least_squares
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False


class CameraOptimizer:
    """
    Optimizes camera parameters to minimize reprojection error.
    """
    
    def __init__(self, camera_params: CameraParameters, locator_pairs: List[LocatorPair],
                 image_width: int, image_height: int):
        """
        Initialize the camera optimizer.
        
        Args:
            camera_params: Camera parameters to optimize
            locator_pairs: List of 3D-2D locator pairs
            image_width: Width of the reference image in pixels
            image_height: Height of the reference image in pixels
        """
        if not SCIPY_AVAILABLE:
            raise RuntimeError("scipy is required for camera optimization but is not available")
        
        self.camera_params = camera_params
        self.locator_pairs = locator_pairs
        self.image_width = image_width
        self.image_height = image_height
        
        # Optimization settings
        self.max_iterations = 1000
        self.tolerance = 1e-6
        self.method = 'lm'  # Levenberg-Marquardt
        
        # Progress callback
        self.progress_callback: Optional[Callable[[int, float], None]] = None
        self.iteration_count = 0
    
    def set_progress_callback(self, callback: Callable[[int, float], None]) -> None:
        """
        Set a callback function to track optimization progress.
        
        Args:
            callback: Function that takes iteration count and current error
        """
        self.progress_callback = callback
    
    def _objective_function(self, params: np.ndarray) -> np.ndarray:
        """
        Objective function for optimization - returns residuals for least squares.
        
        Args:
            params: Parameter vector
            
        Returns:
            Array of residuals (reprojection errors)
        """
        # Update camera parameters
        self.camera_params.set_parameter_vector(params.tolist())
        
        # Calculate residuals for all locator pairs
        residuals = []
        
        for pair in self.locator_pairs:
            if not pair.is_valid:
                continue
                
            try:
                # Get projected coordinates in NDC
                proj_ndc = pair.get_projected_coords(self.camera_params.camera_transform)
                
                # Convert NDC to pixel coordinates
                proj_pixel_x = (proj_ndc[0] + 1.0) * 0.5 * self.image_width
                proj_pixel_y = (1.0 - proj_ndc[1]) * 0.5 * self.image_height  # Flip Y
                
                # Calculate residuals in x and y
                dx = proj_pixel_x - pair.pixel_coords[0]
                dy = proj_pixel_y - pair.pixel_coords[1]
                
                residuals.extend([dx, dy])
                
            except Exception:
                # If projection fails, add large residuals
                residuals.extend([1000.0, 1000.0])
        
        return np.array(residuals)
    
    def _cost_function(self, params: np.ndarray) -> float:
        """
        Cost function for optimization - returns total squared error.
        
        Args:
            params: Parameter vector
            
        Returns:
            Total squared reprojection error
        """
        residuals = self._objective_function(params)
        cost = np.sum(residuals ** 2)
        
        # Update iteration count and call progress callback
        self.iteration_count += 1
        if self.progress_callback:
            self.progress_callback(self.iteration_count, cost)
        
        return cost
    
    def _get_parameter_bounds(self) -> Tuple[List[float], List[float]]:
        """
        Get parameter bounds for optimization.
        
        Returns:
            Tuple of (lower_bounds, upper_bounds)
        """
        param_names = self.camera_params.get_unlocked_parameter_names()
        lower_bounds = []
        upper_bounds = []
        
        for param_name in param_names:
            constraints = self.camera_params.get_constraints(param_name)
            
            if constraints.min_value is not None:
                lower_bounds.append(constraints.min_value)
            else:
                lower_bounds.append(-np.inf)
            
            if constraints.max_value is not None:
                upper_bounds.append(constraints.max_value)
            else:
                upper_bounds.append(np.inf)
        
        return lower_bounds, upper_bounds
    
    def optimize(self, method: Optional[str] = None) -> Tuple[bool, float, int]:
        """
        Perform camera parameter optimization.
        
        Args:
            method: Optimization method ('lm', 'trf', or 'dogbox' for least_squares)
                   or 'L-BFGS-B', 'SLSQP', etc. for minimize
            
        Returns:
            Tuple of (success, final_error, iterations)
        """
        if not self.locator_pairs:
            raise ValueError("No locator pairs available for optimization")
        
        valid_pairs = [pair for pair in self.locator_pairs if pair.is_valid]
        if not valid_pairs:
            raise ValueError("No valid locator pairs available for optimization")
        
        if len(valid_pairs) < 3:
            raise ValueError("At least 3 valid locator pairs are required for optimization")
        
        # Get initial parameter values
        initial_params = np.array(self.camera_params.get_parameter_vector())
        
        if len(initial_params) == 0:
            raise ValueError("No unlocked parameters available for optimization")
        
        # Reset iteration counter
        self.iteration_count = 0
        
        # Choose optimization method
        opt_method = method or self.method
        
        try:
            if opt_method in ['lm', 'trf', 'dogbox']:
                # Use least_squares for these methods
                lower_bounds, upper_bounds = self._get_parameter_bounds()
                
                result = least_squares(
                    self._objective_function,
                    initial_params,
                    method=opt_method,
                    bounds=(lower_bounds, upper_bounds),
                    max_nfev=self.max_iterations,
                    ftol=self.tolerance,
                    xtol=self.tolerance
                )
                
                success = result.success
                final_params = result.x
                final_error = np.sum(result.fun ** 2)
                iterations = result.nfev
                
            else:
                # Use minimize for other methods
                lower_bounds, upper_bounds = self._get_parameter_bounds()
                bounds = list(zip(lower_bounds, upper_bounds))
                
                # Replace infinite bounds with large values
                bounds = [(lb if lb != -np.inf else -1e6, 
                          ub if ub != np.inf else 1e6) for lb, ub in bounds]
                
                result = minimize(
                    self._cost_function,
                    initial_params,
                    method=opt_method,
                    bounds=bounds,
                    options={
                        'maxiter': self.max_iterations,
                        'ftol': self.tolerance,
                        'gtol': self.tolerance
                    }
                )
                
                success = result.success
                final_params = result.x
                final_error = result.fun
                iterations = result.nit
            
            # Apply optimized parameters
            self.camera_params.set_parameter_vector(final_params.tolist())
            
            return success, final_error, iterations
            
        except Exception as e:
            raise RuntimeError(f"Optimization failed: {str(e)}")
    
    def calculate_total_error(self) -> float:
        """
        Calculate the total reprojection error for current parameters.
        
        Returns:
            Total squared reprojection error
        """
        total_error = 0.0
        valid_count = 0
        
        for pair in self.locator_pairs:
            if not pair.is_valid:
                continue
                
            try:
                error = pair.get_reprojection_error(
                    self.camera_params.camera_transform,
                    self.image_width,
                    self.image_height
                )
                total_error += error ** 2
                valid_count += 1
            except Exception:
                continue
        
        return total_error
    
    def calculate_rms_error(self) -> float:
        """
        Calculate the RMS (root mean square) reprojection error.
        
        Returns:
            RMS reprojection error in pixels
        """
        total_error = self.calculate_total_error()
        valid_count = sum(1 for pair in self.locator_pairs if pair.is_valid)
        
        if valid_count == 0:
            return float('inf')
        
        return (total_error / valid_count) ** 0.5
    
    def get_individual_errors(self) -> List[Tuple[int, float]]:
        """
        Get individual reprojection errors for each locator pair.
        
        Returns:
            List of (pair_id, error) tuples
        """
        errors = []
        
        for pair in self.locator_pairs:
            if not pair.is_valid:
                continue
                
            try:
                error = pair.get_reprojection_error(
                    self.camera_params.camera_transform,
                    self.image_width,
                    self.image_height
                )
                errors.append((pair.pair_id, error))
            except Exception:
                errors.append((pair.pair_id, float('inf')))
        
        return errors
    
    def validate_setup(self) -> Tuple[bool, str]:
        """
        Validate that the optimization setup is correct.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if scipy is available
        if not SCIPY_AVAILABLE:
            return False, "scipy is required for optimization but is not available"
        
        # Check camera parameters
        if not self.camera_params:
            return False, "Camera parameters not set"
        
        # Check if camera exists
        try:
            self.camera_params.camera_transform
        except Exception as e:
            return False, f"Camera validation failed: {str(e)}"
        
        # Check locator pairs
        if not self.locator_pairs:
            return False, "No locator pairs available"
        
        valid_pairs = [pair for pair in self.locator_pairs if pair.is_valid]
        if len(valid_pairs) < 3:
            return False, f"At least 3 valid locator pairs required, found {len(valid_pairs)}"
        
        # Check unlocked parameters
        unlocked_params = self.camera_params.get_unlocked_parameter_names()
        if not unlocked_params:
            return False, "No unlocked parameters available for optimization"
        
        # Check image dimensions
        if self.image_width <= 0 or self.image_height <= 0:
            return False, f"Invalid image dimensions: {self.image_width}x{self.image_height}"
        
        return True, "Setup is valid"