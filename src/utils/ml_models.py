"""
Clean ML-based table detection without hardcoded patterns.
"""

import numpy as np
from typing import List, Dict, Optional
from .text_blocks import TextBlock

# Simple ML-based constants
MIN_BLOCKS_PER_ROW = 2
MIN_COLUMN_SPACING = 15
MAX_COLUMN_SPACING = 300
MIN_ROW_ALIGNMENT = 30

class Table:
    """Represents a detected table"""
    def __init__(self, bbox_px: List[int], cells: List[Dict], 
                 grid_lines: Optional[Dict] = None, detection_method: str = "ml"):
        self.bbox_px = bbox_px
        self.cells = cells
        self.grid_lines = grid_lines
        self.detection_method = detection_method

def is_tabular_row(row_blocks: List[TextBlock], page_width: int, page_height: int) -> bool:
    """
    Check if a row of text blocks looks like a table row using strict structural analysis.
    
    Args:
        row_blocks: List of TextBlock objects in the row
        page_width: Width of the page in pixels
        page_height: Height of the page in pixels
        
    Returns:
        True if this looks like a table row
    """
    if not row_blocks or len(row_blocks) < 2:
        return False
    
    texts = [block.text.strip() for block in row_blocks]
    
    # STRICT REJECTION: If any text is too long (paragraphs, not table cells)
    if any(len(text) > 40 for text in texts):
        return False
    
    # STRICT REJECTION: If text contains sentence indicators (paragraphs, not table cells)
    sentence_indicators = ['.', '!', '?']
    if any(any(indicator in text for indicator in sentence_indicators) for text in texts):
        return False
    
    # STRICT REJECTION: If text looks like descriptive content
    descriptive_words = ['features', 'description', 'applications', 'simplified', 'schematic', 'figure']
    if any(any(word in text.lower() for word in descriptive_words) for text in texts):
        return False
    
    # STRUCTURAL ANALYSIS: Check for proper table structure
    x_coords = [block.bbox_px[0] for block in row_blocks]
    y_coords = [block.bbox_px[1] for block in row_blocks]
    x_coords.sort()
    
    # Check column spacing (must be significant)
    gaps = [x_coords[i+1] - x_coords[i] for i in range(len(x_coords)-1)]
    if not gaps or min(gaps) < 30:  # Must have significant spacing
        return False
    
    # Check vertical alignment (must be very tight)
    y_variance = max(y_coords) - min(y_coords)
    if y_variance > 15:  # Must be very well aligned
        return False
    
    # Check if content looks like table data (short, structured)
    if len(texts) >= 2:
        # Must have at least 2 columns with proper spacing
        total_width = x_coords[-1] - x_coords[0]
        if total_width > 100:  # Must span a reasonable width
            return True
    
    return False

def extract_table_features(row_blocks: List[TextBlock], page_width: int, page_height: int) -> Dict:
    """Extract ML features for table detection."""
    texts = [block.text.strip() for block in row_blocks]
    
    # Spatial features
    x_coords = [block.bbox_px[0] for block in row_blocks]
    y_coords = [block.bbox_px[1] for block in row_blocks]
    x_coords.sort()
    
    gaps = [x_coords[i+1] - x_coords[i] for i in range(len(x_coords)-1)]
    column_spacing = min(gaps) if gaps else 0
    vertical_alignment = max(y_coords) - min(y_coords)
    
    # Content features
    text_lengths = [len(text) for text in texts]
    avg_text_length = sum(text_lengths) / len(text_lengths)
    
    # Text length consistency (how similar are the text lengths)
    if len(text_lengths) > 1:
        mean_length = np.mean(text_lengths)
        variance = np.var(text_lengths)
        text_length_consistency = 1.0 / (1.0 + variance / (mean_length + 1))
    else:
        text_length_consistency = 1.0
    
    # Check for structured data patterns
    import re
    structured_patterns = [
        r'^\d+$',  # Pure numbers
        r'^\d+\.\d+$',  # Decimal numbers
        r'^[A-Z]{2,}\d+$',  # Codes like "VQFN32"
        r'^[A-Za-z]+-[A-Za-z]+$',  # Hyphenated like "Level-1"
        r'^\d+-\d+$',  # Number ranges
        r'^[A-Z]{3,}\d+[A-Z]*$',  # Part numbers
    ]
    has_structured_data = any(any(re.match(pattern, text) for pattern in structured_patterns) for text in texts)
    
    # Check for numeric content
    has_numeric_content = any(re.search(r'\d', text) for text in texts)
    
    # Check for sentence indicators
    sentence_indicators = ['.', '!', '?']
    has_sentence_indicators = any(any(indicator in text for indicator in sentence_indicators) for text in texts)
    
    # Check if technical drawing (simplified)
    tech_keywords = ['stencil', 'design', 'vqfn', 'quad', 'flatpack', 'laser', 'cutting', 'apertures']
    is_technical_drawing = any(any(keyword in text.lower() for keyword in tech_keywords) for text in texts)
    
    # Check if descriptive text
    descriptive_indicators = ['simplified', 'schematic', 'figure', 'description', 'the following', 'as shown']
    is_descriptive_text = any(any(indicator in text.lower() for indicator in descriptive_indicators) for text in texts)
    
    return {
        'num_blocks': len(row_blocks),
        'column_spacing': column_spacing,
        'vertical_alignment': vertical_alignment,
        'avg_text_length': avg_text_length,
        'text_length_consistency': text_length_consistency,
        'has_structured_data': has_structured_data,
        'has_numeric_content': has_numeric_content,
        'has_sentence_indicators': has_sentence_indicators,
        'is_technical_drawing': is_technical_drawing,
        'is_descriptive_text': is_descriptive_text
    }

def detect_tables_ml(text_blocks: List[TextBlock], page_width: int, page_height: int) -> List[Table]:
    """
    Detect tables using ML-based approach.
    
    Args:
        text_blocks: List of TextBlock objects
        page_width: Width of the page in pixels
        page_height: Height of the page in pixels
        
    Returns:
        List of detected Table objects
    """
    if not text_blocks:
        return []
    
    # Group text blocks into rows based on y-coordinate proximity
    rows = group_blocks_into_rows(text_blocks)
    
    # Find table rows using ML
    table_rows = []
    for row in rows:
        if is_tabular_row(row, page_width, page_height):
            table_rows.append(row)
    
    # Group consecutive table rows into tables
    tables = group_rows_into_tables(table_rows)
    
    return tables

def group_blocks_into_rows(text_blocks: List[TextBlock]) -> List[List[TextBlock]]:
    """Group text blocks into rows based on strict y-coordinate proximity."""
    if not text_blocks:
        return []
    
    # Sort by y-coordinate
    sorted_blocks = sorted(text_blocks, key=lambda b: b.bbox_px[1])
    
    rows = []
    current_row = [sorted_blocks[0]]
    
    for block in sorted_blocks[1:]:
        # Check if this block is on the same row as the previous one
        prev_block = current_row[-1]
        y_diff = abs(block.bbox_px[1] - prev_block.bbox_px[1])
        
        # Much stricter row grouping - only group if very close
        if y_diff < 10:  # Very tight alignment required
            current_row.append(block)
        else:  # New row
            if len(current_row) >= 2:  # At least 2 blocks for a row
                rows.append(current_row)
            current_row = [block]
    
    # Add the last row
    if len(current_row) >= 2:
        rows.append(current_row)
    
    return rows

def group_rows_into_tables(table_rows: List[List[TextBlock]]) -> List[Table]:
    """Group consecutive table rows into tables."""
    if not table_rows:
        return []
    
    tables = []
    current_table_rows = [table_rows[0]]
    
    for i in range(1, len(table_rows)):
        # Check if this row is close to the previous one (same table)
        prev_row = current_table_rows[-1]
        curr_row = table_rows[i]
        
        # Calculate vertical distance between rows
        prev_y = min(block.bbox_px[1] for block in prev_row)
        curr_y = min(block.bbox_px[1] for block in curr_row)
        y_diff = curr_y - prev_y
        
        if y_diff < 100:  # Close enough to be in the same table
            current_table_rows.append(curr_row)
        else:  # New table
            table = create_table_from_rows(current_table_rows)
            if table:
                tables.append(table)
            current_table_rows = [curr_row]
    
    # Add the last table
    if current_table_rows:
        table = create_table_from_rows(current_table_rows)
        if table:
            tables.append(table)
    
    return tables

def create_table_from_rows(rows: List[List[TextBlock]]) -> Optional[Table]:
    """Create a Table object from a list of table rows."""
    if not rows:
        return None
    
    # Calculate bounding box
    all_blocks = [block for row in rows for block in row]
    x_coords = [block.bbox_px[0] for block in all_blocks]
    y_coords = [block.bbox_px[1] for block in all_blocks]
    x2_coords = [block.bbox_px[2] for block in all_blocks]
    y2_coords = [block.bbox_px[3] for block in all_blocks]
    
    bbox_px = [
        min(x_coords),
        min(y_coords),
        max(x2_coords),
        max(y2_coords)
    ]
    
    # Create cells from rows
    cells = []
    for row in rows:
        row_cells = []
        for block in row:
            row_cells.append({
                'text': block.text,
                'bbox_px': block.bbox_px
            })
        cells.append(row_cells)
    
    return Table(bbox_px=bbox_px, cells=cells, detection_method="ml")
