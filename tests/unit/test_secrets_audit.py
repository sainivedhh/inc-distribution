import pytest
from cli.audit_secrets import SECRET_PATTERNS
from pathlib import Path
import re

def test_repo_has_zero_secrets():
    root_dir = Path(".")
    findings = []
    ignored = {".git", ".pytest_cache", ".ruff_cache", "test_pack/outputs", "__pycache__"}
    for path in root_dir.rglob("*"):
        if path.is_file() and not any(part in ignored for part in path.parts):
            if path.name in ("test_phase1_skeleton.py", "audit_secrets.py", "test_secrets_audit.py"):
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                for pat, label in SECRET_PATTERNS:
                    if re.search(pat, content):
                        findings.append((str(path), label))
            except Exception:
                pass
    assert len(findings) == 0, f"Found secrets in repository: {findings}"
