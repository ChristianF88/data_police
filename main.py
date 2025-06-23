import json
import sys
from openai import OpenAI
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown
api_key ="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"
client = OpenAI(api_key=api_key)

def crawl_directory(path: Path, max_file_size=10_000):
    structure = []
    for file_path in path.rglob('*'):
        if file_path.is_file():
            entry = {
                "path": str(file_path.relative_to(path)),
                "size": file_path.stat().st_size,
                "content": None,
            }
            if entry["size"] < max_file_size:
                try:
                    entry["content"] = file_path.read_text(errors='ignore')[:500]  # First 500 chars
                except Exception:
                    pass
            structure.append(entry)
    return structure

def load_policy_document(policy_path: Path):
    return policy_path.read_text()

def ask_chatgpt(structure, policy):
    system_prompt = """
You are an expert project steward whose job is to keep every code or data repository in a clean, transparent, and reproducible state. Whenever a user asks you to create, rename, reorganise, or review files and folders, apply the following policy strictly and proactively. Never apologise for enforcing these rules—simply explain the required change and show the corrected structure.
"""
    user_prompt = f"""Policy:
{policy}

Folder Structure and Files:
{structure}
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    folder = sys.argv[1]
    path = Path(folder)
    if not path.exists():
        print("The folder you provided does not exist!!")
        sys.exit()
    
    structure = json.dumps(crawl_directory(path),indent=2)
    policy_file = Path("policy.txt")
    if not policy_file.exists():
        print("The policy file is missing!")
        sys.exit()
    
    policy = policy_file.read_text()

    answer = ask_chatgpt(structure, policy)
    console = Console()
    renderable_markup = Markdown(answer)
    console.print(renderable_markup)




