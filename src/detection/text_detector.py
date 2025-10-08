"""
Text block extraction and paragraph grouping
"""
import re
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import logging

# Constants
TEXT_MERGE_VGAP = 10  # pixels
ROW_DY_FACTOR = 0.6   # for line baseline clustering

class TextBlock:
    """Represents a text block with bounding box and content"""
    def __init__(self, bbox_px: List[int], text: str, font_size: float = 0, 
                 is_bold: bool = False, is_italic: bool = False, 
                 is_heading: bool = False):
        self.bbox_px = bbox_px  # [x0, y0, x1, y1]
        self.text = text
        self.font_size = font_size
        self.is_bold = is_bold
        self.is_italic = is_italic
        self.is_heading = is_heading
        self.paragraph_id = None
        self.section_id = None
    
    @property
    def center_x(self) -> float:
        return (self.bbox_px[0] + self.bbox_px[2]) / 2
    
    @property
    def center_y(self) -> float:
        return (self.bbox_px[1] + self.bbox_px[3]) / 2
    
    @property
    def width(self) -> int:
        return self.bbox_px[2] - self.bbox_px[0]
    
    @property
    def height(self) -> int:
        return self.bbox_px[3] - self.bbox_px[1]
    
    def overlaps_with(self, other: 'TextBlock', threshold: float = 0.3) -> bool:
        """Check if this block overlaps with another block"""
        x0_1, y0_1, x1_1, y1_1 = self.bbox_px
        x0_2, y0_2, x1_2, y1_2 = other.bbox_px
        
        # Calculate intersection
        x0_i = max(x0_1, x0_2)
        y0_i = max(y0_1, y0_2)
        x1_i = min(x1_1, x1_2)
        y1_i = min(y1_1, y1_2)
        
        if x0_i >= x1_i or y0_i >= y1_i:
            return False
        
        # Calculate areas
        area1 = (x1_1 - x0_1) * (y1_1 - y0_1)
        area2 = (x1_2 - x0_2) * (y1_2 - y0_2)
        area_i = (x1_i - x0_i) * (y1_i - y0_i)
        
        # Check if overlap exceeds threshold
        overlap_ratio = area_i / min(area1, area2)
        return overlap_ratio >= threshold

def extract_text_blocks(raw_dict: Dict[str, Any]) -> List[TextBlock]:
    """
    Extract text blocks from PyMuPDF raw dictionary
    
    Args:
        raw_dict: Raw text dictionary from PyMuPDF
        
    Returns:
        List of TextBlock objects
    """
    blocks = []
    
    for block in raw_dict.get("blocks", []):
        if "lines" not in block:
            continue
            
        for line in block["lines"]:
            if "spans" not in line:
                continue
                
            # Get line bounding box - use 150 DPI instead of 600
            bbox = line["bbox"]  # [x0, y0, x1, y1] in points
            bbox_px = [int(coord * (150/72)) for coord in bbox]
            
            # Collect text from all spans in the line
            line_text = ""
            font_sizes = []
            is_bold = False
            is_italic = False
            
            for span in line["spans"]:
                span_text = span.get("text", "").strip()
                if span_text:
                    line_text += span_text + " "
                    font_sizes.append(span.get("size", 12))
                    
                    # Check font flags
                    flags = span.get("flags", 0)
                    if flags & 2**4:  # Bold flag
                        is_bold = True
                    if flags & 2**1:  # Italic flag
                        is_italic = True
            
            if line_text.strip():
                avg_font_size = np.mean(font_sizes) if font_sizes else 12
                text_block = TextBlock(
                    bbox_px=bbox_px,
                    text=line_text.strip(),
                    font_size=avg_font_size,
                    is_bold=is_bold,
                    is_italic=is_italic
                )
                blocks.append(text_block)
    
    logging.info(f"Extracted {len(blocks)} text blocks")
    return blocks

def group_lines_into_paragraphs(blocks: List[TextBlock]) -> List[TextBlock]:
    """
    Group text lines into paragraphs based on vertical proximity and column awareness
    
    Args:
        blocks: List of TextBlock objects (lines)
        
    Returns:
        List of TextBlock objects (paragraphs)
    """
    if not blocks:
        return []
    
    # Sort blocks by y-coordinate first, then by x-coordinate
    blocks = sorted(blocks, key=lambda b: (b.bbox_px[1], b.bbox_px[0]))
    
    # Calculate median line height for baseline clustering
    heights = [b.height for b in blocks]
    median_height = np.median(heights)
    baseline_threshold = median_height * ROW_DY_FACTOR
    
    # Group lines by baseline proximity, but be more conservative about horizontal grouping
    line_groups = []
    current_group = [blocks[0]]
    
    for i in range(1, len(blocks)):
        prev_block = blocks[i-1]
        curr_block = blocks[i]
        
        # Check if blocks are on same baseline
        y_diff = abs(curr_block.bbox_px[1] - prev_block.bbox_px[1])
        
        # Also check if blocks are in similar horizontal position (same column)
        x_diff = abs(curr_block.bbox_px[0] - prev_block.bbox_px[0])
        page_width = 1275  # Approximate page width
        column_threshold = page_width * 0.3  # 30% of page width
        
        if y_diff <= baseline_threshold and x_diff <= column_threshold:
            current_group.append(curr_block)
        else:
            line_groups.append(current_group)
            current_group = [curr_block]
    
    if current_group:
        line_groups.append(current_group)
    
    # Merge lines within groups into paragraphs, but be more conservative
    paragraphs = []
    for group in line_groups:
        if not group:
            continue
            
        # Sort by x-coordinate within group
        group = sorted(group, key=lambda b: b.bbox_px[0])
        
        # Check if lines should be merged into paragraphs
        merged_blocks = []
        current_para = [group[0]]
        
        for i in range(1, len(group)):
            prev_block = group[i-1]
            curr_block = group[i]
            
            # Check vertical gap
            vgap = curr_block.bbox_px[1] - prev_block.bbox_px[3]
            
            # Check horizontal overlap or proximity
            prev_right = prev_block.bbox_px[2]
            curr_left = curr_block.bbox_px[0]
            hgap = curr_left - prev_right
            
            # Only merge if they're close vertically AND horizontally
            if vgap <= TEXT_MERGE_VGAP and hgap <= 50:  # 50px horizontal gap threshold
                current_para.append(curr_block)
            else:
                # Merge current paragraph
                if current_para:
                    merged_blocks.append(merge_blocks_to_paragraph(current_para))
                current_para = [curr_block]
        
        # Add final paragraph
        if current_para:
            merged_blocks.append(merge_blocks_to_paragraph(current_para))
        
        paragraphs.extend(merged_blocks)
    
    return paragraphs

def merge_blocks_to_paragraph(blocks: List[TextBlock]) -> TextBlock:
    """
    Merge multiple text blocks into a single paragraph block
    
    Args:
        blocks: List of TextBlock objects to merge
        
    Returns:
        Single merged TextBlock
    """
    if not blocks:
        return None
    
    if len(blocks) == 1:
        return blocks[0]
    
    # Calculate combined bounding box
    x0 = min(b.bbox_px[0] for b in blocks)
    y0 = min(b.bbox_px[1] for b in blocks)
    x1 = max(b.bbox_px[2] for b in blocks)
    y1 = max(b.bbox_px[3] for b in blocks)
    
    # Combine text
    text_parts = []
    for block in blocks:
        text_parts.append(block.text)
    
    combined_text = " ".join(text_parts)
    
    # Fix hyphenations
    combined_text = fix_hyphenations(combined_text)
    
    # Get dominant font properties
    font_sizes = [b.font_size for b in blocks if b.font_size > 0]
    avg_font_size = np.mean(font_sizes) if font_sizes else 12
    
    is_bold = any(b.is_bold for b in blocks)
    is_italic = any(b.is_italic for b in blocks)
    
    return TextBlock(
        bbox_px=[x0, y0, x1, y1],
        text=combined_text,
        font_size=avg_font_size,
        is_bold=is_bold,
        is_italic=is_italic
    )

def fix_hyphenations(text: str) -> str:
    """
    Fix hyphenated words that were split across lines
    
    Args:
        text: Text with potential hyphenations
        
    Returns:
        Text with hyphenations fixed
    """
    # Pattern for hyphenated words: word-\nword
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    
    # Pattern for hyphenated words: word- word
    text = re.sub(r'(\w+)-\s+(\w+)', r'\1\2', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

def detect_headings(blocks: List[TextBlock]) -> List[TextBlock]:
    """
    Detect heading blocks based on font size and formatting
    
    Args:
        blocks: List of TextBlock objects
        
    Returns:
        List of TextBlock objects marked as headings
    """
    if not blocks:
        return []
    
    # Calculate font size statistics
    font_sizes = [b.font_size for b in blocks if b.font_size > 0]
    if not font_sizes:
        return []
    
    mean_font_size = np.mean(font_sizes)
    std_font_size = np.std(font_sizes)
    # More conservative threshold - only clearly larger text
    threshold = mean_font_size + 2.0 * std_font_size
    
    headings = []
    for block in blocks:
        is_heading = False
        
        # Check font size
        if block.font_size >= threshold:
            is_heading = True
        
        # Check if bold and centered (heuristic)
        elif block.is_bold and is_centered(block):
            is_heading = True
        
        # Check for heading patterns (only if font size is reasonable)
        elif block.font_size >= mean_font_size and is_heading_pattern(block.text):
            is_heading = True
        
        if is_heading:
            block.is_heading = True
            headings.append(block)
    
    # Return all blocks, not just headings
    return blocks

def is_centered(block: TextBlock, tolerance: float = 0.1) -> bool:
    """
    Check if a text block appears to be centered
    
    Args:
        block: TextBlock to check
        tolerance: Tolerance for centering (fraction of page width)
        
    Returns:
        True if block appears centered
    """
    # This is a simplified check - in practice, you'd need page width
    # For now, assume blocks with small width relative to their position are centered
    return block.width < 200  # Simple heuristic

def is_heading_pattern(text: str) -> bool:
    """
    Check if text matches common heading patterns
    
    Args:
        text: Text to check
        
    Returns:
        True if text appears to be a heading
    """
    # Common heading patterns
    patterns = [
        r'^\d+\.?\s+[A-Z]',  # "1. Introduction" or "1 Introduction"
        r'^[A-Z][A-Z\s]+$',  # "ABSTRACT" or "INTRODUCTION"
        r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)*$',  # "Introduction" or "Related Work"
        r'^\d+\.\d+',  # "1.1" or "2.3"
    ]
    
    for pattern in patterns:
        if re.match(pattern, text.strip()):
            return True
    
    return False

def filter_blocks_in_columns(blocks: List[TextBlock], columns: List[Tuple[int, int]]) -> List[TextBlock]:
    """
    Filter text blocks to only include those within column boundaries
    
    Args:
        blocks: List of TextBlock objects
        columns: List of column boundaries (x0, x1)
        
    Returns:
        Filtered list of TextBlock objects
    """
    if not columns:
        return blocks
    
    filtered = []
    for block in blocks:
        center_x = block.center_x
        for x0, x1 in columns:
            if x0 <= center_x < x1:
                filtered.append(block)
                break
    
    return filtered
