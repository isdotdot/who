import datetime
import os
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT / "content" / "posts"
CONTENT_DIR.mkdir(parents=True, exist_ok=True)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "llama3.1:8b")

SYSTEM_PROMPT = """
You write short, friendly blog posts that answer everyday "why does ... ?" questions.
Tone: neutral + friendly, clear, practical. Audience: normal people searching the web.
"""

USER_PROMPT = """
Write ONE complete blog post that answers a common "why does ... ?" question people might Google.

Output format:
- Plain Markdown only.
- First line MUST be a top-level heading starting with "# " and containing the title.
- After that, write 700-900 words of content with headings and short paragraphs.
- Do NOT include any front matter.
- Do NOT include JSON.
- Do NOT include backticks or ``` fences.
"""

def slugify(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug or "post"

def call_ollama() -> str:
    url = f"{OLLAMA_URL}/api/generate"
    prompt = SYSTEM_PROMPT.strip() + "\n\n" + USER_PROMPT.strip()

    resp = requests.post(
        url,
        json={"model": MODEL, "prompt": prompt, "stream": False},
        timeout=300,
    )
    resp.raise_for_status()
    data = resp.json()
    return data["response"].strip()

def extract_title_and_body(md: str):
    lines = md.splitlines()
    title = "Why Things Happen"
    body_lines = []

    # Find first non-empty line as heading/title
    first_nonempty = None
    for i, line in enumerate(lines):
        if line.strip():
            first_nonempty = i
            break

    if first_nonempty is None:
        return title, ""

    first_line = lines[first_nonempty].strip()

    # Handle "# Title" or "## Title" or bold "**Title**"
    if first_line.startswith("#"):
        # strip leading #'s and spaces
        title = first_line.lstrip("#").strip(" *")
        body_lines = lines[first_nonempty + 1 :]
    elif first_line.startswith("**") and first_line.endswith("**"):
        title = first_line.strip("* ").strip()
        body_lines = lines[first_nonempty + 1 :]
    else:
        # fallback: treat first line as title anyway
        title = first_line
        body_lines = lines[first_nonempty + 1 :]

    body = "\n".join(body_lines).strip()
    return title or "Why Things Happen", body

def make_description(body: str) -> str:
    # Find first non-empty, non-heading line and use first ~180 chars
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        desc = stripped.replace('"', "'")
        if len(desc) > 180:
            desc = desc[:177] + "..."
        return desc
    return "A simple explanation for an everyday question."

def main():
    raw = call_ollama()
    title, body = extract_title_and_body(raw)

    if not body:
        raise SystemExit(f"Model output had no body:\n{raw}")

    description = make_description(body)

    tags = ["why", "everyday"]
    today = datetime.date.today().strftime("%Y-%m-%d")
    slug = slugify(title)
    filename = f"{today}-{slug}.md"
    path = CONTENT_DIR / filename
    if path.exists():
        path = CONTENT_DIR / f"{today}-{slug}-2.md"

    tags_toml = ", ".join(f'"{t}"' for t in tags)

    front_matter = f"""+++
title = "{title.replace('"', "'")}"
description = "{description}"
date = "{today}"
tags = [{tags_toml}]
draft = false
+++

"""

    md_out = front_matter + body + "\n"
    path.write_text(md_out, encoding="utf-8")

    print(f"Wrote {path}")

if __name__ == "__main__":
    main()

