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

if __name__ == "__main__":

    a=["This is a test.", "This is another test.", "This is the last test."]
    b=["This is a test.", "This is a modified test.", "This is the last test."]
    for op in diff_ops(a, b):
        print(op)