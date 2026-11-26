"""实验模板：把一个实验的"变量、模型、目标公式、仪器"写成 JSON。

新增一个实验只需要在 ``templates/experiments/`` 里加一个 JSON 文件，
不需要改任何代码 —— 这是系统"功能多但代码不多"的关键。
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


class TemplateError(ValueError):
    """模板缺字段、字段非法或公式写错。"""


SUPPORTED_MODELS = ("linear", "power", "exponential")
SUPPORTED_TRANSFORMS = ("none", "square")


@dataclass(frozen=True)
class Variable:
    name: str
    unit: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Instrument:
    name: str
    resolution: float
    unit: str
    variable: str


@dataclass(frozen=True)
class Target:
    name: str
    expr: str
    unit: str
    reference: float | None = None


@dataclass(frozen=True)
class Template:
    id: str
    name: str
    model: str
    x: Variable
    y: Variable
    target: Target
    instruments: tuple[Instrument, ...]
    constants: dict[str, float]
    y_transform: str
    formula_text: str
    notes: str
    demo_x: tuple[float, ...]
    demo_y: tuple[float, ...]
    source: Path

    @property
    def demo_rows(self) -> list[tuple[float, float]]:
        return list(zip(self.demo_x, self.demo_y))


# numpy 命名空间作为公式白名单：模板是本地可信文件，但仍禁用 __builtins__
_SAFE_FUNCS: dict[str, Any] = {"pi": np.pi, "e": np.e}
for _name in ("exp", "log", "log10", "sqrt", "abs", "sin", "cos", "tan",
              "arctan", "power", "square"):
    _SAFE_FUNCS[_name] = getattr(np, _name)


def eval_target(
    expr: str,
    params: dict[str, Any],
    constants: dict[str, float] | None = None,
) -> Any:
    """计算公式。``params`` 的值可以是标量，也可以是数组（用于蒙特卡洛向量化）。"""
    context = dict(_SAFE_FUNCS)
    context.update(constants or {})
    context.update(params)
    try:
        return eval(expr, {"__builtins__": {}}, context)  # noqa: S307 - 本地模板
    except Exception as exc:  # noqa: BLE001
        raise TemplateError(f"公式 {expr!r} 计算失败：{exc}") from exc


def _require(mapping: dict, key: str, where: str) -> Any:
    if key not in mapping:
        raise TemplateError(f"{where} 缺少字段 {key!r}")
    return mapping[key]


def _parse_variable(raw: dict, where: str) -> Variable:
    name = str(_require(raw, "name", where))
    unit = str(raw.get("unit", ""))
    aliases = tuple(str(a) for a in raw.get("aliases", []))
    return Variable(name=name, unit=unit, aliases=aliases)


def load_template(path: Path) -> Template:
    """读取并校验收一个 JSON 模板。"""
    where = str(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TemplateError(f"{where} 不是合法 JSON：{exc}") from exc

    template_id = str(_require(data, "id", where))
    model = str(_require(data, "model", where))
    if model not in SUPPORTED_MODELS:
        raise TemplateError(f"{where} 的 model 必须是 {SUPPORTED_MODELS}，现在是 {model!r}")

    variables = _require(data, "variables", where)
    x = _parse_variable(_require(variables, "x", f"{where}.variables"), f"{where}.variables.x")
    y = _parse_variable(_require(variables, "y", f"{where}.variables"), f"{where}.variables.y")

    target_raw = _require(data, "target", where)
    expr = str(_require(target_raw, "expr", f"{where}.target"))
    try:
        compile(expr, "<target>", "eval")
    except SyntaxError as exc:
        raise TemplateError(f"{where} 的 target.expr 语法错误：{exc}") from exc

    target = Target(
        name=str(_require(target_raw, "name", f"{where}.target")),
        expr=expr,
        unit=str(target_raw.get("unit", "")),
        reference=float(target_raw["reference"]) if target_raw.get("reference") is not None else None,
    )

    instruments: list[Instrument] = []
    for i, item in enumerate(data.get("instruments", [])):
        sub = f"{where}.instruments[{i}]"
        instruments.append(
            Instrument(
                name=str(_require(item, "name", sub)),
                resolution=float(_require(item, "resolution", sub)),
                unit=str(item.get("unit", "")),
                variable=str(item.get("variable", "y")),
            )
        )

    constants = {str(k): float(v) for k, v in data.get("constants", {}).items()}

    y_transform = str(data.get("y_transform", "none"))
    if y_transform not in SUPPORTED_TRANSFORMS:
        raise TemplateError(f"{where} 的 y_transform 必须是 {SUPPORTED_TRANSFORMS}")

    demo = _require(data, "demo", where)
    demo_x = tuple(float(v) for v in _require(demo, "x", f"{where}.demo"))
    demo_y = tuple(float(v) for v in _require(demo, "y", f"{where}.demo"))
    if len(demo_x) != len(demo_y):
        raise TemplateError(f"{where} 的 demo.x 与 demo.y 长度不一致")
    if len(demo_x) < 3:
        raise TemplateError(f"{where} 的 demo 至少需要 3 组数据")

    return Template(
        id=template_id,
        name=str(_require(data, "name", where)),
        model=model,
        x=x,
        y=y,
        target=target,
        instruments=tuple(instruments),
        constants=constants,
        y_transform=y_transform,
        formula_text=str(data.get("formula_text", "")),
        notes=str(data.get("notes", "")),
        demo_x=demo_x,
        demo_y=demo_y,
        source=path,
    )


def load_templates(directory: Path) -> dict[str, Template]:
    """加载目录下所有 ``*.json`` 模板，返回 ``{id: Template}``。"""
    directory = Path(directory)
    if not directory.is_dir():
        raise TemplateError(f"模板目录不存在：{directory}")

    templates: dict[str, Template] = {}
    for path in sorted(directory.glob("*.json")):
        template = load_template(path)
        if template.id in templates:
            raise TemplateError(f"模板 id 重复：{template.id}")
        templates[template.id] = template

    if not templates:
        raise TemplateError(f"{directory} 里没有任何 .json 模板")
    return templates


def apply_transform(values: Any, transform: str) -> Any:
    """对 y 做预处理，例如牛顿环要把半径 r 平方成 r²。"""
    array = np.asarray(values, dtype=float)
    if transform == "square":
        return array ** 2
    if transform == "none":
        return array
    raise TemplateError(f"未知的 y_transform：{transform!r}")


def human_transform(transform: str, y_name: str) -> str:
    if transform == "square":
        return f"{y_name}²"
    return y_name
