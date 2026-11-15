"""Repo scanner — clones or reads a repository and extracts AI-governance-relevant content."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

_PRIORITY_FILES = [
    "README.md",
    "README.rst",
    "README.txt",
    "ETHICS.md",
    "GOVERNANCE.md",
    "FAIRNESS.md",
    "SAFETY.md",
    "MODEL_CARD.md",
    "model_card.md",
    "DATA_PROCESSING.md",
    "PRIVACY.md",
    "SECURITY.md",
    "CONTRIBUTING.md",
]

_AI_KEYWORDS = {
    "model",
    "train",
    "inference",
    "predict",
    "classifier",
    "neural",
    "embedding",
    "tokenizer",
    "pipeline",
    "dataset",
    "evaluation",
    "fairness",
    "bias",
    "accuracy",
    "loss",
    "gradient",
    "agent",
    "llm",
    "prompt",
    "finetune",
}

_SKIP_DIRS = {
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "node_modules",
    ".mypy_cache",
    "dist",
    "build",
}
_MAX_FILE_CHARS = 8_000
_MAX_TOTAL_CHARS = 80_000


def _extract_pdf(file_obj) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        return "[pypdf not installed — run: uv add pypdf]"
    reader = PdfReader(file_obj)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(file_obj) -> str:
    try:
        from docx import Document
    except ImportError:
        return "[python-docx not installed — run: uv add python-docx]"
    doc = Document(file_obj)
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_uploaded_files(uploaded_files: list) -> list[dict]:
    """Extract text from Streamlit UploadedFile objects (PDF, DOCX, TXT, MD)."""
    results = []
    for uf in uploaded_files:
        name = getattr(uf, "name", "unknown")
        ext = Path(name).suffix.lower()
        try:
            if ext == ".pdf":
                content = _extract_pdf(uf)
            elif ext == ".docx":
                content = _extract_docx(uf)
            else:
                raw = uf.read()
                content = raw.decode("utf-8", errors="ignore") if isinstance(raw, bytes) else raw
        except Exception as e:
            content = f"[Could not extract: {e}]"
        results.append({"path": f"uploaded/{name}", "content": content[:_MAX_FILE_CHARS]})
    return results


def fetch_url_content(url: str) -> dict:
    """Fetch plain text from a URL; strips HTML tags if the response is HTML."""
    import re
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "Aegis-Scanner/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read(_MAX_FILE_CHARS * 6)
        content_type = resp.headers.get("Content-Type", "")
    text = raw.decode("utf-8", errors="ignore")
    if "html" in content_type or text.lstrip().startswith("<"):
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
    return {"path": url, "content": text[:_MAX_FILE_CHARS]}


def clone_repo(url_or_path: str, branch: str = "") -> tuple[Path, bool]:
    """
    Clone a remote repo or validate a local path.
    Returns (resolved_path, is_temp). Caller must delete temp dirs when done.
    """
    p = Path(url_or_path)
    if p.exists() and p.is_dir():
        return p.resolve(), False

    tmp = tempfile.mkdtemp(prefix="aegis-scan-")
    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd += ["--branch", branch]
    cmd += [url_or_path, tmp]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if result.returncode != 0 and branch:
        # Retry without branch
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url_or_path, tmp],
            capture_output=True,
            text=True,
            timeout=180,
        )
    if result.returncode != 0:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError(f"Clone failed: {result.stderr.strip()[:500]}")

    return Path(tmp), True


def _should_skip(path: Path, repo_root: Path) -> bool:
    try:
        parts = path.relative_to(repo_root).parts
        return any(part in _SKIP_DIRS for part in parts)
    except ValueError:
        return True


def extract_context(repo_path: Path) -> dict:
    """Extract AI-governance-relevant files and structure from a cloned repo."""
    total_chars = 0
    extracted: list[dict] = []
    seen_paths: set[str] = set()

    def _add(f: Path) -> bool:
        nonlocal total_chars
        if total_chars >= _MAX_TOTAL_CHARS:
            return False
        if _should_skip(f, repo_path):
            return False
        rel = str(f.relative_to(repo_path))
        if rel in seen_paths:
            return False
        try:
            content = f.read_text(errors="ignore")[:_MAX_FILE_CHARS]
        except OSError:
            return False
        if not content.strip():
            return False
        extracted.append({"path": rel, "content": content})
        seen_paths.add(rel)
        total_chars += len(content)
        return True

    # 1. Priority files (root level)
    for name in _PRIORITY_FILES:
        f = repo_path / name
        if f.exists():
            _add(f)

    # 2. All markdown docs
    for f in sorted(repo_path.rglob("*.md")):
        if total_chars >= _MAX_TOTAL_CHARS:
            break
        _add(f)

    # 3. Python files whose name contains AI keywords
    for f in sorted(repo_path.rglob("*.py")):
        if total_chars >= _MAX_TOTAL_CHARS:
            break
        if any(kw in f.stem.lower() for kw in _AI_KEYWORDS):
            _add(f)

    # 4. Config and dependency files
    for name in [
        "requirements.txt",
        "requirements-ml.txt",
        "requirements-ai.txt",
        "pyproject.toml",
        "setup.py",
        "package.json",
        "config.yaml",
        "config.yml",
    ]:
        f = repo_path / name
        if f.exists():
            _add(f)

    # 5. YAML/JSON config files that look AI-related
    for f in sorted(repo_path.rglob("*.yaml")) + sorted(repo_path.rglob("*.yml")):
        if total_chars >= _MAX_TOTAL_CHARS:
            break
        if any(kw in f.stem.lower() for kw in _AI_KEYWORDS):
            _add(f)

    # 6. Directory tree (top 3 levels, excluding hidden/build dirs)
    dirs: set[str] = set()
    for item in sorted(repo_path.iterdir()):
        if item.name.startswith(".") or item.name in _SKIP_DIRS:
            continue
        dirs.add(item.name + ("/" if item.is_dir() else ""))
        if item.is_dir():
            for sub in sorted(item.iterdir()):
                if sub.name.startswith(".") or sub.name in _SKIP_DIRS:
                    continue
                dirs.add(f"{item.name}/{sub.name}" + ("/" if sub.is_dir() else ""))

    all_files = [f for f in repo_path.rglob("*") if f.is_file() and not _should_skip(f, repo_path)]

    return {
        "files": extracted,
        "total_files": len(all_files),
        "directory_tree": sorted(dirs),
        "repo_path": str(repo_path),
        "total_chars_extracted": total_chars,
    }
