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
            ops.append({"op": "equal", "a": a[i - 1], "b": b[j - 1]})
            i -= 1
            j -= 1
        elif j > 0 and (i == 0 or dp[i][j - 1] >= dp[i - 1][j]):
            ops.append({"op": "insert", "a": None, "b": b[j - 1]})
            j -= 1
        else:
            ops.append({"op": "delete", "a": a[i - 1], "b": None})
            i -= 1
    return list(reversed(ops))

def detect_moves(ops: list[dict]) -> list[dict]:
    text_to_delete_op = {}
    for op in ops:
        if op["op"] == "delete":
            text = op["a"]
            if text not in text_to_delete_op:
                text_to_delete_op[text] = []
            text_to_delete_op[text].append(op)

    moved_ops_map = {}
    matched_inserts = set()
    
    for op in ops:
        if op["op"] == "insert":
            text = op["b"]
            if text in text_to_delete_op and text_to_delete_op[text]:
                del_op = text_to_delete_op[text].pop(0)
                moved_ops_map[id(del_op)] = {
                    "op": "moved",
                    "a": text,
                    "b": text
                }
                matched_inserts.add(id(op))

    new_ops = []
    for op in ops:
        if id(op) in moved_ops_map:
            new_ops.append(moved_ops_map[id(op)])
        elif id(op) in matched_inserts:
            continue
        else:
            new_ops.append(op)

    return new_ops


if __name__ == "__main__":
    a = ["甲", "乙", "丙", "丁", "戊"]
    b = ["甲", "丁", "乙", "丙", "戊"]

    raw_ops = diff_ops(a, b)

    final_ops = detect_moves(raw_ops)  

    for op in final_ops:
        print(op)