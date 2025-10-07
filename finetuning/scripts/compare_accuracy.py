"""
Compare accuracy between original and finetuned systems
"""
import sys
from pathlib import Path

# Add the main project to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

import json
from src.runner import process_pdf
from finetuning.scripts.integrate_model import enhance_pdf_processing
import logging

logger = logging.getLogger(__name__)

def run_original_system(pdf_path, output_dir):
    """Run the original system without ML enhancement"""
    logger.info("🔧 Running ORIGINAL system...")
    
    # Process with original system
    result = process_pdf(pdf_path, output_dir)
    
    # Count results
    total_figures = sum(len(p.get('figures', [])) for p in result['pages'])
    total_tables = sum(len(p.get('tables', [])) for p in result['pages'])
    
    return {
        'figures': total_figures,
        'tables': total_tables,
        'pages': result['pages']
    }

def run_enhanced_system(pdf_path, output_dir):
    """Run the enhanced system with ML model"""
    logger.info("🤖 Running ENHANCED system...")
    
    # Process with enhanced system
    result = enhance_pdf_processing(pdf_path, output_dir)
    
    return {
        'figures': result['enhanced_totals']['figures'],
        'tables': result['enhanced_totals']['tables'],
        'pages': result['pages']
    }

def compare_results(original, enhanced, pdf_name):
    """Compare the results and show improvements"""
    print(f"\n📊 COMPARISON RESULTS for {pdf_name}")
    print("=" * 60)
    
    print(f"🔧 ORIGINAL SYSTEM:")
    print(f"   Figures: {original['figures']}")
    print(f"   Tables:  {original['tables']}")
    
    print(f"\n🤖 ENHANCED SYSTEM:")
    print(f"   Figures: {enhanced['figures']}")
    print(f"   Tables:  {enhanced['tables']}")
    
    print(f"\n📈 CHANGES:")
    figure_change = enhanced['figures'] - original['figures']
    table_change = enhanced['tables'] - original['tables']
    
    print(f"   Figures: {figure_change:+d} ({'📈' if figure_change > 0 else '📉' if figure_change < 0 else '➡️'})")
    print(f"   Tables:  {table_change:+d} ({'📈' if table_change > 0 else '📉' if table_change < 0 else '➡️'})")
    
    # Page-by-page comparison
    print(f"\n📄 PAGE-BY-PAGE COMPARISON:")
    print("Page | Original (F/T) | Enhanced (F/T) | Change")
    print("-" * 50)
    
    for i, (orig_page, enh_page) in enumerate(zip(original['pages'], enhanced['pages'])):
        orig_fig = len(orig_page.get('figures', []))
        orig_tab = len(orig_page.get('tables', []))
        enh_fig = len(enh_page.get('figures', []))
        enh_tab = len(enh_page.get('tables', []))
        
        fig_change = enh_fig - orig_fig
        tab_change = enh_tab - orig_tab
        
        change_str = f"F:{fig_change:+d} T:{tab_change:+d}"
        
        print(f"{i+1:4d} | {orig_fig:2d}/{orig_tab:2d}         | {enh_fig:2d}/{enh_tab:2d}         | {change_str}")
        
        # Highlight the problematic page 11
        if i == 10:  # Page 11 (0-indexed)
            print(f"     🎯 Page 11 (problematic): Original had {orig_fig} figures, {orig_tab} tables")
            print(f"     🎯 Page 11 (problematic): Enhanced has {enh_fig} figures, {enh_tab} tables")

def test_specific_pdf(pdf_path, pdf_name):
    """Test a specific PDF with both systems"""
    print(f"\n🧪 TESTING {pdf_name}")
    print("=" * 60)
    
    # Create output directories
    original_output = f"comparison_output/original_{pdf_name}"
    enhanced_output = f"comparison_output/enhanced_{pdf_name}"
    
    Path(original_output).mkdir(parents=True, exist_ok=True)
    Path(enhanced_output).mkdir(parents=True, exist_ok=True)
    
    try:
        # Run original system
        original_result = run_original_system(pdf_path, original_output)
        
        # Run enhanced system  
        enhanced_result = run_enhanced_system(pdf_path, enhanced_output)
        
        # Compare results
        compare_results(original_result, enhanced_result, pdf_name)
        
        return True
        
    except Exception as e:
        logger.error(f"Error testing {pdf_name}: {e}")
        return False

def main():
    """Main comparison script"""
    logging.basicConfig(level=logging.INFO)
    
    print("🔍 PDF EXTRACTION ACCURACY COMPARISON")
    print("=" * 60)
    print("Comparing Original System vs Finetuned ML System")
    
    # Test the problematic PDF
    test_pdf = "../test_pdf/tps51633.pdf"
    if Path(test_pdf).exists():
        success = test_specific_pdf(test_pdf, "tps51633")
        
        if success:
            print(f"\n✅ Comparison completed!")
            print(f"📁 Check 'comparison_output/' folder for detailed results")
        else:
            print(f"\n❌ Comparison failed!")
    else:
        print(f"❌ Test PDF not found: {test_pdf}")

if __name__ == "__main__":
    main()
