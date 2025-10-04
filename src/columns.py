"""
Column detection using whitespace valley analysis
"""
import numpy as np
import cv2
from typing import List, Tuple
import logging

# Constants - Adjusted for 150 DPI
COLUMN_VALLEY_MIN_WIDTH = 0.04  # Minimum width as fraction of page width

def detect_columns(img: np.ndarray) -> List[Tuple[int, int]]:
    """
    Detect column boundaries using whitespace valley analysis
    
    Args:
        img: Grayscale page image
        
    Returns:
        List of (x0, x1) column boundaries in pixels
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img.copy()
    
    h, w = gray.shape
    
    # Downsample for faster processing
    scale_factor = min(1.0, 1000.0 / w)  # Don't process images wider than 1000px
    if scale_factor < 1.0:
        new_w = int(w * scale_factor)
        gray = cv2.resize(gray, (new_w, int(h * scale_factor)))
        h, w = gray.shape
    
    # Invert image so text becomes white (ink map)
    inverted = 255 - gray
    
    # Apply Otsu threshold to get binary ink map
    _, binary = cv2.threshold(inverted, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Create vertical projection profile
    projection = np.sum(binary, axis=0)
    
    # Smooth the projection to reduce noise
    window_size = max(3, int(0.02 * w))  # 2% of page width
    if window_size % 2 == 0:
        window_size += 1
    projection_smooth = cv2.GaussianBlur(projection.astype(np.float32), (window_size, 1), 0)
    
    # Find valleys (deep minima) in the projection
    valleys = find_valleys(projection_smooth, w)
    
    # Filter valleys by minimum width
    min_width = int(COLUMN_VALLEY_MIN_WIDTH * w)
    valid_valleys = [v for v in valleys if v[1] - v[0] >= min_width]
    
    # Convert valleys to column boundaries
    columns = []
    if not valid_valleys:
        # No clear columns detected, treat as single column
        columns = [(0, w)]
    else:
        # Start from left edge
        prev_x = 0
        for valley_start, valley_end in valid_valleys:
            columns.append((prev_x, valley_start))
            prev_x = valley_end
        # Add final column to right edge
        columns.append((prev_x, w))
    
    # Merge very narrow columns (less than 5% of page width)
    min_column_width = int(0.05 * w)
    merged_columns = []
    for x0, x1 in columns:
        if x1 - x0 >= min_column_width:
            merged_columns.append((x0, x1))
        elif merged_columns:
            # Merge with previous column
            prev_x0, prev_x1 = merged_columns[-1]
            merged_columns[-1] = (prev_x0, x1)
        else:
            # First column is too narrow, keep it anyway
            merged_columns.append((x0, x1))
    
    # Filter out zero-width columns
    merged_columns = [(x0, x1) for x0, x1 in merged_columns if x1 > x0]
    
    # Scale back to original dimensions
    if scale_factor < 1.0:
        original_w = int(w / scale_factor)
        merged_columns = [(int(x0 / scale_factor), int(x1 / scale_factor)) 
                         for x0, x1 in merged_columns]
        # Ensure we don't exceed original width
        merged_columns = [(max(0, x0), min(original_w, x1)) for x0, x1 in merged_columns]
    
    logging.info(f"Detected {len(merged_columns)} columns: {merged_columns}")
    return merged_columns

def find_valleys(projection: np.ndarray, page_width: int) -> List[Tuple[int, int]]:
    """
    Find valleys in the vertical projection profile
    
    Args:
        projection: Smoothed vertical projection
        page_width: Width of the page in pixels
        
    Returns:
        List of (start, end) valley positions
    """
    # Calculate threshold for deep valleys (15th percentile)
    threshold = np.percentile(projection, 15)
    
    # Find regions below threshold
    below_threshold = projection < threshold
    
    # Find connected components of valleys
    valleys = []
    in_valley = False
    valley_start = 0
    
    for i, is_valley in enumerate(below_threshold):
        if is_valley and not in_valley:
            # Start of valley
            valley_start = i
            in_valley = True
        elif not is_valley and in_valley:
            # End of valley
            valleys.append((valley_start, i))
            in_valley = False
    
    # Handle case where valley extends to end of page
    if in_valley:
        valleys.append((valley_start, len(projection)))
    
    return valleys

def snap_to_column_edges(x: int, columns: List[Tuple[int, int]], tolerance: int = 10) -> int:
    """
    Snap a coordinate to the nearest column edge
    
    Args:
        x: X coordinate to snap
        columns: List of column boundaries
        tolerance: Maximum distance for snapping
        
    Returns:
        Snapped X coordinate
    """
    best_x = x
    min_distance = float('inf')
    
    for x0, x1 in columns:
        for edge in [x0, x1]:
            distance = abs(x - edge)
            if distance < min_distance and distance <= tolerance:
                min_distance = distance
                best_x = edge
    
    return best_x

def get_column_for_x(x: int, columns: List[Tuple[int, int]]) -> int:
    """
    Get the column index that contains the given X coordinate
    
    Args:
        x: X coordinate
        columns: List of column boundaries
        
    Returns:
        Column index (0-based), or -1 if not in any column
    """
    for i, (x0, x1) in enumerate(columns):
        if x0 <= x < x1:
            return i
    return -1

def validate_columns(columns: List[Tuple[int, int]], page_width: int) -> List[Tuple[int, int]]:
    """
    Validate and clean up column boundaries
    
    Args:
        columns: List of column boundaries
        page_width: Width of the page in pixels
        
    Returns:
        Cleaned column boundaries
    """
    if not columns:
        return [(0, page_width)]
    
    # Sort columns by x0
    columns = sorted(columns, key=lambda x: x[0])
    
    # Remove overlapping columns (keep the larger one)
    cleaned = []
    for x0, x1 in columns:
        if not cleaned:
            cleaned.append((x0, x1))
        else:
            prev_x0, prev_x1 = cleaned[-1]
            if x0 < prev_x1:  # Overlap
                # Merge with previous column
                cleaned[-1] = (prev_x0, max(prev_x1, x1))
            else:
                cleaned.append((x0, x1))
    
    # Ensure first column starts at 0 and last column ends at page_width
    if cleaned[0][0] > 0:
        cleaned[0] = (0, cleaned[0][1])
    if cleaned[-1][1] < page_width:
        cleaned[-1] = (cleaned[-1][0], page_width)
    
    return cleaned
