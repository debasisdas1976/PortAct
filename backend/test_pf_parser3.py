"""
Debug script using pdfplumber to extract PF PDF text
"""
import sys
import pdfplumber
import traceback

def extract_pdf_text(pdf_path):
    """Extract and print text from PDF using pdfplumber"""
    try:
        print(f"Opening PDF: {pdf_path}")
        with pdfplumber.open(pdf_path) as pdf:
            print(f"Number of pages: {len(pdf.pages)}")
            print("\n" + "="*80)
            print("EXTRACTED TEXT:")
            print("="*80 + "\n")
            
            for i, page in enumerate(pdf.pages):
                print(f"\n--- PAGE {i+1} ---\n")
                text = page.extract_text()
                if text:
                    print(text)
                else:
                    print("(No text extracted from this page)")
                print("\n" + "-"*80 + "\n")
    except Exception as e:
        print(f"Error: {e}")
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_pf_parser3.py <path_to_pf_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    extract_pdf_text(pdf_path)

# Made with Bob
