"""experiments/bench.py — 性能基准:5 组文档对 × 3 次,取中位数。

方法(手册 6.2):/usr/bin/time -l 量整次 CLI 调用(docdiff --json,输出丢弃),
时间取 real,内存取 maximum resident set size;3 次取中位数压掉冷启动抖动。
环境:macOS / Python 3.13。生成的 samples/big_*.docx 已被 .gitignore 排除。

用法: python3 experiments/bench.py
"""
import re
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
PY = sys.executable
GEN = str(ROOT / "experiments" / "gen_big_docx.py")

# (标签, 变更比例, 段数, 每段字数, 改动段数, 表格数)
ROWS = [
    ("100 段", "5%", 100, 50, 5, 0),
    ("500 段", "5%", 500, 50, 25, 0),
    ("2000 段", "5%", 2000, 50, 100, 0),
    ("500 段", "50%", 500, 50, 250, 0),
    ("500 段 + 20 表", "5%", 500, 50, 25, 20),
]


def _gen(path: str, n: int, m: int, mutate: int, tables: int) -> None:
    subprocess.run(
        [PY, GEN, str(n), str(m), path, "--mutate", str(mutate), "--tables", str(tables)],
        check=True,
    )


def _measure(old: str, new: str) -> tuple[float, int]:
    """跑一次 CLI,返回 (wall 秒, peak RSS 字节)。"""
    proc = subprocess.run(
        ["/usr/bin/time", "-l", PY, "-m", "docdiff.cli", old, new, "--json"],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, cwd=ROOT,
    )
    # 两份文档有差异时 CLI 退出码是 1,这是正常语义,不是错误
    assert proc.returncode in (0, 1), proc.stderr
    stderr = proc.stderr
    # 行形如 "0.03 real  0.02 user  0.00 sys",以 sys 结尾,不能 endswith("real")
    real = next(
        float(m.group(1)) for line in stderr.splitlines()
        if (m := re.match(r"^\s*([\d.]+) real\s", line))
    )
    rss = next(
        int(line.split()[0]) for line in stderr.splitlines() if "maximum resident set size" in line
    )
    return real, rss


def main() -> None:
    print(f"{'文档规模':<16} {'变更比例':<8} {'耗时':>8} {'峰值内存':>8}")
    for label, ratio, n, m, mutate, tables in ROWS:
        a = str(ROOT / "samples" / "big_a.docx")
        b = str(ROOT / "samples" / "big_b.docx")
        _gen(a, n, m, 0, tables)          # 旧文档:无改动
        _gen(b, n, m, mutate, tables)     # 新文档:改 mutate 段(+1 个表格单元格)
        times, rsses = [], []
        for _ in range(3):
            real, rss = _measure(a, b)
            times.append(real)
            rsses.append(rss)
        t = statistics.median(times)
        mem = statistics.median(rsses) / (1024 * 1024)
        print(f"{label:<16} {ratio:<8} {t:>7.2f}s {mem:>7.0f} MB")


if __name__ == "__main__":
    main()
