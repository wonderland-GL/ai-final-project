"""提交前自检：扫描仓库里有没有疑似密钥。

用法：``python scripts/check_secrets.py``
返回码 0 表示干净，1 表示发现问题。

它不是万能的，但能挡住 90% 的低级事故：把 sk-xxx、ghp_xxx、
私钥、真实 .env 一起 commit 上去。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache",
             "data", "reports", "models", "knowledge", "node_modules"}

SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".docx", ".xlsx",
                 ".pdf", ".zip", ".exe", ".dll", ".pyc"}

PATTERNS = [
    ("OpenAI/DeepSeek 风格 Key", re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}\b")),
    ("GitHub 经典 Token", re.compile(r"\bghp_[A-Za-z0-9]{20,}\b")),
    ("GitHub 细粒度 Token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("私钥文件内容", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----")),
    ("疑似赋值型密钥", re.compile(
        r"(?i)\b(api[_-]?key|secret|token|password)\b\s*[:=]\s*['\"]([^'\"]{8,})['\"]"
    )),
]

# 这些占位值允许出现
PLACEHOLDERS = {"", "xxx", "your-key", "your_api_key", "changeme", "test"}


def iter_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIXES:
            continue
        yield path


def main() -> int:
    findings: list[tuple[Path, int, str, str]] = []

    for path in iter_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for label, pattern in PATTERNS:
                match = pattern.search(line)
                if not match:
                    continue
                value = match.group(2) if match.lastindex and match.lastindex >= 2 else ""
                if value.strip().lower() in PLACEHOLDERS:
                    continue
                findings.append((path, lineno, label, line.strip()[:120]))

    if findings:
        print("发现疑似敏感信息，先处理再提交：\n")
        for path, lineno, label, snippet in findings:
            relative = path.relative_to(ROOT)
            print(f"  {relative}:{lineno}  [{label}]  {snippet}")
        print("\n如果这是误报（例如文档里的示例），请改成明显的占位符。")
        return 1

    print("未发现疑似密钥。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
