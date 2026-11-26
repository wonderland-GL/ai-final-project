"""生成第 14 周进展报告（DOCX）与配图。

运行：python docs/weekly/build_week14.py
输出：docs/weekly/第14周进展报告.docx
      docs/weekly/fig_fit.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import fit as fitmod  # noqa: E402
from core import templates as tplmod  # noqa: E402

OUT_DIR = Path(__file__).resolve().parent
FIG_PATH = OUT_DIR / "fig_fit.png"
DOCX_PATH = OUT_DIR / "第14周进展报告.docx"

FONT_CN = "C:/Windows/Fonts/msyh.ttc"
FONT_CN_BOLD = "C:/Windows/Fonts/msyhbd.ttc"


# ---------------------------------------------------------------- 图
def make_figure() -> tuple[float, float]:
    template = tplmod.load_templates(ROOT / "templates" / "experiments")["pendulum_g"]
    x = np.asarray(template.demo_x, dtype=float)
    y = np.asarray(template.demo_y, dtype=float)
    result = fitmod.fit(template.model, x, y)
    g = float(tplmod.eval_target(
        template.target.expr, dict(zip(result.param_names, result.params)), template.constants
    ))

    width, height = 1800, 1000
    left, right, top, bottom = 170, 60, 150, 120
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)

    x_min, x_max = 0.3, 1.3
    y_min, y_max = 1.1, 2.4

    def sx(value: float) -> float:
        return left + (value - x_min) / (x_max - x_min) * (width - left - right)

    def sy(value: float) -> float:
        return height - bottom - (value - y_min) / (y_max - y_min) * (height - top - bottom)

    title_font = ImageFont.truetype(FONT_CN_BOLD, 46)
    sub_font = ImageFont.truetype(FONT_CN, 30)
    label_font = ImageFont.truetype(FONT_CN, 34)
    tick_font = ImageFont.truetype(FONT_CN, 26)

    draw.text((left, 28), "单摆实验：T = a·L^b 拟合结果", font=title_font, fill="#1a1a1a")
    draw.text(
        (left, 90),
        f"g = {g:.2f} m/s²（参考 9.79）    R² = {result.r2:.5f}    n = {result.n}",
        font=sub_font,
        fill="#444444",
    )

    # 网格
    for i in range(6):
        value = 0.4 + 0.2 * i
        px = sx(value)
        draw.line([(px, top), (px, height - bottom)], fill="#e6e6e6", width=2)
        draw.text((px - 32, height - bottom + 16), f"{value:.1f}", font=tick_font, fill="#555555")
    for i in range(7):
        value = 1.2 + 0.2 * i
        py = sy(value)
        draw.line([(left, py), (width - right, py)], fill="#e6e6e6", width=2)
        draw.text((left - 78, py - 16), f"{value:.1f}", font=tick_font, fill="#555555")

    # 坐标轴
    draw.line([(left, top), (left, height - bottom)], fill="#222222", width=3)
    draw.line([(left, height - bottom), (width - right, height - bottom)], fill="#222222", width=3)

    # 拟合曲线
    xs = np.linspace(0.4, 1.2, 240)
    ys = fitmod.curve(result, xs)
    points = [(sx(float(a)), sy(float(b))) for a, b in zip(xs, ys)]
    draw.line(points, fill="#d62728", width=6, joint="curve")

    # 数据点
    for a, b in zip(x, y):
        cx, cy = sx(float(a)), sy(float(b))
        draw.ellipse([cx - 11, cy - 11, cx + 11, cy + 11], fill="#1f77b4", outline="white", width=4)

    # 图例
    draw.line([(width - 470, 74), (width - 400, 74)], fill="#d62728", width=6)
    draw.text((width - 390, 54), "拟合曲线", font=sub_font, fill="#333333")
    draw.ellipse([width - 470, 116, width - 448, 138], fill="#1f77b4", outline="white", width=3)
    draw.text((width - 390, 108), "实验数据", font=sub_font, fill="#333333")

    # 轴标题
    draw.text((width // 2 - 90, height - 62), "摆长 L / m", font=label_font, fill="#222222")
    draw.text((18, height // 2 - 40), "周期 T / s", font=label_font, fill="#222222")

    image.save(FIG_PATH, dpi=(220, 220))
    return g, float(result.r2)


# ---------------------------------------------------------------- DOCX 工具
from docx import Document  # noqa: E402
from docx.enum.table import WD_ALIGN_VERTICAL, WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT  # noqa: E402
from docx.enum.text import WD_ALIGN_PARAGRAPH  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Cm, Pt, RGBColor  # noqa: E402

BODY_FONT = "宋体"
HEAD_FONT = "黑体"
LATIN_FONT = "Times New Roman"
USABLE_WIDTH = 17.0


def set_run(run, size=10.5, bold=False, chinese=BODY_FONT, color=None):
    run.font.name = LATIN_FONT
    run.font.size = Pt(size)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = RGBColor(*color)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:eastAsia"), chinese)
    rfonts.set(qn("w:ascii"), LATIN_FONT)
    rfonts.set(qn("w:hAnsi"), LATIN_FONT)


def para(doc, text="", size=10.5, bold=False, indent=True, align=None,
         space_before=0, space_after=2, line=1.08, color=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing = line
    if indent:
        pf.first_line_indent = Cm(0.74)
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    set_run(run, size=size, bold=bold, color=color)
    return p


def heading(doc, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(7)
    pf.space_after = Pt(3)
    pf.keep_with_next = True
    run = p.add_run(text)
    set_run(run, size=11.5, bold=True, chinese=HEAD_FONT, color=(0x1F, 0x3A, 0x5F))
    return p


def horizontal_rule(p, color="1F3A5F", size=12):
    ppr = p._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), color)
    borders.append(bottom)
    ppr.append(borders)


def shade(cell, fill):
    tcpr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), fill)
    tcpr.append(shd)


def table_borders(table, color="C9D3E0", size=4):
    tblpr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), str(size))
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)
        borders.append(element)
    tblpr.append(borders)


def table_margins(table, top=25, bottom=25, left=70, right=70):
    tblpr = table._tbl.tblPr
    margins = OxmlElement("w:tblCellMar")
    for side, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        element = OxmlElement(f"w:{side}")
        element.set(qn("w:w"), str(value))
        element.set(qn("w:type"), "dxa")
        margins.append(element)
    tblpr.append(margins)


def add_table(doc, headers, rows, widths, size=9.0, align_center=None, keep_together=False):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    tblpr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblpr.append(layout)

    table_borders(table)
    table_margins(table)

    header_row = table.rows[0]
    trpr = header_row._tr.get_or_add_trPr()
    header_flag = OxmlElement("w:tblHeader")
    trpr.append(header_flag)

    for index, header in enumerate(headers):
        cell = header_row.cells[index]
        cell.width = Cm(widths[index])
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        set_run(p.add_run(str(header)), size=size, bold=True, chinese=HEAD_FONT)
        shade(cell, "E8EEF7")

    for row_values in rows:
        row = table.add_row()
        for index, value in enumerate(row_values):
            cell = row.cells[index]
            cell.width = Cm(widths[index])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            centered = align_center is None or index in align_center
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if centered else WD_ALIGN_PARAGRAPH.LEFT
            set_run(p.add_run(str(value)), size=size)

    for index, width in enumerate(widths):
        table.columns[index].width = Cm(width)

    # 禁止单行跨页断开
    for row in table.rows:
        trpr = row._tr.get_or_add_trPr()
        trpr.append(OxmlElement("w:cantSplit"))

    if keep_together:
        for row in table.rows[:-1]:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.keep_with_next = True

    return table


def screenshot_slot(doc, text):
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table_borders(table, color="A6A6A6", size=6)
    row = table.rows[0]
    row.height = Cm(4.0)
    row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
    cell = row.cells[0]
    cell.width = Cm(8.2)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    set_run(p.add_run(text), size=8.5, color=(0x80, 0x80, 0x80))


# ---------------------------------------------------------------- 报告
def build(g: float, r2: float) -> None:
    doc = Document()

    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(1.7)
    section.bottom_margin = Cm(1.6)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.header_distance = Cm(0.8)
    section.footer_distance = Cm(0.8)

    normal = doc.styles["Normal"]
    normal.font.name = LATIN_FONT
    normal.font.size = Pt(10.5)
    normal.paragraph_format.line_spacing = 1.08
    normal.paragraph_format.space_after = Pt(2)

    # 标题
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    set_run(p.add_run("第 14 周进展报告"), size=18, bold=True, chinese=HEAD_FONT,
            color=(0x14, 0x2B, 0x47))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    set_run(p.add_run("从选题到可运行 MVP：实验数据台（AI + 大学物理实验）"),
            size=11, bold=True, chinese=HEAD_FONT)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(5)
    set_run(p.add_run(
        "小组：计算机专业 2 人｜仓库：github.com/wonderland-GL/ai-final-project"
    ), size=8.5, color=(0x66, 0x66, 0x66))
    horizontal_rule(p)

    # 一、概览
    heading(doc, "一、本周概览")
    for text in (
        "• 本周目标：把第 13 周的选题做成能跑、能截图、能讲清的第一版。",
        "• 已完成：5 个实验模板、数据导入与单位换算、线性/幂/指数拟合、参数标准误与残差图；"
        "不确定度（GUM + 蒙特卡洛）与 Word 报告完成算法层并通过单测；23 个单元测试；GitHub 仓库与 CI。",
        "• 顺延：真实用户访谈（2 人）、真实实验数据对比、不确定度/报告界面联调，安排在第 15 周。",
        "• 一句话：MVP 已跑通，下周进入“误差评定 + 报告导出”。",
    ):
        para(doc, text, indent=False, space_after=1)

    # 二、背景
    heading(doc, "二、选题背景、目标用户与核心需求")
    para(doc,
         "大学物理实验的报告环节有一个固定痛点：实验能做完，数据却处理不好。非线性模型不会选、"
         "不会给初值；现成软件只给 R²，不给参数误差；B 类不确定度靠猜；有效数字和扩展不确定度"
         "的写法每次都要查。大量时间花在重复劳动上，而不是理解物理。")
    para(doc,
         "目标用户是物理、电子、机械、材料等专业修“大学物理实验”的大一、大二学生。他们需要的"
         "不是“替我做实验”，而是一个把数据变成规范结果的工具：输入两列数据，输出参数、误差、"
         "图和可直接交的报告。")
    para(doc,
         "新颖点在于垂直和规范：不做通用计算器，而是用“实验模板”把变量、单位、模型、目标公式"
         "和仪器固定下来；换一个实验只改配置、不改代码。模板来自本校实验项目，这是通用工具没有的部分。")

    add_table(
        doc,
        ["核心需求", "现状", "本周做法"],
        [
            ["不会选模型和初值", "只会套直线，非线性不收敛", "模板预设模型 + 对数线性化给初值"],
            ["只看到 R²", "软件不给参数标准误", "输出参数 ± 标准误，并画残差图"],
            ["报告格式反复调", "每次重画图、重排表", "模板化输出，第 15 周接 Word"],
        ],
        widths=[4.2, 6.2, 6.6],
        align_center=[],
    )

    # 三、功能
    heading(doc, "三、系统功能设计（第 14 周范围）")
    para(doc,
         "本周主线是 3 个功能，先把一条链跑通；不确定度与报告只做到算法层和单测，"
         "界面下周接入，避免同时铺开、做出三个半成品。")
    add_table(
        doc,
        ["功能", "输入", "处理", "输出"],
        [
            ["E1 模板库",
             "选择实验（单摆/弹簧/RC/伏安/牛顿环）",
             "读取 JSON：变量、单位、模型、目标公式、仪器",
             "自动填好的表单"],
            ["C1 数据与单位",
             "粘贴两列数据，或上传 CSV；选择单位",
             "解析 → 换算到 SI → 按模板做 y 变换（如 r→r²）",
             "规范数据表（可下载）"],
            ["C2 拟合与诊断",
             "两列数据 + 模型",
             "对数线性化初值 → 阻尼高斯-牛顿 → 协方差、残差、R²",
             "参数 ± 标准误、拟合图、残差图"],
        ],
        widths=[3.1, 4.4, 6.3, 3.2],
        align_center=[],
    )
    para(doc,
         "三个功能共用一条数据链：选模板 → 粘数据 → 拟合 → FitResult；下周的不确定度只消费这个结果对象。",
         size=9, color=(0x55, 0x55, 0x55))

    # 四、技术路线
    heading(doc, "四、技术路线与系统结构")
    para(doc,
         "Python 3.10 + Streamlit；拟合用 numpy 自实现阻尼高斯-牛顿，不依赖 scipy，便于讲清原理和调试；"
         "实验配置用 JSON；core/ 不 import streamlit，可以单独测试；SQLite 保存运行记录；报告用 python-docx 生成。")
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.left_indent = Cm(0.3)
    set_run(p.add_run(
        "app.py → dataio.parse_pairs → units.convert → templates.apply_transform → fit.fit → FitResult → 页面/报告"
    ), size=8.5, chinese=HEAD_FONT)
    para(doc,
         "这样第 15 周接不确定度时，只新增 uncertainty.py，不改拟合和数据层。")

    # 五、完成
    heading(doc, "五、本周完成与验证")
    add_table(
        doc,
        ["事项", "结果", "证据"],
        [
            ["实验模板", "5 个，切换模板不改代码", "templates/experiments/*.json"],
            ["拟合正确性", "5 组演示数据与参考值最大偏差 < 1%", "scripts/selfcheck.py 输出"],
            ["不确定度与报告", "GUM + 蒙特卡洛双模式 + docx 通过单测", "core/uncertainty.py、core/report.py"],
            ["单元测试", "23 个全部通过", "tests/test_core.py"],
            ["仓库与协作", "main 已推送，CI 已配置", "commit 1191967"],
        ],
        widths=[3.2, 7.6, 6.2],
        align_center=[],
    )
    para(doc,
         "验证方式：python -m unittest discover -s tests -t . -v；scripts/selfcheck.py 跑完 5 个模板并生成一份测试报告。",
         size=9, color=(0x55, 0x55, 0x55))

    doc.add_picture(str(FIG_PATH), width=Cm(12.8))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    doc.paragraphs[-1].paragraph_format.space_after = Pt(1)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    set_run(p.add_run(
        f"图 1  单摆实验拟合结果（由 core/fit.py 真实计算，g = {g:.2f} m/s²，R² = {r2:.5f}）"
    ), size=8.5, color=(0x66, 0x66, 0x66))

    # 六、AI
    heading(doc, "六、AI 辅助开发记录")
    para(doc,
         "大模型主要用在三件事：生成脚手架、核对公式、分析报错。我们定了一条规则：数字必须由代码产生，"
         "AI 只负责解释和写文字；生成后做数字回查，文中出现结果表以外的数字就人工核对。")
    add_table(
        doc,
        ["环节", "我们的提示（摘要）", "AI 输出与问题", "我们的处理"],
        [
            ["拟合协方差",
             "用 numpy 写最小二乘，并给出参数标准误",
             "用 RSS/n 估方差，自由度写成 n",
             "改为 n-2；增加与蒙特卡洛对照的测试，误差不再偏小"],
            ["模型选择",
             "如何判断该用直线还是指数",
             "建议看 R²，越高越好",
             "R² 会随模型灵活度虚高；改为看残差结构 + 物理约束（单摆 b≈0.5）"],
            ["编码问题",
             "CSV 读入报 UnicodeDecodeError",
             "建议统一用 utf-8",
             "Excel 导出实际是 GBK；改为 utf-8-sig→utf-8→gbk 依次尝试"],
        ],
        widths=[2.4, 4.6, 5.6, 4.4],
        align_center=[],
    )
    para(doc, "下面两个位置放真实对话与页面截图（截屏后粘贴，删除灰色提示文字）：",
         size=9, color=(0x55, 0x55, 0x55), indent=False)

    slot_table = doc.add_table(rows=1, cols=2)
    slot_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    slot_table.autofit = False
    for index, text in enumerate((
        "截图位 1：与 AI 讨论协方差自由度的对话",
        "截图位 2：第一版页面 + 拟合结果",
    )):
        cell = slot_table.rows[0].cells[index]
        cell.width = Cm(8.4)
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        set_run(p.add_run(text), size=8.5, color=(0x80, 0x80, 0x80))
        shade(cell, "F7F9FC")
    # 外框
    tblpr = slot_table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{edge}")
        element.set(qn("w:val"), "dashed")
        element.set(qn("w:sz"), "6")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), "A6A6A6")
        borders.append(element)
    tblpr.append(borders)
    slot_table.rows[0].height = Cm(3.2)
    slot_table.rows[0].height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST

    # 七、踩坑
    heading(doc, "七、踩坑与解决")
    add_table(
        doc,
        ["现象", "原因", "解决"],
        [
            ["输入 8.1cm 被当成 8.1m，k 小了 100 倍",
             "解析只取数字，把单位丢了",
             "建单位表 + 换算函数；加单位一致性单测"],
            ["页面正常，导出的 Word 中文不是宋体",
             "python-docx 的 font.name 不写 w:eastAsia",
             "单独设置 eastAsia；单测直接读 document.xml 校验"],
            ["剔除“异常点”后 R² 升高，结果反而更偏",
             "把拟合好看当成物理正确",
             "只标记不自动删除；保留全部点并提示“剔除前后对比”"],
        ],
        widths=[5.2, 5.4, 6.4],
        align_center=[],
        keep_together=True,
    )

    # 八、记录与计划
    heading(doc, "八、记录方式、分工与下周计划")
    para(doc,
         "记录三件套：Git commit（哈希可追溯）、docs/bugs.md（现象/定位/原因/修复/证据）、"
         "docs/screenshots（按周命名）。周报滚动累加，但每周把旧内容压缩成半页，保证不超过 4 页。")
    add_table(
        doc,
        ["成员", "分工", "本周产出"],
        [
            ["成员 A", "数值核心：拟合、协方差、测试", "core/fit.py、23 个单测"],
            ["成员 B", "界面、模板、文档、仓库", "app.py、5 个模板、README 与 CI"],
        ],
        widths=[2.4, 7.2, 7.4],
        align_center=[],
    )
    para(doc, "下周计划（第 15 周）：", size=9.5, bold=True, indent=False, space_before=3)
    add_table(
        doc,
        ["下周目标", "交付物", "风险与应对"],
        [
            ["不确定度接入：A/B 类 + GUM + 蒙特卡洛",
             "不确定度页、直方图、两模式对比",
             "非线性协方差可能不稳；用合成数据回测覆盖率"],
            ["Word 报告导出", "三线表、图、结果表达式",
             "中文字体与表格样式；提前做样例验证"],
            ["真实用户访谈 2 人 + 真实数据", "访谈记录、与手算结果对比", "数据难拿；先用演示数据 + 同学实验报告"],
        ],
        widths=[5.4, 6.4, 5.2],
        align_center=[],
    )
    para(doc,
         "本周结论：选题成立、MVP 成立、工程骨架成立；下周把误差评定做扎实，并让报告能直接交。",
         bold=True, size=9.5, space_before=3)
    para(doc,
         "复盘：做得最好的是把“模板”提前抽象出来，换实验只改配置；做得不够的是界面还比较粗糙，"
         "真实截图和真实实验数据要等下周补。下周先把 GUM 与蒙特卡洛两个数字对齐，再谈报告美化。",
         size=9.5, color=(0x44, 0x44, 0x44))

    # 附：模板自检结果
    heading(doc, "附：5 个模板的自检结果（scripts/selfcheck.py，演示数据）")
    add_table(
        doc,
        ["实验", "模型", "目标量", "拟合结果", "参考值"],
        [
            ["单摆测 g", "幂函数", "g", "9.77 m/s²", "9.79"],
            ["弹簧劲度系数", "直线", "k", "12.3 N/m", "12.3"],
            ["RC 放电", "指数", "τ", "1.000 s", "1.0"],
            ["伏安特性", "直线", "R", "100 Ω", "100"],
            ["牛顿环", "直线（r²）", "R", "2.000 m", "2.0"],
        ],
        widths=[3.6, 3.0, 2.2, 4.6, 3.6],
    )

    doc.core_properties.title = "第14周进展报告：实验数据台"
    doc.core_properties.author = "计算机专业 2 人小组"
    doc.core_properties.subject = "专业导论实践大作业"

    # 默认模板的 <w:zoom w:val="bestFit"/> 会让部分渲染器按“适应宽度”缩放并裁切，
    # 这里固定为 100%，保证打印/导出时是完整 A4。
    zoom = doc.settings.element.find(qn("w:zoom"))
    if zoom is not None:
        for attr in list(zoom.attrib):
            del zoom.attrib[attr]
        zoom.set(qn("w:percent"), "100")

    doc.save(DOCX_PATH)


def main() -> int:
    g, r2 = make_figure()
    build(g, r2)
    print(f"figure: {FIG_PATH}")
    print(f"docx:   {DOCX_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
