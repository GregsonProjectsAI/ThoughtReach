import sys
import os

sys.path.append(os.getcwd())

from app.services.ingestion import detect_source_family, parse_transcript_export, parse_raw_text_to_messages

def validate_boundary(name, text, expected_family):
    family = detect_source_family(text)
    print(f"[{name}]")
    print(f"  - Detected Family: {family}")
    
    if family == "transcript":
        msgs = parse_transcript_export(text)
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
    ("Clear Transcript", "Alice: Hello\nBob: Hi\nAlice: How are you?", "transcript"),
    ("Weak Transcript (One Label)", "Alice: This is just a single label.\nThere is no repeated structure.", "unknown"),
    ("Inconsistent/Mixed", "Alice: Hello\nThis is a line with a random: colon but shouldn't match.\nOnly one valid header.", "unknown"),
    ("Ambiguous Plain", "Just a regular paragraph of text.\n\nAnother one.", "unknown")
]

all_pass = True
for name, text, expected in cases:
    if not validate_boundary(name, text, expected):
        all_pass = False
        break

if all_pass:
    print("\n--- TRANSCRIPT BOUNDARY VALIDATION PASSED ---")
else:
    print("\n--- TRANSCRIPT BOUNDARY VALIDATION FAILED ---")
    sys.exit(1)
