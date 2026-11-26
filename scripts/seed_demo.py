"""把 5 个模板的演示数据导出成 CSV，方便没有网络/没有实验数据时演示。

运行：``python scripts/seed_demo.py``
输出：``data/demo_<模板id>.csv``
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import dataio, templates as tplmod  # noqa: E402


def main() -> int:
    output_dir = ROOT / "data"
    output_dir.mkdir(exist_ok=True)

    templates = tplmod.load_templates(ROOT / "templates" / "experiments")
    for template in templates.values():
        text = dataio.to_csv_text(template.demo_x, template.demo_y)
        path = output_dir / f"demo_{template.id}.csv"
        path.write_text(text, encoding="utf-8")
        print(f"写入 {path.relative_to(ROOT)}")

    print(f"\n完成，共 {len(templates)} 个文件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
