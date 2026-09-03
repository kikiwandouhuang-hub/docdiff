from docdiff.refine import _expected_new_idx, pair_modified


# 用例 1：就地修改 (dist=0 的候选正常配成 modified - 回归保护)
def test_in_place_modification():
    a = ["锚点1", "这是一个将被就地修改的测试段落，相似度很高", "锚点2"]
    b = ["锚点1", "这是一个已被就地修改的测试段落，相似度极高", "锚点2"]
    ops = [
        {"op": "unchanged", "old_idx": 0, "new_idx": 0},
        {"op": "deleted", "old_idx": 1},
        {"op": "inserted", "new_idx": 1},  # old=1, a_old=0, expected=1. dist = |1-1| = 0
        {"op": "unchanged", "old_idx": 2, "new_idx": 2}
    ]
    res = pair_modified(ops, a, b)
    assert any(op["op"] == "modified" and op["old_idx"] == 1 for op in res)


# 用例 2：远距离模板句 (amb_old vs amb_new -> 0 个 modified, 1删1增)
def test_distant_template():
    # 模拟 samples 中第 3 段被删，在第 10 段被添加
    a = [
        "背景", "架构", "项目编号：2023-A-001",
        "占位4", "占位5", "占位6", "占位7", "占位8", "占位9", "结束",
    ]
    b = [
        "背景", "架构",
        "占位4", "占位5", "占位6", "占位7", "占位8", "占位9", "结束",
        "项目编号：2024-B-002",
    ]
    ops = [
        {"op": "unchanged", "old_idx": 0, "new_idx": 0},
        {"op": "unchanged", "old_idx": 1, "new_idx": 1},
        {"op": "deleted", "old_idx": 2},   # 依据前面锚点，expected_new_idx = 2
        {"op": "unchanged", "old_idx": 9, "new_idx": 8},
        {"op": "inserted", "new_idx": 9}   # dist = |9 - 2| = 7 (远远大于 2)
    ]
    res = pair_modified(ops, a, b)
    
    # 核心断言：不能出现 modified，必须保持原始的 1删 1增
    assert not any(op["op"] == "modified" for op in res)
    assert any(op["op"] == "deleted" and op["old_idx"] == 2 for op in res)
    assert any(op["op"] == "inserted" and op["new_idx"] == 9 for op in res)


# 用例 3：窗口边界 (dist 恰好 = 2 配对, = 3 不配对)
def test_window_boundaries():
    a = ["锚点", "测试边界的一段话，字数稍微多一点点以满足阈值", "占位", "占位", "占位"]
    
    # 子测试 A：dist = 2 (允许配对)
    b_dist_2 = ["锚点", "占位", "占位", "测试边界的这段话，字数稍微多一点点来满足阈值", "占位"]
    ops_dist_2 = [
        {"op": "unchanged", "old_idx": 0, "new_idx": 0},
        {"op": "deleted", "old_idx": 1},   # expected = 1
        {"op": "inserted", "new_idx": 3}   # dist = |3 - 1| = 2
    ]
    res_2 = pair_modified(ops_dist_2, a, b_dist_2)
    assert any(op["op"] == "modified" for op in res_2)
    
    # 子测试 B：dist = 3 (拒绝配对)
    b_dist_3 = ["锚点", "占位", "占位", "占位", "测试边界的这段话，字数稍微多一点点来满足阈值"]
    ops_dist_3 = [
        {"op": "unchanged", "old_idx": 0, "new_idx": 0},
        {"op": "deleted", "old_idx": 1},   # expected = 1
        {"op": "inserted", "new_idx": 4}   # dist = |4 - 1| = 3
    ]
    res_3 = pair_modified(ops_dist_3, a, b_dist_3)
    assert not any(op["op"] == "modified" for op in res_3)


# 用例 4：无锚点 (手造 a、b 完全不同, 退化为 old_idx 不崩)
def test_no_anchor():
    # 当两篇文章毫无共同之处 (LCS 长度 0)，anchors 为空列表
    # 期望 _expected_new_idx 直接返回传入的 old_idx 本身
    assert _expected_new_idx(5, []) == 5