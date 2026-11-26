"""数据读入：把粘贴的文本或 CSV 变成两列浮点数。"""

from __future__ import annotations

import re

import numpy as np


class DataError(ValueError):
    """数据格式不对。"""


_NUMBER_RE = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def parse_pairs(text: str) -> tuple[np.ndarray, np.ndarray]:
    """解析两列数据。

    支持逗号、制表符、分号、空格分隔；允许 ``#`` 注释；
    允许第一行是表头（没有数字就跳过）。
    """
    xs: list[float] = []
    ys: list[float] = []

    for lineno, line in enumerate(str(text).splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        numbers = _NUMBER_RE.findall(stripped)
        if len(numbers) < 2:
            if not xs:
                continue  # 首行表头
            raise DataError(f"第 {lineno} 行少于两个数字：{stripped!r}")

        try:
            xs.append(float(numbers[0]))
            ys.append(float(numbers[1]))
        except ValueError as exc:
            raise DataError(f"第 {lineno} 行无法转成数字：{stripped!r}") from exc

    if len(xs) < 3:
        raise DataError("至少需要 3 行有效数据（每行两个数字）")

    x_arr = np.asarray(xs, dtype=float)
    y_arr = np.asarray(ys, dtype=float)
    if not np.all(np.isfinite(x_arr)) or not np.all(np.isfinite(y_arr)):
        raise DataError("数据里有 NaN 或无穷大")
    return x_arr, y_arr


def decode_bytes(raw: bytes) -> str:
    """兼容 UTF-8 和 GBK（Windows 上导出的 CSV 常见）。"""
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise DataError("无法识别文件编码，请另存为 UTF-8 后重试")


def to_csv_text(x, y, x_name: str = "x", y_name: str = "y") -> str:
    """导出成两列 CSV 文本，方便用户存档。"""
    lines = [f"{x_name},{y_name}"]
    lines.extend(f"{float(a):.10g},{float(b):.10g}" for a, b in zip(x, y))
    return "\n".join(lines) + "\n"
