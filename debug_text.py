#!/usr/bin/env python3
"""
Debug script to test text extraction
"""
import sys
import os
sys.path.append('src')

from src.pdf_io import load_pdf_page_data
from src.text_blocks import extract_text_blocks, group_lines_into_paragraphs, detect_headings

def main():
    print("🔍 Debugging text extraction for page 1")
    
    # Load page data
    page_data = load_pdf_page_data('tps51633.pdf', 0)
    
    # Extract raw text blocks
    raw_blocks = extract_text_blocks(page_data['raw_dict'])
    print(f"Raw text blocks extracted: {len(raw_blocks)}")
    
    # Show first 10 raw blocks
    print("\nFirst 10 raw text blocks:")
    for i, block in enumerate(raw_blocks[:10]):
        print(f"  {i+1}. {block.bbox_px} - \"{block.text[:50]}...\"")
    
    # Group into paragraphs
    paragraph_blocks = group_lines_into_paragraphs(raw_blocks)
    print(f"\nAfter paragraph grouping: {len(paragraph_blocks)}")
    
    # Show first 10 paragraph blocks
    print("\nFirst 10 paragraph blocks:")
    for i, block in enumerate(paragraph_blocks[:10]):
        print(f"  {i+1}. {block.bbox_px} - \"{block.text[:50]}...\"")
    
    # Detect headings
    heading_blocks = detect_headings(paragraph_blocks)
    print(f"\nHeadings detected: {len(heading_blocks)}")
    
    # Show headings
    print("\nHeadings:")
    for i, block in enumerate(heading_blocks):
        print(f"  {i+1}. {block.bbox_px} - \"{block.text[:50]}...\"")

if __name__ == "__main__":
    main()
