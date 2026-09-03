from .parser import extract_blocks
from .align import diff_ops, detect_moves
from .refine import pair_modified, inline_diff
from .seqdiff import trim_common

def diff_docx(old_path: str, new_path: str) -> list[dict]:
    a = extract_blocks(old_path)
    b = extract_blocks(new_path)

    # 用键对齐,用下标索引载荷:掐头去尾、LCS、移动检测、配对全部作用在 key() 上,
    # 而 ops 里的 old_idx / new_idx 依然指向 a / b。
    # 这个分离让后面加载荷字段(fmt、rows)不需要碰算法层一行。
    keys_a = [x.key() for x in a]
    keys_b = [x.key() for x in b]

    # 掐头去尾:公共前缀必属于某个最优解,数学上安全
    head, tail = trim_common(keys_a, keys_b)

    mid_a = keys_a[head : len(keys_a) - tail] if tail > 0 else keys_a[head:]
    mid_b = keys_b[head : len(keys_b) - tail] if tail > 0 else keys_b[head:]

    # 1. 算法内核处理
    mid_ops = diff_ops(mid_a, mid_b)
    mid_ops = detect_moves(mid_ops, mid_a, mid_b)
    # 2. 相似配对:段落按文本、表格按行级 LCS 覆盖率(V2-C 身份配对)
    #    pair_modified 需要 Block 载荷才能拿到 rows,传块切片;
    #    ops 里的 old_idx / new_idx 仍指向 a / b 的下标。
    mid_blocks_a = a[head : len(a) - tail] if tail > 0 else a[head:]
    mid_blocks_b = b[head : len(b) - tail] if tail > 0 else b[head:]
    mid_ops = pair_modified(mid_ops, mid_blocks_a, mid_blocks_b)

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
        # (表格的 modified 在 V2-C 3.4 挂载行级 rows,这里先跳过)
        if new_op["op"] == "modified" and a[new_op["old_idx"]].kind == "paragraph":
            old_text = a[new_op["old_idx"]].text
            new_text = b[new_op["new_idx"]].text
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
