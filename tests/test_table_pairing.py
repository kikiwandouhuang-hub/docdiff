"""表格身份配对(table_similarity + pair_modified 的表格路径)。

阈值 TABLE_SIM_THRESHOLD=0.5 由 experiments/scan_table_threshold.py 扫参确定:
正样本最小 0.750 / 负样本最大 0.333。
"""
from docdiff.model import Block
from docdiff.refine import (
    TABLE_SIM_THRESHOLD,
    pair_modified,
    table_similarity,
)


def _tbl(rows):
    return Block(kind="table", rows=rows)


def _para(text):
    return Block(kind="paragraph", text=text)


# ---- table_similarity:行级 LCS 覆盖率 ----

def test_table_similarity_identical():
    t = _tbl([["姓名", "部门"], ["张三", "技术部"]])
    assert table_similarity(t, t) == 1.0


def test_table_similarity_row_reversed_below_threshold():
    # 行序颠倒(表头不同):Jaccard 会给 1.0,行级 LCS 覆盖率必须给低分
    a = _tbl([["姓名", "部门"], ["张三", "技术部"], ["李四", "市场部"]])
    b = _tbl([["员工", "部门"], ["李四", "市场部"], ["张三", "技术部"]])
    assert table_similarity(a, b) < TABLE_SIM_THRESHOLD


def test_table_similarity_column_insert_above_threshold():
    # 插列:行键整体错位,行级覆盖率为 0,列视角兜底把它捞回来
    a = _tbl([["姓名", "部门"], ["张三", "技术部"]])
    b = _tbl([["姓名", "部门", "状态"], ["张三", "技术部", "在职"]])
    assert table_similarity(a, b) >= TABLE_SIM_THRESHOLD


def test_table_similarity_unrelated_zero():
    a = _tbl([["姓名", "部门"], ["张三", "技术部"]])
    b = _tbl([["产品", "价格"], ["咖啡", "25元"]])
    assert table_similarity(a, b) < TABLE_SIM_THRESHOLD


def test_table_similarity_empty_tables():
    assert table_similarity(_tbl([]), _tbl([])) == 1.0
    assert table_similarity(_tbl([]), _tbl([["A"]])) == 0.0


# ---- pair_modified:表格对走 table_similarity 路径 ----

def test_pair_modified_pairs_similar_tables():
    a = [_tbl([["姓名", "部门"], ["张三", "技术部"]])]
    b = [_tbl([["员工", "部门"], ["张三", "技术部"]])]  # 表头不同,内容重叠
    ops = [{"op": "deleted", "old_idx": 0}, {"op": "inserted", "new_idx": 0}]
    assert pair_modified(ops, a, b) == [
        {"op": "modified", "old_idx": 0, "new_idx": 0}
    ]


def test_pair_modified_unrelated_tables_stay_delete_insert():
    a = [_tbl([["姓名", "部门"], ["张三", "技术部"]])]
    b = [_tbl([["产品", "价格"], ["咖啡", "25元"]])]
    ops = [{"op": "deleted", "old_idx": 0}, {"op": "inserted", "new_idx": 0}]
    assert pair_modified(ops, a, b) == ops


def test_pair_modified_cross_kind_never_pairs():
    # 段落文本恰好与表格 key 撞车也不配对(kind 必须一致)
    a = [_tbl([["姓名"]])]
    b = [_para("TBL:姓名")]
    ops = [{"op": "deleted", "old_idx": 0}, {"op": "inserted", "new_idx": 0}]
    assert pair_modified(ops, a, b) == ops


def test_pair_modified_paragraph_path_still_works():
    # v2 Block 载荷下,段落路径语义不变(SIM_THRESHOLD=0.7)
    a = [_para("今天天气很好")]
    b = [_para("今天天气非常好")]
    ops = [{"op": "deleted", "old_idx": 0}, {"op": "inserted", "new_idx": 0}]
    assert pair_modified(ops, a, b) == [
        {"op": "modified", "old_idx": 0, "new_idx": 0}
    ]
    b2 = [_para("完全不同的内容")]
    assert pair_modified(ops, a, b2) == ops


def test_pair_modified_str_list_backward_compat():
    # v1 载荷 list[str] 仍然可用
    a = ["hello world"]
    b = ["hello wordl"]
    ops = [{"op": "deleted", "old_idx": 0}, {"op": "inserted", "new_idx": 0}]
    assert pair_modified(ops, a, b) == [
        {"op": "modified", "old_idx": 0, "new_idx": 0}
    ]
