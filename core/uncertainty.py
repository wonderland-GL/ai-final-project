"""不确定度评定。

三条路线，互相印证：
1. GUM 线性传播：由参数协方差矩阵算统计不确定度（解析、快）。
2. 蒙特卡洛-快速：从参数分布抽样，验证线性传播是否成立（应接近 1）。
3. 蒙特卡洛-严格：对原始数据点按仪器不确定度加噪、重新拟合，
   得到仪器 B 类不确定度（GUM 里最难手算的那部分）。

最后按平方和合成：u_c = sqrt(u_stat² + u_B²)，扩展不确定度 U = 2·u_c。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from . import fit as fitmod
from .templates import apply_transform


class UncertaintyError(ValueError):
    """抽样失败或样本不足。"""


def u_a(repeats) -> float:
    """A 类：重复测量的标准偏差除以 sqrt(n)。"""
    values = np.asarray(repeats, dtype=float).ravel()
    if values.size < 2:
        raise UncertaintyError("A 类评定至少需要 2 次重复测量")
    return float(values.std(ddof=1) / np.sqrt(values.size))


def u_b_uniform(half_width: float) -> float:
    """B 类：已知半宽 a，按均匀分布取 a/sqrt(3)。"""
    return float(abs(half_width) / np.sqrt(3.0))


def u_b_resolution(resolution: float) -> float:
    """B 类：仪器分辨率为 d，半宽取 d/2，再除 sqrt(3)。"""
    return u_b_uniform(abs(resolution) / 2.0)


def combine(*components: float) -> float:
    """平方和合成。"""
    return float(np.sqrt(sum(float(c) ** 2 for c in components)))


@dataclass
class MCResult:
    samples: np.ndarray
    n: int
    mean: float
    std: float
    ci_low: float
    ci_high: float
    label: str = ""

    @property
    def u(self) -> float:
        return float(self.std)

    @property
    def expanded(self) -> float:
        """95% 区间的半宽。"""
        return float((self.ci_high - self.ci_low) / 2.0)


def _interval(values: np.ndarray, confidence: float) -> tuple[float, float]:
    alpha = (1.0 - confidence) / 2.0
    low, high = np.percentile(values, [alpha * 100.0, (1.0 - alpha) * 100.0])
    return float(low), float(high)


def target_gradient(eval_scalar: Callable[[np.ndarray], float],
                    params: np.ndarray, rel: float = 1e-5) -> np.ndarray:
    """目标量对每个拟合参数的中心差分梯度。"""
    p = np.asarray(params, dtype=float)
    grad = np.empty_like(p)
    for i in range(p.size):
        step = rel * max(1.0, abs(p[i]))
        plus = p.copy()
        minus = p.copy()
        plus[i] += step
        minus[i] -= step
        grad[i] = (float(eval_scalar(plus)) - float(eval_scalar(minus))) / (2.0 * step)
    return grad


def gum(fit_result: fitmod.FitResult,
        eval_scalar: Callable[[np.ndarray], float]) -> dict[str, Any]:
    """GUM 线性传播：u = sqrt(gᵀ Σ g)。"""
    grad = target_gradient(eval_scalar, fit_result.params)
    variance = float(grad @ fit_result.cov @ grad)
    if variance < 0 and variance > -1e-15:
        variance = 0.0
    if variance < 0:
        raise UncertaintyError("协方差矩阵非正定，无法做线性传播")
    return {
        "value": float(eval_scalar(fit_result.params)),
        "gradient": grad,
        "u": float(np.sqrt(variance)),
    }


def mc_fast(fit_result: fitmod.FitResult,
            eval_vector: Callable[[dict[str, Any]], Any],
            n: int = 10_000,
            confidence: float = 0.95,
            seed: int | None = 0) -> MCResult:
    """从参数分布抽样，验证线性传播。

    ``eval_vector`` 接收一个"参数名 -> 数组"的字典，返回同长度数组。
    """
    if n < 100:
        raise UncertaintyError("抽样次数至少 100 次")
    rng = np.random.default_rng(seed)
    params = rng.multivariate_normal(
        fit_result.params, fit_result.cov, size=n, check_valid="ignore"
    )
    columns = {name: params[:, i] for i, name in enumerate(fit_result.param_names)}
    values = np.asarray(eval_vector(columns), dtype=float).ravel()
    values = values[np.isfinite(values)]
    if values.size < 100:
        raise UncertaintyError("有效样本太少，请检查公式或协方差矩阵")
    low, high = _interval(values, confidence)
    return MCResult(
        samples=values,
        n=int(values.size),
        mean=float(values.mean()),
        std=float(values.std(ddof=1)),
        ci_low=low,
        ci_high=high,
        label="蒙特卡洛-快速",
    )


def mc_strict(model: str,
              x,
              y_raw,
              u_y: float,
              transform: str,
              eval_scalar: Callable[[np.ndarray], float],
              n: int = 1_000,
              confidence: float = 0.95,
              seed: int | None = 0) -> MCResult:
    """对原始数据加仪器噪声后重新拟合，得到 B 类不确定度。"""
    if n < 100:
        raise UncertaintyError("抽样次数至少 100 次")
    x_arr = np.asarray(x, dtype=float).ravel()
    y_arr = np.asarray(y_raw, dtype=float).ravel()
    rng = np.random.default_rng(seed)

    values: list[float] = []
    for _ in range(n):
        y_sim = y_arr + rng.normal(0.0, u_y, size=y_arr.size)
        try:
            result = fitmod.fit(model, x_arr, apply_transform(y_sim, transform))
            values.append(float(eval_scalar(result.params)))
        except (fitmod.FitError, np.linalg.LinAlgError):
            continue

    samples = np.asarray(values, dtype=float)
    samples = samples[np.isfinite(samples)]
    if samples.size < 50:
        raise UncertaintyError("有效重拟合次数太少，请调小仪器不确定度或换模型")

    low, high = _interval(samples, confidence)
    return MCResult(
        samples=samples,
        n=int(samples.size),
        mean=float(samples.mean()),
        std=float(samples.std(ddof=1)),
        ci_low=low,
        ci_high=high,
        label="蒙特卡洛-严格",
    )


def budget(u_stat: float, u_b: float) -> dict[str, float]:
    """合成标准不确定度与扩展不确定度。"""
    u_c = combine(u_stat, u_b)
    return {"u_c": u_c, "U": 2.0 * u_c}
