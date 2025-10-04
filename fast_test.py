#!/usr/bin/env python3
"""
Fast test script to check performance improvements
"""
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.runner import run_single_page

def main():
    print("🚀 Fast PDF Processing Test")
    print("=" * 40)
    
    pdf_path = "drylab.pdf"
    
    if not Path(pdf_path).exists():
        print(f"❌ PDF file not found: {pdf_path}")
        return
    
    print(f"📄 Testing with: {pdf_path}")
    print()
    
    # Test single page
    start_time = time.time()
    
    try:
        result = run_single_page(pdf_path, 0, "fast_test_output", debug=False)
        
        elapsed = time.time() - start_time
        
        print(f"\n✅ SUCCESS! Completed in {elapsed:.1f} seconds")
        print(f"📊 Results:")
        print(f"  - Page size: {result.get('page_size', {})}")
        print(f"  - Columns: {len(result.get('columns', []))}")
        print(f"  - Text blocks: {len(result.get('text_blocks', []))}")
        print(f"  - Figures: {len(result.get('figures', []))}")
        print(f"  - Tables: {len(result.get('tables', []))}")
        print(f"  - Sections: {len(result.get('sections', []))}")
        
        if elapsed < 10:
            print(f"🎉 EXCELLENT! Under 10 seconds!")
        elif elapsed < 30:
            print(f"👍 GOOD! Under 30 seconds")
        else:
            print(f"🐌 Still slow, but better than before!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
