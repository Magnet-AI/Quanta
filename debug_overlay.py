#!/usr/bin/env python3
"""
Debug script to test overlay rendering
"""
import sys
import os
sys.path.append('src')

from src.runner import process_page
import json

def main():
    print("🔍 Debugging overlay rendering for page 1")
    
    # Process just page 1
    result = process_page('tps51633.pdf', 0, 'output', debug=True)
    
    print(f"Text blocks detected: {len(result.get('text_blocks', []))}")
    print(f"Figures detected: {len(result.get('figures', []))}")
    print(f"Tables detected: {len(result.get('tables', []))}")
    
    # Check if text blocks are being passed to overlay
    print("\nText blocks details:")
    for i, block in enumerate(result.get('text_blocks', [])[:3]):
        print(f"  {i+1}. {block.bbox_px} - \"{block.text[:30]}...\"")
        print(f"     is_heading: {getattr(block, 'is_heading', False)}")
    
    # Check JSON output
    with open('output/page_1.json', 'r') as f:
        json_data = json.load(f)
        print(f"\nJSON text blocks: {len(json_data.get('text_blocks', []))}")
        for i, block in enumerate(json_data.get('text_blocks', [])[:3]):
            print(f"  {i+1}. {block.get('bbox_px', [])} - \"{block.get('text', '')[:30]}...\"")

if __name__ == "__main__":
    main()
