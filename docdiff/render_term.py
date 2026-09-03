"""render_term.py — ANSI 彩色终端渲染层

v1: 只渲染段落(list[str])
v2: 渲染 Block 流。table_modified 用 ASCII 边框画出整表,
    行级颜色语义与段落一致:绿 + 增 / 红 - 删 / 黄 ↑↓ 移 / 黄 ~ 改,
    单元格内 inline 高亮与段落段内细化同一套配色。
"""
import os
import sys

from .model import Block, Op
from .tokenize import _is_cjk


def _setup_ansi() -> bool:
    """在 Windows 终端下启用 ANSI 颜色支持；若不支持则降级为无颜色模式。"""
    if sys.platform == "win32":
        # Windows 10+ 可通过 os.system('') 激活 VT100 控制台 ANSI 模式
        ret = os.system("")
        if ret != 0:
            return False
    return True


HAS_COLOR = _setup_ansi()

if HAS_COLOR:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    GREY = "\033[90m"
    # 段内细化：删除文字带下划线，新增文字带加粗
    RED_INLINE = "\033[31m\033[4m"
    GREEN_INLINE = "\033[32m\033[1m"
else:
    RESET = RED = GREEN = YELLOW = GREY = RED_INLINE = GREEN_INLINE = ""

# 表格宽度上限:CJK 按 2 格计,超宽截断加省略号
MAX_CELL_WIDTH = 12   # 单个单元格显示宽度上限
MAX_TABLE_COLS = 5    # 最多渲染的列数,再多折叠成 "…" 列
MARKER_W = 2          # 行标记列宽(↑↓ 两个箭头)


def _disp_w(text: str) -> int:
    """显示宽度:CJK/全角按 2 格,其余按 1 格。与 tokenize._is_cjk 同一口径,
    保证和截图生成器的逐字符排版对齐。"""
    return sum(2 if _is_cjk(c) else 1 for c in text)


def _truncate_segments(segs: list[tuple[str, str]], max_w: int) -> list[tuple[str, str]]:
    """把 [(tag, text)] 分段截断到显示宽度 max_w,超宽截断加 "…"。
    截断发生在分段内部,颜色语义不丢。"""
    if sum(_disp_w(t) for _, t in segs) <= max_w:
        return segs
    out = []
    w = 0
    for tag, text in segs:
        for c in text:
            cw = 2 if _is_cjk(c) else 1
            if w + cw > max_w - 1:  # 给省略号留 1 格
                out.append(("plain", "…"))
                return out
            if out and out[-1][0] == tag:
                out[-1] = (tag, out[-1][1] + c)
            else:
                out.append((tag, c))
            w += cw
    out.append(("plain", "…"))
    return out


def _row_display(
    rows_ops: list[Op], rows_a: list[list[str]], rows_b: list[list[str]]
) -> list[tuple[str, str, list[list[tuple[str, str]]]]]:
    """行级 ops -> [(marker, kind, cells)]。
    cells 的每个元素是 [(tag, text)] 分段,tag 为 plain/delete/insert;
    inline 的 equal 归并成 plain。单元格内换行用 ¶ 表示。"""
    disp = []
    for r in rows_ops:
        rop = r["op"]
        if rop == "row_unchanged":
            disp.append(("  ", "unchanged", [[("plain", c)] for c in rows_a[r["old_row"]]]))
        elif rop == "row_deleted":
            disp.append(("- ", "deleted", [[("plain", c)] for c in rows_a[r["old_row"]]]))
        elif rop == "row_inserted":
            disp.append(("+ ", "inserted", [[("plain", c)] for c in rows_b[r["new_row"]]]))
        elif rop == "row_moved":
            disp.append(("↑↓", "moved", [[("plain", c)] for c in rows_b[r["new_row"]]]))
        else:  # row_modified
            cells = []
            for c in r["cells"]:
                cop = c["op"]
                if cop == "cell_unchanged":
                    cells.append([("plain", rows_b[r["new_row"]][c["new_col"]])])
                elif cop == "cell_modified":
                    cells.append([
                        ("plain" if i["tag"] == "equal" else i["tag"], i["text"])
                        for i in c["inline"]
                    ])
                elif cop == "cell_deleted":
                    cells.append([("delete", rows_a[r["old_row"]][c["old_col"]])])
                else:  # cell_inserted
                    cells.append([("insert", rows_b[r["new_row"]][c["new_col"]])])
            disp.append(("~ ", "modified", cells))
    # 单元格内多段落用 ¶ 显式标出(纯文本换行会破坏 ASCII 边框)
    return [
        (mk, kind, [[(tag, text.replace("\n", "¶")) for tag, text in segs] for segs in cells])
        for mk, kind, cells in disp
    ]


def _marker_color(kind: str) -> str:
    if kind == "deleted":
        return RED
    if kind == "inserted":
        return GREEN
    if kind in ("moved", "modified"):
        return YELLOW
    if kind == "unchanged":
        return GREY
    return RESET


def _plain_color(kind: str) -> str:
    if kind == "deleted":
        return RED
    if kind == "inserted":
        return GREEN
    if kind == "moved":
        return YELLOW
    if kind == "unchanged":
        return GREY
    return RESET  # modified 的 plain 部分用默认色


def _cell_str(segs: list[tuple[str, str]], kind: str, width: int) -> str:
    """一个单元格的着色文本,右侧空格补齐到列宽。"""
    chunks = []
    w = 0
    for tag, text in segs:
        if tag == "delete":
            color = RED_INLINE
        elif tag == "insert":
            color = GREEN_INLINE
        else:
            color = _plain_color(kind)
        chunks.append(f"{color}{text}{RESET}")
        w += _disp_w(text)
    return "".join(chunks) + " " * (width - w)


def _draw_table(
    rows_ops: list[Op], rows_a: list[list[str]], rows_b: list[list[str]]
) -> list[str]:
    """ASCII 边框表,行标记列在最左。第一行后画表头分隔线。"""
    disp = _row_display(rows_ops, rows_a, rows_b)
    n_cols = max((len(cells) for _, _, cells in disp), default=0)
    # 逐格截断到上限,再按列取最大宽度;列数超上限折叠成 "…" 列
    trunc = [
        [_truncate_segments(segs, MAX_CELL_WIDTH) for segs in cells]
        for _, _, cells in disp
    ]
    shown = min(n_cols, MAX_TABLE_COLS)
    widths = [1] * shown
    for cells in trunc:
        for j in range(shown):
            if j < len(cells):
                widths[j] = max(widths[j], _disp_w("".join(t for _, t in cells[j])))
    if n_cols > shown:
        widths.append(1)

    seg = "─" * MARKER_W  # 标记列没有两侧空格,边框段宽 = MARKER_W
    top = "┌" + seg + "".join("┬" + "─" * (w + 2) for w in widths) + "┐"
    mid = "├" + seg + "".join("┼" + "─" * (w + 2) for w in widths) + "┤"
    bot = "└" + seg + "".join("┴" + "─" * (w + 2) for w in widths) + "┘"

    lines = [f"{GREY}{top}{RESET}"]
    for i, ((marker, kind, _), cells) in enumerate(zip(disp, trunc, strict=False)):
        # 标记列的右竖线同时是第一单元格的左竖线,不能重复画
        body = f"{GREY}│{RESET}" + f"{_marker_color(kind)}{marker}{RESET}"
        for j in range(shown):
            segs = cells[j] if j < len(cells) else []
            body += f"{GREY}│{RESET} " + _cell_str(segs, kind, widths[j]) + " "
        if n_cols > shown:
            body += f"{GREY}│{RESET} " + f"{GREY}…{RESET}" + " "
        body += f"{GREY}│{RESET}"
        lines.append(body)
        if i == 0 and len(disp) > 1:
            lines.append(f"{GREY}{mid}{RESET}")
    lines.append(f"{GREY}{bot}{RESET}")
    return lines


def _row_warnings(op: Op) -> list[str]:
    """收集行级 warning(如列数漂移),按首次出现顺序去重。"""
    warns = []
    for r in op.get("rows", []):
        w = r.get("warning")
        if w and w not in warns:
            warns.append(w)
    return warns


def render(ops: list[Op], a: list[Block], b: list[Block]) -> None:
    """在终端格式化打印彩色对比结果。a / b 是 list[Block]。"""
    for op in ops:
        op_type = op["op"]

        if op_type == "unchanged":
            old_idx = op["old_idx"]
            new_idx = op["new_idx"]
            text = a[old_idx].text
            short_text = text[:20] + ("..." if len(text) > 20 else "")
            print(f"{GREY}  [{old_idx + 1}→{new_idx + 1}]  {short_text}{RESET}")

        elif op_type in ("inserted", "insert"):
            new_idx = op["new_idx"]
            text = b[new_idx].text
            print(f"{GREEN}+ [  →{new_idx + 1}] {text}{RESET}")

        elif op_type in ("deleted", "delete"):
            old_idx = op["old_idx"]
            text = a[old_idx].text
            print(f"{RED}- [{old_idx + 1}→  ] {text}{RESET}")

        elif op_type == "moved":
            old_idx = op["old_idx"]
            new_idx = op["new_idx"]
            text = b[new_idx].text
            print(
                f"{YELLOW}⇅ [{old_idx + 1}→{new_idx + 1}] ⇅ 从第{old_idx + 1}段移至"
                f"第{new_idx + 1}段: {text}{RESET}"
            )

        elif op_type == "modified":
            old_idx = op["old_idx"]
            new_idx = op["new_idx"]
            inline = op.get("inline", [])

            inline_chunks = []
            for item in inline:
                tag = item["tag"]
                txt = item["text"]
                if tag == "equal":
                    inline_chunks.append(f"{RESET}{txt}")
                elif tag == "delete":
                    inline_chunks.append(f"{RED_INLINE}{txt}{RESET}")
                elif tag == "insert":
                    inline_chunks.append(f"{GREEN_INLINE}{txt}{RESET}")

            inline_str = "".join(inline_chunks)
            print(f"{YELLOW}~ [{old_idx + 1}→{new_idx + 1}] {inline_str}{RESET}")

        elif op_type == "formatted":
            old_idx = op["old_idx"]
            new_idx = op["new_idx"]
            desc = ", ".join(
                f"{c['attr']}={c['old']}→{c['new']}" for c in op.get("changes", [])
            )
            print(f"{YELLOW}# [{old_idx + 1}→{new_idx + 1}] 格式: {desc}{RESET}")

        elif op_type == "table_modified":
            old_idx = op["old_idx"]
            new_idx = op["new_idx"]
            old_block = a[old_idx]
            new_block = b[new_idx]
            if (old_block.fmt or {}).get("unsupported") == "merged_cells" or \
               (new_block.fmt or {}).get("unsupported") == "merged_cells":
                print(f"{YELLOW}警告: 此表格含合并单元格,当前按展开的单元格近似渲染{RESET}")
            for warn in _row_warnings(op):
                print(f"{YELLOW}警告: {warn}{RESET}")
            print(f"{YELLOW}~ [{old_idx + 1}→{new_idx + 1}] 表格:{RESET}")
            for line in _draw_table(op["rows"], old_block.rows, new_block.rows):
                print(line)
