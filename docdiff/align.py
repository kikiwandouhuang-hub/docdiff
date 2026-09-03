"""align.py — 段落序列对齐(基于通用 seqdiff 层)"""
from .seqdiff import lcs_table, diff_ops  # re-export,兼容既有调用方

def detect_moves(ops: list[dict], a: list[str], b: list[str]) -> list[dict]:
    """把'文本完全相同的 deleted+inserted 对'改判为 moved。
    输出中 moved 的格式: {"op": "moved", "old_idx": i, "new_idx": j}
    重复段落歧义用"按文档顺序贪心配对"解决。
    """
    deleted_items = []
    inserted_items = []
    for op in ops:
        if op["op"] == "deleted":
            deleted_items.append((op["old_idx"], a[op["old_idx"]]))
        elif op["op"] == "inserted":
            inserted_items.append((op["new_idx"], b[op["new_idx"]]))

    text_to_old_idxs = {}
    for old_idx, text in deleted_items:
        if text not in text_to_old_idxs:
            text_to_old_idxs[text] = []
        text_to_old_idxs[text].append(old_idx)

    matched_old_idxs = set()
    matched_new_idxs = set()
    old_to_new_map = {}

    for new_idx, text in inserted_items:
        if text in text_to_old_idxs and text_to_old_idxs[text]:
            matched_old = text_to_old_idxs[text].pop(0)
            matched_old_idxs.add(matched_old)
            matched_new_idxs.add(new_idx)
            old_to_new_map[matched_old] = new_idx

    new_ops = []
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
