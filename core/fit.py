"""最小二乘拟合（纯 numpy 实现，不依赖 scipy）。

支持三类模型：
- linear       y = a·x + b
- power        y = a·x^b      （要求 x>0, y>0）
- exponential  y = a·exp(b·x) （要求 y>0）

非线性模型用带阻尼的高斯-牛顿迭代，初值由对数线性化给出。
拟合完成后用残差方差估计参数协方差矩阵，供不确定度传播使用。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


class FitError(ValueError):
    """数据不满足模型要求，或者拟合不收敛。"""


def _linear(p: np.ndarray, x: np.ndarray) -> np.ndarray:
    return p[0] * x + p[1]


def _power(p: np.ndarray, x: np.ndarray) -> np.ndarray:
    return p[0] * np.power(x, p[1])


def _exponential(p: np.ndarray, x: np.ndarray) -> np.ndarray:
    return p[0] * np.exp(p[1] * x)


_MODEL_FN = {
    "linear": _linear,
    "power": _power,
    "exponential": _exponential,
}

PARAM_NAMES = ("a", "b")

MODEL_LABELS = {
    "linear": "y = a·x + b",
    "power": "y = a·x^b",
    "exponential": "y = a·e^(b·x)",
}


@dataclass
class FitResult:
    model: str
    param_names: tuple[str, str]
    params: np.ndarray
    cov: np.ndarray
    se: np.ndarray
    yhat: np.ndarray
    resid: np.ndarray
    r2: float
    chi2_red: float
    dof: int
    x: np.ndarray
    y: np.ndarray

    @property
    def n(self) -> int:
        return int(self.x.size)

    def param_dict(self) -> dict[str, float]:
        return {name: float(value) for name, value in zip(self.param_names, self.params)}

    def summary(self) -> dict[str, float]:
        return {
            "r2": self.r2,
            "chi2_red": self.chi2_red,
            "dof": float(self.dof),
            **{f"se_{k}": float(v) for k, v in zip(self.param_names, self.se)},
        }


def model_function(model: str):
    if model not in _MODEL_FN:
        raise FitError(f"不支持的模型：{model!r}")
    return _MODEL_FN[model]


def initial_guess(model: str, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """给非线性模型一个靠谱的初值，否则高斯-牛顿很容易发散。"""
    if model == "linear":
        slope, intercept = np.polyfit(x, y, 1)
        return np.array([slope, intercept], dtype=float)

    if model == "power":
        mask = (x > 0) & (y > 0)
        if mask.sum() < 2:
            raise FitError("幂函数拟合要求至少两个点满足 x>0 且 y>0")
        exponent, log_a = np.polyfit(np.log(x[mask]), np.log(y[mask]), 1)
        return np.array([np.exp(log_a), exponent], dtype=float)

    if model == "exponential":
        mask = y > 0
        if mask.sum() < 2:
            raise FitError("指数拟合要求至少两个点满足 y>0")
        rate, log_a = np.polyfit(x[mask], np.log(y[mask]), 1)
        return np.array([np.exp(log_a), rate], dtype=float)

    raise FitError(f"不支持的模型：{model!r}")


def _jacobian(fn, p: np.ndarray, x: np.ndarray) -> np.ndarray:
    """数值雅可比矩阵：对每个参数做中心差分。"""
    p = np.asarray(p, dtype=float)
    base = fn(p, x)
    jac = np.empty((x.size, p.size), dtype=float)
    for j in range(p.size):
        step = 1e-7 * max(1.0, abs(p[j]))
        plus = p.copy()
        plus[j] += step
        jac[:, j] = (fn(plus, x) - base) / step
    return jac


def least_squares(fn, p0: np.ndarray, x: np.ndarray, y: np.ndarray,
                  max_iter: int = 200) -> np.ndarray:
    """带阻尼（Levenberg 风格）的高斯-牛顿迭代。"""
    p = np.asarray(p0, dtype=float).copy()
    resid = fn(p, x) - y
    cost = float(resid @ resid)
    damping = 1e-3

    for _ in range(max_iter):
        jac = _jacobian(fn, p, x)
        normal = jac.T @ jac
        gradient = jac.T @ resid
        step = None
        improved = False

        for _ in range(30):
            try:
                candidate = np.linalg.solve(
                    normal + damping * np.diag(np.diag(normal) + 1e-12),
                    -gradient,
                )
            except np.linalg.LinAlgError:
                damping *= 10.0
                continue

            p_new = p + candidate
            resid_new = fn(p_new, x) - y
            cost_new = float(resid_new @ resid_new)

            if np.isfinite(cost_new) and cost_new < cost:
                step = candidate
                p, resid, cost = p_new, resid_new, cost_new
                damping = max(damping / 3.0, 1e-12)
                improved = True
                break
            damping *= 10.0

        if not improved:
            break
        if step is not None and np.linalg.norm(step) < 1e-12 * max(1.0, np.linalg.norm(p)):
            break

    if not np.all(np.isfinite(p)):
        raise FitError("拟合发散，请检查数据或换一个模型")
    return p


def fit(model: str, x, y) -> FitResult:
    """对数据做拟合，返回参数、协方差、残差和拟合优度。"""
    x_arr = np.asarray(x, dtype=float).ravel()
    y_arr = np.asarray(y, dtype=float).ravel()

    if x_arr.size != y_arr.size:
        raise FitError("x 与 y 的数据个数不一致")
    if x_arr.size < 3:
        raise FitError("至少需要 3 个数据点才能拟合")
    if not (np.all(np.isfinite(x_arr)) and np.all(np.isfinite(y_arr))):
        raise FitError("数据里有 NaN 或无穷大")
    if model == "power" and (np.any(x_arr <= 0) or np.any(y_arr <= 0)):
        raise FitError("幂函数拟合要求所有 x>0 且 y>0")

    fn = model_function(model)
    p0 = initial_guess(model, x_arr, y_arr)
    params = least_squares(fn, p0, x_arr, y_arr)

    yhat = fn(params, x_arr)
    resid = y_arr - yhat
    dof = x_arr.size - params.size
    rss = float(resid @ resid)
    tss = float(((y_arr - y_arr.mean()) ** 2).sum())

    if dof <= 0:
        raise FitError("数据点太少，无法估计误差（需要比参数个数多）")

    sigma2 = rss / dof
    jac = _jacobian(fn, params, x_arr)
    try:
        cov = sigma2 * np.linalg.inv(jac.T @ jac)
    except np.linalg.LinAlgError:
        cov = sigma2 * np.linalg.pinv(jac.T @ jac)
    se = np.sqrt(np.clip(np.diag(cov), 0.0, None))

    r2 = 1.0 - rss / tss if tss > 0 else float("nan")

    return FitResult(
        model=model,
        param_names=PARAM_NAMES,
        params=params,
        cov=cov,
        se=se,
        yhat=yhat,
        resid=resid,
        r2=r2,
        chi2_red=sigma2,
        dof=dof,
        x=x_arr,
        y=y_arr,
    )


def curve(fit_result: FitResult, x_values) -> np.ndarray:
    """在给定 x 上计算拟合曲线，用于画图。"""
    fn = model_function(fit_result.model)
    return fn(fit_result.params, np.asarray(x_values, dtype=float))
