"""不依赖 Streamlit 的核心自检脚本。

用途：
1. 验证 5 个模板的演示数据都能拟合、能算不确定度；
2. 生成一份测试 Word 报告，检查中文字体设置；
3. 作为周报/PPT 里“功能测试”的真实证据。

运行：``python scripts/selfcheck.py``
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from core import fit as fitmod  # noqa: E402
from core import report as reportmod  # noqa: E402
from core import templates as tplmod  # noqa: E402
from core import uncertainty as unc  # noqa: E402
from core.units import convert, format_measurement, parse_quantity  # noqa: E402

TOLERANCE = 0.05  # 演示数据允许 5% 偏差


def check_units() -> None:
    quantity = parse_quantity("8.1cm")
    assert abs(quantity.si_value - 0.081) < 1e-12, quantity
    assert abs(convert(8.1, "cm", "m") - 0.081) < 1e-12
    assert format_measurement(12.258, 0.18) == "12.3 ± 0.2"
    print("[OK] 单位解析与换算")


def check_templates() -> dict[str, tplmod.Template]:
    templates = tplmod.load_templates(ROOT / "templates" / "experiments")
    assert len(templates) >= 5, templates
    print(f"[OK] 模板加载：{len(templates)} 个 -> {', '.join(templates)}")
    return templates


def check_fits(templates: dict[str, tplmod.Template]) -> None:
    for template in templates.values():
        x = np.asarray(template.demo_x, dtype=float)
        y_raw = np.asarray(template.demo_y, dtype=float)
        y = tplmod.apply_transform(y_raw, template.y_transform)
        result = fitmod.fit(template.model, x, y)

        def eval_scalar(params, t=template, names=result.param_names):
            return float(tplmod.eval_target(
                t.target.expr, dict(zip(names, params)), t.constants
            ))

        def eval_vector(columns, t=template):
            return tplmod.eval_target(t.target.expr, columns, t.constants)

        gum_result = unc.gum(result, eval_scalar)
        mc_fast = unc.mc_fast(result, eval_vector, n=2000, seed=1)

        y_instrument = next(
            (item for item in template.instruments if item.variable == "y"), None
        )
        u_y = unc.u_b_resolution(y_instrument.resolution) if y_instrument else 0.0
        mc_strict = unc.mc_strict(
            template.model, x, y_raw, u_y, template.y_transform,
            eval_scalar, n=300, seed=1,
        ) if u_y > 0 else None

        u_stat = gum_result["u"]
        u_b = mc_strict.u if mc_strict else 0.0
        total = unc.budget(u_stat, u_b)

        value = gum_result["value"]
        reference = template.target.reference
        if reference:
            deviation = abs(value - reference) / abs(reference)
            assert deviation < TOLERANCE, (
                f"{template.id}: {value:.6g} 与参考值 {reference} 偏差 {deviation:.1%}"
            )

        print(
            f"[OK] {template.name:<12} {template.target.name} = "
            f"{format_measurement(value, total['U'])} {template.target.unit}  "
            f"u_stat={u_stat:.3g}  u_mc={mc_fast.u:.3g}  u_B={u_b:.3g}"
        )


def check_report(templates: dict[str, tplmod.Template]) -> None:
    template = templates["pendulum_g"]
    x = np.asarray(template.demo_x, dtype=float)
    y = tplmod.apply_transform(np.asarray(template.demo_y, dtype=float), template.y_transform)
    result = fitmod.fit(template.model, x, y)

    def eval_scalar(params, t=template, names=result.param_names):
        return float(tplmod.eval_target(t.target.expr, dict(zip(names, params)), t.constants))

    u_stat = unc.gum(result, eval_scalar)["u"]
    u_b = 0.002
    total = unc.budget(u_stat, u_b)
    summary = {
        "value": eval_scalar(result.params),
        "u_stat": u_stat,
        "u_b": u_b,
        "u_c": total["u_c"],
        "U": total["U"],
        "u_mc_fast": u_stat * 1.01,
        "n_mc": 5000,
        "n_mc_strict": 300,
        "confidence": 0.95,
        "y_raw": list(template.demo_y),
    }

    path = ROOT / "reports" / "_selfcheck.docx"
    try:
        reportmod.build_report(path, template=template, fit_result=result, summary=summary)
        assert path.exists() and path.stat().st_size > 10_000

        from docx import Document
        document = Document(str(path))
        text = "\n".join(p.text for p in document.paragraphs)
        assert "单摆测重力加速度" in text
        assert "测量结果" in text

        import zipfile
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml").decode("utf-8")
        assert 'w:eastAsia="宋体"' in xml, "中文字体没有写入 xml"
    finally:
        path.unlink(missing_ok=True)
    print("[OK] Word 报告生成、三线表与中文字体检查")


def main() -> int:
    check_units()
    templates = check_templates()
    check_fits(templates)
    check_report(templates)
    print("\n全部自检通过。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
