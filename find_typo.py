with open(r"c:\Users\Lenovo\Code\Software builder\coordinator\main.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if "LAST_PREVIEW_TARGET_BY_IP" in line:
            print(f"Found on line {i+1}: {line.strip()}")
