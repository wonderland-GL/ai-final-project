"""导出 Word 实验报告。

排版约定：
- 正文中文宋体、西文 Times New Roman，10.5 pt；
- 表格使用三线表（上下粗线 + 表头下细线，无竖线）；
- 所有数字来自本次运行结果，AI 只负责"误差分析"那段文字。

注意：python-docx 里中文字体必须单独设置 ``w:eastAsia``，
否则导出的 Word 会变成默认字体 —— 这是我们踩过的坑。
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from .templates import Template, human_transform
from .units import format_measurement


def _set_run_font(run, size: float = 10.5, bold: bool = False,
                  chinese: str = "宋体", latin: str = "Times New Roman") -> None:
    run.font.name = latin
    run.font.size = Pt(size)
    run.bold = bold
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:eastAsia"), chinese)
    rfonts.set(qn("w:ascii"), latin)
    rfonts.set(qn("w:hAnsi"), latin)


def _paragraph(doc, text: str = "", size: float = 10.5, bold: bool = False,
               align=None, space_after: float = 6.0):
    paragraph = doc.add_paragraph()
    if align is not None:
        paragraph.alignment = align
    paragraph.paragraph_format.space_after = Pt(space_after)
    paragraph.paragraph_format.line_spacing = 1.25
    run = paragraph.add_run(text)
    _set_run_font(run, size=size, bold=bold)
    return paragraph


def _section(doc, title: str) -> None:
    _paragraph(doc, title, size=12, bold=True, space_after=4.0)


def _set_outer_borders(table) -> None:
    """表格上下粗线，其余全部去掉。"""
    tbl_pr = table._tbl.tblPr
    for old in tbl_pr.findall(qn("w:tblBorders")):
        tbl_pr.remove(old)

    borders = OxmlElement("w:tblBorders")
    spec = (("top", 12, "single"), ("bottom", 12, "single"),
            ("left", 0, "nil"), ("right", 0, "nil"),
            ("insideH", 0, "nil"), ("insideV", 0, "nil"))
    for edge, size, value in spec:
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), value)
        if value == "single":
            element.set(qn("w:sz"), str(size))
            element.set(qn("w:space"), "0")
            element.set(qn("w:color"), "000000")
        borders.append(element)
    tbl_pr.append(borders)


def _set_row_bottom_border(row, size: int = 6) -> None:
    """表头下加一条细线。"""
    for cell in row.cells:
        tc_pr = cell._tc.get_or_add_tcPr()
        for old in tc_pr.findall(qn("w:tcBorders")):
            tc_pr.remove(old)
        borders = OxmlElement("w:tcBorders")
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single")
        bottom.set(qn("w:sz"), str(size))
        bottom.set(qn("w:space"), "0")
        bottom.set(qn("w:color"), "000000")
        borders.append(bottom)
        tc_pr.append(borders)


def _add_table(doc, headers: list[str], rows: list[list[str]]):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True

    header_cells = table.rows[0].cells
    for index, header in enumerate(headers):
        header_cells[index].text = ""
        paragraph = header_cells[index].paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _set_run_font(paragraph.add_run(str(header)), size=10.5, bold=True)

    for row_values in rows:
        cells = table.add_row().cells
        for index, value in enumerate(row_values):
            cells[index].text = ""
            paragraph = cells[index].paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _set_run_font(paragraph.add_run(str(value)), size=10.5)

    _set_outer_borders(table)
    _set_row_bottom_border(table.rows[0])
    return table


def _fmt(value: float, digits: int = 6) -> str:
    return f"{float(value):.{digits}g}"


def build_report(
    path: str | Path,
    *,
    template: Template,
    fit_result,
    summary: dict[str, Any],
    figures: list[Path] | None = None,
    ai_text: str = "",
) -> Path:
    """生成报告，返回文件路径。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    doc = Document()
    for section in doc.sections:
        section.top_margin = Cm(2.2)
        section.bottom_margin = Cm(2.2)
        section.left_margin = Cm(2.6)
        section.right_margin = Cm(2.6)

    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(10.5)

    # 标题
    _paragraph(doc, f"{template.name} 实验数据报告", size=16, bold=True,
               align=WD_ALIGN_PARAGRAPH.CENTER, space_after=12)

    # 一、实验信息
    _section(doc, "一、实验信息")
    _add_table(
        doc,
        ["项目", "内容"],
        [
            ["实验名称", template.name],
            ["拟合模型", fit_result.model],
            ["目标量", f"{template.target.name}（{template.target.unit}）"],
            ["数据点数", str(fit_result.n)],
            ["报告日期", date.today().isoformat()],
        ],
    )

    # 二、数据与拟合
    _section(doc, "二、原始数据与拟合结果")
    y_label = human_transform(template.y_transform, template.y.name)
    headers = [template.x.name, template.y.name, y_label, "拟合值", "残差"]
    data_rows: list[list[str]] = []
    for index in range(fit_result.n):
        raw_y = summary.get("y_raw", [])
        transformed = fit_result.y[index]
        row = [
            _fmt(fit_result.x[index]),
            _fmt(raw_y[index]) if index < len(raw_y) else "",
            _fmt(transformed),
            _fmt(fit_result.yhat[index]),
            _fmt(fit_result.resid[index]),
        ]
        data_rows.append(row)
    _add_table(doc, headers, data_rows)

    _paragraph(doc, "")
    _paragraph(
        doc,
        f"拟合优度：R² = {fit_result.r2:.5f}，约化卡方 = {fit_result.chi2_red:.4g}，"
        f"自由度 = {fit_result.dof}。",
    )

    # 三、拟合参数
    _section(doc, "三、拟合参数")
    param_rows = []
    for name, value, error in zip(fit_result.param_names, fit_result.params, fit_result.se):
        param_rows.append([name, _fmt(value), _fmt(error)])
    _add_table(doc, ["参数", "估计值", "标准误"], param_rows)

    # 四、不确定度
    _section(doc, "四、不确定度评定")
    confidence = float(summary.get("confidence", 0.95))
    uncertainty_rows = [
        ["拟合统计不确定度（GUM 线性传播）", _fmt(summary["u_stat"]),
         f"由参数协方差传播，k=1"],
        ["仪器 B 类不确定度（蒙特卡洛重拟合）", _fmt(summary["u_b"]),
         f"{summary.get('n_mc_strict', 0)} 次重拟合"],
        ["蒙特卡洛快速校验", _fmt(summary.get("u_mc_fast", float('nan'))),
         f"{summary.get('n_mc', 0)} 次抽样，应与第一行接近"],
        ["合成标准不确定度 u_c", _fmt(summary["u_c"]), "平方和合成"],
        ["扩展不确定度 U（k=2）", _fmt(summary["U"]), f"置信水平约 {confidence:.0%}"],
    ]
    _add_table(doc, ["来源", "标准不确定度", "说明"], uncertainty_rows)

    # 五、结果
    _section(doc, "五、测量结果")
    result_text = (
        f"{template.target.name} = {format_measurement(summary['value'], summary['U'])} "
        f"{template.target.unit}"
    )
    _paragraph(doc, result_text, size=12, bold=True)
    _paragraph(
        doc,
        "注：结果按“不确定度保留 1 位有效数字、末位对齐”的规则表示；"
        "U 为扩展不确定度（k=2）。",
        size=9,
    )

    # 六、图
    if figures:
        _section(doc, "六、图表")
        captions = ["图 1  拟合曲线", "图 2  残差分布", "图 3  不确定度分布"]
        for index, figure in enumerate(figures):
            figure = Path(figure)
            if not figure.exists():
                continue
            doc.add_picture(str(figure), width=Cm(14))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
            caption = captions[index] if index < len(captions) else f"图 {index + 1}"
            _paragraph(doc, caption, size=9, align=WD_ALIGN_PARAGRAPH.CENTER)

    # 七、误差分析
    _section(doc, "七、误差分析")
    default_text = (
        "本报告的拟合与不确定度均由程序计算：拟合采用最小二乘，"
        "统计不确定度由参数协方差按 GUM 线性传播得到；仪器 B 类不确定度"
        "通过对原始数据加噪并重复拟合（蒙特卡洛）估计；两者按平方和合成。"
        "若快速蒙特卡洛与线性传播结果接近，说明模型在参数附近近似线性，"
        "线性传播可信；若差异明显，应以蒙特卡洛结果为准。"
    )
    _paragraph(doc, ai_text.strip() or default_text)

    doc.save(path)
    return path
