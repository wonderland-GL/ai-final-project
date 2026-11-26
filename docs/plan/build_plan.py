"""生成“产品介绍与推进计划”（DOCX），不含分工。

运行：python docs/plan/build_plan.py
输出：docs/plan/项目介绍与计划.docx
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = Path(__file__).resolve().parent / "项目介绍与计划.docx"

BODY = "宋体"
HEAD = "黑体"
LATIN = "Times New Roman"


def set_run(run, size=9.5, bold=False, chinese=BODY, color=None):
    run.font.name = LATIN
    run.font.size = Pt(size)
    run.bold = bold
    if color:
        run.font.color.rgb = RGBColor(*color)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.insert(0, rfonts)
    rfonts.set(qn("w:eastAsia"), chinese)
    rfonts.set(qn("w:ascii"), LATIN)
    rfonts.set(qn("w:hAnsi"), LATIN)


def para(doc, text="", size=9.5, bold=False, indent=False, align=None,
         before=0, after=2, line=1.05, color=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if indent:
        pf.first_line_indent = Cm(0.67)
    if align is not None:
        p.alignment = align
    set_run(p.add_run(text), size=size, bold=bold, color=color)
    return p


def heading(doc, text, before=6):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(before)
    pf.space_after = Pt(2)
    pf.keep_with_next = True
    set_run(p.add_run(text), size=11, bold=True, chinese=HEAD, color=(0x1F, 0x3A, 0x5F))


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


def cell_margins(table, top=20, bottom=20, left=55, right=55):
    tblpr = table._tbl.tblPr
    margins = OxmlElement("w:tblCellMar")
    for side, value in (("top", top), ("left", left), ("bottom", bottom), ("right", right)):
        element = OxmlElement(f"w:{side}")
        element.set(qn("w:w"), str(value))
        element.set(qn("w:type"), "dxa")
        margins.append(element)
    tblpr.append(margins)


def add_table(doc, headers, rows, widths, size=8.5, zebra=True):
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False

    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    table._tbl.tblPr.append(layout)
    table_borders(table)
    cell_margins(table)

    for index, header in enumerate(headers):
        cell = table.rows[0].cells[index]
        cell.width = Cm(widths[index])
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = 1.0
        set_run(p.add_run(str(header)), size=size, bold=True, chinese=HEAD)
        shade(cell, "E8EEF7")

    header_trpr = table.rows[0]._tr.get_or_add_trPr()
    header_trpr.append(OxmlElement("w:tblHeader"))

    for row_index, values in enumerate(rows):
        row = table.add_row()
        for index, value in enumerate(values):
            cell = row.cells[index]
            cell.width = Cm(widths[index])
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if index == 0 else WD_ALIGN_PARAGRAPH.LEFT
            set_run(p.add_run(str(value)), size=size)
            if zebra and row_index % 2 == 1:
                shade(cell, "F7F9FC")

    for row in table.rows:
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
    for index, width in enumerate(widths):
        table.columns[index].width = Cm(width)
    return table


def build() -> None:
    doc = Document()
    section = doc.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(1.6)
    section.bottom_margin = Cm(1.5)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)

    normal = doc.styles["Normal"]
    normal.font.name = LATIN
    normal.font.size = Pt(9.5)
    normal.paragraph_format.space_after = Pt(2)
    normal.paragraph_format.line_spacing = 1.05

    # 标题
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(1)
    set_run(p.add_run("实验数据台 · 产品介绍与推进计划"), size=17, bold=True,
            chinese=HEAD, color=(0x14, 0x2B, 0x47))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(1)
    set_run(p.add_run("AI + 大学物理实验｜2 人小组"), size=10.5, bold=True, chinese=HEAD)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    set_run(p.add_run(
        "更新：第 14 周｜仓库：github.com/wonderland-GL/ai-final-project"
    ), size=8, color=(0x66, 0x66, 0x66))

    para(doc,
         "给组员的话：这份文档只讲两件事——产品是什么，以及到 1 月 6 日怎么推进。"
         "看完回我一句“没问题”或“哪里要改”，我们就不再重复讨论方向。",
         size=9, color=(0x55, 0x55, 0x55), after=3)

    # 一、产品是什么
    heading(doc, "一、产品是什么", before=2)
    para(doc,
         "一句话：把大学物理实验的原始数据，变成“拟合结果 + 不确定度 + 可直接交的 Word 报告”。",
         bold=True, indent=True)
    para(doc,
         "目标用户是物理、电子、机械、材料等专业修“大学物理实验”的大一、大二学生。"
         "他们能做完实验，却处理不好数据：非线性模型不会选、不会给初值；软件只给 R²，"
         "不给参数误差；B 类不确定度靠猜；有效数字和扩展不确定度每次都要查。",
         indent=True)
    para(doc,
         "产品把这条链做成固定流程：选实验模板 → 粘两列数据 → 拟合 → 算不确定度 → 导出报告。"
         "所有数字由程序计算、可复现；AI 只负责解释和写文字，并且做数字回查。",
         indent=True)
    para(doc,
         "新颖点在于“垂直 + 规范”：不做通用计算器，而是用 JSON 模板把变量、单位、模型、目标公式"
         "和仪器固定下来，换实验只改配置、不改代码；输出按实验报告的规范排版（三线表、有效数字、k=2）。")

    # 二、功能一览
    heading(doc, "二、功能一览")
    add_table(
        doc,
        ["功能", "输入", "输出"],
        [
            ["① 实验模板库", "选择实验（单摆/弹簧/RC/伏安/牛顿环）",
             "自动填好变量、单位、模型、目标公式和仪器"],
            ["② 数据与单位", "粘贴两列数据，或上传 CSV；选择单位",
             "换算到 SI 的规范数据表，可下载"],
            ["③ 拟合与诊断", "两列数据 + 模型",
             "参数 ± 标准误、R²、拟合图、残差图"],
            ["④ 不确定度评定", "仪器分辨率、抽样次数、置信水平",
             "A/B 类合成、GUM 与蒙特卡洛对比、直方图、结果 ± U"],
            ["⑤ Word 报告", "一次完整运行的结果",
             "三线表、图、结果表达式、误差分析（中文宋体）"],
        ],
        widths=[3.4, 6.8, 6.8],
    )

    # 三、现在做到哪了
    heading(doc, "三、现在做到哪了（第 14 周）")
    add_table(
        doc,
        ["项目", "状态", "说明"],
        [
            ["代码", "已完成", "5 个模板、拟合、GUM + 蒙特卡洛、Word 导出、23 个单元测试"],
            ["仓库", "已完成", "main 已推送，GitHub Actions 自动跑测试与密钥扫描"],
            ["第 14 周报告", "已完成", "3 页，已上传到 docs/weekly/"],
            ["报告截图", "待补", "第 2 页两个截图位：AI 对话、第一版页面"],
            ["真实数据", "待补", "还没用同学的真实实验报告跑过完整流程"],
            ["部署验证", "待补", "还需要在第二台电脑的全新环境跑一遍"],
        ],
        widths=[3.0, 2.0, 12.0],
    )

    # 四、时间表
    heading(doc, "四、时间表（到 1 月 6 日）")
    add_table(
        doc,
        ["周次 / 截止", "要做的事", "交付物", "验收标准"],
        [
            ["第 14 周\n（现在）",
             "补 2 张报告截图；找 1 份真实实验报告跑对比；报告定稿",
             "3–3.5 页报告（含截图）",
             "截图真实、页数 ≤3.5、已上传仓库"],
            ["第 15 周",
             "界面接入 GUM + 蒙特卡洛；对比两种方法差异；验证 Word 三线表与中文字体；访谈 2 名物理同学",
             "3.5 页报告、对比图、访谈记录",
             "GUM 与 MC 快速差异 <5%；Word 格式正确；访谈有原话"],
            ["第 16 周",
             "第二台电脑全新环境部署；5 条测试用例；1 万次抽样性能；清理源码；4 页滚动报告",
             "4 页报告、部署截图、测试用例表",
             "断网可运行；5 条用例全过；git ls-files 无数据/模型"],
            ["第 17 周\n（缓冲）",
             "PPT 初稿（10 页内）；3–5 分钟录屏脚本；补“第 14 周 MVP vs 最终版”对比",
             "PPT v1、录屏脚本",
             "每页一个观点；无 AI 幻觉数字；视频 3–5 分钟"],
            ["第 18 周\n1 月 6 日 24:00",
             "学习通提交 PPT、源码、视频；1 月 7 日课堂交流；准备 3 个可能被问的问题",
             "全部材料",
             "按时提交；现场能演示、能回答"],
        ],
        widths=[2.8, 7.6, 3.4, 3.2],
    )

    # 第二页
    doc.add_page_break()

    # 五、周报内容
    heading(doc, "五、三份周报分别写什么", before=0)
    add_table(
        doc,
        ["周次", "页数", "内容要点", "截图配额"],
        [
            ["第 14 周", "3–3.5 页",
             "产品背景/用户/功能/架构；MVP 跑通截图；AI 对话；记录方式",
             "4 张"],
            ["第 15 周", "3.5 页",
             "上周压缩成半页；功能迭代跑通；AI 调 Bug；纠正 AI 幻觉；数据结构",
             "4 张"],
            ["第 16 周", "4 页",
             "前两周压缩成 1 页；本地部署；防幻觉策略；测试用例；项目心得",
             "4 张"],
        ],
        widths=[2.2, 1.8, 9.6, 3.4],
    )
    para(doc,
         "红线：三份周报是滚动累加的，但排版绝不能超过 4 页；每周新增截图不超过 4 张，超了就删旧内容。",
         size=8.5, color=(0x99, 0x33, 0x33), bold=True)

    # 六、风险
    heading(doc, "六、主要风险与应对")
    add_table(
        doc,
        ["风险", "影响", "应对"],
        [
            ["拿不到同学的真实实验数据", "报告里只有演示数据，真实性不足",
             "第 15 周前必须拿到 1 份；拿不到就用公开实验报告 + 自己重测"],
            ["GUM 与蒙特卡洛差异大", "结果被质疑",
             "以蒙特卡洛为准，报告里解释非线性；用合成数据回测覆盖率"],
            ["加截图后超过 4 页", "直接扣分",
             "截图缩到 7–8cm；删旧内容；表格并排；先排版再写正文"],
            ["第二台电脑部署失败", "“本地成功运行”这条拿不到分",
             "第 16 周提前试；requirements 固定版本；准备离线包"],
        ],
        widths=[5.0, 5.2, 6.8],
    )

    # 七、本周三件事
    heading(doc, "七、本周先做三件事")
    for index, text in enumerate((
        "运行 streamlit run app.py，走一遍“单摆 → 示例数据 → 拟合”，截 2 张图贴进第 14 周报告。",
        "找 1 份真实的大物实验报告，用 selfcheck.py / 页面跑一遍，记录和手算结果的差异。",
        "周三 20:00 开 30 分钟会，确认第 15 周任务和访谈安排。",
    ), 1):
        para(doc, f"{index}. {text}", size=9, after=2)

    # 八、提交红线
    heading(doc, "八、提交红线")
    for text in (
        "• 源码不含模型权重和实验数据（data/、models/ 已在 .gitignore）。",
        "• 周报滚动累加，但最终不超过 4 页。",
        "• 项目介绍视频 3–5 分钟，展示本地运行和主要功能。",
        "• 1 月 6 日 24:00 前在学习通提交 PPT、源码、视频。",
        "• PPT 里的数字必须和程序输出一致，不能有 AI 幻觉。",
        "• 换一台电脑、断网也能跑通，才算“本地成功运行”。",
    ):
        para(doc, text, size=8.5, after=1)

    # 保存
    zoom = doc.settings.element.find(qn("w:zoom"))
    if zoom is not None:
        for attr in list(zoom.attrib):
            del zoom.attrib[attr]
        zoom.set(qn("w:percent"), "100")

    doc.save(OUT)
    print(f"docx: {OUT}")


if __name__ == "__main__":
    build()
