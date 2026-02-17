"""Search AMFI data for fund names"""
import requests

url = "https://www.amfiindia.com/spages/NAVAll.txt"
response = requests.get(url, timeout=10)

search_terms = [
    "CANARA ROBECO",
    "PARAG PARIKH",
    "KOTAK SMALL CAP"
]

print("Searching AMFI NAV data for matching funds:\n")

for term in search_terms:
    print(f"=== Searching for: {term} ===")
    matches = []
    for line in response.text.split('\n'):
        if term in line.upper():
            parts = line.split(';')
            if len(parts) >= 6:
                scheme_name = parts[3]
                nav = parts[4]
                matches.append(f"  {scheme_name} | NAV: {nav}")
    
    if matches:
        print(f"Found {len(matches)} matches:")
        for match in matches[:5]:  # Show first 5 matches
            print(match)
    else:
        print("  No matches found")
    print()
