def lcs_table(a: list[str], b: list[str]) -> list[list[int]]:
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp

def diff_ops(a: list[str], b: list[str]) -> list[dict]:
    dp = lcs_table(a, b)
    ops = []
    i, j = len(a), len(b)
    while i > 0 or j > 0:
        if i > 0 and j > 0 and a[i - 1] == b[j - 1]:
            ops.append({"op": "unchanged", "old_idx": i - 1, "new_idx": j - 1})
            i -= 1
            j -= 1
        elif j > 0 and (i == 0 or dp[i][j - 1] >= dp[i - 1][j]):
            ops.append({"op": "inserted", "new_idx": j - 1})
            j -= 1
        else:
            ops.append({"op": "deleted", "old_idx": i - 1})
            i -= 1
    return list(reversed(ops))

def detect_moves(ops: list[dict], a: list[str], b: list[str]) -> list[dict]:
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