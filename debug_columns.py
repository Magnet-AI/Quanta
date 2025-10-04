#!/usr/bin/env python3
"""
Debug script to test column detection
"""
import sys
import os
sys.path.append('src')

from src.pdf_io import load_pdf_page_data
from src.columns import detect_columns
from src.text_blocks import extract_text_blocks, group_lines_into_paragraphs, filter_blocks_in_columns

def main():
    print("🔍 Debugging column detection for page 1")
    
    # Load page data
    page_data = load_pdf_page_data('tps51633.pdf', 0)
    
    # Detect columns
    columns = detect_columns(page_data['img_page'])
    print(f"Columns detected: {columns}")
    
    # Extract text blocks
    raw_blocks = extract_text_blocks(page_data['raw_dict'])
    paragraph_blocks = group_lines_into_paragraphs(raw_blocks)
    print(f"Paragraph blocks before filtering: {len(paragraph_blocks)}")
    
    # Filter by columns
    filtered_blocks = filter_blocks_in_columns(paragraph_blocks, columns)
    print(f"Paragraph blocks after column filtering: {len(filtered_blocks)}")
    
    # Show some examples
    print("\nFirst 5 blocks before filtering:")
    for i, block in enumerate(paragraph_blocks[:5]):
        print(f"  {i+1}. Center: {block.center_x}, Bbox: {block.bbox_px} - \"{block.text[:30]}...\"")
    
    print("\nFirst 5 blocks after filtering:")
    for i, block in enumerate(filtered_blocks[:5]):
        print(f"  {i+1}. Center: {block.center_x}, Bbox: {block.bbox_px} - \"{block.text[:30]}...\"")

if __name__ == "__main__":
    main()

