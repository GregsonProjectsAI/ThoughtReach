import sys
import os

# Ensure current directory is in path
sys.path.append(os.getcwd())

from app.services.ingestion import (
    detect_source_family, 
    parse_chatgpt_export, 
    parse_claude_export, 
    parse_whatsapp_export, 
    parse_email_thread,
    parse_raw_text_to_messages
)

def test_case(name, text, expected_family, expected_roles):
    family = detect_source_family(text)
    print(f"[{name}]")
    print(f"  - Detected Family: {family}")
    
    if family == "chatgpt":
        msgs = parse_chatgpt_export(text)
    elif family == "claude":
        msgs = parse_claude_export(text)
    elif family == "whatsapp":
        msgs = parse_whatsapp_export(text)
    elif family == "email_thread":
        msgs = parse_email_thread(text)
    else:
        msgs, st = parse_raw_text_to_messages(text)
        print(f"  - Source Type: {st}")
    
    roles = [m['role'] for m in msgs]
    print(f"  - Roles: {roles}")
    
    # Validation logic
    pass_family = (family == expected_family)
    pass_roles = all(r in expected_roles for r in roles)
    
    result = "PASS" if (pass_family and pass_roles) else "FAIL"
    print(f"  - Result: {result}")
    return result == "PASS"

# Test cases
cases = [
    ("ChatGPT-Style", "User\nHello world\nChatGPT\nI am here", "chatgpt", ["user", "assistant"]),
    ("Claude-Style", "Human: Tell me a joke\nAssistant: Why? because.", "claude", ["user", "assistant"]),
    ("WhatsApp-Style", "[12/31/23, 11:59 PM] Sarah: Hey\n[12/31/23, 11:59 PM] John: Yo", "whatsapp", ["Sarah", "John"]),
    ("Email-Style", "From: Sarah\nTo: John\nDate: Jan 1\nSubject: Hello\n\nHey there!\nFrom: John\nTo: Sarah\nDate: Jan 2\nSubject: Re: Hello\n\nHi Sarah!\nHow are you?", "email_thread", ["Sarah", "John"]),
    ("Ambiguous", "Line one.\n\nLine two after empty line.", "unknown", ["unknown"])
]

all_pass = True
for name, text, fam, roles in cases:
    if not test_case(name, text, fam, roles):
        all_pass = False
        break

if all_pass:
    print("\n--- ALL VALIDATIONS PASSED ---")
else:
    print("\n--- VALIDATION FAILED ---")
    sys.exit(1)
