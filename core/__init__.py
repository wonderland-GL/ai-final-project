"""实验数据台核心算法包。

模块划分:
- units:        单位解析与换算
- templates:    实验模板加载与目标量计算
- fit:          最小二乘拟合与参数协方差
- uncertainty:  A/B 类不确定度、GUM 传播、蒙特卡洛
- report:       Word 报告导出
- dataio:       文本/CSV 数据解析
- llm:          可选的大模型调用（未配置 Key 时自动降级）
"""

__version__ = "0.1.0"
