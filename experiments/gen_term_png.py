"""experiments/gen_term_png.py — 终端截图生成器(README 插图用)

运行 docdiff CLI,解析 ANSI 颜色,渲染成 VS Code 深色终端风格的 PNG。

字体:SimSong 是严格的 2:1 等宽字体(Latin 前进 0.5em,CJK 前进 1.0em,
实测 size=24 时 Latin=16.6px / CJK=33.4px),所以整屏统一用 SimSong,
按字符宽度手工排版,中英混排天然对齐。宽度不硬编码,启动时实测。

用法: python3.13 experiments/gen_term_png.py OLD.docx NEW.docx OUT.png
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # 让 experiments/ 目录外也能直接跑

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Circle, Rectangle

from docdiff.tokenize import _is_cjk

# VS Code Dark+ 配色
BG = "#1e1e1e"
TITLEBAR = "#3c3c3c"
TRAFFIC = ["#ff5f56", "#ffbd2e", "#27c93f"]
GREY = "#9e9e9e"
RED = "#f14c4c"
GREEN = "#3fb950"
GREEN_BOLD = "#7ee787"  # 终端把 \033[1m 渲染成亮色
YELLOW = "#e3b341"
PROMPT = "#569cd6"
TITLE_FG = "#d4d4d4"

ANSI_RE = re.compile(r"\x1b\[([0-9;]*)m")

STYLE_CODES = {
    "31": "red",
    "32": "green",
    "33": "yellow",
    "90": "grey",
    "1": "bold",
    "4": "underline",
}


def parse_ansi(text: str) -> list[tuple[frozenset, str]]:
    """解析 ANSI 转义序列,返回 [(style, text)] 段列表。"""
    segments: list[tuple[frozenset, str]] = []
    style: frozenset = frozenset()
    pos = 0
    for m in ANSI_RE.finditer(text):
        if m.start() > pos:
            segments.append((style, text[pos : m.start()]))
        for code in m.group(1).split(";"):
            if code in ("", "0"):
                style = frozenset()
            else:
                attr = STYLE_CODES.get(code)
                if attr:
                    style = style | {attr}
        pos = m.end()
    if pos < len(text):
        segments.append((style, text[pos:]))
    return segments


def _fg_color(style: frozenset) -> str:
    if "red" in style:
        return RED
    if "green" in style:
        return GREEN_BOLD if "bold" in style else GREEN
    if "yellow" in style:
        return YELLOW
    return GREY


def render_terminal(
    lines: list[str], command: str, prompt: str, out_path: Path, fontsize: int = 15
) -> None:
    # 实测 SimSong 前进宽度:CJK 应恰为 Latin 两倍
    fig = plt.figure(figsize=(1, 1), dpi=100)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    fp = FontProperties(family="SimSong", size=fontsize)
    probe = fig.text(0, 0, "a", fontproperties=fp)
    latin_w = probe.get_window_extent(renderer).width
    probe.set_text("字")
    cjk_w = probe.get_window_extent(renderer).width
    cjk_h = probe.get_window_extent(renderer).height
    plt.close(fig)
    ratio = cjk_w / latin_w
    assert 1.9 < ratio < 2.1, f"SimSong 不是 2:1 等宽: ratio={ratio:.3f}"
    line_h = int(cjk_h * 1.55)

    pad = 18
    title_h = 34
    # 内容最宽行的像素宽度
    content_max = 0
    for line in lines:
        w = sum(cjk_w if _is_cjk(ch) else latin_w for seg in parse_ansi(line) for ch in seg[1])
        content_max = max(content_max, w)
    w_total = pad * 2 + content_max
    h_total = title_h + line_h + pad * 2 + line_h * len(lines)

    # add_axes([0,0,1,1]) 让 1 数据单位 = 1 像素:subplots() 默认的 axes 边距
    # 会把数据坐标压缩 ~0.775 倍,而字体按绝对像素渲染,CJK 墨迹会溢出
    # 它的单元与相邻字符粘连(探针实测:5 个字形连成 1 片)。
    fig = plt.figure(figsize=(w_total / 100, h_total / 100), dpi=100)
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, w_total)
    ax.set_ylim(0, h_total)
    ax.axis("off")

    # 标题栏:三色圆点 + 命令
    ax.add_patch(Rectangle((0, h_total - title_h), w_total, title_h, facecolor=TITLEBAR))
    for i, color in enumerate(TRAFFIC):
        ax.add_patch(Circle((pad + 8 + i * 20, h_total - title_h / 2), 6, facecolor=color))
    ax.text(
        pad + 70, h_total - title_h / 2, command,
        fontproperties=FontProperties(family="SimSong", size=fontsize - 3),
        color=TITLE_FG, va="center",
    )

    # 提示符行
    y = h_total - title_h - pad - line_h * 0.7
    ax.text(
        pad, y, prompt,
        fontproperties=FontProperties(family="SimSong", size=fontsize - 2),
        color=PROMPT, va="center",
    )

    # 内容行:逐字符手工排版,保证中英混排对齐
    y = h_total - title_h - pad - line_h * 1.9
    for line in lines:
        x = pad
        for style, text in parse_ansi(line):
            fg = _fg_color(style)
            for ch in text:
                adv = cjk_w if _is_cjk(ch) else latin_w
                if "underline" in style:
                    ax.plot([x, x + adv], [y - 4, y - 4], lw=1.5, color=fg)
                ax.text(
                    x, y, ch,
                    fontproperties=FontProperties(family="SimSong", size=fontsize),
                    color=fg, va="center",
                )
                x += adv
        y -= line_h

    fig.savefig(out_path, facecolor=BG, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)
    print(f"ok: {out_path}")


if __name__ == "__main__":
    old, new, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    proc = subprocess.run(
        [sys.executable, "-m", "docdiff.cli", old, new],
        capture_output=True, text=True,
    )
    command = f"docdiff — {Path(old).name} vs {Path(new).name}"
    prompt = f"$ python3.13 -m docdiff.cli {old} {new}"
    render_terminal(proc.stdout.splitlines(), command, prompt, out)
