# 踩坑日志（Bugs & Fixes）

> 用途：周报里"遇到的主要问题及解决方法"和 PPT 的"AI 辅助踩坑史"，
> 直接从这里取素材。每条都要有**现象、定位、原因、修复、证据**。

---

## 2024-11-xx 单位换算差 100 倍

- **现象**：输入 `8.1cm`，程序当成 `8.1m`，弹簧劲度系数 k 直接小了 100 倍。
- **定位**：`core/units.py` 的 `parse_quantity` 只取了数字，把单位丢了。
- **原因**：最初版本假设"用户输入的都是 SI 单位"，没有做单位字段。
- **修复**：加单位表 + `convert()`；界面上单位下拉框默认跟模板一致；
  新增单元测试 `test_parse_with_unit`、`test_convert_dimension_mismatch`。
- **证据**：`docs/screenshots/week15_bug_units.png`

## 2024-11-xx 导出的 Word 中文变成默认字体

- **现象**：页面预览正常，下载的 docx 里中文不是宋体，和学校报告模板不一致。
- **定位**：`core/report.py` 只设置了 `run.font.name = "Times New Roman"`。
- **原因**：python-docx 的 `font.name` 只写 `w:ascii`/`w:hAnsi`，
  中文字体要走 `w:eastAsia`，否则 Word 用默认中文字体。
- **修复**：`_set_run_font()` 里同时设置 `w:eastAsia="宋体"`；
  单元测试直接读 `word/document.xml` 检查该属性。
- **证据**：`docs/screenshots/week15_bug_docx_font.png`

## 2024-11-xx 剔除"异常点"后 R² 变好，结果反而偏了

- **现象**：模型建议删掉残差最大的点，删完 R² 从 0.97 升到 0.995，
  但算出的 g 离 9.79 更远了。
- **定位**：那个点是真实测量值，不是记录错误；它恰好体现了系统误差。
- **原因**：把"拟合好看"当成"物理正确"，用 R² 做删除标准。
- **修复**：页面保留全部点；异常点只做标记，是否删除由用户决定；
  增加"剔除前后对比"提示；误差分析里写明判断依据。
- **证据**：`docs/screenshots/week16_outlier.png`

---

## 模板（复制使用）

```markdown
## YYYY-MM-DD 一句话标题

- **现象**：
- **定位**：哪个文件 / 哪个函数 / 哪一行
- **原因**：
- **修复**：
- **证据**：截图路径
- **如果重来**：
```
