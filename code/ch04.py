"""第4章可运行入口：拉曼教学模拟与泛化验证。

从仓库根目录运行 python code/ch04.py；其参数转交主案例。
完整复现、扩展与校验见 code/ch04_exercises/raman/README.md。
所有数据为教学模拟，不代表实测矿物性能。
"""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).parent / "ch04_exercises/raman/exercise.py"), run_name="__main__")
