import sys
import os

sys.path.append(os.getcwd())

from app.services.ingestion import detect_source_family, parse_timestamp_chat_export, parse_raw_text_to_messages

def validate_boundary(name, text, expected_family):
    family = detect_source_family(text)
    print(f"[{name}]")
    print(f"  - Detected Family: {family}")
    
    if family == "timestamp_chat":
        msgs = parse_timestamp_chat_export(text)
    else:
        msgs, st = parse_raw_text_to_messages(text)
        print(f"  - Source Type: {st}")
    
    roles = [m['role'] for m in msgs]
    print(f"  - Roles: {roles}")
    
    success = (family == expected_family)
    print(f"  - Result: {'PASS' if success else 'FAIL'}")
    return success

# Validation Cases
cases = [
    ("Clear Timestamped Chat", "2024-01-31 10:00 - Alice: Hi\n2024-01-31 10:01 - Bob: Hello", "timestamp_chat"),
    ("Weak Timestamp (One Line)", "2024-01-31 10:00 - Alice: Only one line here.", "unknown"),
    ("Inconsistent/Mixed", "2024-01-31 10:00 - Alice: Hi\nSome random: line that is not a timestamp.\nAnother line.", "unknown"),
    ("Ambiguous Plain", "Just a regular paragraph of text.\n\nAnother one.", "unknown")
]

all_pass = True
for name, text, expected in cases:
    if not validate_boundary(name, text, expected):
        all_pass = False
        break

if all_pass:
    print("\n--- TIMESTAMP BOUNDARY VALIDATION PASSED ---")
else:
    print("\n--- TIMESTAMP BOUNDARY VALIDATION FAILED ---")
    sys.exit(1)
