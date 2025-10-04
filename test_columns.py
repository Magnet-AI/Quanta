#!/usr/bin/env python3
"""
Test script to verify column-aware text grouping
"""
import sys
import os
sys.path.append('src')

from src.runner import process_page
import json

def main():
    print("🔍 Testing column-aware text grouping on page 1")
    
    # Process just page 1
    result = process_page('tps51633.pdf', 0, 'output', debug=True)
    
    print(f"Text blocks detected: {len(result.get('text_blocks', []))}")
    
    # Check for column separation
    print("\nChecking column separation:")
    left_column_blocks = []
    right_column_blocks = []
    
    for block in result.get('text_blocks', []):
        center_x = block.center_x
        if center_x < 600:  # Left column
            left_column_blocks.append(block)
        elif center_x > 700:  # Right column
            right_column_blocks.append(block)
    
    print(f"Left column blocks: {len(left_column_blocks)}")
    print(f"Right column blocks: {len(right_column_blocks)}")
    
    # Show some examples
    print("\nLeft column examples:")
    for i, block in enumerate(left_column_blocks[:5]):
        print(f"  {i+1}. {block.bbox_px} - \"{block.text[:40]}...\"")
    
    print("\nRight column examples:")
    for i, block in enumerate(right_column_blocks[:5]):
        print(f"  {i+1}. {block.bbox_px} - \"{block.text[:40]}...\"")

if __name__ == "__main__":
    main()
