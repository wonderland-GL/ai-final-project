"""单位解析与换算。

目标：让用户可以直接输入 ``8.1cm``、``0.081 m``、``1.2e-3`` 这类写法，
程序统一换算到 SI 单位后再参与计算，避免"厘米当成米"的事故。

对外接口：
- ``parse_quantity(text)``  把一段文本解析成 Quantity
- ``convert(value, from_unit, to_unit)``  同量纲换算
- ``units_for(dimension)``  列出某个量纲可用的单位
- ``format_measurement(value, u)``  按不确定度位数格式化
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass


class UnitError(ValueError):
    """单位无法识别，或者两个单位量纲不一致。"""


# 单位 -> (换算到 SI 的倍数, 量纲, SI 单位符号)
_UNITS: dict[str, tuple[float, str, str]] = {
    # 长度
    "m": (1.0, "length", "m"),
    "cm": (1e-2, "length", "m"),
    "mm": (1e-3, "length", "m"),
    "um": (1e-6, "length", "m"),
    "nm": (1e-9, "length", "m"),
    "km": (1e3, "length", "m"),
    # 时间
    "s": (1.0, "time", "s"),
    "ms": (1e-3, "time", "s"),
    "min": (60.0, "time", "s"),
    "h": (3600.0, "time", "s"),
    # 质量
    "kg": (1.0, "mass", "kg"),
    "g": (1e-3, "mass", "kg"),
    "mg": (1e-6, "mass", "kg"),
    # 力 / 压强
    "n": (1.0, "force", "N"),
    "pa": (1.0, "pressure", "Pa"),
    "kpa": (1e3, "pressure", "Pa"),
    # 电学
    "v": (1.0, "voltage", "V"),
    "mv": (1e-3, "voltage", "V"),
    "a": (1.0, "current", "A"),
    "ma": (1e-3, "current", "A"),
    "ua": (1e-6, "current", "A"),
    "ohm": (1.0, "resistance", "Ω"),
    "hz": (1.0, "frequency", "Hz"),
    "khz": (1e3, "frequency", "Hz"),
    # 复合
    "m/s": (1.0, "velocity", "m/s"),
    "m/s^2": (1.0, "acceleration", "m/s²"),
    "m/s2": (1.0, "acceleration", "m/s²"),
    "n/m": (1.0, "stiffness", "N/m"),
}

_DIMENSION_NAMES = {
    "length": "长度",
    "time": "时间",
    "mass": "质量",
    "force": "力",
    "pressure": "压强",
    "voltage": "电压",
    "current": "电流",
    "resistance": "电阻",
    "frequency": "频率",
    "velocity": "速度",
    "acceleration": "加速度",
    "stiffness": "劲度系数",
}


def normalise_unit(unit: str) -> str:
    """把各种花式写法归一：μ→u、Ω→ohm、²→^2、转小写。"""
    u = (unit or "").strip()
    if not u:
        return ""
    u = u.replace("μ", "u").replace("µ", "u")
    u = u.replace("Ω", "ohm").replace("ω", "ohm")
    u = u.replace("²", "^2").replace("³", "^3")
    u = u.replace(" ", "")
    return u.lower()


_QTY_RE = re.compile(
    r"^\s*([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)\s*([^\s\d]*)\s*$"
)


@dataclass(frozen=True)
class Quantity:
    """一个带单位的量。"""

    raw: str          # 原始输入
    value: float      # 数值
    unit: str         # 归一后的单位（可能为空）
    si_value: float   # 换算到 SI 后的数值
    si_unit: str      # SI 单位符号


def parse_quantity(text: str, default_unit: str = "") -> Quantity:
    """解析 ``"8.1 cm"`` 这样的文本。

    没有写单位时使用 ``default_unit``；两者都为空则按纯数字处理。
    """
    raw = str(text).strip()
    match = _QTY_RE.match(raw)
    if not match:
        raise UnitError(f"无法解析数值：{text!r}")

    value = float(match.group(1))
    unit = normalise_unit(match.group(2) or default_unit)

    if not unit:
        return Quantity(raw, value, "", value, "")

    if unit not in _UNITS:
        known = "、".join(sorted(_UNITS))
        raise UnitError(f"不认识的单位 {unit!r}；支持：{known}")

    factor, _dim, si_unit = _UNITS[unit]
    return Quantity(raw, value, unit, value * factor, si_unit)


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """同量纲换算，例如 ``convert(8.1, "cm", "m") -> 0.081``。"""
    fu = normalise_unit(from_unit) or normalise_unit(to_unit)
    tu = normalise_unit(to_unit) or normalise_unit(from_unit)
    if not fu or not tu:
        return float(value)
    if fu not in _UNITS:
        raise UnitError(f"不认识的单位：{from_unit!r}")
    if tu not in _UNITS:
        raise UnitError(f"不认识的单位：{to_unit!r}")

    factor_from, dim_from, _ = _UNITS[fu]
    factor_to, dim_to, _ = _UNITS[tu]
    if dim_from != dim_to:
        raise UnitError(f"量纲不一致：{fu} 是{_DIMENSION_NAMES.get(dim_from, dim_from)}，"
                        f"{tu} 是{_DIMENSION_NAMES.get(dim_to, dim_to)}")
    return float(value) * factor_from / factor_to


def units_for(unit: str) -> list[str]:
    """列出与 ``unit`` 同量纲的所有单位，用于下拉框。"""
    key = normalise_unit(unit)
    if not key or key not in _UNITS:
        return [unit] if unit else []
    dim = _UNITS[key][1]
    return sorted(u for u, (_f, d, _s) in _UNITS.items() if d == dim)


def dimension_of(unit: str) -> str:
    key = normalise_unit(unit)
    if not key or key not in _UNITS:
        return ""
    return _UNITS[key][1]


def si_unit_of(unit: str) -> str:
    key = normalise_unit(unit)
    if not key or key not in _UNITS:
        return unit
    return _UNITS[key][2]


def format_measurement(value: float, u: float | None) -> str:
    """按"不确定度保留 1 位有效数字、结果末位对齐"的规则格式化。

    >>> format_measurement(12.258, 0.18)
    '12.3 ± 0.2'
    """
    if u is None or not math.isfinite(u) or u <= 0:
        return f"{value:.6g}"

    exponent = math.floor(math.log10(abs(u)))
    decimals = max(0, -exponent)
    u_rounded = round(u, decimals)
    if u_rounded == 0:
        u_rounded = 10.0 ** exponent
    v_rounded = round(value, decimals)

    if decimals == 0:
        return f"{v_rounded:.0f} ± {u_rounded:.0f}"
    return f"{v_rounded:.{decimals}f} ± {u_rounded:.{decimals}f}"
