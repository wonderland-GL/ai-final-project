# 实验数据台（Physics Lab Data Desk）

> 把大学物理实验的原始数据，变成 **拟合结果 + 不确定度 + 可直接交的 Word 报告**。

一个面向物理/电子/机械/材料专业大一、大二学生的课程工具：
选实验模板 → 粘数据 → 拟合 → 算不确定度（GUM + 蒙特卡洛）→ 导出报告。

> 这个仓库是"AI + 专业工具"方向的期末大作业实现：
> 专业是**物理实验**，工具负责**数据处理与误差评定**，AI 只参与解释和文字，
> **所有数字都由程序计算并做回查**。

---

## 课程文档

- [第 14 周进展报告](docs/weekly/第14周进展报告.docx)（3 页，含选题、功能设计、验证与踩坑）
- [小组计划表](docs/plan/小组计划表.docx)（到 1 月 6 日的时间表与分工）
- [系统架构与核心调用链](docs/ARCHITECTURE.md)（可直接粘进 draw.io）
- [踩坑日志](docs/bugs.md)（周报与 PPT 素材）
- [安全与上传说明](docs/SECURITY.md)

---

## 一、它解决什么问题

大物实验报告里最花时间、最容易扣分的不是"做实验"，而是：

1. 非线性数据不会拟合，或者只会看 R²；
2. 不确定度只会算 A 类，B 类仪器误差靠猜；
3. 有效数字、扩展不确定度（k=2）写法不规范；
4. 每次报告都要重新画图、重排表格。

本工具把这条链自动化，并保证**每个数字可复现、可追溯**。

**目标用户**：物理、电子、机械、材料等专业修"大学物理实验"的本科生。

---

## 二、功能

| # | 功能 | 说明 |
|---|---|---|
| ① | 实验模板库 | 5 个内置实验（单摆、弹簧、RC、伏安、牛顿环），JSON 配置，新增实验不改代码 |
| ② | 数据与单位 | 粘贴/CSV 导入，自动单位换算（cm→m、mA→A） |
| ③ | 拟合与诊断 | 线性/幂函数/指数，参数 ± 标准误、R²、残差图 |
| ④ | 不确定度评定 | A/B 类合成 + GUM 线性传播 + 蒙特卡洛（快速 / 严格两种模式） |
| ⑤ | Word 报告导出 | 三线表、图、结果表达式、误差分析，中文宋体 |

AI 是**可选**功能：配置 `LLM_API_KEY` 后可让模型写"误差分析"段落，
不配置也能完整使用，且模型输出会做数字回查。

---

## 三、快速开始

要求：Python 3.10+（Windows / macOS / Linux 均可）。

```powershell
cd physics-lab-tool
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

浏览器打开 <http://localhost:8501>。

Windows 也可以直接双击 `start.bat`（前提是依赖已安装）。

**不需要 API Key 也能跑通全部核心功能。**

---

## 四、使用流程

1. 左侧选实验模板（先点"载入示例数据"可以 30 秒看完整效果）；
2. "② 数据"里粘贴两列数据，选单位，点"解析数据"；
3. "③ 拟合诊断"点"开始拟合"，看参数、R²、残差；
4. "④ 不确定度"填仪器分辨率，点"计算不确定度"；
5. "⑤ 导出报告"生成 Word，下载即可。

---

## 五、项目结构

```text
physics-lab-tool/
├─ app.py                     # Streamlit 界面（只做展示，不含算法）
├─ core/
│  ├─ units.py                # 单位解析与换算
│  ├─ templates.py            # 模板加载、目标量公式
│  ├─ fit.py                  # 最小二乘 + 参数协方差
│  ├─ uncertainty.py          # A/B 类、GUM、蒙特卡洛
│  ├─ report.py               # Word 报告（三线表、中文字体）
│  ├─ store.py                # SQLite：保存运行记录与报告路径
│  ├─ dataio.py               # 文本/CSV 解析
│  └─ llm.py                  # 可选的大模型调用与数字回查
├─ templates/experiments/     # 5 个实验模板（JSON）
├─ tests/                     # 23 个单元测试
├─ scripts/
│  ├─ selfcheck.py            # 不依赖 Streamlit 的核心自检
│  ├─ check_secrets.py        # 提交前扫密钥
│  └─ seed_demo.py            # 导出演示 CSV
├─ docs/                      # 上传 GitHub、安全、踩坑日志、架构图、周报
├─ .github/workflows/tests.yml# 推送到 GitHub 后自动跑测试
├─ data/                      # 本地数据（已 gitignore）
├─ reports/                   # 生成的报告和图（已 gitignore）
├─ requirements.txt
├─ .env.example
└─ .gitignore
```

**分层原则**：`core/` 不 import streamlit，可以单独测试、单独复用；
以后要换 FastAPI + React，只换 `app.py` 这一层。

---

## 六、新增一个实验模板

在 `templates/experiments/` 新建一个 JSON，例如：

```json
{
  "id": "example",
  "name": "示例实验",
  "model": "linear",
  "formula_text": "y = a·x + b，目标量 = 1/a",
  "y_transform": "none",
  "variables": {
    "x": {"name": "自变量", "unit": "m", "aliases": []},
    "y": {"name": "因变量", "unit": "s", "aliases": []}
  },
  "target": {"name": "目标量", "expr": "1/a", "unit": "m/s", "reference": null},
  "constants": {},
  "instruments": [
    {"name": "米尺", "resolution": 0.001, "unit": "m", "variable": "x"}
  ],
  "notes": "注意事项",
  "demo": {"x": [1, 2, 3], "y": [2.1, 3.9, 6.2]}
}
```

| 字段 | 说明 |
|---|---|
| `model` | `linear` / `power` / `exponential` |
| `target.expr` | 用参数 `a`、`b` 和常数写公式，如 `4*pi**2/a**2`；`lambda` 是 Python 关键字，请用 `lam` |
| `constants` | 公式里用到的常数，界面上可改 |
| `y_transform` | `none` 或 `square`（牛顿环把 r 平方成 r²） |
| `demo` | 演示数据，至少 3 组 |

改完刷新页面即生效，**不需要改 Python 代码**。

---

## 七、数据与模型分离（源码提交规范）

课程要求"源码不包括模型和数据"，本仓库默认做到：

- `data/`、`reports/`、`models/` 全部在 `.gitignore` 里；
- 仓库里只有代码、模板、文档；
- 没有实验数据也能演示：每个模板自带 `demo`，或运行：

```powershell
python scripts/seed_demo.py
```

生成 `data/demo_*.csv`（同样不会进仓库）。

---

## 八、测试

```powershell
python -m unittest discover -s tests -t . -v
python scripts/selfcheck.py
```

- 23 个单元测试覆盖单位、拟合、不确定度、模板、报告、数据库；
- `selfcheck.py` 会跑完 5 个模板并生成一份测试报告，适合截图进周报。

---

## 九、安全与隐私

- **仓库里没有任何密钥**；API Key 只从环境变量读（见 `.env.example`）；
- `.env` 已被 `.gitignore` 忽略；
- 提交前运行 `python scripts/check_secrets.py`；
- 数据只保存在本地 `data/`，不上传、不联网（除非你主动点 AI 按钮）；
- GitHub 账户安全操作见 [docs/SECURITY.md](docs/SECURITY.md) 和
  [docs/GITHUB_UPLOAD.md](docs/GITHUB_UPLOAD.md)。

---

## 十、每周路线（对应课程 14–16 周）

| 周 | 交付 |
|---|---|
| 14 | 模板库 + 数据/单位 + 线性拟合 + 参数误差（本项目已实现） |
| 15 | 幂/指数拟合 + 残差诊断 + GUM 合成 + Word 导出（本项目已实现） |
| 16 | 蒙特卡洛两模式 + 收敛/对比 + 部署与测试（本项目已实现，待补 PPT 截图） |

> 当前代码已经把 14–16 周的主线全部跑通，后续每周只需补"记录与截图"。

---

## 十一、常见问题

**Q：没有安装 matplotlib 会怎样？**
A：图和报告里的插图不显示，但拟合、不确定度、报告表格都正常。

**Q：图里的中文变成方框？**
A：Windows 一般不会；Linux 请安装 Noto Sans CJK，或在 `app.py` 的字体列表里加本机字体。

**Q：8501 端口被占用？**
A：`streamlit run app.py --server.port 8502`。

**Q：Excel 导出的 CSV 打开是乱码？**
A：工具已兼容 UTF-8 和 GBK；仍失败时请另存为"CSV UTF-8"。

---

## 十二、参考

- JJF 1059.1-2012《测量不确定度评定与表示》
- JJF 1059.2-2012《用蒙特卡洛法评定测量不确定度》
- ISO/IEC Guide 98-3 (GUM)

> 本项目仅用于课程学习，结果不构成计量校准结论。
