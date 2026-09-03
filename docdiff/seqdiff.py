"""seqdiff.py — 与领域无关的通用序列对齐层
被 align.py(段落序列)、refine.py(token 序列)、tablediff.py(行序列)共用。
这一层不知道什么是 docx,不知道什么是段落 —— 只认 Sequence[T] 和 ==。
"""
from typing import Sequence, TypeVar

T = TypeVar("T")


def lcs_table(a: Sequence[T], b: Sequence[T]) -> list[list[int]]:
    """计算 LCS 的 DP 表。
    dp[i][j] = a 的前 i 个元素与 b 的前 j 个元素的最长公共子序列长度。
    """
    m, n = len(a), len(b)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp


def diff_ops(a: Sequence[T], b: Sequence[T]) -> list[dict]:
    """回溯 DP 表,输出操作列表,按新文档顺序排列。
    操作格式:
      {"op": "unchanged", "old_idx": i, "new_idx": j}
      {"op": "deleted",   "old_idx": i}
      {"op": "inserted",  "new_idx": j}
    """
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


def trim_common(a: Sequence[T], b: Sequence[T]) -> tuple[int, int]:
    """掐头去尾,返回 (head, tail)。
    注意 head + tail 不能超过 min(len(a), len(b))——
    两个列表完全相同时,朴素写法会把同一段既算进 head 又算进 tail。
    """
    min_len = min(len(a), len(b))

    head = 0
    while head < min_len and a[head] == b[head]:
        head += 1

    tail = 0
    while (
        tail < min_len - head
        and a[len(a) - 1 - tail] == b[len(b) - 1 - tail]
    ):
        tail += 1

    return head, tail
