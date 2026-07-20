import re
with open("knowledge_expand.py", "r", encoding="utf-8") as f:
    content = f.read()
# Replace Chinese double quotes with corner brackets
content = content.replace("\u201c", "\u300c").replace("\u201d", "\u300d")
# Replace ASCII double quotes that appear inside strings (pattern: "text" inside "string")
# We look for lines that are string values in the dict and have inner quotes
lines = content.split("\n")
fixed = []
for line in lines:
    s = line.strip()
    # If it's a string value line with inner double quotes that aren't part of the Python syntax
    # We need to be more careful - only replace inner " that are not at start/end
    if s.startswith('"') and (s.endswith('",') or s.endswith('"')):
        # Find the inner content
        inner = s[1:]
        if inner.endswith('",'):
            inner = inner[:-2]
        elif inner.endswith('"'):
            inner = inner[:-1]
        # Check if inner content has unescaped double quotes
        if '"' in inner:
            inner = inner.replace('"', '\u300c').replace('"', '\u300d')
            # Rebuild the line
            indent = line[:len(line) - len(line.lstrip())]
            line = f'{indent}"{inner}",' if s.endswith('",') else f'{indent}"{inner}"'
    fixed.append(line)
content = "\n".join(fixed)
with open("knowledge_expand.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Done fixing quotes")
