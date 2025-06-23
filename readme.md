# data_police

data_police is a small example project that demonstrates how to audit the contents of a repository using a written policy. The code crawls a folder, summarizes file metadata, and sends that structure to OpenAI's API together with a policy document. The API then returns a styled report pointing out any naming or structural issues.

This repo matters for anyone interested in lightweight repository hygiene checks. It shows how a short policy can be turned into an automated assistant that highlights broken naming conventions or missing documentation. Developers or data stewards can adapt the included scripts to enforce custom rules across many projects.

The project root contains a few key pieces:

- `main.py` – command-line utility that analyzes a folder and prints a markdown report.
- `main_web.py` – Streamlit interface with a friendlier UI.
- `policy.txt` – plain language description of the repository rules.
- `test/` – sample files used during development and testing.

To reproduce the core behaviour, install the dependencies listed in `requirements.txt` (create it with the needed packages if not present) and run `python main.py /path/to/repo`. The script will read `policy.txt`, call OpenAI, and display the generated advice. You can also launch the interface with `streamlit run main_web.py`.
