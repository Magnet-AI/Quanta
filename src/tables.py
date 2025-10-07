"""
Table detection using ruled and borderless table detection
"""
import numpy as np
import cv2
from typing import List, Dict, Any, Tuple, Optional
import logging
import csv
import io

# Constants
HOUGH_MINLINE = 0.1  # Fraction of page width
HOUGH_MAXGAP = 0.02  # Fraction of page width
ROW_DY_FACTOR = 0.6  # For line baseline clustering

class Table:
    """Represents a detected table"""
    def __init__(self, bbox_px: List[int], cells: List[Dict], 
                 grid_lines: Optional[Dict] = None, detection_method: str = "unknown"):
        self.bbox_px = bbox_px  # [x0, y0, x1, y1]
        self.cells = cells  # List of cell dictionaries
        self.grid_lines = grid_lines  # Optional grid line information
        self.detection_method = detection_method
        self.image_path = None
        self.csv_path = None
        self.caption = None
    
    @property
    def num_rows(self) -> int:
        if not self.cells:
            return 0
        return max(cell.get('r', 0) for cell in self.cells) + 1
    
    @property
    def num_cols(self) -> int:
        if not self.cells:
            return 0
        return max(cell.get('c', 0) for cell in self.cells) + 1

def extract_tables(img: np.ndarray, text_blocks: List, columns: List[Tuple[int, int]], 
                  page_width: int) -> List[Table]:
    """
    Extract tables from page image using both ruled and text-based detection
    
    Args:
        img: Page image
        text_blocks: List of text blocks
        columns: List of column boundaries
        page_width: Width of page in pixels
        
    Returns:
        List of detected Table objects
    """
    tables = []
    
    logging.info(f"Extracting tables with {len(text_blocks)} text blocks, {len(columns)} columns")
    
    # Try ruled table detection first (for tables with visible lines)
    ruled_tables = detect_ruled_tables(img, columns, page_width)
    logging.info(f"Ruled table detection found {len(ruled_tables)} tables")
    tables.extend(ruled_tables)
    
    # Use text-based table detection as fallback
    text_tables = detect_text_based_tables(text_blocks, columns, page_width)
    logging.info(f"Text-based table detection found {len(text_tables)} tables")
    tables.extend(text_tables)
    
    # Filter out false positives
    filtered_tables = filter_table_candidates(tables)
    logging.info(f"Final table count after filtering: {len(filtered_tables)}")
    
    return filtered_tables

def detect_ruled_tables(img: np.ndarray, columns: List[Tuple[int, int]], 
                       page_width: int) -> List[Table]:
    """
    Detect tables with visible lines using Hough line detection
    
    Args:
        img: Page image
        columns: List of column boundaries
        page_width: Width of page in pixels
        
    Returns:
        List of detected Table objects
    """
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img.copy()
    
    tables = []
    
    for col_x0, col_x1 in columns:
        # Crop column region
        col_img = gray[:, col_x0:col_x1]
        
        # Detect lines in this column
        table = detect_ruled_table_in_region(col_img, col_x0, page_width)
        if table:
            tables.append(table)
    
    return tables

def detect_ruled_table_in_region(img: np.ndarray, col_offset: int, 
                                page_width: int) -> Optional[Table]:
    """
    Detect ruled table in a specific image region
    
    Args:
        img: Image region
        col_offset: X offset of the column
        page_width: Full page width
        
    Returns:
        Table object if detected, None otherwise
    """
    h, w = img.shape
    
    # Check if image is empty or too small
    if h == 0 or w == 0 or h < 10 or w < 10:
        logging.info(f"Image too small for table detection: {w}x{h}")
        return None
    
    logging.info(f"Detecting table in region {w}x{h} at offset {col_offset}")
    
    # Apply morphological operations to emphasize lines
    # Horizontal lines - more aggressive for 150 DPI
    kernel_h = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(3, w//15)))
    img_h = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel_h)
    
    # Vertical lines - more aggressive for 150 DPI
    kernel_v = cv2.getStructuringElement(cv2.MORPH_RECT, (max(3, h//15), 1))
    img_v = cv2.morphologyEx(img, cv2.MORPH_CLOSE, kernel_v)
    
    # Combine horizontal and vertical
    img_lines = cv2.addWeighted(img_h, 0.5, img_v, 0.5, 0)
    
    # Debug: Save intermediate images (disabled for now)
    # debug_dir = "debug_tables"
    # import os
    # os.makedirs(debug_dir, exist_ok=True)
    # cv2.imwrite(f"{debug_dir}/original_{col_offset}.png", img)
    # cv2.imwrite(f"{debug_dir}/horizontal_{col_offset}.png", img_h)
    # cv2.imwrite(f"{debug_dir}/vertical_{col_offset}.png", img_v)
    # cv2.imwrite(f"{debug_dir}/combined_{col_offset}.png", img_lines)
    
    # Detect lines using Hough transform - improved parameters for better detection
    min_line_length = max(30, int(HOUGH_MINLINE * page_width * 0.3))  # More sensitive
    max_line_gap = max(5, int(HOUGH_MAXGAP * page_width * 0.1))  # More sensitive
    
    logging.info(f"Hough parameters: minLineLength={min_line_length}, maxLineGap={max_line_gap}")
    
    lines = cv2.HoughLinesP(
        img_lines, 1, np.pi/180, threshold=30,  # Lower threshold for more lines
        minLineLength=min_line_length, maxLineGap=max_line_gap
    )
    
    if lines is None:
        logging.info("No lines detected by Hough transform")
        return None
    
    logging.info(f"Detected {len(lines)} lines by Hough transform")
    
    # Debug: Draw all detected lines (disabled for now)
    # debug_img = cv2.cvtColor(img_lines, cv2.COLOR_GRAY2BGR)
    # for line in lines:
    #     x1, y1, x2, y2 = line[0]
    #     cv2.line(debug_img, (x1, y1), (x2, y2), (0, 255, 0), 1)
    # cv2.imwrite(f"{debug_dir}/all_lines_{col_offset}.png", debug_img)
    
    if len(lines) < 4:
        logging.info(f"Not enough lines detected: {len(lines)} < 4")
        return None
    
    # Separate horizontal and vertical lines
    h_lines = []
    v_lines = []
    
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
        
        if abs(angle) < 15 or abs(angle - 180) < 15:
            h_lines.append((x1, y1, x2, y2))
        elif abs(angle - 90) < 15 or abs(angle + 90) < 15:
            v_lines.append((x1, y1, x2, y2))
    
    logging.info(f"Separated into {len(h_lines)} horizontal and {len(v_lines)} vertical lines")
    
    # Debug: Draw separated lines (disabled for now)
    # debug_h = cv2.cvtColor(img_lines, cv2.COLOR_GRAY2BGR)
    # for line in h_lines:
    #     cv2.line(debug_h, (line[0], line[1]), (line[2], line[3]), (0, 0, 255), 2)
    # cv2.imwrite(f"{debug_dir}/horizontal_lines_{col_offset}.png", debug_h)
    
    # debug_v = cv2.cvtColor(img_lines, cv2.COLOR_GRAY2BGR)
    # for line in v_lines:
    #     cv2.line(debug_v, (line[0], line[1]), (line[2], line[3]), (255, 0, 0), 2)
    # cv2.imwrite(f"{debug_dir}/vertical_lines_{col_offset}.png", debug_v)
    
    if len(h_lines) < 2 or len(v_lines) < 2:
        logging.info(f"Not enough lines after separation: h={len(h_lines)}, v={len(v_lines)}")
        return None
    
    # Merge near-collinear lines
    h_lines = merge_collinear_lines(h_lines, threshold=10)  # More lenient
    v_lines = merge_collinear_lines(v_lines, threshold=10)  # More lenient
    
    logging.info(f"After merging: {len(h_lines)} horizontal, {len(v_lines)} vertical lines")
    
    # More lenient requirements - allow single lines for simple tables
    if len(h_lines) < 1 or len(v_lines) < 1:
        logging.info(f"Not enough lines after merging: h={len(h_lines)}, v={len(v_lines)}")
        return None
    
    # Extract grid
    grid = extract_grid_from_lines(h_lines, v_lines, w, h)
    if not grid:
        logging.info("Failed to extract grid from lines")
        return None
    
    logging.info(f"Extracted grid with {len(grid['rows'])} rows and {len(grid['cols'])} columns")
    
    # Extract cells
    cells = extract_cells_from_grid(grid, img)
    logging.info(f"Extracted {len(cells)} cells")
    
    if len(cells) < 1:  # Need at least 1 cell
        logging.info(f"Not enough cells: {len(cells)} < 1")
        return None
    
    # Additional validation: check if cells form a reasonable table structure
    # Calculate cell density - tables should have reasonable cell density
    cell_area = sum((cell['bbox_px'][2] - cell['bbox_px'][0]) * (cell['bbox_px'][3] - cell['bbox_px'][1]) for cell in cells)
    region_area = w * h
    cell_density = cell_area / region_area if region_area > 0 else 0
    
    if cell_density < 0.1:  # Cells should cover at least 10% of the region
        logging.info(f"Cell density too low: {cell_density:.3f} < 0.1")
        return None
    
    # Check if cells are reasonably sized (not too small or too large)
    avg_cell_area = cell_area / len(cells)
    if avg_cell_area < 100 or avg_cell_area > region_area * 0.5:
        logging.info(f"Average cell area unreasonable: {avg_cell_area} (region: {region_area})")
        return None
    
    # Calculate table bounding box
    if cells:
        x0 = min(cell['bbox_px'][0] for cell in cells)
        y0 = min(cell['bbox_px'][1] for cell in cells)
        x1 = max(cell['bbox_px'][2] for cell in cells)
        y1 = max(cell['bbox_px'][3] for cell in cells)
        
        # Check if table is too large (likely false positive)
        table_width = x1 - x0
        table_height = y1 - y0
        table_area = table_width * table_height
        
        # If table is too large relative to the region, it's likely a false positive
        region_area = w * h
        if table_area > region_area * 0.8:  # Table takes up more than 80% of region
            logging.info(f"Filtering oversized table: {table_area} > {region_area * 0.8} (80% of region)")
            return None
        
        # If table is too large in absolute terms, it's likely a false positive
        if table_width > w * 0.9 or table_height > h * 0.9:
            logging.info(f"Filtering oversized table: w={table_width}/{w}, h={table_height}/{h}")
            return None
        
        # Adjust for column offset
        bbox_px = [x0 + col_offset, y0, x1 + col_offset, y1]
        
        logging.info(f"Detected table with bbox: {bbox_px} (w={table_width}, h={table_height})")
        
        return Table(
            bbox_px=bbox_px,
            cells=cells,
            grid_lines={'horizontal': h_lines, 'vertical': v_lines},
            detection_method='ruled'
        )
    
    return None

def merge_collinear_lines(lines: List[Tuple], threshold: int) -> List[Tuple]:
    """
    Merge near-collinear lines
    
    Args:
        lines: List of (x1, y1, x2, y2) line coordinates
        threshold: Distance threshold for merging
        
    Returns:
        List of merged lines
    """
    if not lines:
        return []
    
    merged = []
    used = set()
    
    for i, line1 in enumerate(lines):
        if i in used:
            continue
        
        x1_1, y1_1, x2_1, y2_1 = line1
        group = [line1]
        used.add(i)
        
        for j, line2 in enumerate(lines[i+1:], i+1):
            if j in used:
                continue
            
            x1_2, y1_2, x2_2, y2_2 = line2
            
            # Check if lines are collinear
            if are_collinear(line1, line2, threshold):
                group.append(line2)
                used.add(j)
        
        # Merge lines in group
        if len(group) == 1:
            merged.append(group[0])
        else:
            merged_line = merge_line_group(group)
            merged.append(merged_line)
    
    return merged

def are_collinear(line1: Tuple, line2: Tuple, threshold: int) -> bool:
    """
    Check if two lines are collinear within threshold
    
    Args:
        line1: First line (x1, y1, x2, y2)
        line2: Second line (x1, y1, x2, y2)
        threshold: Distance threshold
        
    Returns:
        True if lines are collinear
    """
    x1_1, y1_1, x2_1, y2_1 = line1
    x1_2, y1_2, x2_2, y2_2 = line2
    
    # Calculate distance from line1 to line2 endpoints
    dist1 = point_to_line_distance((x1_2, y1_2), line1)
    dist2 = point_to_line_distance((x2_2, y2_2), line1)
    
    return max(dist1, dist2) <= threshold

def point_to_line_distance(point: Tuple, line: Tuple) -> float:
    """
    Calculate distance from point to line
    
    Args:
        point: (x, y) point coordinates
        line: (x1, y1, x2, y2) line coordinates
        
    Returns:
        Distance from point to line
    """
    px, py = point
    x1, y1, x2, y2 = line
    
    # Line equation: ax + by + c = 0
    a = y2 - y1
    b = x1 - x2
    c = x2 * y1 - x1 * y2
    
    return abs(a * px + b * py + c) / np.sqrt(a**2 + b**2)

def merge_line_group(lines: List[Tuple]) -> Tuple:
    """
    Merge a group of collinear lines into a single line
    
    Args:
        lines: List of collinear lines
        
    Returns:
        Single merged line
    """
    if not lines:
        return (0, 0, 0, 0)
    
    if len(lines) == 1:
        return lines[0]
    
    # Find extreme points
    all_points = []
    for line in lines:
        all_points.extend([(line[0], line[1]), (line[2], line[3])])
    
    # Sort by x-coordinate
    all_points.sort()
    
    return (all_points[0][0], all_points[0][1], 
            all_points[-1][0], all_points[-1][1])

def extract_grid_from_lines(h_lines: List[Tuple], v_lines: List[Tuple], 
                           w: int, h: int) -> Optional[Dict]:
    """
    Extract grid structure from horizontal and vertical lines
    
    Args:
        h_lines: List of horizontal lines
        v_lines: List of vertical lines
        w: Image width
        h: Image height
        
    Returns:
        Grid dictionary with rows and columns, or None if invalid
    """
    if not h_lines or not v_lines:
        return None
    
    # Extract unique Y coordinates for rows - use line centers for better accuracy
    y_coords = set()
    for line in h_lines:
        y_center = (line[1] + line[3]) / 2  # Use center of line
        y_coords.add(int(y_center))
    y_coords = sorted(y_coords)
    
    # Extract unique X coordinates for columns - use line centers for better accuracy
    x_coords = set()
    for line in v_lines:
        x_center = (line[0] + line[2]) / 2  # Use center of line
        x_coords.add(int(x_center))
    x_coords = sorted(x_coords)
    
    # Filter out coordinates that are too close together (likely duplicates)
    min_gap = 10  # Minimum 10 pixels between grid lines
    filtered_y = [y_coords[0]]
    for y in y_coords[1:]:
        if y - filtered_y[-1] >= min_gap:
            filtered_y.append(y)
    
    filtered_x = [x_coords[0]]
    for x in x_coords[1:]:
        if x - filtered_x[-1] >= min_gap:
            filtered_x.append(x)
    
    # More lenient requirements - allow single row/column tables
    if len(filtered_y) < 1 or len(filtered_x) < 1:
        logging.info(f"Not enough grid lines after filtering: rows={len(filtered_y)}, cols={len(filtered_x)}")
        return None
    
    # Check if grid is reasonable (not too many lines)
    if len(filtered_y) > 20 or len(filtered_x) > 20:
        logging.info(f"Too many grid lines: rows={len(filtered_y)}, cols={len(filtered_x)}")
        return None
    
    logging.info(f"Grid: {len(filtered_y)} rows, {len(filtered_x)} columns")
    
    return {
        'rows': filtered_y,
        'cols': filtered_x
    }

def extract_cells_from_grid(grid: Dict, img: np.ndarray) -> List[Dict]:
    """
    Extract cell information from grid structure
    
    Args:
        grid: Grid dictionary with rows and columns
        img: Image region
        
    Returns:
        List of cell dictionaries
    """
    cells = []
    rows = grid['rows']
    cols = grid['cols']
    
    # Add safety checks to prevent index errors
    if not rows or not cols or len(rows) < 2 or len(cols) < 2:
        logging.warning(f"Invalid grid structure: rows={len(rows)}, cols={len(cols)}")
        return cells
    
    try:
        for r in range(len(rows) - 1):
            for c in range(len(cols) - 1):
                x0, y0 = cols[c], rows[r]
                x1, y1 = cols[c + 1], rows[r + 1]
                
                # Validate cell coordinates
                if x0 >= x1 or y0 >= y1:
                    logging.warning(f"Invalid cell coordinates: ({x0}, {y0}, {x1}, {y1})")
                    continue
                
                # Ensure coordinates are within image bounds
                h, w = img.shape[:2]
                x0, y0 = max(0, int(x0)), max(0, int(y0))
                x1, y1 = min(w, int(x1)), min(h, int(y1))
                
                if x0 >= x1 or y0 >= y1:
                    continue
                
                # Extract text from cell region
                cell_img = img[y0:y1, x0:x1]
                text = extract_text_from_cell(cell_img)
                
                cell = {
                    'r': r,
                    'c': c,
                    'text': text,
                    'bbox_px': [int(x0), int(y0), int(x1), int(y1)]
                }
                cells.append(cell)
    except (IndexError, ValueError) as e:
        logging.error(f"Error extracting cells from grid: {e}")
        return []
    
    return cells

def extract_text_from_cell(cell_img: np.ndarray) -> str:
    """
    Extract text from a cell image using OCR
    
    Args:
        cell_img: Cell image region
        
    Returns:
        Extracted text
    """
    # Simple text extraction - in practice, you'd use OCR here
    # For now, return empty string
    return ""

def detect_borderless_tables(img: np.ndarray, text_blocks: List, 
                            columns: List[Tuple[int, int]], 
                            page_width: int) -> List[Table]:
    """
    Detect tables without visible lines using text alignment analysis
    
    Args:
        img: Page image
        text_blocks: List of text blocks
        columns: List of column boundaries
        page_width: Width of page in pixels
        
    Returns:
        List of detected Table objects
    """
    tables = []
    
    for col_x0, col_x1 in columns:
        # Filter text blocks within this column
        col_blocks = [b for b in text_blocks 
                     if col_x0 <= b.center_x < col_x1]
        
        if len(col_blocks) < 4:  # Need at least 4 blocks for a table
            continue
        
        # Group blocks into rows by baseline proximity
        rows = group_blocks_into_rows(col_blocks)
        
        if len(rows) < 2:  # Need at least 2 rows
            continue
        
        # Detect column structure
        cols = detect_column_structure(rows)
        
        if len(cols) < 2:  # Need at least 2 columns
            continue
        
        # Validate table structure
        if validate_table_structure(rows, cols):
            table = create_borderless_table(rows, cols, col_x0)
            if table:
                tables.append(table)
    
    return tables

def group_blocks_into_rows(blocks: List) -> List[List]:
    """
    Group text blocks into rows based on baseline proximity
    
    Args:
        blocks: List of text blocks
        
    Returns:
        List of rows, where each row is a list of blocks
    """
    if not blocks:
        return []
    
    # Sort blocks by y-coordinate
    blocks = sorted(blocks, key=lambda b: b.bbox_px[1])
    
    # Calculate median line height
    heights = [b.height for b in blocks]
    median_height = np.median(heights)
    baseline_threshold = median_height * ROW_DY_FACTOR
    
    rows = []
    current_row = [blocks[0]]
    
    for i in range(1, len(blocks)):
        prev_block = blocks[i-1]
        curr_block = blocks[i]
        
        y_diff = curr_block.bbox_px[1] - prev_block.bbox_px[1]
        
        if y_diff <= baseline_threshold:
            current_row.append(curr_block)
        else:
            rows.append(current_row)
            current_row = [curr_block]
    
    if current_row:
        rows.append(current_row)
    
    return rows

def detect_column_structure(rows: List[List]) -> List[float]:
    """
    Detect column structure from aligned text blocks
    
    Args:
        rows: List of rows, each containing text blocks
        
    Returns:
        List of column X coordinates
    """
    if not rows:
        return []
    
    # Collect all X coordinates
    x_coords = []
    for row in rows:
        for block in row:
            x_coords.append(block.bbox_px[0])  # left edge
            x_coords.append(block.bbox_px[2])  # right edge
    
    if not x_coords:
        return []
    
    # Cluster X coordinates
    x_coords = np.array(x_coords)
    
    # Use simple clustering based on proximity
    x_coords_sorted = np.sort(x_coords)
    clusters = []
    current_cluster = [x_coords_sorted[0]]
    
    for i in range(1, len(x_coords_sorted)):
        if x_coords_sorted[i] - x_coords_sorted[i-1] < 20:  # 20px threshold
            current_cluster.append(x_coords_sorted[i])
        else:
            clusters.append(current_cluster)
            current_cluster = [x_coords_sorted[i]]
    
    if current_cluster:
        clusters.append(current_cluster)
    
    # Get cluster centers
    col_centers = [np.mean(cluster) for cluster in clusters]
    col_centers.sort()
    
    return col_centers

def validate_table_structure(rows: List[List], cols: List[float]) -> bool:
    """
    Validate that the detected structure forms a proper table
    
    Args:
        rows: List of rows
        cols: List of column X coordinates
        
    Returns:
        True if structure is valid
    """
    if len(rows) < 2 or len(cols) < 2:
        return False
    
    # Check that most rows have blocks in multiple columns
    multi_col_rows = 0
    for row in rows:
        if len(row) >= 2:
            multi_col_rows += 1
    
    # At least 60% of rows should have multiple columns
    return multi_col_rows >= 0.6 * len(rows)

def create_borderless_table(rows: List[List], cols: List[float], 
                           col_offset: int) -> Optional[Table]:
    """
    Create a Table object from detected rows and columns
    
    Args:
        rows: List of rows
        cols: List of column X coordinates
        col_offset: X offset of the column
        
    Returns:
        Table object if successful, None otherwise
    """
    if not rows or not cols:
        return None
    
    # Create cells
    cells = []
    for r, row in enumerate(rows):
        for c in range(len(cols) - 1):
            # Find blocks in this column
            col_blocks = []
            for block in row:
                if cols[c] <= block.center_x < cols[c + 1]:
                    col_blocks.append(block)
            
            # Merge blocks in this cell
            if col_blocks:
                # Calculate cell bounding box
                x0 = min(b.bbox_px[0] for b in col_blocks)
                y0 = min(b.bbox_px[1] for b in col_blocks)
                x1 = max(b.bbox_px[2] for b in col_blocks)
                y1 = max(b.bbox_px[3] for b in col_blocks)
                
                # Combine text
                text = " ".join(b.text for b in col_blocks)
                
                cell = {
                    'r': r,
                    'c': c,
                    'text': text,
                    'bbox_px': [int(x0), int(y0), int(x1), int(y1)]
                }
                cells.append(cell)
    
    if not cells:
        return None
    
    # Calculate table bounding box
    x0 = min(cell['bbox_px'][0] for cell in cells)
    y0 = min(cell['bbox_px'][1] for cell in cells)
    x1 = max(cell['bbox_px'][2] for cell in cells)
    y1 = max(cell['bbox_px'][3] for cell in cells)
    
    bbox_px = [x0 + col_offset, y0, x1 + col_offset, y1]
    
    return Table(
        bbox_px=bbox_px,
        cells=cells,
        detection_method='borderless'
    )

def merge_tables(tables: List[Table]) -> List[Table]:
    """
    Merge overlapping tables and filter out false positives
    
    Args:
        tables: List of Table objects
        
    Returns:
        List of merged Table objects
    """
    if not tables:
        return []
    
    # Filter out false positive tables
    filtered_tables = []
    for table in tables:
        bbox = table.bbox_px
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        area = width * height
        
        logging.info(f"Evaluating table: {bbox} (w={width}, h={height}, area={area}, cells={len(table.cells)})")
        
        # Filter out very narrow tables (likely margin artifacts)
        if width < 30:
            logging.info(f"Filtering narrow table: {bbox} (width: {width})")
            continue
        
        # Filter out very tall, narrow tables (likely page margins)
        if height > 1500 and width < 50:
            logging.info(f"Filtering margin table: {bbox} (width: {width}, height: {height})")
            continue
        
        # Filter out tables with very few cells (need at least 2x2 grid)
        if len(table.cells) < 4:
            logging.info(f"Filtering table with too few cells: {bbox} (cells: {len(table.cells)})")
            continue
        
        # Filter out tables that are too small overall
        if area < 2000:  # 2000 pixels minimum area
            logging.info(f"Filtering small table: {bbox} (area: {area})")
            continue
        
        # Filter out tables with extreme aspect ratios (likely not real tables)
        aspect_ratio = width / height if height > 0 else 0
        if aspect_ratio > 20 or aspect_ratio < 0.05:
            logging.info(f"Filtering table with extreme aspect ratio: {bbox} (ratio: {aspect_ratio:.2f})")
            continue
        
        # Check if table has reasonable structure (at least 2 rows and 2 columns)
        if table.num_rows < 2 or table.num_cols < 2:
            logging.info(f"Filtering table with insufficient structure: {bbox} (rows={table.num_rows}, cols={table.num_cols})")
            continue
        
        logging.info(f"Keeping table: {bbox}")
        filtered_tables.append(table)
    
    logging.info(f"Filtered {len(tables) - len(filtered_tables)} false positive tables, kept {len(filtered_tables)}")
    return filtered_tables

def save_table_csv(table: Table, output_path: str) -> None:
    """
    Save table data as CSV file
    
    Args:
        table: Table object
        output_path: Path to save CSV file
    """
    if not table.cells:
        return
    
    # Create 2D array
    data = [[""] * table.num_cols for _ in range(table.num_rows)]
    
    for cell in table.cells:
        r = cell['r']
        c = cell['c']
        text = cell['text']
        if r < table.num_rows and c < table.num_cols:
            data[r][c] = text
    
    # Write CSV
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(data)

def detect_text_based_tables(text_blocks: List, columns: List[Tuple[int, int]], 
                            page_width: int) -> List[Table]:
    """
    Detect tables by analyzing text block patterns and alignment
    
    Args:
        text_blocks: List of text blocks
        columns: List of column boundaries
        page_width: Width of page in pixels
        
    Returns:
        List of detected Table objects
    """
    tables = []
    
    if not text_blocks:
        return tables
    
    # Group text blocks by column
    for col_idx, (col_x0, col_x1) in enumerate(columns):
        col_blocks = [block for block in text_blocks 
                     if col_x0 <= block.bbox_px[0] <= col_x1]
        
        if len(col_blocks) < 3:  # Need at least 3 blocks for a table
            continue
        
        # Look for tabular patterns in this column
        table_candidates = find_tabular_patterns(col_blocks, col_x0, col_x1)
        tables.extend(table_candidates)
    
    return tables

def find_tabular_patterns(blocks: List, col_x0: int, col_x1: int) -> List[Table]:
    """
    Find tabular patterns in a group of text blocks
    
    Args:
        blocks: List of text blocks in a column
        col_x0: Column left boundary
        col_x1: Column right boundary
        
    Returns:
        List of detected Table objects
    """
    tables = []
    
    if len(blocks) < 3:
        return tables
    
    # Sort blocks by y-coordinate
    blocks = sorted(blocks, key=lambda b: b.bbox_px[1])
    
    # Look for patterns that suggest tables
    # Pattern 1: Multiple lines with similar x-coordinates (aligned columns)
    # Pattern 2: Lines with multiple short text segments
    # Pattern 3: Lines with numbers, codes, or structured data
    
    # Group blocks by similar y-coordinates (same row) - more lenient
    row_groups = []
    current_row = [blocks[0]]
    row_threshold = 30  # pixels - more lenient
    
    for i in range(1, len(blocks)):
        if abs(blocks[i].bbox_px[1] - blocks[i-1].bbox_px[1]) <= row_threshold:
            current_row.append(blocks[i])
        else:
            if len(current_row) >= 1:  # At least 1 block in row (more lenient)
                row_groups.append(current_row)
            current_row = [blocks[i]]
    
    if len(current_row) >= 1:
        row_groups.append(current_row)
    
    # Look for table-like patterns - very lenient
    if len(row_groups) >= 1:  # At least 1 row (very lenient)
        # Check if rows have similar structure
        table_rows = []
        for row in row_groups:
            if len(row) >= 1:  # At least 1 column (more lenient)
                # Check if this looks like tabular data
                if is_tabular_row(row):
                    table_rows.append(row)
        
        if len(table_rows) >= 1:  # At least 1 valid table row (more lenient)
            # Create table from these rows
            table = create_table_from_rows(table_rows, col_x0, col_x1)
            if table:
                tables.append(table)
    
    return tables

def is_tabular_row(row_blocks: List) -> bool:
    """
    Check if a row of text blocks looks like tabular data
    
    Args:
        row_blocks: List of text blocks in a row
        
    Returns:
        True if this looks like tabular data
    """
    if len(row_blocks) < 2:  # Need at least 2 blocks for a table row
        return False
    
    # Check for patterns that suggest table data
    texts = [block.text.strip() for block in row_blocks]
    
    # FIRST: Check if this looks like a technical drawing (reject early)
    if is_technical_drawing_text(texts):
        return False
    
    # Pattern 1: Multiple segments with table-specific keywords
    table_keywords = [
        'status', 'material', 'package', 'qty', 'rohs', 'lead', 'msl', 'temp',
        'part', 'number', 'type', 'pins', 'carrier', 'finish', 'rating', 'reflow',
        'active', 'production', 'vqfn', 'rsm', 'nipdau', 'level-1', 'unlimited',
        'orderable', 'ball', 'peak', 'op', 'marking', 'addendum', 'information'
    ]
    
    keyword_count = 0
    for text in texts:
        if any(keyword in text.lower() for keyword in table_keywords):
            keyword_count += 1
    
    # Need at least 2 keywords for table-like content (more strict)
    if keyword_count >= 2:
        return True
    
    # Pattern 2: Contains structured codes AND multiple blocks
    structured_patterns = [
        r'^[A-Z]{2,}\d+$',  # Codes like "VQFN32", "RSM32"
        r'^\d+$',  # Pure numbers
        r'^[A-Za-z]+-[A-Za-z]+$',  # Hyphenated codes like "Level-1"
        r'^\d+-\d+$',  # Number ranges like "3000-250"
        r'^[A-Z]{3,}\d+[A-Z]*$',  # Part numbers like "TPS51633RSMR"
        r'^\([0-9]+\)$',  # Numbered items like "(1)", "(2)"
    ]
    
    import re
    pattern_count = 0
    for text in texts:
        if any(re.match(pattern, text) for pattern in structured_patterns):
            pattern_count += 1
    
    # Need at least 2 structured patterns AND multiple blocks
    if pattern_count >= 2 and len(texts) >= 3:
        return True
    
    # Pattern 3: Check if blocks are aligned in a proper grid pattern
    if len(texts) >= 3:  # Need at least 3 blocks for a proper table row
        # Check if x-coordinates are reasonably spaced (suggesting columns)
        x_coords = [block.bbox_px[0] for block in row_blocks]
        x_coords.sort()
        
        # Check for reasonable spacing between columns
        gaps = [x_coords[i+1] - x_coords[i] for i in range(len(x_coords)-1)]
        if gaps and min(gaps) > 20:  # At least 20px between columns
            return True
    
    # Pattern 4: Very short text segments with table keywords
    if (len(texts) >= 3 and all(len(text) < 30 for text in texts) and 
        keyword_count >= 1):
        return True
    
    return False

def is_technical_drawing_text(texts: List[str]) -> bool:
    """
    Check if text blocks look like they're from a technical drawing
    
    Args:
        texts: List of text strings
        
    Returns:
        True if this looks like technical drawing text
    """
    import re
    
    # Technical drawing indicators
    tech_keywords = [
        'stencil', 'design', 'vqfn', 'quad', 'flatpack', 'lead', 'metal',
        'laser', 'cutting', 'apertures', 'trapezoidal', 'rounded', 'corners',
        'ipc-7525', 'texas', 'instruments', 'example', 'based', 'thick',
        'printed', 'scale', 'continued', 'notes', 'symm', 'typ', 'max',
        'height', 'width', 'diameter', 'radius', 'exposed', 'pad', 'solder',
        'paste', 'coverage', 'area', 'package', 'mm', 'dimensions'
    ]
    
    # Dimension patterns (very specific to technical drawings)
    dimension_patterns = [
        r'\(\d+\.?\d*\)',  # (0.715), (1.23), etc.
        r'\(\d+\.?\d*\s*[A-Za-z]+\)',  # (R0.05) TYP, etc.
        r'\d+X\s*\(\d+\.?\d*\)',  # 32X (0.55), 4X (1.23), etc.
        r'^\d+\.\d+$',  # Pure decimal numbers like "0.715"
        r'^[A-Z]\d+[A-Z]*\d*$',  # Part numbers like "RSM0032B"
    ]
    
    tech_keyword_count = 0
    dimension_count = 0
    
    for text in texts:
        text_lower = text.lower()
        
        # Count technical keywords
        if any(keyword in text_lower for keyword in tech_keywords):
            tech_keyword_count += 1
        
        # Count dimension patterns
        for pattern in dimension_patterns:
            if re.search(pattern, text):
                dimension_count += 1
                break
    
    # If we have both technical keywords AND dimension patterns, it's likely a technical drawing
    if tech_keyword_count >= 2 and dimension_count >= 2:
        return True
    
    # If we have many dimension patterns (4+), it's definitely a technical drawing
    if dimension_count >= 4:
        return True
    
    # If we have technical keywords and short text blocks (typical of dimension labels)
    if tech_keyword_count >= 1 and dimension_count >= 1 and all(len(text) < 15 for text in texts):
        return True
    
    return False

def create_table_from_rows(table_rows: List, col_x0: int, col_x1: int) -> Optional[Table]:
    """
    Create a Table object from detected table rows
    
    Args:
        table_rows: List of rows, each containing text blocks
        col_x0: Column left boundary
        col_x1: Column right boundary
        
    Returns:
        Table object if valid, None otherwise
    """
    if not table_rows:
        return None
    
    # Calculate table bounding box
    all_blocks = []
    for row in table_rows:
        all_blocks.extend(row)
    
    x0 = min(block.bbox_px[0] for block in all_blocks)
    y0 = min(block.bbox_px[1] for block in all_blocks)
    x1 = max(block.bbox_px[2] for block in all_blocks)
    y1 = max(block.bbox_px[3] for block in all_blocks)
    
    # Validate table size - very lenient for better detection
    width = x1 - x0
    height = y1 - y0
    
    if width < 50 or height < 20:  # Too small (very lenient)
        return None
    
    if width > (col_x1 - col_x0) * 0.95:  # Too wide for column (95% max)
        return None
    
    if height > 1200:  # Too tall (likely not a real table)
        return None
    
    # Create cells from the table structure
    cells = []
    for row_idx, row in enumerate(table_rows):
        for col_idx, block in enumerate(row):
            cell = {
                'bbox_px': block.bbox_px,
                'text': block.text,
                'r': row_idx,
                'c': col_idx
            }
            cells.append(cell)
    
    if len(cells) < 4:  # Need at least 2x2 grid
        return None
    
    return Table(
        bbox_px=[x0, y0, x1, y1],
        cells=cells,
        detection_method='text_based'
    )

def filter_table_candidates(tables: List[Table]) -> List[Table]:
    """
    Filter out false positive table candidates
    
    Args:
        tables: List of table candidates
        
    Returns:
        List of filtered Table objects
    """
    if not tables:
        return []
    
    filtered_tables = []
    for table in tables:
        bbox = table.bbox_px
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        area = width * height
        
        # Filter criteria
        if width < 50 or height < 30:  # Too small
            continue
        
        if area < 2000:  # Too small area
            continue
        
        if len(table.cells) < 4:  # Need at least 2x2 grid
            continue
        
        # Check aspect ratio
        aspect_ratio = width / height if height > 0 else 0
        if aspect_ratio > 10 or aspect_ratio < 0.1:  # Too extreme
            continue
        
        filtered_tables.append(table)
    
    return filtered_tables
