"""实验数据台：大学物理实验拟合与不确定度工具（Streamlit 界面）。

运行：``streamlit run app.py``

界面按系统的 5 个功能组织：
① 选模板 → ② 数据 → ③ 拟合诊断 → ④ 不确定度 → ⑤ 导出报告
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from core import dataio, fit as fitmod, llm, report as reportmod  # noqa: E402
from core import store  # noqa: E402
from core import templates as tplmod  # noqa: E402
from core import uncertainty as unc  # noqa: E402
from core.units import UnitError, convert, format_measurement, units_for  # noqa: E402

REPORTS_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data"
REPORTS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="实验数据台", page_icon="📐", layout="wide")


@st.cache_data(show_spinner=False)
def load_all_templates() -> dict[str, tplmod.Template]:
    return tplmod.load_templates(ROOT / "templates" / "experiments")


def unit_options(unit: str) -> list[str]:
    options = units_for(unit)
    if options:
        return options
    return [unit] if unit else ["1"]


def convert_series(values, from_unit: str, to_unit: str) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if not from_unit or not to_unit or from_unit == to_unit:
        return array
    if from_unit == "1" or to_unit == "1":
        return array
    return np.asarray([convert(v, from_unit, to_unit) for v in array], dtype=float)


def unit_label(unit: str) -> str:
    return unit if unit else "—"


def make_figures(result: fitmod.FitResult, template: tplmod.Template):
    """画拟合图和残差图，返回 (用于展示的合并图, [拟合图路径, 残差图路径])。"""
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None, []

    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    x_min, x_max = float(result.x.min()), float(result.x.max())
    if template.model == "power":
        x_min = max(x_min, 1e-12)
    xs = np.linspace(x_min, x_max, 200)

    y_label = tplmod.human_transform(template.y_transform, template.y.name)
    y_unit = template.y.unit
    if template.y_transform == "square" and y_unit:
        y_unit = f"{y_unit}²"
    x_label = f"{template.x.name} / {unit_label(template.x.unit)}"
    y_full_label = f"{y_label} / {unit_label(y_unit)}"

    # 用于界面展示的合并图
    fig, (ax_fit, ax_resid) = plt.subplots(1, 2, figsize=(10.5, 3.8))

    ax_fit.scatter(result.x, result.y, s=22, color="#1f77b4", label="实验数据", zorder=3)
    ax_fit.plot(xs, fitmod.curve(result, xs), color="#d62728", lw=1.8, label="拟合曲线")
    ax_fit.set_xlabel(x_label)
    ax_fit.set_ylabel(y_full_label)
    ax_fit.legend(frameon=False)
    ax_fit.grid(alpha=0.25)

    ax_resid.axhline(0.0, color="#888888", lw=1)
    ax_resid.scatter(result.x, result.resid, s=22, color="#2ca02c")
    ax_resid.set_xlabel(x_label)
    ax_resid.set_ylabel("残差")
    ax_resid.grid(alpha=0.25)

    fig.tight_layout()

    # 用于 Word 报告的两张独立图
    fig_fit, single = plt.subplots(figsize=(6.4, 4.0))
    single.scatter(result.x, result.y, s=22, color="#1f77b4", label="实验数据", zorder=3)
    single.plot(xs, fitmod.curve(result, xs), color="#d62728", lw=1.8, label="拟合曲线")
    single.set_xlabel(x_label)
    single.set_ylabel(y_full_label)
    single.legend(frameon=False)
    single.grid(alpha=0.25)
    fig_fit.tight_layout()

    fig_resid, single = plt.subplots(figsize=(6.4, 3.4))
    single.axhline(0.0, color="#888888", lw=1)
    single.scatter(result.x, result.resid, s=22, color="#2ca02c")
    single.set_xlabel(x_label)
    single.set_ylabel("残差")
    single.grid(alpha=0.25)
    fig_resid.tight_layout()

    stamp = f"{template.id}_{int(result.n)}"
    fit_path = REPORTS_DIR / f"fit_{stamp}.png"
    resid_path = REPORTS_DIR / f"resid_{stamp}.png"
    fig_fit.savefig(fit_path, dpi=200, bbox_inches="tight")
    fig_resid.savefig(resid_path, dpi=200, bbox_inches="tight")
    return fig, [fit_path, resid_path]


def make_histogram(fast: unc.MCResult, strict: unc.MCResult):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None, None

    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS", "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    ax.hist(fast.samples, bins=60, density=True, alpha=0.55,
            label=f"参数抽样（u={fast.u:.3g}）", color="#1f77b4")
    ax.hist(strict.samples, bins=40, density=True, alpha=0.55,
            label=f"仪器加噪（u={strict.u:.3g}）", color="#ff7f0e")
    ax.set_xlabel("目标量")
    ax.set_ylabel("概率密度")
    ax.legend(frameon=False)
    ax.grid(alpha=0.25)
    fig.tight_layout()

    path = REPORTS_DIR / "uncertainty_hist.png"
    fig.savefig(path, dpi=200, bbox_inches="tight")
    return fig, path


def reset_for_template(template_id: str) -> None:
    if st.session_state.get("template_id") != template_id:
        st.session_state["template_id"] = template_id
        for key in (
            "fit", "unc", "x", "y_raw", "figures", "hist_path", "ai_text",
            "fit_figure", "hist_figure", "run_id", "upload_signature", "report_path",
        ):
            st.session_state.pop(key, None)
        st.session_state["raw_text"] = ""


try:
    TEMPLATES = load_all_templates()
except Exception as exc:  # noqa: BLE001
    st.error(f"模板加载失败：{exc}")
    st.stop()

if not TEMPLATES:
    st.error("没有找到任何实验模板，请检查 templates/experiments/ 目录。")
    st.stop()

# ---------------- 侧边栏 ----------------
st.sidebar.title("📐 实验数据台")
st.sidebar.caption("大物实验：拟合 · 不确定度 · 报告")

template_id = st.sidebar.selectbox(
    "① 选择实验模板",
    options=list(TEMPLATES),
    format_func=lambda key: TEMPLATES[key].name,
)
reset_for_template(template_id)
template = TEMPLATES[template_id]

with st.sidebar.expander("模板说明", expanded=False):
    st.markdown(f"**公式**：{template.formula_text}")
    st.markdown(f"**注意**：{template.notes}")
    st.markdown(f"**模型**：{fitmod.MODEL_LABELS.get(template.model, template.model)}")

constants: dict[str, float] = {}
if template.constants:
    st.sidebar.markdown("**常数（可修改）**")
    for name, value in template.constants.items():
        constants[name] = float(
            st.sidebar.number_input(name, value=float(value), format="%.6g")
        )

st.sidebar.divider()
n_mc = st.sidebar.select_slider(
    "蒙特卡洛抽样次数", options=[1000, 2000, 5000, 10000, 20000], value=10000
)
confidence = st.sidebar.selectbox("置信水平", options=[0.95, 0.99], index=0)
seed = int(st.sidebar.number_input("随机种子", value=2024, step=1, min_value=0))

st.title("实验数据台")
st.caption("把实验数据变成“结果 ± 不确定度”的规范报告：拟合、误差评定、一键导出 Word。")

tab_data, tab_fit, tab_unc, tab_report = st.tabs(
    ["② 数据", "③ 拟合诊断", "④ 不确定度", "⑤ 导出报告"]
)

# ---------------- ② 数据 ----------------
with tab_data:
    st.subheader("录入数据")
    col_unit_x, col_unit_y, col_demo = st.columns([1, 1, 1])

    x_options = unit_options(template.x.unit)
    y_options = unit_options(template.y.unit)
    x_index = x_options.index(template.x.unit) if template.x.unit in x_options else 0
    y_index = y_options.index(template.y.unit) if template.y.unit in y_options else 0

    x_unit = col_unit_x.selectbox(f"{template.x.name} 单位", x_options, index=x_index)
    y_unit = col_unit_y.selectbox(f"{template.y.name} 单位", y_options, index=y_index)

    if col_demo.button("载入示例数据", use_container_width=True):
        st.session_state["raw_text"] = "\n".join(
            f"{x:.10g},{y:.10g}" for x, y in template.demo_rows
        )
        st.session_state.pop("fit", None)
        st.session_state.pop("unc", None)

    upload = st.file_uploader("或者上传 CSV 文件（先上传，再在下面核对文本）", type=["csv", "txt"])
    if upload is not None:
        signature = f"{upload.name}:{upload.size}"
        if st.session_state.get("upload_signature") != signature:
            try:
                st.session_state["raw_text"] = dataio.decode_bytes(upload.getvalue())
                st.session_state["upload_signature"] = signature
            except dataio.DataError as exc:
                st.error(str(exc))

    st.text_area(
        "粘贴两列数据（逗号/空格/制表符分隔，可带表头）",
        key="raw_text",
        height=190,
        placeholder="0.40,1.27\n0.60,1.56\n0.80,1.80",
    )

    if st.button("解析数据", type="primary"):
        try:
            x_raw, y_raw = dataio.parse_pairs(st.session_state.get("raw_text", ""))
            x_si = convert_series(x_raw, x_unit, template.x.unit)
            y_si = convert_series(y_raw, y_unit, template.y.unit)
            st.session_state["x"] = x_si
            st.session_state["y_raw"] = y_si
            st.session_state.pop("fit", None)
            st.session_state.pop("unc", None)
            st.success(f"已解析 {x_si.size} 组数据。")
        except (dataio.DataError, UnitError) as exc:
            st.error(str(exc))

    if "x" in st.session_state:
        x_values = st.session_state["x"]
        y_values = st.session_state["y_raw"]
        st.dataframe(
            {
                f"{template.x.name} ({unit_label(template.x.unit)})": x_values,
                f"{template.y.name} ({unit_label(template.y.unit)})": y_values,
            },
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "下载这两列数据（CSV）",
            data=dataio.to_csv_text(x_values, y_values, "x", "y"),
            file_name=f"{template.id}_data.csv",
            mime="text/csv",
        )
    else:
        st.info("粘数据后点“解析数据”。没有数据可以先点“载入示例数据”。")

# ---------------- ③ 拟合 ----------------
with tab_fit:
    st.subheader("拟合与诊断")
    if "x" not in st.session_state:
        st.info("先在“② 数据”里解析数据。")
    else:
        if st.button("开始拟合", type="primary"):
            y_fit = tplmod.apply_transform(st.session_state["y_raw"], template.y_transform)
            try:
                result = fitmod.fit(template.model, st.session_state["x"], y_fit)
                st.session_state["fit"] = result
                st.session_state.pop("unc", None)
                figure, figure_paths = make_figures(result, template)
                st.session_state["figures"] = figure_paths
                st.session_state["fit_figure"] = figure
            except fitmod.FitError as exc:
                st.error(str(exc))

        result = st.session_state.get("fit")
        if result is not None:
            col_r2, col_chi, col_n = st.columns(3)
            col_r2.metric("R²", f"{result.r2:.5f}")
            col_chi.metric("约化卡方", f"{result.chi2_red:.4g}")
            col_n.metric("数据点", str(result.n))

            st.dataframe(
                [
                    {"参数": name, "估计值": float(value), "标准误": float(error)}
                    for name, value, error in zip(
                        result.param_names, result.params, result.se
                    )
                ],
                use_container_width=True,
                hide_index=True,
            )

            if result.model in ("power", "exponential"):
                b_index = result.param_names.index("b")
                st.caption(f"提示：b 的估计值为 {result.params[b_index]:.5g}，可与理论值对照，检查数据质量。")

            figure = st.session_state.get("fit_figure")
            if figure is not None:
                st.pyplot(figure, use_container_width=True)
            else:
                st.warning("没有安装 matplotlib，图暂时不显示；不影响计算和导出报告（报告里也没有图）。")
        else:
            st.info("点“开始拟合”运行最小二乘。")

# ---------------- ④ 不确定度 ----------------
with tab_unc:
    st.subheader("不确定度评定")
    result = st.session_state.get("fit")
    if result is None:
        st.info("先完成“③ 拟合诊断”。")
    else:
        st.markdown("**仪器与 B 类评定**")
        instrument_rows = [
            {
                "仪器": item.name,
                "分辨率": item.resolution,
                "单位": unit_label(item.unit),
                "对应变量": template.x.name if item.variable == "x" else template.y.name,
            }
            for item in template.instruments
        ]
        if instrument_rows:
            st.dataframe(instrument_rows, use_container_width=True, hide_index=True)

        y_instrument = next(
            (item for item in template.instruments if item.variable == "y"), None
        )
        default_u = unc.u_b_resolution(y_instrument.resolution) if y_instrument else 0.0
        u_y = float(
            st.number_input(
                f"{template.y.name} 的仪器标准不确定度 u（默认按分辨率/2/√3）",
                min_value=0.0,
                value=float(default_u),
                format="%.4g",
                help="由仪器分辨率换算得到；如果已知仪器精度等级，可以手动改。",
            )
        )

        if st.button("计算不确定度", type="primary"):
            try:
                def eval_scalar(params, t=template, names=result.param_names):
                    return float(
                        tplmod.eval_target(
                            t.target.expr, dict(zip(names, params)), constants
                        )
                    )

                def eval_vector(columns, t=template):
                    return tplmod.eval_target(t.target.expr, columns, constants)

                gum_result = unc.gum(result, eval_scalar)
                fast = unc.mc_fast(
                    result, eval_vector, n=n_mc, confidence=confidence, seed=seed
                )
                strict_n = min(2000, max(200, n_mc // 5))
                strict = unc.mc_strict(
                    template.model,
                    result.x,
                    st.session_state["y_raw"],
                    u_y,
                    template.y_transform,
                    eval_scalar,
                    n=strict_n,
                    confidence=confidence,
                    seed=seed,
                )
                total = unc.budget(gum_result["u"], strict.u)
                histogram, hist_path = make_histogram(fast, strict)

                st.session_state["unc"] = {
                    "value": gum_result["value"],
                    "u_stat": gum_result["u"],
                    "u_mc_fast": fast.u,
                    "u_b": strict.u,
                    "u_c": total["u_c"],
                    "U": total["U"],
                    "n_mc": fast.n,
                    "n_mc_strict": strict.n,
                    "confidence": confidence,
                    "hist_sample_fast": fast.samples,
                    "hist_sample_strict": strict.samples,
                    "hist_path": hist_path,
                }
                st.session_state["hist_figure"] = histogram
                try:
                    st.session_state["run_id"] = store.save_run(
                        template_id=template.id,
                        model=result.model,
                        n_points=result.n,
                        params=result.param_dict(),
                        cov=result.cov,
                        summary={
                            "value": float(gum_result["value"]),
                            "u_stat": float(gum_result["u"]),
                            "u_mc_fast": float(fast.u),
                            "u_b": float(strict.u),
                            "u_c": float(total["u_c"]),
                            "U": float(total["U"]),
                            "n_mc": float(fast.n),
                            "n_mc_strict": float(strict.n),
                            "confidence": float(confidence),
                        },
                    )
                except Exception as exc:  # noqa: BLE001
                    st.session_state["run_id"] = None
                    st.warning(f"结果未写入本地数据库：{exc}")
            except (unc.UncertaintyError, tplmod.TemplateError) as exc:
                st.error(str(exc))

        summary = st.session_state.get("unc")
        if summary:
            st.dataframe(
                [
                    ["拟合统计不确定度（GUM 线性传播）", f"{summary['u_stat']:.4g}", "k=1"],
                    ["蒙特卡洛快速校验", f"{summary['u_mc_fast']:.4g}",
                     f"{summary['n_mc']} 次抽样"],
                    ["仪器 B 类不确定度（蒙特卡洛重拟合）", f"{summary['u_b']:.4g}",
                     f"{summary['n_mc_strict']} 次重拟合"],
                    ["合成标准不确定度 u_c", f"{summary['u_c']:.4g}", "平方和"],
                    ["扩展不确定度 U（k=2）", f"{summary['U']:.4g}",
                     f"约 {summary['confidence']:.0%}"],
                ],
                use_container_width=True,
                hide_index=True,
            )

            st.markdown(
                f"### {template.target.name} = "
                f"{format_measurement(summary['value'], summary['U'])} "
                f"{template.target.unit}"
            )

            if template.target.reference is not None:
                reference = float(template.target.reference)
                deviation = abs(summary["value"] - reference) / abs(reference)
                st.caption(
                    f"参考值 {reference:g} {template.target.unit}，"
                    f"相对偏差 {deviation:.2%}。"
                )

            st.caption(
                "GUM 与蒙特卡洛快速结果接近，说明线性传播可信；"
                "两者差得越多，说明模型非线性越强，应以蒙特卡洛为准。"
            )

            hist_figure = st.session_state.get("hist_figure")
            if hist_figure is not None:
                st.pyplot(hist_figure, use_container_width=True)

# ---------------- ⑤ 报告 ----------------
with tab_report:
    st.subheader("导出 Word 报告")
    summary = st.session_state.get("unc")
    result = st.session_state.get("fit")
    if result is None or summary is None:
        st.info("先完成拟合和不确定度计算，再导出报告。")
    else:
        st.markdown("**AI 误差分析（可选）**")
        if llm.is_configured():
            st.caption("已检测到 LLM_API_KEY。模型只写文字，数字由程序提供并做回查。")
        else:
            st.caption("未配置 LLM_API_KEY：AI 按钮不可用，其余功能不受影响。")

        if st.button("让 AI 写一段误差分析", disabled=not llm.is_configured()):
            prompt = (
                f"实验：{template.name}\n"
                f"模型：{result.model}\n"
                f"参数：{dict(zip(result.param_names, np.round(result.params, 6)))}\n"
                f"目标量：{template.target.name} = {summary['value']:.6g} {template.target.unit}\n"
                f"统计不确定度 u_stat = {summary['u_stat']:.4g}\n"
                f"仪器 B 类不确定度 u_B = {summary['u_b']:.4g}\n"
                f"合成不确定度 u_c = {summary['u_c']:.4g}\n"
                f"扩展不确定度 U = {summary['U']:.4g}\n"
                f"R² = {result.r2:.5f}\n"
                "请用 150 字以内写误差分析，只能使用上面出现的数字。"
            )
            try:
                text = llm.chat(prompt)
                allowed = [
                    summary["value"], summary["u_stat"], summary["u_b"],
                    summary["u_c"], summary["U"], result.r2,
                ]
                unknown = llm.unknown_numbers(text, allowed)
                st.session_state["ai_text"] = text
                if unknown:
                    st.warning(f"AI 文本里出现了结果之外的数字：{unknown}，请人工核对。")
            except llm.LLMError as exc:
                st.error(str(exc))

        ai_text = st.text_area(
            "报告里的“误差分析”段落（可手改，也可留空用默认文字）",
            value=st.session_state.get("ai_text", ""),
            height=140,
        )

        if st.button("生成 Word 报告", type="primary"):
            figures = st.session_state.get("figures", [])
            hist_path = summary.get("hist_path")
            if hist_path:
                figures = list(figures) + [hist_path]

            report_summary = {
                **summary,
                "y_raw": list(st.session_state.get("y_raw", [])),
            }
            path = REPORTS_DIR / f"report_{template.id}.docx"
            try:
                reportmod.build_report(
                    path,
                    template=template,
                    fit_result=result,
                    summary=report_summary,
                    figures=[Path(p) for p in figures if Path(p).exists()],
                    ai_text=ai_text,
                )
                st.success(f"已生成：{path.name}")
                st.session_state["report_path"] = str(path)
                run_id = st.session_state.get("run_id")
                if run_id:
                    try:
                        store.save_report(int(run_id), path)
                    except Exception as exc:  # noqa: BLE001
                        st.warning(f"报告已生成，但数据库记录失败：{exc}")
            except Exception as exc:  # noqa: BLE001
                st.error(f"生成失败：{exc}")

        report_path = st.session_state.get("report_path")
        if report_path and Path(report_path).exists():
            st.download_button(
                "下载 Word 报告",
                data=Path(report_path).read_bytes(),
                file_name=f"{template.name}_实验报告.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

st.divider()
st.caption(
    "数据与报告只保存在本地 data/ 和 reports/ 目录（已在 .gitignore 中排除）。"
    "本项目不收集任何个人信息。"
)
