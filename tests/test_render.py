"""渲染层测试:段落行为不变 + 表格三色语义 + 对齐不变量 + 宽度/截断单元测试。"""
import io
import re
from contextlib import redirect_stdout

from docdiff.core import diff_docx
from docdiff.model import Block
from docdiff.parser import extract_blocks
from docdiff.render_term import (
    RESET, GREY, GREEN, RED, YELLOW, RED_INLINE, GREEN_INLINE,
    _disp_w, _truncate_segments, _draw_table,
)
from docdiff.render_term import render as render_term
from docdiff.render_html import render as render_html

ANSI = re.compile(r"\x1b\[[0-9;]*m")
S = "samples/tbl_"


def _term_output(old_name: str, new_name: str) -> str:
    a = extract_blocks(S + old_name + ".docx")
    b = extract_blocks(S + new_name + ".docx")
    buf = io.StringIO()
    with redirect_stdout(buf):
        render_term(diff_docx(S + old_name + ".docx", S + new_name + ".docx"), a, b)
    return buf.getvalue()


def _html_output(old_name: str, new_name: str) -> str:
    a = extract_blocks(S + old_name + ".docx")
    b = extract_blocks(S + new_name + ".docx")
    render_html(diff_docx(S + old_name + ".docx", S + new_name + ".docx"), a, b, "/tmp/docdiff_test.html")
    return open("/tmp/docdiff_test.html", encoding="utf-8").read()


def _table_blocks(lines: list[str]) -> list[list[str]]:
    """从剥离 ANSI 后的输出里切出 ASCII 表格块。"""
    blocks = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("┌"):
            j = i
            while not lines[j].startswith("└"):
                j += 1
            blocks.append(lines[i : j + 1])
            i = j + 1
        else:
            i += 1
    return blocks


# ---- 段落行为不变(逐字节断言) ----

def test_paragraph_ops_output_unchanged():
    old_p = Block(kind="paragraph", text="段落A")
    new_p = Block(kind="paragraph", text="段落B")
    ops = [
        {"op": "unchanged", "old_idx": 0, "new_idx": 0},
        {"op": "inserted", "old_idx": None, "new_idx": 1},
        {"op": "deleted", "old_idx": 1, "new_idx": None},
        {"op": "modified", "old_idx": 0, "new_idx": 1,
         "inline": [{"tag": "equal", "text": "段落"}, {"tag": "delete", "text": "A"},
                    {"tag": "insert", "text": "B"}]},
    ]
    a = [old_p, old_p, Block(kind="paragraph", text="")]
    b = [new_p, new_p, Block(kind="paragraph", text="")]
    buf = io.StringIO()
    with redirect_stdout(buf):
        render_term(ops, a, b)
    lines = ANSI.sub("", buf.getvalue()).splitlines()
    assert lines[0] == "  [1→1]  段落A"
    assert lines[1] == "+ [  →2] 段落B"
    assert lines[2] == "- [2→  ] 段落A"
    assert lines[3] == "~ [1→2] 段落AB"
    # 颜色语义不变:unchanged 灰、插绿、删红、modified 黄 + inline 红下划线/绿加粗
    raw = buf.getvalue()
    assert f"{GREY}  [1→1]" in raw
    assert f"{GREEN}+ [  →2]" in raw
    assert f"{RED}- [2→  ]" in raw
    assert f"{YELLOW}~ [1→2]" in raw
    assert f"{RED_INLINE}A" in raw and f"{GREEN_INLINE}B" in raw


# ---- 终端表格:三色语义 ----

def test_term_new1_cell_modified_inline_colors():
    out = _term_output("old", "new1")
    assert "~ [7→7] 表格:" in out
    assert RED_INLINE in out and GREEN_INLINE in out  # 市场->运营 的词级高亮
    assert "│~ │" in ANSI.sub("", out)  # 行级 ~ 标记


def test_term_new2_row_inserted_marker():
    out = _term_output("old", "new2")
    plain = ANSI.sub("", out)
    assert "│+ │" in plain  # 插入行绿 + 标记
    assert plain.count("│  │") == 4  # 其余 4 行 unchanged


def test_term_new3_row_moved_marker():
    plain = ANSI.sub("", _term_output("old", "new3"))
    assert "│↑↓│" in plain
    assert "↑↓" in plain


def test_term_new4_column_warning_dedup():
    out = _term_output("old", "new4")
    assert out.count("列数不同") == 1  # 4 行同一条 warning,只显示一次
    assert YELLOW in out


# ---- 对齐不变量:表格块内所有行显示宽度一致、竖线对齐 ----

def _pipe_positions(line: str) -> list[int]:
    w = 0
    pipes = []
    for ch in line:
        if ch in "│┌┬┐├┼┤└┴┘":
            pipes.append(w)
        w += _disp_w(ch)
    return pipes


def test_table_border_alignment_all_samples():
    for n in ["new1", "new2", "new3", "new4"]:
        lines = ANSI.sub("", _term_output("old", n)).splitlines()
        for block in _table_blocks(lines):
            widths = {sum(_disp_w(c) for c in l) for l in block}
            assert len(widths) == 1, f"{n}: 行宽不一致 {sorted(widths)}"
            pipes0 = _pipe_positions(block[0])
            for l in block:
                assert _pipe_positions(l) == pipes0, f"{n}: 竖线错位 {l!r}"


# ---- 合并单元格警告(Block.fmt) ----

def test_term_merged_cells_warning():
    old_t = Block(kind="table", rows=[["A"]], fmt={"unsupported": "merged_cells"})
    new_t = Block(kind="table", rows=[["A"]])
    ops = [{"op": "table_modified", "old_idx": 0, "new_idx": 0, "rows": []}]
    buf = io.StringIO()
    with redirect_stdout(buf):
        render_term(ops, [old_t], [new_t])
    assert "含合并单元格" in buf.getvalue()


# ---- 显示宽度与截断 ----

def test_disp_w_cjk():
    assert _disp_w("中") == 2
    assert _disp_w("a") == 1
    assert _disp_w("。") == 2  # CJK 标点全角
    assert _disp_w("中文abc") == 7
    assert _disp_w("") == 0


def test_truncate_segments():
    segs = [("plain", "这是很长很长的一段文字")]
    out = _truncate_segments(segs, 6)
    assert sum(_disp_w(t) for _, t in out) <= 6
    assert out[-1] == ("plain", "…")
    # 不超宽原样返回
    segs2 = [("delete", "市场"), ("insert", "运营"), ("plain", "部")]
    assert _truncate_segments(segs2, 20) == segs2
    # 截断保留分段颜色语义
    out2 = _truncate_segments(segs2, 4)
    tags = [t for t, _ in out2]
    assert "delete" in tags and tags[-1] == "plain"


def test_draw_table_wide_cell_truncated():
    ops = [{"op": "row_unchanged", "old_row": 0, "new_row": 0}]
    rows = [["这是一个超过十二格显示宽度的超长单元格内容"]]
    lines = _draw_table(ops, rows, rows)
    plain = ANSI.sub("", "".join(lines))
    assert "…" in plain
    widths = {sum(_disp_w(c) for c in ANSI.sub("", l)) for l in lines}
    assert len(widths) == 1


# ---- HTML:真 <table> + 行/格/词三层底色 + 统计条 ----

def test_html_new2_real_table_and_row_classes():
    h = _html_output("old", "new2")
    assert h.count('<table class="diff-table">') == 2  # 左右两侧
    assert 'class="row-ins"' in h          # 新侧插入行整行底色
    assert 'class="row-absent"' in h       # 旧侧斜纹占位行
    assert '共 1 处变更(0 增 0 删 0 改 0 移;表格:1 行增 0 行删 0 格改)' in h


def test_html_new1_cell_class_and_token_spans():
    h = _html_output("old", "new1")
    assert 'class="cell-mod"' in h
    assert 'class="token-del"' in h      # 旧侧"市场"删除词
    assert 'class="token-ins"' in h      # 新侧"运营"插入词
    assert ';表格:0 行增 0 行删 1 格改)' in h


def test_html_new3_moved_badges():
    h = _html_output("old", "new3")
    assert 'class="row-mov"' in h
    assert "移至右侧第" in h and "来自左侧第" in h


def test_html_new4_cell_inserted_and_warning():
    h = _html_output("old", "new4")
    assert 'class="cell-ins"' in h       # 新侧"状态"列
    assert 'class="cell-absent"' in h    # 旧侧无此列
    assert h.count('列数不同') == 1      # 行级 warning 去重显示


def test_html_paragraph_stats_unchanged_format():
    ops = diff_docx("samples/old.docx", "samples/new1.docx")
    a = extract_blocks("samples/old.docx")
    b = extract_blocks("samples/new1.docx")
    render_html(ops, a, b, "/tmp/docdiff_test.html")
    h = open("/tmp/docdiff_test.html", encoding="utf-8").read()
    assert "共 1 处变更(0 增 0 删 1 改 0 移)" in h
    assert "表格:" not in h.split("stat-total")[1][:200]
