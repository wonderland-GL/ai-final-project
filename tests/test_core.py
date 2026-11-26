"""核心算法单元测试（只用标准库 unittest，不依赖 pytest）。

运行：``python -m unittest discover -s tests -t . -v``
"""

from __future__ import annotations

import sys
import unittest
import zipfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import fit as fitmod  # noqa: E402
from core import report as reportmod  # noqa: E402
from core import store  # noqa: E402
from core import templates as tplmod  # noqa: E402
from core import uncertainty as unc  # noqa: E402
from core.units import (  # noqa: E402
    UnitError, convert, format_measurement, parse_quantity, units_for,
)


class TestUnits(unittest.TestCase):
    def test_parse_with_unit(self):
        quantity = parse_quantity("8.1cm")
        self.assertAlmostEqual(quantity.si_value, 0.081, places=12)

    def test_parse_with_space(self):
        quantity = parse_quantity("0.081 m")
        self.assertAlmostEqual(quantity.si_value, 0.081, places=12)

    def test_convert(self):
        self.assertAlmostEqual(convert(500, "mm", "m"), 0.5)
        self.assertAlmostEqual(convert(1, "min", "s"), 60.0)

    def test_convert_dimension_mismatch(self):
        with self.assertRaises(UnitError):
            convert(1, "cm", "s")

    def test_unknown_unit(self):
        with self.assertRaises(UnitError):
            parse_quantity("1 furlong")

    def test_units_for(self):
        self.assertIn("cm", units_for("m"))
        self.assertIn("ms", units_for("s"))

    def test_format_measurement(self):
        self.assertEqual(format_measurement(12.258, 0.18), "12.3 ± 0.2")
        self.assertEqual(format_measurement(9.79, 0.04), "9.79 ± 0.04")


class TestFit(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        self.x = np.linspace(0.5, 3.0, 12)
        self.y = 2.5 * self.x + 1.2 + rng.normal(0, 0.02, self.x.size)

    def test_linear_recovers_parameters(self):
        result = fitmod.fit("linear", self.x, self.y)
        self.assertAlmostEqual(result.params[0], 2.5, delta=0.02)
        self.assertAlmostEqual(result.params[1], 1.2, delta=0.03)
        self.assertGreater(result.r2, 0.999)
        self.assertTrue(np.all(np.isfinite(result.se)))
        self.assertGreater(result.se[0], 0)

    def test_power_demo(self):
        x = np.array([0.4, 0.6, 0.8, 1.0, 1.2])
        y = 2.0 * np.sqrt(x)
        result = fitmod.fit("power", x, y)
        self.assertAlmostEqual(result.params[1], 0.5, delta=0.01)

    def test_exponential_demo(self):
        x = np.linspace(0, 3, 7)
        y = 5.0 * np.exp(-x)
        result = fitmod.fit("exponential", x, y)
        self.assertAlmostEqual(result.params[1], -1.0, delta=0.02)

    def test_too_few_points(self):
        with self.assertRaises(fitmod.FitError):
            fitmod.fit("linear", [1, 2], [1, 2])

    def test_power_requires_positive(self):
        with self.assertRaises(fitmod.FitError):
            fitmod.fit("power", [-1, 1, 2], [1, 2, 3])


class TestUncertainty(unittest.TestCase):
    def test_a_type(self):
        repeats = [1.00, 1.02, 0.98, 1.01, 0.99]
        self.assertAlmostEqual(unc.u_a(repeats), np.std(repeats, ddof=1) / np.sqrt(5))

    def test_b_type_resolution(self):
        self.assertAlmostEqual(unc.u_b_resolution(0.01), 0.005 / np.sqrt(3))

    def test_combine(self):
        self.assertAlmostEqual(unc.combine(3.0, 4.0), 5.0)

    def test_gum_matches_mc(self):
        x = np.linspace(0.5, 3.0, 8)
        y = 2.0 * x + 1.0 + np.array([0.01, -0.02, 0.005, -0.01, 0.02, -0.005, 0.01, -0.01])
        result = fitmod.fit("linear", x, y)

        def eval_scalar(params):
            return float(1.0 / params[0])

        def eval_vector(columns):
            return 1.0 / columns["a"]

        gum_result = unc.gum(result, eval_scalar)
        fast = unc.mc_fast(result, eval_vector, n=5000, seed=1)
        self.assertAlmostEqual(gum_result["u"] / fast.u, 1.0, delta=0.1)

    def test_strict_mc_runs(self):
        x = np.linspace(0.5, 3.0, 8)
        y = 2.0 * x + 1.0
        result = fitmod.fit("linear", x, y)

        def eval_scalar(params):
            return float(params[0])

        strict = unc.mc_strict(
            "linear", x, y, 0.01, "none", eval_scalar, n=120, seed=2
        )
        self.assertGreater(strict.u, 0)
        self.assertTrue(np.isfinite(strict.u))
        self.assertGreaterEqual(strict.n, 50)

    def test_budget(self):
        total = unc.budget(3.0, 4.0)
        self.assertAlmostEqual(total["u_c"], 5.0)
        self.assertAlmostEqual(total["U"], 10.0)


class TestTemplates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.templates = tplmod.load_templates(ROOT / "templates" / "experiments")

    def test_five_templates_loaded(self):
        self.assertGreaterEqual(len(self.templates), 5)

    def test_demo_data_close_to_reference(self):
        for template in self.templates.values():
            x = np.asarray(template.demo_x, dtype=float)
            y = tplmod.apply_transform(
                np.asarray(template.demo_y, dtype=float), template.y_transform
            )
            result = fitmod.fit(template.model, x, y)
            params = dict(zip(result.param_names, result.params))
            value = float(tplmod.eval_target(template.target.expr, params, template.constants))
            if template.target.reference:
                deviation = abs(value - template.target.reference) / abs(template.target.reference)
                self.assertLess(deviation, 0.05, f"{template.id} 偏差 {deviation:.1%}")

    def test_eval_target_vectorised(self):
        template = self.templates["pendulum_g"]
        values = tplmod.eval_target(
            template.target.expr, {"a": np.array([2.0, 4.0])}, template.constants
        )
        self.assertEqual(values.shape, (2,))
        self.assertAlmostEqual(float(values[0]), 4 * np.pi ** 2 / 4.0)


class TestReport(unittest.TestCase):
    def test_report_build(self):
        template = tplmod.load_templates(ROOT / "templates" / "experiments")["spring_k"]
        x = np.asarray(template.demo_x, dtype=float)
        y = tplmod.apply_transform(np.asarray(template.demo_y, dtype=float), template.y_transform)
        result = fitmod.fit(template.model, x, y)
        summary = {
            "value": 12.3,
            "u_stat": 0.08,
            "u_b": 0.01,
            "u_c": 0.081,
            "U": 0.16,
            "u_mc_fast": 0.08,
            "n_mc": 10000,
            "n_mc_strict": 1000,
            "confidence": 0.95,
            "y_raw": list(template.demo_y),
        }
        path = ROOT / "reports" / "_unittest.docx"
        try:
            reportmod.build_report(path, template=template, fit_result=result, summary=summary)
            self.assertTrue(path.exists())
            self.assertGreater(path.stat().st_size, 10_000)

            from docx import Document
            document = Document(str(path))
            text = "\n".join(p.text for p in document.paragraphs)
            self.assertIn(template.name, text)
            self.assertIn("测量结果", text)

            with zipfile.ZipFile(path) as archive:
                xml = archive.read("word/document.xml").decode("utf-8")
            self.assertIn('w:eastAsia="宋体"', xml)
        finally:
            path.unlink(missing_ok=True)


class TestStore(unittest.TestCase):
    def test_save_run_and_report(self):
        db_path = ROOT / "data" / "_unittest_store.db"
        try:
            run_id = store.save_run(
                template_id="demo",
                model="linear",
                n_points=5,
                params={"a": 1.0, "b": 2.0},
                cov=np.eye(2),
                summary={"value": 1.0, "U": 0.1},
                db_path=db_path,
            )
            self.assertGreater(run_id, 0)

            report_id = store.save_report(run_id, "reports/demo.docx", db_path=db_path)
            self.assertGreater(report_id, 0)

            runs = store.list_runs(db_path=db_path)
            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0]["template_id"], "demo")
            self.assertAlmostEqual(runs[0]["summary"]["value"], 1.0)
        finally:
            db_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
