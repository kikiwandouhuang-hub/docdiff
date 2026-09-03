"""tablediff 测试:四类样本的集成断言 + 行/单元格级单元测试 + 行索引不变量。

样本约定(见 experiments/gen_tbl_samples.py):
- tbl_new1 改单元格 / tbl_new2 插行 / tbl_new3 移动行 / tbl_new4 插列(负样本)
"""
from docdiff.core import diff_docx
from docdiff.parser import extract_blocks
from docdiff.tablediff import diff_row, diff_table, row_similarity

S = "samples/tbl_"


def _table_modified(old_name: str, new_name: str) -> list[dict]:
    ops = diff_docx(S + old_name + ".docx", S + new_name + ".docx")
    return [op for op in ops if op["op"] == "table_modified"]


# ---- 四类样本集成断言 ----

def test_tbl_new1_cell_modified():
    to = _table_modified("old", "new1")
    assert len(to) == 1
    rows = to[0]["rows"]
    mods = [r for r in rows if r["op"] == "row_modified"]
    assert len(mods) == 1
    cells = mods[0]["cells"]
    cm = [c for c in cells if c["op"] == "cell_modified"]
    assert len(cm) == 1
    assert "inline" in cm[0]
    tags = [i["tag"] for i in cm[0]["inline"]]
    assert "delete" in tags and "insert" in tags  # 市场部 -> 运营部


def test_tbl_new2_row_inserted():
    # 二维版"战胜雪崩":插一行只报一行,其余行 unchanged
    rows = _table_modified("old", "new2")[0]["rows"]
    types = [r["op"] for r in rows]
    assert types.count("row_inserted") == 1
    assert types.count("row_unchanged") == 4
    ins = next(r for r in rows if r["op"] == "row_inserted")
    assert ins["new_row"] == 2  # 赵六插在张三之后


def test_tbl_new3_row_moved():
    rows = _table_modified("old", "new3")[0]["rows"]
    moved = [r for r in rows if r["op"] == "row_moved"]
    assert len(moved) == 1
    assert {moved[0]["old_row"], moved[0]["new_row"]} == {2, 3}


def test_tbl_new4_column_insert_fails_reasonably():
    # 负样本:不崩、每行给 warning、每行报一个 cell_inserted
    rows = _table_modified("old", "new4")[0]["rows"]
    assert len(rows) == 4  # 表头 + 3 数据行全部 row_modified
    for r in rows:
        assert r["op"] == "row_modified"
        assert "warning" in r
        assert "列数不同" in r["warning"]
        inserted = [c for c in r["cells"] if c["op"] == "cell_inserted"]
        assert len(inserted) == 1  # 状态/在职 列


def test_tbl_identical_no_table_modified():
    # 内容完全相同的表格不产生 table_modified,保持 unchanged
    ops = diff_docx(S + "old.docx", S + "old.docx")
    assert not any(op["op"] == "table_modified" for op in ops)
    assert any(op["op"] == "unchanged" for op in ops)


# ---- 行索引不变量:每个表格内部 old_row/new_row 恰好覆盖 range(行数) ----

def assert_table_rows_complete(old_name: str, new_name: str) -> None:
    a = extract_blocks(S + old_name + ".docx")
    b = extract_blocks(S + new_name + ".docx")
    ops = diff_docx(S + old_name + ".docx", S + new_name + ".docx")
    for op in ops:
        if op["op"] == "table_modified":
            rows_a = a[op["old_idx"]].rows
            rows_b = b[op["new_idx"]].rows
            old_rows = sorted(r["old_row"] for r in op["rows"] if "old_row" in r)
            new_rows = sorted(r["new_row"] for r in op["rows"] if "new_row" in r)
            assert old_rows == list(range(len(rows_a)))
            assert new_rows == list(range(len(rows_b)))


def test_row_indices_complete_all_samples():
    for name in ["new1", "new2", "new3", "new4"]:
        assert_table_rows_complete("old", name)


# ---- diff_table / diff_row 单元测试 ----

def test_diff_table_identical():
    rows = [["姓名", "部门"], ["张三", "技术部"]]
    ops = diff_table(rows, rows)
    assert all(op["op"] == "row_unchanged" for op in ops)
    assert [op["new_row"] for op in ops] == [0, 1]


def test_diff_table_empty():
    assert diff_table([], []) == []
    assert [op["op"] for op in diff_table([], [["A"]])] == ["row_inserted"]
    assert [op["op"] for op in diff_table([["A"]], [])] == ["row_deleted"]


def test_diff_table_single_row_modified():
    ops = diff_table([["A"]], [["B"]])
    assert len(ops) == 1 and ops[0]["op"] == "row_modified"
    cells = ops[0]["cells"]
    assert len(cells) == 1 and cells[0]["op"] == "cell_modified"


def test_diff_row_column_count_mismatch():
    # 列数不同 -> 列级 LCS 退化处理,不崩
    cells = diff_row(["a", "b"], ["a", "x", "c"])
    kinds = sorted(c["op"] for c in cells)
    assert kinds == ["cell_deleted", "cell_inserted", "cell_inserted", "cell_unchanged"]


def test_row_similarity_positional():
    assert row_similarity(["张三", "技术部", "x"], ["张三", "运营部", "x"]) == 2 / 3
    assert row_similarity(["张三", "技术部"], ["李四", "市场部"]) == 0.0
    assert row_similarity([], []) == 1.0
