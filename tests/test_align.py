from docdiff.align import diff_ops, detect_moves

def assert_indices_complete(ops, a, b):
    """
    加分项防线：验证旧文档和新文档的每一个下标是否不多不少恰好出现一次。
    这能有效防止段落被“重复渲染”或“意外丢失”。
    """
    old_indices = []
    new_indices = []
    
    for op in ops:
        if "old_idx" in op:
            old_indices.append(op["old_idx"])
        if "new_idx" in op:
            new_indices.append(op["new_idx"])
            
    # 增加详细报错信息，一旦失败能立刻看清缺了哪个、多了哪个
    assert sorted(old_indices) == list(range(len(a))), f"old_idx 错乱! 收集到: {sorted(old_indices)}, 期望: {list(range(len(a)))}"
    assert sorted(new_indices) == list(range(len(b))), f"new_idx 错乱! 收集到: {sorted(new_indices)}, 期望: {list(range(len(b)))}"


def test_identical():
    """测试完全相同的文档"""
    a = ["a", "b"]
    b = ["a", "b"]
    ops = diff_ops(a, b)
    assert len(ops) == 2
    assert all(o["op"] == "unchanged" for o in ops)
    assert_indices_complete(ops, a, b)  # 👈 终极防线

def test_insert_head():
    """测试在开头插入内容（验证不会引发索引雪崩）"""
    a = ["a", "b"]
    b = ["x", "a", "b"]
    ops = diff_ops(a, b)
    assert sum(1 for o in ops if o["op"] == "inserted") == 1
    assert sum(1 for o in ops if o["op"] == "unchanged") == 2
    assert_indices_complete(ops, a, b)  # 👈 终极防线

def test_all_different():
    """测试完全不同的文档（没有交集）"""
    a = ["a", "b"]
    b = ["c", "d"]
    ops = diff_ops(a, b)
    assert sum(1 for o in ops if o["op"] == "deleted") == 2
    assert sum(1 for o in ops if o["op"] == "inserted") == 2
    assert_indices_complete(ops, a, b)  # 👈 终极防线

def test_empty_side():
    """测试一边为空的极端情况"""
    a = []
    b = ["x", "y"]
    ops = diff_ops(a, b)
    assert all(o["op"] == "inserted" for o in ops)
    assert len(ops) == 2
    assert_indices_complete(ops, a, b)  # 👈 终极防线

    # 反过来测试删除
    ops2 = diff_ops(b, a)
    assert all(o["op"] == "deleted" for o in ops2)
    assert len(ops2) == 2
    assert_indices_complete(ops2, b, a) # 👈 终极防线

def test_move_detected():
    """测试移动操作能否被正确识别"""
    a = ["甲", "乙", "丙", "丁", "戊"]
    b = ["甲", "丁", "乙", "丙", "戊"]
    raw_ops = diff_ops(a, b)
    final_ops = detect_moves(raw_ops, a, b)
    
    moves = [o for o in final_ops if o["op"] == "moved"]
    assert len(moves) == 1
    assert moves[0]["old_idx"] == 3
    assert moves[0]["new_idx"] == 1
    assert_indices_complete(final_ops, a, b)  # 👈 终极防线

def test_duplicate_paragraphs():
    """测试包含重复段落的移动（验证贪心配对逻辑不崩溃）"""
    a = ["重复", "重复", "独有"]
    b = ["独有", "重复", "重复"]
    raw_ops = diff_ops(a, b)
    final_ops = detect_moves(raw_ops, a, b)
    
    moves = [o for o in final_ops if o["op"] == "moved"]
    assert len(moves) == 1
    assert moves[0]["old_idx"] == 2
    assert moves[0]["new_idx"] == 0
    assert_indices_complete(final_ops, a, b)  # 👈 终极防线