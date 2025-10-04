"""
Figure detection using vector clustering and image XObjects
"""
import numpy as np
import cv2
from sklearn.cluster import DBSCAN
from typing import List, Dict, Any, Tuple, Optional
import logging

# Constants - Focus on larger figures, not tiny fragments
DBSCAN_EPS = 30          # pixels @ 150 DPI (larger clusters for complete figures)
DBSCAN_MIN_SAMPLES = 50  # higher threshold to avoid tiny fragments
MIN_STROKE_LEN = 500     # pixels (focus on substantial drawings)
NMS_IOU = 0.1            # more aggressive merging

class Figure:
    """Represents a detected figure"""
    def __init__(self, bbox_px: List[int], source: str, stroke_length: float = 0):
        self.bbox_px = bbox_px  # [x0, y0, x1, y1]
        self.source = source  # 'vector', 'image', or 'mixed'
        self.stroke_length = stroke_length
        self.image_path = None
        self.caption = None
    
    @property
    def area(self) -> int:
        return (self.bbox_px[2] - self.bbox_px[0]) * (self.bbox_px[3] - self.bbox_px[1])
    
    @property
    def center(self) -> Tuple[float, float]:
        return (
            (self.bbox_px[0] + self.bbox_px[2]) / 2,
            (self.bbox_px[1] + self.bbox_px[3]) / 2
        )

def detect_figures(drawings: List[Dict], xobjects: List[Dict], 
                  columns: List[Tuple[int, int]], page_size: Dict[str, Any]) -> List[Figure]:
    """
    Detect figures using vector clustering and image XObjects
    
    Args:
        drawings: List of drawing operations from PyMuPDF
        xobjects: List of image XObjects with bounding boxes
        columns: List of column boundaries
        page_size: Page size information
        
    Returns:
        List of detected Figure objects
    """
    figures = []
    
    # D1. Vector-density clustering
    vector_figures = detect_vector_figures(drawings, columns)
    figures.extend(vector_figures)
    
    # D2. Image XObjects
    image_figures = detect_image_figures(xobjects, columns, page_size)
    figures.extend(image_figures)
    
    # D3. Merge and apply NMS
    merged_figures = merge_figures(figures)

    # D4. Proximity merge and pruning to reduce fragmentation
    merged_figures = refine_figures(merged_figures, page_size)

    # D5. Schematic-specific merging - merge figures that are clearly part of the same schematic
    merged_figures = merge_schematic_figures(merged_figures, page_size)

    # D6. Filter out headers and footers
    merged_figures = filter_headers_footers(merged_figures, page_size)

    # Snap to column edges
    for figure in merged_figures:
        snap_to_columns(figure, columns)

    # D7. Final safety padding to avoid tight crops in exports/overlays
    page_w, page_h = page_size.get('px', (1275, 1650))
    # pad ~0.7% of page width, min 8px, max 18px at 150DPI
    final_pad = int(max(8, min(18, 0.007 * page_w)))
    for f in merged_figures:
        x0, y0, x1, y1 = f.bbox_px
        x0 = max(0, x0 - final_pad)
        y0 = max(0, y0 - final_pad)
        x1 = x1 + final_pad
        y1 = y1 + final_pad
        f.bbox_px = [x0, y0, x1, y1]
    
    return merged_figures

def detect_vector_figures(drawings: List[Dict], columns: List[Tuple[int, int]]) -> List[Figure]:
    """
    Detect figures from vector drawings using adaptive parameters based on page content
    
    Args:
        drawings: List of drawing operations
        columns: List of column boundaries
        
    Returns:
        List of Figure objects from vector drawings
    """
    if not drawings:
        return []
    
    # Step 1: Analyze page content to determine adaptive parameters
    page_analysis = analyze_page_content(drawings)
    logging.info(f"Page analysis: {page_analysis}")
    
    # Step 2: Collect drawing bounding boxes with adaptive filtering
    drawing_boxes = []
    
    for drawing in drawings:
        if drawing.get("type") in ["s", "f"]:  # Only stroke and fill types exist in PyMuPDF
            rect = drawing.get("rect")
            if rect:
                # Convert to pixels
                x0 = int(rect.x0 * (150/72))
                y0 = int(rect.y0 * (150/72))
                x1 = int(rect.x1 * (150/72))
                y1 = int(rect.y1 * (150/72))
                
                # Calculate area
                area = (x1 - x0) * (y1 - y0)
                
                # Use adaptive threshold based on page analysis
                if area > page_analysis['min_drawing_area']:
                    drawing_boxes.append({
                        'bbox': [x0, y0, x1, y1],
                        'area': area,
                        'drawing': drawing
                    })
    
    if not drawing_boxes:
        return []
    
    # Step 3: Use adaptive parameters for detection
    figures = detect_figures_adaptive(drawing_boxes, page_analysis)
    
    return figures

def analyze_page_content(drawings: List[Dict]) -> Dict[str, Any]:
    """
    Analyze page content to determine adaptive parameters
    
    Args:
        drawings: List of drawing operations
        
    Returns:
        Dictionary with adaptive parameters
    """
    if not drawings:
        return {
            'min_drawing_area': 2000,
            'merge_distance': 100,
            'min_figure_area': 5000,
            'padding': 20,
            'content_type': 'unknown'
        }
    
    # Collect all drawing areas
    areas = []
    aspect_ratios = []
    
    for drawing in drawings:
        if drawing.get("type") in ["s", "f"]:
            rect = drawing.get("rect")
            if rect:
                x0 = int(rect.x0 * (150/72))
                y0 = int(rect.y0 * (150/72))
                x1 = int(rect.x1 * (150/72))
                y1 = int(rect.y1 * (150/72))
                
                area = (x1 - x0) * (y1 - y0)
                width = x1 - x0
                height = y1 - y0
                aspect_ratio = width / height if height > 0 else 0
                
                if area > 100:  # Only consider meaningful drawings
                    areas.append(area)
                    aspect_ratios.append(aspect_ratio)
    
    if not areas:
        return {
            'min_drawing_area': 2000,
            'merge_distance': 100,
            'min_figure_area': 5000,
            'padding': 20,
            'content_type': 'unknown'
        }
    
    # Calculate statistics
    areas = np.array(areas)
    aspect_ratios = np.array(aspect_ratios)
    
    median_area = np.median(areas)
    mean_area = np.mean(areas)
    std_area = np.std(areas)
    
    # Determine content type based on drawing characteristics
    if median_area > 50000:
        content_type = 'large_diagrams'  # Large technical schematics
    elif median_area > 10000:
        content_type = 'medium_diagrams'  # Medium technical drawings
    elif median_area > 2000:
        content_type = 'small_diagrams'  # Small technical details
    else:
        content_type = 'fine_details'  # Very fine technical details
    
    # Calculate density (drawings per unit area)
    total_drawing_area = np.sum(areas)
    page_area = 1275 * 1650  # Approximate page area at 150 DPI
    density = total_drawing_area / page_area if page_area > 0 else 0
    
    # Adaptive parameters based on content analysis
    if content_type == 'large_diagrams':
        min_drawing_area = max(5000, median_area * 0.1)
        merge_distance = 150
        min_figure_area = max(20000, median_area * 0.5)
        padding = 30
    elif content_type == 'medium_diagrams':
        min_drawing_area = max(2000, median_area * 0.2)
        merge_distance = 100
        min_figure_area = max(10000, median_area * 0.3)
        padding = 25
    elif content_type == 'small_diagrams':
        min_drawing_area = max(1000, median_area * 0.3)
        merge_distance = 75
        min_figure_area = max(5000, median_area * 0.4)
        padding = 20
    else:  # fine_details
        min_drawing_area = max(500, median_area * 0.5)
        merge_distance = 50
        min_figure_area = max(2000, median_area * 0.6)
        padding = 15
    
    # Adjust for density - higher density needs more aggressive merging
    if density > 0.1:  # High density
        merge_distance = int(merge_distance * 1.5)
        min_figure_area = int(min_figure_area * 0.8)
    elif density < 0.01:  # Low density
        merge_distance = int(merge_distance * 0.7)
        min_figure_area = int(min_figure_area * 1.2)
    
    return {
        'min_drawing_area': int(min_drawing_area),
        'merge_distance': int(merge_distance),
        'min_figure_area': int(min_figure_area),
        'padding': int(padding),
        'content_type': content_type,
        'median_area': int(median_area),
        'density': density,
        'num_drawings': len(areas)
    }

def detect_figures_adaptive(drawing_boxes: List[Dict], page_analysis: Dict[str, Any]) -> List[Figure]:
    """
    Detect figures using adaptive parameters
    
    Args:
        drawing_boxes: List of drawing bounding boxes
        page_analysis: Adaptive parameters from page analysis
        
    Returns:
        List of Figure objects
    """
    if not drawing_boxes:
        return []
    
    # Sort by area (largest first)
    drawing_boxes.sort(key=lambda x: x['area'], reverse=True)
    
    figures = []
    processed = set()
    
    # Process each drawing box
    for i, box in enumerate(drawing_boxes):
        if i in processed:
            continue
            
        bbox = box['bbox']
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        area = width * height
        aspect_ratio = width / height if height > 0 else 0
        
        # Skip table-like elements (more lenient threshold)
        table_threshold = 5 if page_analysis['content_type'] in ['large_diagrams', 'medium_diagrams'] else 4
        if aspect_ratio > table_threshold and height < 50:  # More lenient height threshold
            logging.info(f"Skipping table element: {bbox} (aspect_ratio: {aspect_ratio:.1f})")
            continue
        
        # Skip very small elements (more lenient threshold)
        min_area = page_analysis['min_figure_area'] * 0.5  # Reduce minimum area by 50%
        if area < min_area:
            logging.info(f"Skipping small element: {bbox} (area: {area})")
            continue
        
        # Find nearby drawings to merge (adaptive distance)
        nearby_boxes = [box]
        processed.add(i)
        
        for j in range(i+1, len(drawing_boxes)):
            if j in processed:
                continue
                
            other_bbox = drawing_boxes[j]['bbox']
            
            # Check if boxes are close enough to merge (adaptive distance)
            distance = calculate_bbox_distance(bbox, other_bbox)
            if distance < page_analysis['merge_distance']:
                nearby_boxes.append(drawing_boxes[j])
                processed.add(j)
        
        # Calculate combined bounding box
        if len(nearby_boxes) > 1:
            x0 = min(b['bbox'][0] for b in nearby_boxes)
            y0 = min(b['bbox'][1] for b in nearby_boxes)
            x1 = max(b['bbox'][2] for b in nearby_boxes)
            y1 = max(b['bbox'][3] for b in nearby_boxes)
            
            # Add adaptive padding
            padding = page_analysis['padding']
            merged_bbox = [
                max(0, x0 - padding),
                max(0, y0 - padding),
                x1 + padding,
                y1 + padding
            ]
            
            # Calculate total area
            total_area = (merged_bbox[2] - merged_bbox[0]) * (merged_bbox[3] - merged_bbox[1])
            
            figure = Figure(
                bbox_px=merged_bbox,
                source='vector',
                stroke_length=total_area * 0.1
            )
            figures.append(figure)
            logging.info(f"Merged {len(nearby_boxes)} drawings into figure: {merged_bbox} (area: {total_area})")
        else:
            # Single drawing, add adaptive padding
            padding = page_analysis['padding']
            single_bbox = [
                max(0, bbox[0] - padding),
                max(0, bbox[1] - padding),
                bbox[2] + padding,
                bbox[3] + padding
            ]
            
            figure = Figure(
                bbox_px=single_bbox,
                source='vector',
                stroke_length=area * 0.1
            )
            figures.append(figure)
            logging.info(f"Detected single drawing: {single_bbox} (area: {area})")
    
    return figures

def merge_schematic_figures(figures: List[Figure], page_size: Dict[str, Any]) -> List[Figure]:
    """
    Merge figures that are clearly part of the same schematic diagram
    
    Args:
        figures: List of Figure objects
        page_size: Page size information
        
    Returns:
        List of merged Figure objects
    """
    if not figures:
        return []
    
    # Sort figures by area (largest first)
    figures = sorted(figures, key=lambda f: f.area, reverse=True)
    
    merged = []
    used = set()
    
    for i, figure in enumerate(figures):
        if i in used:
            continue
        
        # Start with this figure
        schematic_group = [figure]
        used.add(i)
        
        # Look for nearby figures that could be part of the same schematic
        for j in range(i+1, len(figures)):
            if j in used:
                continue
            
            other_figure = figures[j]
            
            # Check if figures are close enough to be part of the same schematic
            if should_merge_schematic_figures(figure, other_figure, page_size):
                schematic_group.append(other_figure)
                used.add(j)
        
        # If we found multiple figures, merge them
        if len(schematic_group) > 1:
            # Calculate combined bounding box
            x0 = min(f.bbox_px[0] for f in schematic_group)
            y0 = min(f.bbox_px[1] for f in schematic_group)
            x1 = max(f.bbox_px[2] for f in schematic_group)
            y1 = max(f.bbox_px[3] for f in schematic_group)
            
            # Add generous padding for complete schematics
            padding = 30
            merged_bbox = [
                max(0, x0 - padding),
                max(0, y0 - padding),
                x1 + padding,
                y1 + padding
            ]
            
            # Calculate total stroke length
            total_stroke_length = sum(f.stroke_length for f in schematic_group)
            
            merged_figure = Figure(
                bbox_px=merged_bbox,
                source='vector',
                stroke_length=total_stroke_length
            )
            merged.append(merged_figure)
            logging.info(f"Merged {len(schematic_group)} figures into schematic: {merged_bbox}")
        else:
            # Single figure, keep as is
            merged.append(figure)
    
    return merged

def should_merge_schematic_figures(fig1: Figure, fig2: Figure, page_size: Dict[str, Any]) -> bool:
    """
    Determine if two figures should be merged as part of the same schematic
    
    Args:
        fig1: First figure
        fig2: Second figure
        page_size: Page size information
        
    Returns:
        True if figures should be merged
    """
    # Calculate distance between figures
    center1 = fig1.center
    center2 = fig2.center
    distance = ((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)**0.5
    
    # Calculate page dimensions
    page_w, page_h = page_size.get('px', (1275, 1650))
    
    # For schematics, be much more aggressive with merging
    # If figures are within 500 pixels and both are substantial, merge them
    if distance < 500 and fig1.area > 10000 and fig2.area > 10000:
        return True
    
    # If figures are very close (within 200 pixels), merge them regardless of size
    if distance < 200:
        return True
    
    # If figures are horizontally aligned and close vertically, merge them
    # This handles cases where schematic components are side by side
    vertical_distance = abs(center1[1] - center2[1])
    horizontal_distance = abs(center1[0] - center2[0])
    
    if vertical_distance < 150 and horizontal_distance < 500:
        return True
    
    # If figures overlap significantly, merge them
    iou = calculate_iou(fig1, fig2)
    if iou > 0.1:  # 10% overlap
        return True
    
    return False

def filter_headers_footers(figures: List[Figure], page_size: Dict[str, Any]) -> List[Figure]:
    """
    Filter out figures that are likely headers or footers
    
    Args:
        figures: List of Figure objects
        page_size: Page size information
        
    Returns:
        List of Figure objects with headers/footers removed
    """
    if not figures:
        return []
    
    # Get page dimensions
    page_w, page_h = page_size.get('px', (1275, 1650))
    
    # Define header and footer regions
    # Header: top 15% of page
    header_threshold = int(page_h * 0.15)  # ~248px for 1650px height
    
    # Footer: bottom 10% of page  
    footer_threshold = int(page_h * 0.90)  # ~1485px for 1650px height
    
    filtered_figures = []
    
    for figure in figures:
        bbox = figure.bbox_px
        y0, y1 = bbox[1], bbox[3]
        
        # Check if figure is in header region
        if y1 < header_threshold:
            logging.info(f"Filtering header figure: {bbox} (y1={y1} < {header_threshold})")
            continue
        
        # Check if figure is in footer region
        if y0 > footer_threshold:
            logging.info(f"Filtering footer figure: {bbox} (y0={y0} > {footer_threshold})")
            continue
        
        # Check if figure spans full width (likely header/footer)
        width = bbox[2] - bbox[0]
        if width > page_w * 0.8:  # Spans 80% of page width
            # If it's also in header/footer region, filter it out
            if y1 < header_threshold or y0 > footer_threshold:
                logging.info(f"Filtering full-width header/footer: {bbox}")
                continue
        
        # Keep the figure
        filtered_figures.append(figure)
    
    logging.info(f"Filtered {len(figures) - len(filtered_figures)} header/footer figures, kept {len(filtered_figures)}")
    return filtered_figures

def calculate_bbox_distance(bbox1: List[int], bbox2: List[int]) -> float:
    """Calculate minimum distance between two bounding boxes"""
    x1_0, y1_0, x1_1, y1_1 = bbox1
    x2_0, y2_0, x2_1, y2_1 = bbox2
    
    # Calculate horizontal and vertical distances
    dx = max(0, max(x1_0 - x2_1, x2_0 - x1_1))
    dy = max(0, max(y1_0 - y2_1, y2_0 - y1_1))
    
    return (dx**2 + dy**2)**0.5

def merge_nearby_figures(figures: List[Figure], max_distance: int = 100) -> List[Figure]:
    """
    Merge figures that are close to each other and might be part of the same technical diagram
    
    Args:
        figures: List of Figure objects
        max_distance: Maximum distance between figures to consider merging
        
    Returns:
        List of merged Figure objects
    """
    if not figures:
        return []
    
    # Sort by area (largest first)
    figures = sorted(figures, key=lambda f: f.area, reverse=True)
    
    merged = []
    used = set()
    
    for i, figure in enumerate(figures):
        if i in used:
            continue
        
        # Find nearby figures to merge
        nearby_figures = [figure]
        used.add(i)
        
        for j in range(i+1, len(figures)):
            if j in used:
                continue
            
            # Check if figures overlap or are very close (using bounding box overlap)
            bbox1 = figure.bbox_px
            bbox2 = figures[j].bbox_px
            
            # Calculate overlap
            x0_overlap = max(bbox1[0], bbox2[0])
            y0_overlap = max(bbox1[1], bbox2[1])
            x1_overlap = min(bbox1[2], bbox2[2])
            y1_overlap = min(bbox1[3], bbox2[3])
            
            # Check if there's overlap or if they're very close
            has_overlap = x0_overlap < x1_overlap and y0_overlap < y1_overlap
            
            # Calculate minimum distance between bounding boxes
            if not has_overlap:
                # Calculate distance between closest edges
                dx = max(0, max(bbox1[0] - bbox2[2], bbox2[0] - bbox1[2]))
                dy = max(0, max(bbox1[1] - bbox2[3], bbox2[1] - bbox1[3]))
                min_distance = (dx**2 + dy**2)**0.5
            else:
                min_distance = 0
            
            # Merge if they overlap or are very close
            if has_overlap or min_distance <= max_distance:
                nearby_figures.append(figures[j])
                used.add(j)
        
        # If we found nearby figures, merge them
        if len(nearby_figures) > 1:
            # Calculate combined bounding box
            x0 = min(f.bbox_px[0] for f in nearby_figures)
            y0 = min(f.bbox_px[1] for f in nearby_figures)
            x1 = max(f.bbox_px[2] for f in nearby_figures)
            y1 = max(f.bbox_px[3] for f in nearby_figures)
            
            # Add extra padding for merged technical diagrams
            padding = 30
            merged_bbox = [
                max(0, x0 - padding),
                max(0, y0 - padding),
                x1 + padding,
                y1 + padding
            ]
            
            # Calculate total stroke length
            total_stroke_length = sum(f.stroke_length for f in nearby_figures)
            
            merged_figure = Figure(
                bbox_px=merged_bbox,
                source='vector',
                stroke_length=total_stroke_length
            )
            merged.append(merged_figure)
            logging.info(f"Merged {len(nearby_figures)} nearby figures into: {merged_bbox}")
        else:
            # No nearby figures, keep original
            merged.append(figure)
    
    return merged

def detect_image_figures(xobjects: List[Dict], columns: List[Tuple[int, int]], page_size: Dict[str, Any]) -> List[Figure]:
    """
    Detect figures from image XObjects
    
    Args:
        xobjects: List of image XObjects with bounding boxes
        columns: List of column boundaries
        
    Returns:
        List of Figure objects from image XObjects
    """
    figures = []
    
    # Page-relative thresholds to drop tiny icons/logos
    page_w, page_h = page_size.get('px', (1275, 1650))
    page_area = max(1, page_w * page_h)
    # Minimum required size for an image to be considered a figure
    min_dim = int(max(70, 0.06 * page_w))        # pixels
    min_area = int(max(8000, 0.004 * page_area)) # pixels^2

    for xobj in xobjects:
        bbox_px = xobj['bbox_px']
        
        # More lenient column checking - just check if image overlaps with any column
        image_center_x = (bbox_px[0] + bbox_px[2]) / 2
        image_center_y = (bbox_px[1] + bbox_px[3]) / 2
        
        in_column = False
        for x0, x1 in columns:
            # Check if image center is within column OR if image overlaps column
            if (x0 <= image_center_x < x1) or (bbox_px[0] < x1 and bbox_px[2] > x0):
                in_column = True
                break
        
        # If no columns detected, accept all images
        if not columns:
            in_column = True
        
        if in_column:
            # Size-based filtering to avoid icons and small warning symbols
            w = max(1, bbox_px[2] - bbox_px[0])
            h = max(1, bbox_px[3] - bbox_px[1])
            area = w * h

            # Extremely elongated and thin -> likely rule/line strip
            aspect = w / h if h > 0 else 0

            is_too_small = (w < min_dim) or (h < min_dim) or (area < min_area)
            is_strip = (aspect > 8.0 and h < 50) or (aspect < 0.125 and w < 50)

            # Near-square tiny images are typical icons/logos
            is_small_square_icon = abs(w - h) <= 0.2 * max(w, h) and max(w, h) < (min_dim + 10)

            if is_too_small or is_strip or is_small_square_icon:
                logging.info(
                    f"Skipping small/strip/icon image {bbox_px} (w={w}, h={h}, area={area})"
                )
                continue

            # Add modest padding for image figures
            padding = 8
            padded_bbox = [
                max(0, bbox_px[0] - padding),
                max(0, bbox_px[1] - padding),
                bbox_px[2] + padding,
                bbox_px[3] + padding
            ]

            figure = Figure(
                bbox_px=padded_bbox,
                source='image',
                stroke_length=0
            )
            figures.append(figure)
            logging.info(f"Detected image figure: {padded_bbox}")
    
    return figures

def merge_figures(figures: List[Figure]) -> List[Figure]:
    """
    Merge overlapping figures using Non-Maximum Suppression
    
    Args:
        figures: List of Figure objects
        
    Returns:
        List of merged Figure objects
    """
    if not figures:
        return []
    
    # Sort by area (largest first)
    figures = sorted(figures, key=lambda f: f.area, reverse=True)
    
    merged = []
    used = set()
    
    for i, figure in enumerate(figures):
        if i in used:
            continue
        
        # Find overlapping figures
        overlapping = [i]
        for j in range(i+1, len(figures)):
            if j in used:
                continue
            
            if calculate_iou(figure, figures[j]) > NMS_IOU:
                overlapping.append(j)
                used.add(j)
        
        if len(overlapping) == 1:
            # No overlaps, keep original
            merged.append(figure)
        else:
            # Merge overlapping figures
            merged_figure = merge_overlapping_figures([figures[k] for k in overlapping])
            merged.append(merged_figure)
        
        used.add(i)
    
    return merged

def calculate_iou(fig1: Figure, fig2: Figure) -> float:
    """
    Calculate Intersection over Union (IoU) between two figures
    
    Args:
        fig1: First figure
        fig2: Second figure
        
    Returns:
        IoU value between 0 and 1
    """
    x0_1, y0_1, x1_1, y1_1 = fig1.bbox_px
    x0_2, y0_2, x1_2, y1_2 = fig2.bbox_px
    
    # Calculate intersection
    x0_i = max(x0_1, x0_2)
    y0_i = max(y0_1, y0_2)
    x1_i = min(x1_1, x1_2)
    y1_i = min(y1_1, y1_2)
    
    if x0_i >= x1_i or y0_i >= y1_i:
        return 0.0
    
    # Calculate areas
    area1 = (x1_1 - x0_1) * (y1_1 - y0_1)
    area2 = (x1_2 - x0_2) * (y1_2 - y0_2)
    area_i = (x1_i - x0_i) * (y1_i - y0_i)
    
    # Calculate union
    area_u = area1 + area2 - area_i
    
    return area_i / area_u if area_u > 0 else 0.0

def merge_overlapping_figures(figures: List[Figure]) -> Figure:
    """
    Merge a list of overlapping figures into a single figure
    
    Args:
        figures: List of overlapping Figure objects
        
    Returns:
        Single merged Figure object
    """
    if not figures:
        return None
    
    if len(figures) == 1:
        return figures[0]
    
    # Calculate combined bounding box
    x0 = min(f.bbox_px[0] for f in figures)
    y0 = min(f.bbox_px[1] for f in figures)
    x1 = max(f.bbox_px[2] for f in figures)
    y1 = max(f.bbox_px[3] for f in figures)
    
    # Determine source type
    sources = [f.source for f in figures]
    if 'vector' in sources and 'image' in sources:
        source = 'mixed'
    elif 'vector' in sources:
        source = 'vector'
    else:
        source = 'image'
    
    # Calculate total stroke length
    total_stroke_length = sum(f.stroke_length for f in figures)
    
    return Figure(
        bbox_px=[x0, y0, x1, y1],
        source=source,
        stroke_length=total_stroke_length
    )

def _expand_bbox(b: List[int], pad: int, w: Optional[int] = None, h: Optional[int] = None) -> List[int]:
    x0, y0, x1, y1 = b
    x0 -= pad
    y0 -= pad
    x1 += pad
    y1 += pad
    if w is not None and h is not None:
        x0 = max(0, min(x0, w))
        y0 = max(0, min(y0, h))
        x1 = max(0, min(x1, w))
        y1 = max(0, min(y1, h))
    return [x0, y0, x1, y1]

def _bbox_iou(a: List[int], b: List[int]) -> float:
    ax0, ay0, ax1, ay1 = a
    bx0, by0, bx1, by1 = b
    ix0, iy0 = max(ax0, bx0), max(ay0, by0)
    ix1, iy1 = min(ax1, bx1), min(ay1, by1)
    if ix0 >= ix1 or iy0 >= iy1:
        return 0.0
    ia = (ix1 - ix0) * (iy1 - iy0)
    ua = (ax1-ax0)*(ay1-ay0) + (bx1-bx0)*(by1-by0) - ia
    return ia/ua if ua > 0 else 0.0

def refine_figures(figures: List[Figure], page_size: Dict[str, Any]) -> List[Figure]:
    """
    Reduce fragmentation via proximity merge, containment pruning, and filters.
    """
    if not figures:
        return []

    page_w, page_h = page_size.get('px', (0, 0))
    page_area = max(1, page_w * page_h)

    # 1) Drop tiny fragments and label strips
    min_area = int(0.0015 * page_area)  # 0.15% page area
    filtered: List[Figure] = []
    for f in figures:
        x0, y0, x1, y1 = f.bbox_px
        w = max(1, x1 - x0)
        h = max(1, y1 - y0)
        ar = w / h
        if f.area < min_area:
            continue
        if ar > 8.0 and h < 40:
            # likely a label strip
            continue
        filtered.append(f)

    if not filtered:
        return []

    # 2) Non-maximum suppression (already done in merge_figures), then proximity merge
    boxes = [f.bbox_px[:] for f in filtered]
    used = [False] * len(filtered)
    proximity = 20  # px
    pad = 12
    merged: List[List[int]] = []
    groups: List[List[int]] = []

    for i in range(len(filtered)):
        if used[i]:
            continue
        group = [i]
        used[i] = True
        changed = True
        while changed:
            changed = False
            bi = _expand_bbox(boxes[group[-1]], pad)
            for j in range(len(filtered)):
                if used[j]:
                    continue
                bj = _expand_bbox(boxes[j], pad)
                # overlap or close proximity: grow by proximity threshold
                close = not (bj[2] < bi[0]-proximity or bj[0] > bi[2]+proximity or 
                             bj[3] < bi[1]-proximity or bj[1] > bi[3]+proximity)
                if close or _bbox_iou(bi, bj) > 0:
                    group.append(j)
                    used[j] = True
                    # update bi to include new box
                    bi = [min(bi[0], bj[0]), min(bi[1], bj[1]), max(bi[2], bj[2]), max(bi[3], bj[3])]
                    changed = True
        groups.append(group)

    # Merge groups
    merged_figs: List[Figure] = []
    for g in groups:
        xs0 = min(filtered[k].bbox_px[0] for k in g)
        ys0 = min(filtered[k].bbox_px[1] for k in g)
        xs1 = max(filtered[k].bbox_px[2] for k in g)
        ys1 = max(filtered[k].bbox_px[3] for k in g)
        merged_figs.append(Figure([xs0, ys0, xs1, ys1], source='mixed',
                                  stroke_length=sum(filtered[k].stroke_length for k in g)))

    # 3) Containment pruning (drop boxes mostly inside larger ones)
    merged_figs = sorted(merged_figs, key=lambda f: f.area, reverse=True)
    keep: List[Figure] = []
    for i, f in enumerate(merged_figs):
        contained = False
        for parent in keep:
            iou = _bbox_iou(f.bbox_px, parent.bbox_px)
            # approximate containment: small box mostly inside big one
            if iou > 0.85 and parent.area >= 1.5 * f.area:
                contained = True
                break
        if not contained:
            keep.append(f)

    # Cap count to avoid excessive boxes
    max_figs = 15
    return keep[:max_figs]

def snap_to_columns(figure: Figure, columns: List[Tuple[int, int]], 
                   tolerance: int = 10) -> None:
    """
    Snap figure edges to nearest column boundaries
    
    Args:
        figure: Figure to snap
        columns: List of column boundaries
        tolerance: Maximum distance for snapping
    """
    if not columns:
        return
    
    x0, y0, x1, y1 = figure.bbox_px
    
    # Snap left edge
    best_left = x0
    min_dist = float('inf')
    for col_x0, col_x1 in columns:
        for edge in [col_x0, col_x1]:
            dist = abs(x0 - edge)
            if dist < min_dist and dist <= tolerance:
                min_dist = dist
                best_left = edge
    
    # Snap right edge
    best_right = x1
    min_dist = float('inf')
    for col_x0, col_x1 in columns:
        for edge in [col_x0, col_x1]:
            dist = abs(x1 - edge)
            if dist < min_dist and dist <= tolerance:
                min_dist = dist
                best_right = edge
    
    figure.bbox_px = [best_left, y0, best_right, y1]

def crop_figure_image(img: np.ndarray, figure: Figure, output_path: str) -> None:
    """
    Crop and save figure image
    
    Args:
        img: Full page image
        figure: Figure object with bounding box
        output_path: Path to save cropped image
    """
    x0, y0, x1, y1 = figure.bbox_px
    
    # Ensure coordinates are within image bounds
    h, w = img.shape[:2]
    x0 = max(0, min(x0, w-1))
    y0 = max(0, min(y0, h-1))
    x1 = max(x0+1, min(x1, w))
    y1 = max(y0+1, min(y1, h))
    
    # Crop image
    cropped = img[y0:y1, x0:x1].copy()
    
    # Convert RGB to BGR for OpenCV
    if len(cropped.shape) == 3 and cropped.shape[2] == 3:
        cropped_bgr = cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR)
    else:
        cropped_bgr = cropped
    
    # Save image
    import cv2
    cv2.imwrite(output_path, cropped_bgr)

def detect_figures_fallback(img: np.ndarray, columns: List[Tuple[int, int]]) -> List[Figure]:
    """
    Fallback figure detection using connected components analysis
    
    Args:
        img: Page image
        columns: List of column boundaries
        
    Returns:
        List of detected Figure objects
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img.copy()
    
    h, w = gray.shape
    
    # Create binary image by removing text
    # Use horizontal erosion to remove text lines
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3))
    eroded = cv2.erode(gray, kernel_h, iterations=2)
    
    # Find connected components
    _, labels, stats, centroids = cv2.connectedComponentsWithStats(eroded, connectivity=8)
    
    figures = []
    min_area = int(0.01 * w * h)  # 1% of page area
    min_aspect = 1.5  # Minimum aspect ratio
    
    for i in range(1, labels.max() + 1):  # Skip background (label 0)
        area = stats[i, cv2.CC_STAT_AREA]
        if area < min_area:
            continue
        
        # Get bounding box
        x0 = stats[i, cv2.CC_STAT_LEFT]
        y0 = stats[i, cv2.CC_STAT_TOP]
        x1 = x0 + stats[i, cv2.CC_STAT_WIDTH]
        y1 = y0 + stats[i, cv2.CC_STAT_HEIGHT]
        
        # Check aspect ratio
        aspect = (x1 - x0) / (y1 - y0)
        if aspect < min_aspect:
            continue
        
        # Check if within columns
        center_x = (x0 + x1) / 2
        in_column = False
        for col_x0, col_x1 in columns:
            if col_x0 <= center_x < col_x1:
                in_column = True
                break
        
        if in_column:
            figure = Figure(
                bbox_px=[x0, y0, x1, y1],
                source='vector',  # Fallback detection
                stroke_length=0
            )
            figures.append(figure)
    
    return figures

def expand_figures_content_aware(img: np.ndarray, figures: List[Figure], 
                                 text_blocks: List[Any], max_expand: int = 60) -> None:
    """
    Expand each figure's bbox outward using local edge connectivity while
    avoiding expansion into nearby text blocks. Operates in-place.
    
    Args:
        img: Full page RGB image
        figures: List of detected Figure objects
        text_blocks: Text blocks to avoid when expanding
        max_expand: Maximum pixels to search outward on each side
    """
    if img is None or not isinstance(img, np.ndarray) or not figures:
        return
    # Prepare grayscale once
    if len(img.shape) == 3:
        gray_full = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray_full = img
    h_full, w_full = gray_full.shape[:2]

    # Build list of exclusion rectangles from text blocks (captions included in text)
    exclusion_rects: List[List[int]] = []
    if text_blocks:
        for tb in text_blocks:
            bbox = getattr(tb, 'bbox_px', None) or getattr(tb, 'bbox', None)
            if bbox and isinstance(bbox, (list, tuple)) and len(bbox) == 4:
                # Inflate slightly to strongly avoid text
                x0, y0, x1, y1 = bbox
                pad = 6
                exclusion_rects.append([
                    max(0, x0 - pad),
                    max(0, y0 - pad),
                    min(w_full, x1 + pad),
                    min(h_full, y1 + pad)
                ])

    for fig in figures:
        x0, y0, x1, y1 = fig.bbox_px
        # Define a search ROI around the current figure
        roi_x0 = max(0, x0 - max_expand)
        roi_y0 = max(0, y0 - max_expand)
        roi_x1 = min(w_full, x1 + max_expand)
        roi_y1 = min(h_full, y1 + max_expand)

        roi_gray = gray_full[roi_y0:roi_y1, roi_x0:roi_x1]
        if roi_gray.size == 0:
            continue

        # Edge detection and cleanup
        blurred = cv2.GaussianBlur(roi_gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 60, 180)
        # Remove edges inside exclusion (text) areas
        if exclusion_rects:
            for rx0, ry0, rx1, ry1 in exclusion_rects:
                ex0 = max(0, rx0 - roi_x0)
                ey0 = max(0, ry0 - roi_y0)
                ex1 = max(0, rx1 - roi_x0)
                ey1 = max(0, ry1 - roi_y0)
                if ex0 < edges.shape[1] and ey0 < edges.shape[0] and ex1 > 0 and ey1 > 0:
                    edges[max(0, ey0):min(edges.shape[0], ey1),
                          max(0, ex0):min(edges.shape[1], ex1)] = 0

        # Connect nearby edges and fill thin gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.dilate(edges, kernel, iterations=1)
        edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=1)

        # Find contours; keep those touching the original bbox region
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            continue

        # Original bbox in ROI coordinates
        bx0 = x0 - roi_x0
        by0 = y0 - roi_y0
        bx1 = x1 - roi_x1 + (roi_x1 - roi_x0)
        by1 = y1 - roi_y1 + (roi_y1 - roi_y0)

        sel_x0, sel_y0, sel_x1, sel_y1 = bx0, by0, bx1, by1
        for cnt in contours:
            cx, cy, cw, ch = cv2.boundingRect(cnt)
            cx1 = cx + cw
            cy1 = cy + ch
            # Overlap test with current bbox region (in ROI coords)
            ox0 = max(bx0, cx)
            oy0 = max(by0, cy)
            ox1 = min(bx1, cx1)
            oy1 = min(by1, cy1)
            if ox0 < ox1 and oy0 < oy1:
                sel_x0 = min(sel_x0, cx)
                sel_y0 = min(sel_y0, cy)
                sel_x1 = max(sel_x1, cx1)
                sel_y1 = max(sel_y1, cy1)

        # Map back to page coordinates
        new_x0 = max(0, roi_x0 + sel_x0)
        new_y0 = max(0, roi_y0 + sel_y0)
        new_x1 = min(w_full, roi_x0 + sel_x1)
        new_y1 = min(h_full, roi_y0 + sel_y1)

        # Only update if area increased meaningfully, to avoid accidental shrink
        old_area = max(1, (x1 - x0) * (y1 - y0))
        new_area = max(1, (new_x1 - new_x0) * (new_y1 - new_y0))
        if new_area > old_area * 1.02:
            fig.bbox_px = [int(new_x0), int(new_y0), int(new_x1), int(new_y1)]

def expand_figures_away_from_text(figures: List[Figure], text_blocks: List[Any],
                                  page_size: Dict[str, Any], max_expand: int = 80,
                                  safety_margin: int = 8) -> None:
    """
    Expand figure bbox sides into nearby whitespace until reaching the closest
    text block (or page edge), capped by max_expand per side.
    This is robust when edge-based growth finds no signal (e.g., vector drawings).
    """
    if not figures:
        return
    page_w, page_h = page_size.get('px', (1275, 1650))

    # Collect text rects once
    rects: List[List[int]] = []
    if text_blocks:
        for tb in text_blocks:
            b = getattr(tb, 'bbox_px', None) or getattr(tb, 'bbox', None)
            if b and len(b) == 4:
                rects.append([int(b[0]), int(b[1]), int(b[2]), int(b[3])])

    def horiz_overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
        return not (a1 <= b0 or a0 >= b1)

    def vert_overlap(a0: int, a1: int, b0: int, b1: int) -> bool:
        return not (a1 <= b0 or a0 >= b1)

    for f in figures:
        x0, y0, x1, y1 = f.bbox_px

        # Bottom expansion: find nearest text above bottom side
        nearest_bottom = page_h
        for tx0, ty0, tx1, ty1 in rects:
            if ty0 >= y1 and horiz_overlap(x0, x1, tx0, tx1):
                nearest_bottom = min(nearest_bottom, ty0)
        target_y1 = min(page_h, y1 + max_expand)
        if nearest_bottom < page_h:
            target_y1 = min(target_y1, max(y1, nearest_bottom - safety_margin))

        # Top expansion: nearest text below top edge (i.e., text above figure)
        nearest_top = 0
        for tx0, ty0, tx1, ty1 in rects:
            if ty1 <= y0 and horiz_overlap(x0, x1, tx0, tx1):
                nearest_top = max(nearest_top, ty1)
        target_y0 = max(0, y0 - max_expand)
        if nearest_top > 0:
            target_y0 = max(target_y0, min(y0, nearest_top + safety_margin))

        # Right expansion
        nearest_right = page_w
        for tx0, ty0, tx1, ty1 in rects:
            if tx0 >= x1 and vert_overlap(y0, y1, ty0, ty1):
                nearest_right = min(nearest_right, tx0)
        target_x1 = min(page_w, x1 + max_expand)
        if nearest_right < page_w:
            target_x1 = min(target_x1, max(x1, nearest_right - safety_margin))

        # Left expansion
        nearest_left = 0
        for tx0, ty0, tx1, ty1 in rects:
            if tx1 <= x0 and vert_overlap(y0, y1, ty0, ty1):
                nearest_left = max(nearest_left, tx1)
        target_x0 = max(0, x0 - max_expand)
        if nearest_left > 0:
            target_x0 = max(target_x0, min(x0, nearest_left + safety_margin))

        # Ensure valid box and apply only if it grows
        target_x0 = int(max(0, min(target_x0, target_x1 - 1)))
        target_y0 = int(max(0, min(target_y0, target_y1 - 1)))
        target_x1 = int(min(page_w, max(target_x1, target_x0 + 1)))
        target_y1 = int(min(page_h, max(target_y1, target_y0 + 1)))

        if (target_x0 <= x0 and target_x1 >= x1 and target_y0 <= y0 and target_y1 >= y1):
            f.bbox_px = [target_x0, target_y0, target_x1, target_y1]
