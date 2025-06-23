# data_police

data_police demonstrates how a small script can enforce repository hygiene through a written policy. The program crawls any directory, records basic metadata, and asks OpenAI to review the structure. The response is a markdown report telling you which files violate your rules.

The project is aimed at developers or data managers who want an automated check on folder names, documentation, or stray notebooks. By adjusting the policy you can adapt the tool for many types of codebases.

## Repository layout

- `main.py` – command-line tool that prints an audit report.
- `main_web.py` – optional Streamlit interface.
- `policy.txt` – plain language list of repository rules.
- `test/` – minimal data used during development.

## Running the audit

1. Install dependencies from `requirements.txt`.
2. Export your OpenAI API key as `OPENAI_API_KEY`.
3. Invoke `python main.py /path/to/repo`.
4. For a graphical view run `streamlit run main_web.py`.

Change `policy.txt` to suit your team’s naming conventions or layout guidelines. The script will flag anything that diverges and suggest fixes. Although the example policy is short, it can enforce surprisingly detailed standards and help keep repositories clean.
