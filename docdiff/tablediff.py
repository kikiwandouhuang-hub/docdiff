"""tablediff.py — 表格内部差异:行级 LCS + 行移动检测 + 单元格级比对

ops 在这里第一次变成嵌套结构:文档级 table_modified 携带 rows,
row_modified 再携带 cells。行/单元格两级都复用 seqdiff 通用层,
行移动检测复用 align.detect_moves(先检测移动,再改行级键名)。

行级 op 契约:
  {"op":"row_unchanged","old_row":i,"new_row":j}
  {"op":"row_inserted", "new_row":j}
  {"op":"row_deleted",  "old_row":i}
  {"op":"row_moved",    "old_row":i,"new_row":j}
  {"op":"row_modified", "old_row":i,"new_row":j,"cells":[...]}
  列数不同的 row_modified 额外带 "warning": str(渲染层去重显示)

单元格 op 契约:
  {"op":"cell_unchanged","old_col":i,"new_col":j}
  {"op":"cell_modified", "old_col":i,"new_col":j,"inline":[...]}
  {"op":"cell_inserted"/"cell_deleted", ...}
"""
from .align import detect_moves
from .model import CELL_SEP
from .refine import inline_diff
from .seqdiff import diff_ops, trim_common

# 行配对阈值:相同单元格数(按列位置)/ max(列数)。
# 样本实测:正样本(改一格 2/3、插列 3/4)最小 0.667,
# 负样本(只同名同姓的两行 1/3)最大 0.333,0.5 分离干净。
ROW_SIM_THRESHOLD = 0.5


def _row_key(row: list[str]) -> str:
    """行比较键 = 单元格文本用 \x1f 拼接。
    用 \x1f(单元分隔符)而不是 "|",因为单元格内容里可能真有竖线。"""
    return CELL_SEP.join(row)


def row_similarity(row_a: list[str], row_b: list[str]) -> float:
    """相同单元格数 / max(列数)。按列位置比对,天然位置敏感。"""
    n = max(len(row_a), len(row_b))
    if n == 0:
        return 1.0
    return sum(1 for ca, cb in zip(row_a, row_b) if ca == cb) / n


def _to_row_ops(ops: list[dict]) -> list[dict]:
    """seqdiff 的 old_idx/new_idx 键名换成行级 old_row/new_row。"""
    out = []
    for op in ops:
        if op["op"] == "unchanged":
            out.append({"op": "row_unchanged", "old_row": op["old_idx"], "new_row": op["new_idx"]})
        elif op["op"] == "deleted":
            out.append({"op": "row_deleted", "old_row": op["old_idx"]})
        elif op["op"] == "inserted":
            out.append({"op": "row_inserted", "new_row": op["new_idx"]})
        else:  # moved
            out.append({"op": "row_moved", "old_row": op["old_idx"], "new_row": op["new_idx"]})
    return out


def diff_row(cells_a: list[str], cells_b: list[str]) -> list[dict]:
    """单元格级比对。列数相同时逐列直比(绝大多数情况);
    列数不同时对单元格文本跑一次列级 LCS 处理列增删——
    这就是插列不会崩的原因:它退化成一次列级 LCS。"""
    if len(cells_a) == len(cells_b):
        cell_ops = []
        for i, (ca, cb) in enumerate(zip(cells_a, cells_b)):
            if ca == cb:
                cell_ops.append({"op": "cell_unchanged", "old_col": i, "new_col": i})
            else:
                cell_ops.append({
                    "op": "cell_modified", "old_col": i, "new_col": i,
                    "inline": inline_diff(ca, cb),
                })
        return cell_ops

    cell_ops = []
    for op in diff_ops(cells_a, cells_b):
        if op["op"] == "unchanged":
            cell_ops.append({"op": "cell_unchanged", "old_col": op["old_idx"], "new_col": op["new_idx"]})
        elif op["op"] == "deleted":
            cell_ops.append({"op": "cell_deleted", "old_col": op["old_idx"]})
        else:
            cell_ops.append({"op": "cell_inserted", "new_col": op["new_idx"]})
    return cell_ops


def _pair_rows(ops: list[dict], rows_a: list[list[str]], rows_b: list[list[str]]) -> list[dict]:
    """剩余 row_deleted + row_inserted 对,配成 row_modified。两条证据,任一成立即可:
    1. 行相似度 >= ROW_SIM_THRESHOLD(内容证据);
    2. 新旧位置相同(位置证据)——单格行改内容时相似度为 0,
       但同一位置的同一行显然是 modified(与 git 的行级直觉一致)。
    内容证据优先于位置证据(防"删 B 插 X"在同一位置被误配)。
    """
    deleted = [op for op in ops if op["op"] == "row_deleted"]
    inserted = [op for op in ops if op["op"] == "row_inserted"]

    candidates = []
    for d_op in deleted:
        for i_op in inserted:
            sim = row_similarity(rows_a[d_op["old_row"]], rows_b[i_op["new_row"]])
            same_pos = d_op["old_row"] == i_op["new_row"]
            if sim >= ROW_SIM_THRESHOLD or same_pos:
                candidates.append((sim, same_pos, d_op, i_op))
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

    used_old = set()
    used_new = set()
    mod_ops = []
    for sim, same_pos, d_op, i_op in candidates:
        old_row, new_row = d_op["old_row"], i_op["new_row"]
        if old_row in used_old or new_row in used_new:
            continue
        used_old.add(old_row)
        used_new.add(new_row)
        rm = {
            "op": "row_modified",
            "old_row": old_row,
            "new_row": new_row,
            "cells": diff_row(rows_a[old_row], rows_b[new_row]),
        }
        if len(rows_a[old_row]) != len(rows_b[new_row]):
            rm["warning"] = (
                f"列数不同({len(rows_a[old_row])} 列 → {len(rows_b[new_row])} 列):"
                "按列级 LCS 对齐单元格,列语义可能漂移"
            )
        mod_ops.append(rm)

    out = []
    for op in ops:
        if op["op"] == "row_deleted" and op["old_row"] in used_old:
            continue
        if op["op"] == "row_inserted" and op["new_row"] in used_new:
            continue
        out.append(op)
    out.extend(mod_ops)
    # 按新表行序排列;被删行没有 new_row,用 old_row 当代理排在后面
    out.sort(key=lambda x: (
        x.get("new_row", x.get("old_row", float("inf"))),
        0 if "new_row" in x else 1,
    ))
    return out


def diff_table(rows_a: list[list[str]], rows_b: list[list[str]]) -> list[dict]:
    """表格内部 diff:输出行级 ops(见模块 docstring 的契约)。"""
    keys_a = [_row_key(r) for r in rows_a]
    keys_b = [_row_key(r) for r in rows_b]

    # 掐头去尾 + LCS:与文档级同一套管线,只是载荷换成行
    head, tail = trim_common(keys_a, keys_b)
    mid_a = keys_a[head : len(keys_a) - tail] if tail > 0 else keys_a[head:]
    mid_b = keys_b[head : len(keys_b) - tail] if tail > 0 else keys_b[head:]

    mid_ops = diff_ops(mid_a, mid_b)
    # 行移动:detect_moves 认 deleted/inserted 原始键名,先做移动检测再改名行级键
    mid_ops = detect_moves(mid_ops, mid_a, mid_b)
    mid_ops = _to_row_ops(mid_ops)
    rows_mid_a = rows_a[head : len(rows_a) - tail] if tail > 0 else rows_a[head:]
    rows_mid_b = rows_b[head : len(rows_b) - tail] if tail > 0 else rows_b[head:]
    mid_ops = _pair_rows(mid_ops, rows_mid_a, rows_mid_b)

    ops = []
    for i in range(head):
        ops.append({"op": "row_unchanged", "old_row": i, "new_row": i})
    for op in mid_ops:
        new_op = op.copy()
        if "old_row" in new_op:
            new_op["old_row"] += head
        if "new_row" in new_op:
            new_op["new_row"] += head
        ops.append(new_op)
    a_tail_start = len(rows_a) - tail
    b_tail_start = len(rows_b) - tail
    for i in range(tail):
        ops.append({
            "op": "row_unchanged",
            "old_row": a_tail_start + i,
            "new_row": b_tail_start + i,
        })
    return ops
