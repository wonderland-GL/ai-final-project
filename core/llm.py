"""可选的大模型调用。

设计原则：
1. 没有配置 ``LLM_API_KEY`` 时，整个应用照常运行，AI 按钮自动禁用；
2. Key 只从环境变量读，绝不写进代码或仓库；
3. 模型只负责"写文字"，所有数字必须来自程序计算结果；
4. 提供 ``unknown_numbers`` 做数字回查，防止模型编造数据。
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from pathlib import Path


class LLMError(RuntimeError):
    """未配置或调用失败。"""


def _load_dotenv() -> None:
    """极简 .env 加载：方便本地配置，且不覆盖已经存在的环境变量。"""
    path = Path(__file__).resolve().parents[1] / ".env"
    if not path.is_file():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


_load_dotenv()


def config() -> dict[str, str]:
    return {
        "key": os.getenv("LLM_API_KEY", "").strip(),
        "base": os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1").rstrip("/"),
        "model": os.getenv("LLM_MODEL", "deepseek-chat").strip(),
    }


def is_configured() -> bool:
    return bool(config()["key"])


def chat(prompt: str, system: str | None = None, timeout: float = 40.0) -> str:
    """调用 OpenAI 兼容接口，返回纯文本。"""
    cfg = config()
    if not cfg["key"]:
        raise LLMError("未配置 LLM_API_KEY（在 .env 或环境变量里设置）")

    payload = {
        "model": cfg["model"],
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": system
                or "你是大学物理实验助教。只根据用户给出的数字写误差分析，"
                   "不得引入任何新的数字，不得编造实验现象。",
            },
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        f"{cfg['base']}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg['key']}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001 - 网络错误统一降级
        raise LLMError(f"调用失败：{exc}") from exc

    try:
        return str(data["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError("接口返回格式不符合预期") from exc


_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def unknown_numbers(text: str, allowed: list[float] | tuple[float, ...]) -> list[str]:
    """找出文本里不在允许集合中的数字，用于人工复核。"""
    allowed_set = {f"{float(value):.6g}" for value in allowed}
    return [token for token in _NUMBER_RE.findall(text)
            if f"{float(token):.6g}" not in allowed_set]
