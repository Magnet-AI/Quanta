"""
Caption detection and linking to figures and tables
"""
import re
from typing import List, Dict, Any, Tuple, Optional
import logging

# Constants
CAPTION_BAND_FACTOR = 1.2  # Vertical search band factor

class Caption:
    """Represents a detected caption"""
    def __init__(self, bbox_px: List[int], text: str, 
                 linked_object: Optional[Any] = None, object_type: str = "unknown"):
        self.bbox_px = bbox_px  # [x0, y0, x1, y1]
        self.text = text
        self.linked_object = linked_object
        self.object_type = object_type  # 'figure' or 'table'
    
    @property
    def center(self) -> Tuple[float, float]:
        return (
            (self.bbox_px[0] + self.bbox_px[2]) / 2,
            (self.bbox_px[1] + self.bbox_px[3]) / 2
        )

def link_captions(text_blocks: List, figures: List, tables: List) -> List[Caption]:
    """
    Link captions to figures and tables
    
    Args:
        text_blocks: List of text blocks
        figures: List of Figure objects
        tables: List of Table objects
        
    Returns:
        List of Caption objects with linked objects
    """
    captions = []
    
    # Find potential caption blocks
    caption_blocks = find_caption_blocks(text_blocks)
    
    # Link captions to figures
    for figure in figures:
        caption = find_caption_for_object(figure, caption_blocks, "figure")
        if caption:
            caption.linked_object = figure
            caption.object_type = "figure"
            figure.caption = caption
            captions.append(caption)
    
    # Link captions to tables
    for table in tables:
        caption = find_caption_for_object(table, caption_blocks, "table")
        if caption:
            caption.linked_object = table
            caption.object_type = "table"
            table.caption = caption
            captions.append(caption)
    
    return captions

def find_caption_blocks(text_blocks: List) -> List:
    """
    Find text blocks that are likely captions
    
    Args:
        text_blocks: List of text blocks
        
    Returns:
        List of potential caption blocks
    """
    caption_blocks = []
    
    for block in text_blocks:
        if is_caption_text(block.text):
            caption_blocks.append(block)
    
    return caption_blocks

def is_caption_text(text: str) -> bool:
    """
    Check if text matches caption patterns
    
    Args:
        text: Text to check
        
    Returns:
        True if text appears to be a caption
    """
    # Common caption patterns
    patterns = [
        r'^(Fig\.|Figure)\s*[\w\-\.\(\)]*',  # "Fig. 1", "Figure 2.1"
        r'^(Table)\s*[\w\-\.\(\)]*',         # "Table 1", "Table 2.1"
        r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)*\s*\([A-Za-z0-9\s\-\.]+\)',  # "Caption (a)"
        r'^[A-Z][a-z]+(\s+[A-Z][a-z]+)*\s*[0-9]+',  # "Caption 1"
    ]
    
    text = text.strip()
    for pattern in patterns:
        if re.match(pattern, text, re.IGNORECASE):
            return True
    
    return False

def find_caption_for_object(obj: Any, caption_blocks: List, obj_type: str) -> Optional[Caption]:
    """
    Find the best caption for a given object
    
    Args:
        obj: Figure or Table object
        caption_blocks: List of potential caption blocks
        obj_type: Type of object ('figure' or 'table')
        
    Returns:
        Caption object if found, None otherwise
    """
    if not caption_blocks:
        return None
    
    obj_bbox = obj.bbox_px
    obj_height = obj_bbox[3] - obj_bbox[1]
    search_band = obj_height * CAPTION_BAND_FACTOR
    
    # Search for captions below the object (preferred)
    below_captions = []
    for block in caption_blocks:
        if is_caption_below_object(block, obj_bbox, search_band):
            below_captions.append(block)
    
    # Search for captions above the object (fallback)
    above_captions = []
    for block in caption_blocks:
        if is_caption_above_object(block, obj_bbox, search_band):
            above_captions.append(block)
    
    # Choose best caption
    best_caption = None
    
    if below_captions:
        best_caption = choose_best_caption(below_captions, obj_type)
    elif above_captions:
        best_caption = choose_best_caption(above_captions, obj_type)
    
    if best_caption:
        return Caption(
            bbox_px=best_caption.bbox_px,
            text=best_caption.text,
            object_type=obj_type
        )
    
    return None

def is_caption_below_object(block: Any, obj_bbox: List[int], search_band: float) -> bool:
    """
    Check if a text block is below an object within the search band
    
    Args:
        block: Text block
        obj_bbox: Object bounding box [x0, y0, x1, y1]
        search_band: Search band height
        
    Returns:
        True if block is below object
    """
    block_center_y = block.center_y
    obj_bottom = obj_bbox[3]
    search_bottom = obj_bottom + search_band
    
    return obj_bottom <= block_center_y <= search_bottom

def is_caption_above_object(block: Any, obj_bbox: List[int], search_band: float) -> bool:
    """
    Check if a text block is above an object within the search band
    
    Args:
        block: Text block
        obj_bbox: Object bounding box [x0, y0, x1, y1]
        search_band: Search band height
        
    Returns:
        True if block is above object
    """
    block_center_y = block.center_y
    obj_top = obj_bbox[1]
    search_top = obj_top - search_band
    
    return search_top <= block_center_y <= obj_top

def choose_best_caption(candidates: List, obj_type: str) -> Optional[Any]:
    """
    Choose the best caption from a list of candidates
    
    Args:
        candidates: List of candidate caption blocks
        obj_type: Type of object ('figure' or 'table')
        
    Returns:
        Best caption block, or None if no good match
    """
    if not candidates:
        return None
    
    if len(candidates) == 1:
        return candidates[0]
    
    # Score candidates based on various criteria
    best_caption = None
    best_score = -1
    
    for candidate in candidates:
        score = score_caption(candidate, obj_type)
        if score > best_score:
            best_score = score
            best_caption = candidate
    
    return best_caption

def score_caption(block: Any, obj_type: str) -> float:
    """
    Score a caption block based on relevance criteria
    
    Args:
        block: Text block
        obj_type: Type of object ('figure' or 'table')
        
    Returns:
        Score between 0 and 1
    """
    score = 0.0
    text = block.text.strip()
    
    # Base score for being a caption
    if is_caption_text(text):
        score += 0.5
    
    # Bonus for matching object type
    if obj_type == "figure" and re.search(r'(fig|figure)', text, re.IGNORECASE):
        score += 0.3
    elif obj_type == "table" and re.search(r'table', text, re.IGNORECASE):
        score += 0.3
    
    # Bonus for smaller font size (captions are often smaller)
    if hasattr(block, 'font_size') and block.font_size > 0:
        # This is a simplified scoring - in practice, you'd compare to page average
        if block.font_size < 12:  # Assuming 12pt is average
            score += 0.2
    
    # Bonus for italic text (captions are often italicized)
    if hasattr(block, 'is_italic') and block.is_italic:
        score += 0.1
    
    # Penalty for very long text (captions are usually concise)
    if len(text) > 200:
        score -= 0.2
    
    return min(1.0, max(0.0, score))

def extract_caption_number(text: str) -> Optional[str]:
    """
    Extract caption number from text
    
    Args:
        text: Caption text
        
    Returns:
        Caption number if found, None otherwise
    """
    # Patterns for caption numbers
    patterns = [
        r'(Fig\.|Figure)\s*([\w\-\.\(\)]+)',
        r'(Table)\s*([\w\-\.\(\)]+)',
        r'([0-9]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(2) if len(match.groups()) > 1 else match.group(1)
    
    return None

def extract_caption_content(text: str) -> str:
    """
    Extract caption content (text after the number)
    
    Args:
        text: Caption text
        
    Returns:
        Caption content without the number
    """
    # Remove common caption prefixes
    patterns = [
        r'^(Fig\.|Figure)\s*[\w\-\.\(\)]*\s*:?\s*',
        r'^(Table)\s*[\w\-\.\(\)]*\s*:?\s*',
    ]
    
    content = text
    for pattern in patterns:
        content = re.sub(pattern, '', content, flags=re.IGNORECASE)
    
    return content.strip()

def validate_caption_link(caption: Caption, obj: Any) -> bool:
    """
    Validate that a caption is properly linked to an object
    
    Args:
        caption: Caption object
        obj: Figure or Table object
        
    Returns:
        True if link is valid
    """
    if not caption or not obj:
        return False
    
    # Check that caption is within reasonable distance
    caption_center = caption.center
    obj_bbox = obj.bbox_px
    
    # Calculate distance from caption to object
    obj_center_x = (obj_bbox[0] + obj_bbox[2]) / 2
    obj_center_y = (obj_bbox[1] + obj_bbox[3]) / 2
    
    distance = ((caption_center[0] - obj_center_x) ** 2 + 
                (caption_center[1] - obj_center_y) ** 2) ** 0.5
    
    # Maximum reasonable distance (in pixels)
    max_distance = 200
    
    return distance <= max_distance

def remove_caption_blocks_from_text(text_blocks: List, captions: List[Caption]) -> List:
    """
    Remove caption blocks from text blocks list to avoid double-counting
    
    Args:
        text_blocks: List of text blocks
        captions: List of caption objects
        
    Returns:
        Filtered list of text blocks
    """
    caption_bboxes = [c.bbox_px for c in captions]
    
    filtered_blocks = []
    for block in text_blocks:
        is_caption = False
        for caption_bbox in caption_bboxes:
            if blocks_overlap(block.bbox_px, caption_bbox):
                is_caption = True
                break
        
        if not is_caption:
            filtered_blocks.append(block)
    
    return filtered_blocks

def blocks_overlap(bbox1: List[int], bbox2: List[int], threshold: float = 0.3) -> bool:
    """
    Check if two bounding boxes overlap significantly
    
    Args:
        bbox1: First bounding box [x0, y0, x1, y1]
        bbox2: Second bounding box [x0, y0, x1, y1]
        threshold: Overlap threshold (0-1)
        
    Returns:
        True if boxes overlap significantly
    """
    x0_1, y0_1, x1_1, y1_1 = bbox1
    x0_2, y0_2, x1_2, y1_2 = bbox2
    
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



