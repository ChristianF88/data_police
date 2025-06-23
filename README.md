# data_police

## What is this project?

data_police is a project structure validation tool that leverages AI and the Model Context Protocol (MCP) to help users ensure their code repositories follow best practices and custom policies. It provides automated enforcement of naming conventions, file formats, and directory layouts, and offers detailed feedback and corrections for non-compliance.

## Why does it matter / who is the audience?

This tool is designed for developers, data scientists, and research teams who want to maintain high-quality, reproducible, and well-organized codebases. By automating policy enforcement, data_police reduces manual review effort, prevents common mistakes, and helps teams adhere to organizational or publication standards.

## How is the directory laid out?

- `app.py`: Streamlit web app for uploading and validating project structures.
- `filesystem_mcp.py`: Integration with the MCP Filesystem server for project inspection and validation.
- `policy.txt`: Defines the rules and policies for project structure, naming, and documentation.
- `README.md`: This documentation file.
- `__pycache__/`: Python bytecode cache.
- `data_police/`: Python virtual environment and dependencies for running the app.

### Recommended project structure (from policy):

- `data_raw/`         - untouched source data
- `data_processed/`   - cleaned & transformed outputs
- `notebooks/`        - exploratory or explanatory notebooks
- `scripts/`          - pure-code, reproducible pipelines
- `results/`          - figures, tables, or reports for publication

## How can someone reproduce the core results?

1. Clone the repository and set up the Python environment (see `data_police/` for venv).
2. Install dependencies from `requirements.txt` or `pyproject.toml`.
3. Run the Streamlit app: `streamlit run app.py`.
4. Upload a zipped project and a policy (or use the default `policy.txt`).
5. Review the validation results and follow the AI-generated recommendations.

---

This project enforces policies such as naming conventions, file format rules, README requirements, and folder layout guidance. See `policy.txt` for full details.
