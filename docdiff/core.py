from .parser import extract_paragraphs
from .align import diff_ops, detect_moves
from .refine import pair_modified, inline_diff
from .seqdiff import trim_common

def diff_docx(old_path: str, new_path: str) -> list[dict]:
    a = extract_paragraphs(old_path)
    b = extract_paragraphs(new_path)

    # 掐头去尾:公共前缀必属于某个最优解,数学上安全
    head, tail = trim_common(a, b)

    mid_a = a[head : len(a) - tail] if tail > 0 else a[head:]
    mid_b = b[head : len(b) - tail] if tail > 0 else b[head:]

    # 1. 算法内核处理
    mid_ops = diff_ops(mid_a, mid_b)
    mid_ops = detect_moves(mid_ops, mid_a, mid_b)
    # 2. 接入 Day 8-9 的相似段落配对
    mid_ops = pair_modified(mid_ops, mid_a, mid_b)

    ops = []

    # 补齐头部 unchanged
    for i in range(head):
        ops.append({"op": "unchanged", "old_idx": i, "new_idx": i})

    # 修正中间坐标并挂载 inline 差异
    for op in mid_ops:
        new_op = op.copy()
        if "old_idx" in new_op:
            new_op["old_idx"] += head
        if "new_idx" in new_op:
            new_op["new_idx"] += head
        
        # 为合并成功的 modified 挂载段内差异
        if new_op["op"] == "modified":
            old_text = a[new_op["old_idx"]]
            new_text = b[new_op["new_idx"]]
            new_op["inline"] = inline_diff(old_text, new_text)

        ops.append(new_op)

    # 补齐尾部 unchanged
    a_tail_start = len(a) - tail
    b_tail_start = len(b) - tail
    for i in range(tail):
        ops.append({
            "op": "unchanged",
            "old_idx": a_tail_start + i,
            "new_idx": b_tail_start + i
        })

    return ops

if __name__ == "__main__":
    import sys, json
    ops = diff_docx(sys.argv[1], sys.argv[2])
    for op in ops:
        print(json.dumps(op, ensure_ascii=False))