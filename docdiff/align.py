"""align.py — 段落序列对齐(基于通用 seqdiff 层)"""
from typing import TypeVar

from .model import Op

# 载荷可以是 str(段落键)也可以是 Block(文档级);只当哈希键用,不比较内容
T = TypeVar("T")


def detect_moves(ops: list[Op], a: list[T], b: list[T]) -> list[Op]:
    """把'文本完全相同的 deleted+inserted 对'改判为 moved。
    输出中 moved 的格式: {"op": "moved", "old_idx": i, "new_idx": j}
    重复段落歧义用"按文档顺序贪心配对"解决。
    """
    deleted_items: list[tuple[int, T]] = []
    inserted_items: list[tuple[int, T]] = []
    for op in ops:
        if op["op"] == "deleted":
            deleted_items.append((op["old_idx"], a[op["old_idx"]]))
        elif op["op"] == "inserted":
            inserted_items.append((op["new_idx"], b[op["new_idx"]]))

    text_to_old_idxs: dict[T, list[int]] = {}
    for old_idx, text in deleted_items:
        if text not in text_to_old_idxs:
            text_to_old_idxs[text] = []
        text_to_old_idxs[text].append(old_idx)

    matched_old_idxs: set[int] = set()
    matched_new_idxs: set[int] = set()
    old_to_new_map: dict[int, int] = {}

    for new_idx, text in inserted_items:
        if text in text_to_old_idxs and text_to_old_idxs[text]:
            matched_old = text_to_old_idxs[text].pop(0)
            matched_old_idxs.add(matched_old)
            matched_new_idxs.add(new_idx)
            old_to_new_map[matched_old] = new_idx

    new_ops: list[Op] = []
    for op in ops:
        op_type = op["op"]
        if op_type == "deleted":
            old_idx = op["old_idx"]
            if old_idx in matched_old_idxs:
                new_ops.append({
                    "op": "moved",
                    "old_idx": old_idx,
                    "new_idx": old_to_new_map[old_idx]
                })
            else:
                new_ops.append(op)
        elif op_type == "inserted":
            new_idx = op["new_idx"]
            if new_idx in matched_new_idxs:
                continue
            else:
                new_ops.append(op)
        else:
            new_ops.append(op)

    return new_ops
