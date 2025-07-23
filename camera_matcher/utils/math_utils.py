"""
Mathematical utility functions for camera matching.
"""

import math
from typing import Tuple, List
import maya.api.OpenMaya as om


def project_point(point_3d: Tuple[float, float, float], 
                 camera_matrix: List[float],
                 focal_length: float,
                 film_width: float,
                 film_height: float,
                 film_offset_x: float = 0.0,
                 film_offset_y: float = 0.0) -> Tuple[float, float]:
    """
    Project a 3D point to 2D screen coordinates using camera parameters.
    
    Args:
        point_3d: 3D point coordinates (x, y, z)
        camera_matrix: 4x4 camera transformation matrix (16 floats)
        focal_length: Camera focal length in mm
        film_width: Film aperture width in mm
        film_height: Film aperture height in mm
        film_offset_x: Horizontal film offset in mm
        film_offset_y: Vertical film offset in mm
        
    Returns:
        2D projected coordinates (x, y) in normalized device coordinates (-1 to 1)
    """
    # Create Maya objects
    point = om.MPoint(point_3d[0], point_3d[1], point_3d[2], 1.0)
    matrix = om.MMatrix(camera_matrix)
    
    # Transform point to camera space
    inv_matrix = matrix.inverse()
    camera_point = point * inv_matrix
    
    # Avoid division by zero
    if abs(camera_point.z) < 1e-6:
        return (0.0, 0.0)
    
    # Project to image plane
    x_proj = -camera_point.x / camera_point.z
    y_proj = camera_point.y / camera_point.z
    
    # Convert to film coordinates
    x_film = x_proj * focal_length + film_offset_x
    y_film = y_proj * focal_length + film_offset_y
    
    # Convert to normalized coordinates
    x_norm = (x_film / (film_width * 0.5))
    y_norm = (y_film / (film_height * 0.5))
    
    return (x_norm, y_norm)


def euler_to_matrix(rotation: Tuple[float, float, float], 
                   order: str = 'XYZ') -> List[float]:
    """
    Convert Euler angles to a 4x4 transformation matrix.
    
    Args:
        rotation: Euler angles in degrees (x, y, z)
        order: Rotation order ('XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX')
        
    Returns:
        4x4 transformation matrix as a list of 16 floats
    """
    # Convert to radians
    rx = math.radians(rotation[0])
    ry = math.radians(rotation[1])
    rz = math.radians(rotation[2])
    
    # Create individual rotation matrices
    cos_x, sin_x = math.cos(rx), math.sin(rx)
    cos_y, sin_y = math.cos(ry), math.sin(ry)
    cos_z, sin_z = math.cos(rz), math.sin(rz)
    
    # X rotation matrix
    rot_x = [
        1, 0, 0, 0,
        0, cos_x, -sin_x, 0,
        0, sin_x, cos_x, 0,
        0, 0, 0, 1
    ]
    
    # Y rotation matrix
    rot_y = [
        cos_y, 0, sin_y, 0,
        0, 1, 0, 0,
        -sin_y, 0, cos_y, 0,
        0, 0, 0, 1
    ]
    
    # Z rotation matrix
    rot_z = [
        cos_z, -sin_z, 0, 0,
        sin_z, cos_z, 0, 0,
        0, 0, 1, 0,
        0, 0, 0, 1
    ]
    
    # Multiply matrices in the specified order
    if order == 'XYZ':
        result = multiply_matrices_4x4(rot_x, multiply_matrices_4x4(rot_y, rot_z))
    elif order == 'XZY':
        result = multiply_matrices_4x4(rot_x, multiply_matrices_4x4(rot_z, rot_y))
    elif order == 'YXZ':
        result = multiply_matrices_4x4(rot_y, multiply_matrices_4x4(rot_x, rot_z))
    elif order == 'YZX':
        result = multiply_matrices_4x4(rot_y, multiply_matrices_4x4(rot_z, rot_x))
    elif order == 'ZXY':
        result = multiply_matrices_4x4(rot_z, multiply_matrices_4x4(rot_x, rot_y))
    elif order == 'ZYX':
        result = multiply_matrices_4x4(rot_z, multiply_matrices_4x4(rot_y, rot_x))
    else:
        raise ValueError(f"Unknown rotation order: {order}")
    
    return result


def matrix_to_euler(matrix: List[float], order: str = 'XYZ') -> Tuple[float, float, float]:
    """
    Convert a 4x4 transformation matrix to Euler angles.
    
    Args:
        matrix: 4x4 transformation matrix as a list of 16 floats
        order: Rotation order ('XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX')
        
    Returns:
        Euler angles in degrees (x, y, z)
    """
    # Extract rotation part of matrix (3x3)
    m = matrix
    
    if order == 'XYZ':
        # Extract angles for XYZ order
        sy = math.sqrt(m[0] * m[0] + m[1] * m[1])
        
        singular = sy < 1e-6
        
        if not singular:
            x = math.atan2(m[6], m[10])
            y = math.atan2(-m[2], sy)
            z = math.atan2(m[1], m[0])
        else:
            x = math.atan2(-m[9], m[5])
            y = math.atan2(-m[2], sy)
            z = 0
            
    elif order == 'ZYX':
        # Extract angles for ZYX order (common)
        sy = math.sqrt(m[0] * m[0] + m[4] * m[4])
        
        singular = sy < 1e-6
        
        if not singular:
            x = math.atan2(m[9], m[10])
            y = math.atan2(-m[8], sy)
            z = math.atan2(m[4], m[0])
        else:
            x = math.atan2(-m[6], m[5])
            y = math.atan2(-m[8], sy)
            z = 0
    else:
        # For other orders, use a more general approach
        # This is a simplified implementation
        x = math.atan2(m[6], m[10])
        y = math.atan2(-m[2], math.sqrt(m[6] * m[6] + m[10] * m[10]))
        z = math.atan2(m[1], m[0])
    
    # Convert to degrees
    return (math.degrees(x), math.degrees(y), math.degrees(z))


def multiply_matrices_4x4(a: List[float], b: List[float]) -> List[float]:
    """
    Multiply two 4x4 matrices.
    
    Args:
        a: First matrix as list of 16 floats (row-major)
        b: Second matrix as list of 16 floats (row-major)
        
    Returns:
        Result matrix as list of 16 floats (row-major)
    """
    result = [0.0] * 16
    
    for i in range(4):
        for j in range(4):
            result[i * 4 + j] = (
                a[i * 4 + 0] * b[0 * 4 + j] +
                a[i * 4 + 1] * b[1 * 4 + j] +
                a[i * 4 + 2] * b[2 * 4 + j] +
                a[i * 4 + 3] * b[3 * 4 + j]
            )
    
    return result


def create_translation_matrix(translation: Tuple[float, float, float]) -> List[float]:
    """
    Create a 4x4 translation matrix.
    
    Args:
        translation: Translation vector (x, y, z)
        
    Returns:
        4x4 translation matrix as list of 16 floats
    """
    return [
        1, 0, 0, translation[0],
        0, 1, 0, translation[1],
        0, 0, 1, translation[2],
        0, 0, 0, 1
    ]


def create_scale_matrix(scale: Tuple[float, float, float]) -> List[float]:
    """
    Create a 4x4 scale matrix.
    
    Args:
        scale: Scale factors (x, y, z)
        
    Returns:
        4x4 scale matrix as list of 16 floats
    """
    return [
        scale[0], 0, 0, 0,
        0, scale[1], 0, 0,
        0, 0, scale[2], 0,
        0, 0, 0, 1
    ]


def invert_matrix_4x4(matrix: List[float]) -> List[float]:
    """
    Invert a 4x4 matrix.
    
    Args:
        matrix: 4x4 matrix as list of 16 floats
        
    Returns:
        Inverted matrix as list of 16 floats
        
    Raises:
        ValueError: If matrix is not invertible
    """
    # Create Maya matrix for inversion
    maya_matrix = om.MMatrix(matrix)
    
    try:
        inverted = maya_matrix.inverse()
        return [inverted[i] for i in range(16)]
    except Exception:
        raise ValueError("Matrix is not invertible")


def distance_3d(point1: Tuple[float, float, float], 
               point2: Tuple[float, float, float]) -> float:
    """
    Calculate 3D distance between two points.
    
    Args:
        point1: First point (x, y, z)
        point2: Second point (x, y, z)
        
    Returns:
        Euclidean distance
    """
    dx = point2[0] - point1[0]
    dy = point2[1] - point1[1]
    dz = point2[2] - point1[2]
    
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def distance_2d(point1: Tuple[float, float], 
               point2: Tuple[float, float]) -> float:
    """
    Calculate 2D distance between two points.
    
    Args:
        point1: First point (x, y)
        point2: Second point (x, y)
        
    Returns:
        Euclidean distance
    """
    dx = point2[0] - point1[0]
    dy = point2[1] - point1[1]
    
    return math.sqrt(dx * dx + dy * dy)


def normalize_vector_3d(vector: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """
    Normalize a 3D vector.
    
    Args:
        vector: Input vector (x, y, z)
        
    Returns:
        Normalized vector (x, y, z)
        
    Raises:
        ValueError: If vector has zero length
    """
    length = math.sqrt(vector[0] * vector[0] + vector[1] * vector[1] + vector[2] * vector[2])
    
    if length < 1e-6:
        raise ValueError("Cannot normalize zero-length vector")
    
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def cross_product_3d(v1: Tuple[float, float, float], 
                    v2: Tuple[float, float, float]) -> Tuple[float, float, float]:
    """
    Calculate cross product of two 3D vectors.
    
    Args:
        v1: First vector (x, y, z)
        v2: Second vector (x, y, z)
        
    Returns:
        Cross product vector (x, y, z)
    """
    return (
        v1[1] * v2[2] - v1[2] * v2[1],
        v1[2] * v2[0] - v1[0] * v2[2],
        v1[0] * v2[1] - v1[1] * v2[0]
    )


def dot_product_3d(v1: Tuple[float, float, float], 
                  v2: Tuple[float, float, float]) -> float:
    """
    Calculate dot product of two 3D vectors.
    
    Args:
        v1: First vector (x, y, z)
        v2: Second vector (x, y, z)
        
    Returns:
        Dot product (scalar)
    """
    return v1[0] * v2[0] + v1[1] * v2[1] + v1[2] * v2[2]