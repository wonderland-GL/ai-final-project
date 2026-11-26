"""生成小组计划表（DOCX），用于发给组员。

运行：python docs/plan/build_plan.py
输出：docs/plan/小组计划表.docx
"""

from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = Path(__file__).resolve().parent / "小组计划表.docx"

BODY = "宋体"
HEAD = "黑体"
LATIN = "Times New Roman"
W = 17.0


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
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if index in (0,) else WD_ALIGN_PARAGRAPH.LEFT
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
    set_run(p.add_run("期末大作业 · 小组计划表"), size=18, bold=True, chinese=HEAD,
            color=(0x14, 0x2B, 0x47))

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(1)
    set_run(p.add_run("项目：实验数据台（AI + 大学物理实验）"), size=10.5, bold=True,
            chinese=HEAD)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    set_run(p.add_run(
        "2 人小组｜更新：第 14 周｜仓库：github.com/wonderland-GL/ai-final-project"
    ), size=8, color=(0x66, 0x66, 0x66))

    para(doc,
         "给组员的话：先看第二节时间表和第七节“本周三件事”。有不同意见，周三 20:00 前提出；"
         "没有异议就按这个执行，后面每周只微调，不再重新讨论方向。",
         size=9, color=(0x55, 0x55, 0x55), after=3)

    # 一、项目与目标
    heading(doc, "一、项目与目标", before=2)
    para(doc,
         "一句话：把大学物理实验的原始数据，变成“拟合结果 + 不确定度 + 可直接交的 Word 报告”。"
         "用户是物理、电子、机械、材料专业修大物实验的大一、大二学生；换实验只改 JSON 模板，不改代码。",
         indent=True)
    para(doc,
         "最终交付：本地可运行的系统 + 3–5 分钟演示视频 + 汇报 PPT + 第 14–16 周滚动周报；"
         "源码里不含模型权重和实验数据。")

    # 二、现在到哪了
    heading(doc, "二、现在到哪了（第 14 周）")
    add_table(
        doc,
        ["项目", "状态", "说明"],
        [
            ["代码", "已完成", "5 个实验模板、拟合、GUM + 蒙特卡洛、Word 导出、23 个单元测试"],
            ["仓库", "已完成", "main 已推送，GitHub Actions 自动跑测试与密钥扫描"],
            ["第 14 周报告", "已完成", "3 页，已上传到 docs/weekly/"],
            ["报告截图", "待补", "第 2 页两个截图位：AI 对话、第一版页面"],
            ["真实数据", "待补", "还没用同学的真实实验报告跑过完整流程"],
            ["部署验证", "待补", "还需要在第二台电脑的全新环境跑一遍"],
        ],
        widths=[3.0, 2.0, 12.0],
    )

    # 三、时间表
    heading(doc, "三、时间表（到 1 月 6 日）")
    add_table(
        doc,
        ["周次 / 截止", "本周要做的事", "交付物", "负责", "验收标准"],
        [
            ["第 14 周\n（现在）",
             "B 跑通界面并补 2 张截图；A 找 1 份真实实验报告跑 selfcheck 对比；两人确认分工",
             "3–3.5 页报告定稿（含截图）",
             "A / B",
             "截图真实、页数 ≤3.5、已上传仓库"],
            ["第 15 周",
             "界面接入 GUM + 蒙特卡洛；对比两种方法差异；验证 Word 三线表/中文字体；访谈 2 名物理同学",
             "3.5 页报告、对比图、访谈记录",
             "A 数值\nB 界面",
             "GUM 与 MC 快速差异 <5%；Word 格式正确；访谈有原话"],
            ["第 16 周",
             "第二台电脑全新环境部署；5 条测试用例；1 万次抽样性能；清理源码（不含 data/models）；4 页滚动报告",
             "4 页报告、部署截图、测试用例表",
             "B 部署\nA 测试",
             "断网可运行；5 条用例全过；git ls-files 无数据/模型"],
            ["第 17 周\n（缓冲）",
             "PPT 初稿（10 页内）；3–5 分钟录屏脚本；补“第 14 周 MVP vs 最终版”对比",
             "PPT v1、录屏脚本",
             "两人",
             "每页一个观点；无 AI 幻觉数字；视频 3–5 分钟"],
            ["第 18 周\n1 月 6 日 24:00",
             "学习通提交 PPT、源码、视频；1 月 7 日课堂交流；准备 3 个可能被问的问题",
             "全部材料",
             "两人",
             "按时提交；现场能演示、能回答"],
        ],
        widths=[2.7, 7.4, 3.2, 1.5, 2.2],
    )

    # 四、周报内容
    heading(doc, "四、三份周报分别写什么")
    add_table(
        doc,
        ["周次", "页数", "内容要点", "截图配额"],
        [
            ["第 14 周", "3–3.5 页",
             "背景/用户/功能/架构；MVP 跑通截图；AI 对话；记录方式",
             "4 张"],
            ["第 15 周", "3.5 页",
             "上周压缩成半页；功能迭代跑通；AI 调 Bug；纠正 AI 幻觉；数据结构",
             "4 张"],
            ["第 16 周", "4 页",
             "前两周压缩成 1 页；本地部署；防幻觉策略；测试用例；两人分工与心得",
             "4 张"],
        ],
        widths=[2.2, 1.8, 9.6, 3.4],
    )
    para(doc,
         "红线：三份周报是滚动累加的，但排版绝不能超过 4 页；每周新增截图不超过 4 张，超了就删旧内容。",
         size=8.5, color=(0x99, 0x33, 0x33), bold=True)

    # 五、分工
    doc.add_page_break()
    heading(doc, "五、分工与协作规则", before=0)
    add_table(
        doc,
        ["成员", "负责", "本周产出"],
        [
            ["成员 A", "数值核心：拟合、协方差、GUM、蒙特卡洛、单元测试；真实数据验证",
             "core/fit.py、core/uncertainty.py、测试用例"],
            ["成员 B", "界面、模板、Word 报告、文档、仓库与截图",
             "app.py、5 个模板、README、周报"],
            ["共同", "每周三 20:00 同步 30 分钟；PPT 与录屏一起做；互相 review 对方的提交",
             "—"],
        ],
        widths=[2.2, 9.2, 5.6],
    )
    for text in (
        "• Git：每个任务一次 commit，消息用 feat / fix / docs 前缀；push 前先 pull。",
        "• 截图：原图放 docs/screenshots/week14/，命名 week14_01_home.png，周报里缩小并排。",
        "• AI 记录：对话当场截图；AI 出错写进 docs/bugs.md（现象/原因/修复/证据）。",
        "• 不提交：.env、data/、reports/、模型文件；提交前跑 python scripts/check_secrets.py。",
    ):
        para(doc, text, size=8.5, after=1)

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
    heading(doc, "七、本周三件事（现在就做）")
    for index, text in enumerate((
        "成员 B：装依赖，运行 streamlit run app.py，走一遍“单摆 → 示例数据 → 拟合”，截 2 张图贴进第 14 周报告。",
        "成员 A：找 1 份真实的大物实验报告，用 selfcheck.py / 页面跑一遍，记录和手算结果的差异。",
        "两人：周三 20:00 开 30 分钟会，确认分工、第 15 周任务，以及谁负责访谈。",
    ), 1):
        para(doc, f"{index}. {text}", size=9, after=2)

    # 八、沟通与记录
    heading(doc, "八、沟通与记录")
    for text in (
        "• 固定会议：每周三 20:00，30 分钟；有事提前在群里说，不能默认缺席。",
        "• 会后在群里发 3 行：决定了什么 / 谁做什么 / 什么时候交。",
        "• 所有文件进仓库；聊天记录不算交付物，截图和文档才算。",
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
