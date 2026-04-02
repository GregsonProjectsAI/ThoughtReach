import re

file_path = r"C:\Users\alexg\Downloads\AI Build Ideas and Skeletons.txt"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

# Split on CHAT TITLE:
parts = re.split(r"CHAT TITLE:\s*", content)

# The first part might be empty if the file starts with CHAT TITLE:
conversations = [p.strip() for p in parts if p.strip()]

print(f"Count of split conversations: {len(conversations)}\n")

if conversations:
    first_conv = conversations[0]
    lines = first_conv.splitlines()
    print("--- FIRST CONVERSATION (Title + First 30 lines) ---")
    for i, line in enumerate(lines[:30]):
        print(f"{i:02d}: {line}")
    print("---------------------------------------------------")
