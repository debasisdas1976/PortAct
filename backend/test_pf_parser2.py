"""
Debug script to test PF parser - alternative approach
"""
import sys
import PyPDF2

def extract_pdf_text(pdf_path):
    """Extract and print text from PDF"""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        
        # Check if encrypted
        if pdf_reader.is_encrypted:
            print("PDF appears encrypted. Trying to decrypt with empty password...")
            try:
                # Try decrypting with empty string
                result = pdf_reader.decrypt('')
                print(f"Decrypt result: {result}")
            except Exception as e:
                print(f"Decrypt error: {e}")
                try:
                    # Some PDFs need None instead of empty string
                    result = pdf_reader.decrypt(None)
                    print(f"Decrypt with None result: {result}")
                except Exception as e2:
                    print(f"Decrypt with None error: {e2}")
        
        try:
            print(f"\nNumber of pages: {len(pdf_reader.pages)}")
            print("\n" + "="*80)
            print("EXTRACTED TEXT:")
            print("="*80 + "\n")
            
            for i, page in enumerate(pdf_reader.pages):
                print(f"\n--- PAGE {i+1} ---\n")
                text = page.extract_text()
                print(text)
                print("\n" + "-"*80 + "\n")
        except Exception as e:
            print(f"Error extracting text: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_pf_parser2.py <path_to_pf_pdf>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    extract_pdf_text(pdf_path)

# Made with Bob
