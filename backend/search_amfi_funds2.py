"""Search AMFI data for fund names"""
import requests

url = "https://www.amfiindia.com/spages/NAVAll.txt"
response = requests.get(url, timeout=10)

search_terms = [
    ("CANARA ROBECO", "LARGE"),
    ("PARAG PARIKH", "FLEXI"),
    ("KOTAK", "SMALL")
]

print("Searching AMFI NAV data for matching funds:\n")

for term1, term2 in search_terms:
    print(f"=== Searching for: {term1} + {term2} ===")
    matches = []
    for line in response.text.split('\n'):
        line_upper = line.upper()
        if term1 in line_upper and term2 in line_upper:
            parts = line.split(';')
            if len(parts) >= 6:
                scheme_name = parts[3]
                nav = parts[4]
                matches.append(f"  {scheme_name} | NAV: {nav}")
    
    if matches:
        print(f"Found {len(matches)} matches:")
        for match in matches[:10]:  # Show first 10 matches
            print(match)
    else:
        print("  No matches found")
    print()
