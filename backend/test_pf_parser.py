"""
Debug script to test PF parser and see what's being extracted
"""
import sys
import PyPDF2
from io import BytesIO

def extract_pdf_text(pdf_path, password=None):
    """Extract and print text from PDF"""
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        
        # Handle password protection
        if pdf_reader.is_encrypted:
            if password:
                pdf_reader.decrypt(password)
                print(f"PDF decrypted with password")
            else:
                print("PDF is password protected. Trying common passwords...")
                # Try common passwords
                common_passwords = ['', '123456', 'password', '12345678']
                decrypted = False
                for pwd in common_passwords:
                    try:
                        if pdf_reader.decrypt(pwd):
                            print(f"Successfully decrypted with password: '{pwd}'")
                            decrypted = True
                            break
                    except:
                        continue
                
                if not decrypted:
                    print("ERROR: Could not decrypt PDF. Please provide password as second argument.")
                    print("Usage: python test_pf_parser.py <path_to_pdf> [password]")
                    return
        
        print(f"Number of pages: {len(pdf_reader.pages)}")
        print("\n" + "="*80)
        print("EXTRACTED TEXT:")
        print("="*80 + "\n")
        
        for i, page in enumerate(pdf_reader.pages):
            print(f"\n--- PAGE {i+1} ---\n")
            text = page.extract_text()
            print(text)
            print("\n" + "-"*80 + "\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_pf_parser.py <path_to_pf_pdf> [password]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    password = sys.argv[2] if len(sys.argv) > 2 else None
    extract_pdf_text(pdf_path, password)

# Made with Bob
