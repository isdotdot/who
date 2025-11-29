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

TITLE_DEFAULT = "Who People Are"
TAGS = ["who", "profile"]
DESCRIPTION_FALLBACK = "A short profile explaining who someone is and why they are notable."

SYSTEM_PROMPT = """
You write engaging but concise biographical posts that answer 'Who is ... ?' questions.
Tone: neutral, respectful, and informative.
"""

USER_PROMPT = """
Write ONE complete blog post answering a 'Who is ... ?' question.

The post should include:
- A short intro explaining who the person is and why they are notable.
- A brief background / early life section.
- Key achievements or reasons they are known.
- Any relevant context or impact.
- A short closing summary.

Output format:
- Plain Markdown only.
- First line MUST be a top-level heading starting with "# " and containing the person's name.
- 700-900 words total, with headings and short paragraphs.
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
    title = TITLE_DEFAULT
    body_lines = []

    first_nonempty = None
    for i, line in enumerate(lines):
        if line.strip():
            first_nonempty = i
            break

    if first_nonempty is None:
        return title, ""

    first_line = lines[first_nonempty].strip()

    if first_line.startswith("#"):
        title = first_line.lstrip("#").strip(" *")
        body_lines = lines[first_nonempty + 1 :]
    elif first_line.startswith("**") and first_line.endswith("**"):
        title = first_line.strip("* ").strip()
        body_lines = lines[first_nonempty + 1 :]
    else:
        title = first_line
        body_lines = lines[first_nonempty + 1 :]

    body = "\n".join(body_lines).strip()
    return title or TITLE_DEFAULT, body

def make_description(body: str) -> str:
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
    return DESCRIPTION_FALLBACK

def main():
    raw = call_ollama()
    title, body = extract_title_and_body(raw)

    if not body:
        raise SystemExit(f"Model output had no body:\n{raw}")

    description = make_description(body)

    today = datetime.date.today().strftime("%Y-%m-%d")
    slug = slugify(title)
    filename = f"{today}-{slug}.md"
    path = CONTENT_DIR / filename
    if path.exists():
        path = CONTENT_DIR / f"{today}-{slug}-2.md"

    tags_toml = ", ".join(f'"{t}"' for t in TAGS)

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
