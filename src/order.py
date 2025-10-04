"""
Reading order and section assembly
"""
from typing import List, Dict, Any, Tuple, Optional
import logging

class Section:
    """Represents a document section"""
    def __init__(self, heading: str, paragraphs: List[str], 
                 figures: List = None, tables: List = None):
        self.heading = heading
        self.paragraphs = paragraphs
        self.figures = figures or []
        self.tables = tables or []
    
    def add_paragraph(self, text: str):
        """Add a paragraph to this section"""
        self.paragraphs.append(text)
    
    def add_figure(self, figure):
        """Add a figure to this section"""
        self.figures.append(figure)
    
    def add_table(self, table):
        """Add a table to this section"""
        self.tables.append(table)

def assemble_sections(text_blocks: List, figures: List, tables: List, 
                     captions: List) -> List[Section]:
    """
    Assemble text blocks into sections with proper reading order
    
    Args:
        text_blocks: List of text blocks
        figures: List of Figure objects
        tables: List of Table objects
        captions: List of Caption objects
        
    Returns:
        List of Section objects
    """
    if not text_blocks:
        return []
    
    # Remove caption blocks from text blocks to avoid double-counting
    from .captions import remove_caption_blocks_from_text
    text_blocks = remove_caption_blocks_from_text(text_blocks, captions)
    
    # Sort blocks by reading order
    ordered_blocks = sort_blocks_by_reading_order(text_blocks)
    
    # Group blocks into sections
    sections = group_blocks_into_sections(ordered_blocks, figures, tables)
    
    return sections

def sort_blocks_by_reading_order(blocks: List) -> List:
    """
    Sort text blocks by reading order (left to right, top to bottom)
    
    Args:
        blocks: List of text blocks
        
    Returns:
        List of blocks sorted by reading order
    """
    if not blocks:
        return []
    
    # Sort by y-coordinate first (top to bottom), then by x-coordinate (left to right)
    return sorted(blocks, key=lambda b: (b.bbox_px[1], b.bbox_px[0]))

def group_blocks_into_sections(blocks: List, figures: List, tables: List) -> List[Section]:
    """
    Group text blocks into sections based on headings
    
    Args:
        blocks: List of text blocks in reading order
        figures: List of Figure objects
        tables: List of Table objects
        
    Returns:
        List of Section objects
    """
    if not blocks:
        return []
    
    sections = []
    current_section = None
    
    for block in blocks:
        if block.is_heading:
            # Start new section
            if current_section:
                sections.append(current_section)
            
            current_section = Section(
                heading=block.text,
                paragraphs=[]
            )
        else:
            # Add to current section
            if current_section is None:
                # No heading yet, create a default section
                current_section = Section(
                    heading="Introduction",  # Default heading
                    paragraphs=[]
                )
            
            current_section.add_paragraph(block.text)
    
    # Add final section
    if current_section:
        sections.append(current_section)
    
    # Associate figures and tables with sections
    associate_objects_with_sections(sections, figures, tables)
    
    return sections

def associate_objects_with_sections(sections: List[Section], figures: List, tables: List):
    """
    Associate figures and tables with the appropriate sections
    
    Args:
        sections: List of Section objects
        figures: List of Figure objects
        tables: List of Table objects
    """
    if not sections:
        return
    
    # Associate figures with sections
    for figure in figures:
        section = find_section_for_object(figure, sections)
        if section:
            section.add_figure(figure)
    
    # Associate tables with sections
    for table in tables:
        section = find_section_for_object(table, sections)
        if section:
            section.add_table(table)

def find_section_for_object(obj: Any, sections: List[Section]) -> Optional[Section]:
    """
    Find the section that contains a given object
    
    Args:
        obj: Figure or Table object
        sections: List of Section objects
        
    Returns:
        Section containing the object, or None if not found
    """
    if not sections or not obj:
        return None
    
    obj_center_y = (obj.bbox_px[1] + obj.bbox_px[3]) / 2
    
    # Find the section whose content is closest to the object
    best_section = None
    min_distance = float('inf')
    
    for section in sections:
        # Calculate section content area (simplified)
        section_blocks = []
        for para in section.paragraphs:
            # This is a simplified approach - in practice, you'd track block positions
            pass
        
        # For now, just return the first section as a fallback
        if not best_section:
            best_section = section
    
    return best_section

def determine_title(text_blocks: List) -> str:
    """
    Determine the document title from text blocks
    
    Args:
        text_blocks: List of text blocks
        
    Returns:
        Document title
    """
    if not text_blocks:
        return "Untitled Document"
    
    # Look for the largest heading at the top of the page
    headings = [b for b in text_blocks if b.is_heading]
    
    if not headings:
        # No headings found, use first block as title
        return text_blocks[0].text if text_blocks else "Untitled Document"
    
    # Sort headings by position (top to bottom) and font size
    headings = sorted(headings, key=lambda h: (h.bbox_px[1], -h.font_size))
    
    # Return the first (topmost) heading
    return headings[0].text

def create_reading_order(blocks: List, figures: List, tables: List) -> List[Dict[str, Any]]:
    """
    Create a reading order list with all elements
    
    Args:
        blocks: List of text blocks
        figures: List of Figure objects
        tables: List of Table objects
        
    Returns:
        List of elements in reading order
    """
    elements = []
    
    # Add text blocks
    for block in blocks:
        elements.append({
            'type': 'text',
            'content': block.text,
            'bbox_px': block.bbox_px,
            'is_heading': getattr(block, 'is_heading', False)
        })
    
    # Add figures
    for figure in figures:
        elements.append({
            'type': 'figure',
            'content': figure.caption.text if figure.caption else "",
            'bbox_px': figure.bbox_px,
            'image_path': figure.image_path
        })
    
    # Add tables
    for table in tables:
        elements.append({
            'type': 'table',
            'content': table.caption.text if table.caption else "",
            'bbox_px': table.bbox_px,
            'csv_path': table.csv_path
        })
    
    # Sort by reading order
    elements = sorted(elements, key=lambda e: (e['bbox_px'][1], e['bbox_px'][0]))
    
    return elements

def validate_reading_order(elements: List[Dict[str, Any]]) -> bool:
    """
    Validate that the reading order makes sense
    
    Args:
        elements: List of elements in reading order
        
    Returns:
        True if reading order is valid
    """
    if not elements:
        return True
    
    # Check that elements are roughly in top-to-bottom, left-to-right order
    for i in range(1, len(elements)):
        prev_bbox = elements[i-1]['bbox_px']
        curr_bbox = elements[i]['bbox_px']
        
        # Check that current element is not significantly above previous
        if curr_bbox[1] < prev_bbox[1] - 50:  # 50px tolerance
            return False
        
        # Check that if elements are at similar heights, current is to the right
        if abs(curr_bbox[1] - prev_bbox[1]) < 20:  # Similar height
            if curr_bbox[0] < prev_bbox[0] - 20:  # Current is significantly to the left
                return False
    
    return True

def extract_paragraphs_from_section(section: Section) -> List[str]:
    """
    Extract all paragraphs from a section
    
    Args:
        section: Section object
        
    Returns:
        List of paragraph texts
    """
    return section.paragraphs.copy()

def get_section_summary(section: Section) -> Dict[str, Any]:
    """
    Get a summary of a section
    
    Args:
        section: Section object
        
    Returns:
        Dictionary with section summary
    """
    return {
        'heading': section.heading,
        'num_paragraphs': len(section.paragraphs),
        'num_figures': len(section.figures),
        'num_tables': len(section.tables),
        'paragraphs': section.paragraphs
    }

def merge_adjacent_sections(sections: List[Section]) -> List[Section]:
    """
    Merge sections that are too small or closely related
    
    Args:
        sections: List of Section objects
        
    Returns:
        List of merged Section objects
    """
    if not sections:
        return []
    
    merged = []
    current = sections[0]
    
    for i in range(1, len(sections)):
        next_section = sections[i]
        
        # Merge if current section is too small (less than 2 paragraphs)
        if len(current.paragraphs) < 2:
            current.paragraphs.extend(next_section.paragraphs)
            current.figures.extend(next_section.figures)
            current.tables.extend(next_section.tables)
        else:
            merged.append(current)
            current = next_section
    
    merged.append(current)
    return merged

def create_document_outline(sections: List[Section]) -> List[Dict[str, Any]]:
    """
    Create a document outline from sections
    
    Args:
        sections: List of Section objects
        
    Returns:
        List of outline entries
    """
    outline = []
    
    for i, section in enumerate(sections):
        outline.append({
            'level': 1,  # All sections are level 1 for now
            'heading': section.heading,
            'section_index': i,
            'num_paragraphs': len(section.paragraphs),
            'num_figures': len(section.figures),
            'num_tables': len(section.tables)
        })
    
    return outline
