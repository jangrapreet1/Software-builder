import os
from pathlib import Path

def main():
    root = Path(__file__).parent.parent
    files_updated = []
    
    # Target files in root/agents, root/workflows, root/coordinator
    for path in root.rglob('*.py'):
        if '.git' in path.parts or 'venv' in path.parts or '__pycache__' in path.parts:
            continue
            
        try:
            content = path.read_text(encoding='utf-8')
            target = "from langchain_core.messages import HumanMessage, SystemMessage"
            replacement = "from langchain_core.messages import HumanMessage, SystemMessage"
            
            if target in content:
                new_content = content.replace(target, replacement)
                path.write_text(new_content, encoding='utf-8')
                files_updated.append(str(path.relative_to(root)))
        except Exception as e:
            print(f"Error reading {path}: {e}")
            
    print(f"Updated imports in {len(files_updated)} files: {', '.join(files_updated)}")

if __name__ == '__main__':
    main()
