"""
This is POC script only tested with ChatGPT that uses a Streamlit Web UI.

Required:
API-Key for ChatGPT

Use via:
python main_web.py

Limitations:
The policy must be in the current working directory
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st
from openai import OpenAI

# ────────────────────────────────────────────────────────────────────────────────
# Native folder dialog (desktop only – never on Linux)
# ────────────────────────────────────────────────────────────────────────────────
try:
    import tkinter as _tk
    from tkinter import filedialog as _fd
except Exception:
    _tk = None  # falls back automatically


def _dialog_supported() -> bool:
    """Return True if we *should* try to open the Tk dialog."""
    if _tk is None:
        return False
    if sys.platform.startswith("linux"):
        # Too many headless/Wayland/X11 corner‑cases – safer to skip.
        return False
    # Windows & macOS tend to work fine.
    return True


def _open_directory_dialog() -> str | None:
    """Open OS folder dialog when supported; else return *None*."""
    if not _dialog_supported():
        return None
    root = _tk.Tk()
    root.withdraw()
    dirname = _fd.askdirectory()  # blocking
    root.destroy()
    return dirname or None


# ────────────────────────────────────────────────────────────────────────────────
# Helpers (mirroring CLI behaviour)
# ────────────────────────────────────────────────────────────────────────────────

def crawl_directory(path: Path, max_file_size: int = 10_000) -> List[Dict[str, Any]]:
    """Return a list describing the repository’s files (preview ≤ 5 lines/200 words)."""

    structure: List[Dict[str, Any]] = []
    for fp in path.rglob("*"):
        if not fp.is_file():
            if fp.name == "venv" or fp.name == ".venv":
                continue
        if fp.is_file():
            entry: Dict[str, Any] = {
                "path": str(fp.relative_to(path)),
                "size": fp.stat().st_size,
            }
            if entry["size"] <= max_file_size:
                try:
                    text = fp.read_text(errors="ignore")
                    snippet = "\n".join(text.splitlines()[:2])
                    words = snippet.split()
                    if len(words) > 100:
                        snippet = " ".join(words[:200])
                    entry["content"] = snippet
                except Exception:
                    entry["content"] = None
            structure.append(entry)
    return structure


def ask_chatgpt(
    structure: List[Dict[str, Any]],
    policy: str,
    api_key: str,
    model: str = "gpt-4o",
    temperature: float = 0.2,
) -> str:
    client = OpenAI(api_key=api_key)
    system_prompt = (
        """
You are an expert project steward whose job is to keep every code or data repository in a clean, transparent, and reproducible state. Whenever a user asks you to create, rename, reorganise, or review files and folders, apply the following policy strictly and proactively. Never apologise for enforcing these rules—simply explain the required change and show the corrected structure.
        """
    ).strip()
    user_prompt = (
        f"Policy:\n{policy}\n\nFolder Structure and Files:\n"
        f"{json.dumps(structure, indent=2, ensure_ascii=False)}\n"
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
    )
    return response.choices[0].message.content


# ────────────────────────────────────────────────────────────────────────────────
# Markdown → collapsible HTML (<details>/<summary>)
# ────────────────────────────────────────────────────────────────────────────────

try:
    import markdown as _mdlib
except ImportError:
    _mdlib = None


def _md_to_details(md: str) -> str:
    lines = md.splitlines()
    html: List[str] = []
    stack: List[int] = []
    in_code = False

    def close(to: int | None = None):
        while stack and (to is None or stack[-1] >= to):
            html.append("</details>")
            stack.pop()

    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            html.append(line)
            continue
        if not in_code:
            m = re.match(r"^(#{1,6})\s+(.*)$", line)
            if m:
                level = len(m.group(1))
                title = m.group(2)
                close(level)
                html.append(
                    f"<details><summary><h{level} style='display:inline'>{title}</h{level}></summary>"
                )
                stack.append(level)
                continue
        html.append(line)
    close()
    joined = "\n".join(html)
    if _mdlib is not None:
        return _mdlib.markdown(joined, extensions=["fenced_code", "tables"])
    return joined


# ────────────────────────────────────────────────────────────────────────────────
# Streamlit UI
# ────────────────────────────────────────────────────────────────────────────────

def run_web_ui():
    st.set_page_config(page_title="Repository Steward", layout="wide")
    st.title("🗂️ Repository Steward")

    # ───────────── Sidebar ─────────────
    api_key = (
        st.sidebar.text_input(
            "OpenAI API key", type="password", value=os.getenv("OPENAI_API_KEY", "")
        )
        or os.getenv("OPENAI_API_KEY", "")
    )

    max_file_size = st.sidebar.number_input(
        "Max preview size (bytes)", 1_000, 1_000_000, 10_000, 1_000
    )
    model_name = st.sidebar.text_input("Model", value="gpt-4o")
    temperature = st.sidebar.slider("Temperature", 0.0, 1.0, 0.2, 0.05)

    repo_root_key = "repo_root_path"
    if repo_root_key not in st.session_state:
        st.session_state[repo_root_key] = ""

    # Folder picker ---------------------------------------------------------
    st.sidebar.markdown("**Select repository folder**")
    col_browse, col_path = st.sidebar.columns([1, 4])

    browse_disabled = not _dialog_supported()
    browse_help = (
        "Folder dialog disabled on Linux; type or paste the path below instead."
        if browse_disabled
        else "Opens your OS's folder picker"
    )

    with col_browse:
        if st.button("Browse…", disabled=browse_disabled, help=browse_help):
            selected = _open_directory_dialog()
            if selected:
                st.session_state[repo_root_key] = selected
                st.rerun()

    with col_path:
        typed = st.text_input(
            label="Selected folder",
            value=st.session_state[repo_root_key],
            key="_path_display",
            placeholder="Type path here…",
        )
        st.session_state[repo_root_key] = typed

    # Policy path – default inside repo ------------------------------------
    def _default_policy_path() -> str:
        root = Path(st.session_state[repo_root_key])
        candidate = root / "policy.txt"
        return str(candidate) if candidate.exists() else "policy.txt"

    policy_path_input = st.sidebar.text_input("Path to policy.txt", value=_default_policy_path())

    # ───────────── Main layout ─────────────
    col_in, col_out = st.columns(2)

    with col_in:
        st.header("1️⃣ Input")
        if st.button("Analyse repository", use_container_width=True):
            repo_path = Path(st.session_state[repo_root_key]).expanduser()
            pol_path = Path(policy_path_input).expanduser()

            if not repo_path.exists():
                st.error("Repository folder not found: %s" % repo_path)
                st.stop()
            if not pol_path.exists():
                st.error("Policy file not found: %s" % pol_path)
                st.stop()
            if not api_key:
                st.error("OpenAI API key is missing.")
                st.stop()

            with st.status("Crawling repository…", expanded=False):
                structure = crawl_directory(repo_path, max_file_size)
            st.session_state.update(structure=structure, policy=pol_path.read_text())
            st.success("Repository crawled – view output on the right.")

    with col_out:
        st.header("2️⃣ Output")
        if "structure" in st.session_state:
            with st.spinner("ChatGPT thinking…"):
                md_answer = ask_chatgpt(
                    st.session_state["structure"],
                    st.session_state["policy"],
                    api_key,
                    model_name,
                    temperature,
                )
            st.markdown(_md_to_details(md_answer), unsafe_allow_html=True)
            st.download_button("Download Markdown", md_answer, "steward_answer.md")


# ────────────────────────────────────────────────────────────────────────────────
# Self-relaunch via Streamlit CLI (avoid bare-mode warnings)
# ────────────────────────────────────────────────────────────────────────────────

def _running_inside_streamlit() -> bool:
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx

        return get_script_run_ctx() is not None
    except Exception:
        return False


if __name__ == "__main__":
    if _running_inside_streamlit():
        run_web_ui()
    else:
        subprocess.run(["streamlit", "run", sys.argv[0], *sys.argv[1:]], check=False)

