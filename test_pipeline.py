#!/usr/bin/env python3
"""
Test script for PDF extraction pipeline
"""
import sys
import os
sys.path.append('src')

from src.runner import process_pdf
import time

def main():
    print("🚀 Testing PDF extraction pipeline on tps51633.pdf")
    
    # Clean output directory
    if os.path.exists('output'):
        import shutil
        shutil.rmtree('output')
    
    # Process the PDF
    start_time = time.time()
    result = process_pdf('tps51633.pdf', 'output', debug=True)
    elapsed = time.time() - start_time
    
    print(f"✅ Done in {elapsed:.1f}s")
    print(f"Pages: {len(result['pages'])}")
    print(f"Figures: {sum(len(p.get('figures', [])) for p in result['pages'])}")
    print(f"Tables: {sum(len(p.get('tables', [])) for p in result['pages'])}")
    print(f"Text blocks: {sum(len(p.get('text_blocks', [])) for p in result['pages'])}")
    
    # Check page 1 specifically
    page1 = result['pages'][0]
    print(f"\nPage 1 details:")
    print(f"  Text blocks: {len(page1.get('text_blocks', []))}")
    print(f"  Figures: {len(page1.get('figures', []))}")
    print(f"  Tables: {len(page1.get('tables', []))}")
    
    # Show first few text blocks
    print(f"\nFirst 5 text blocks:")
    for i, block in enumerate(page1.get('text_blocks', [])[:5]):
        bbox = block.bbox_px
        text = block.text[:50]
        is_heading = getattr(block, 'is_heading', False)
        print(f"  {i+1}. {bbox} - \"{text}...\" (heading: {is_heading})")

if __name__ == "__main__":
    main()