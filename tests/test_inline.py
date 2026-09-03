from docdiff.refine import inline_diff


# 用例 1：改一词 —— 词级边界,周围内容保持 equal
def test_change_word():
    res = inline_diff("这是第一段,讲问题。", "这是第一段,讨论问题。")
    assert res == [
        {"tag": "equal", "text": "这是第一段,"},
        {"tag": "delete", "text": "讲"},
        {"tag": "insert", "text": "讨论"},
        {"tag": "equal", "text": "问题。"},
    ]


# 用例 2：删一词
def test_delete_word():
    res = inline_diff("今天天气很好。", "今天天气好。")
    assert res == [
        {"tag": "equal", "text": "今天天气"},
        {"tag": "delete", "text": "很"},
        {"tag": "equal", "text": "好。"},
    ]


# 用例 3：增一词
def test_insert_word():
    res = inline_diff("今天天气好。", "今天天气很好。")
    assert res == [
        {"tag": "equal", "text": "今天天气"},
        {"tag": "insert", "text": "很"},
        {"tag": "equal", "text": "好。"},
    ]


# 用例 4：完全不同 —— 整体替换,不产生碎片
def test_totally_different():
    res = inline_diff("甲乙丙", "丁戊己")
    assert res == [
        {"tag": "delete", "text": "甲乙丙"},
        {"tag": "insert", "text": "丁戊己"},
    ]


# 用例 5：一边为空
def test_one_side_empty():
    assert inline_diff("", "abc") == [{"tag": "insert", "text": "abc"}]
    assert inline_diff("abc", "") == [{"tag": "delete", "text": "abc"}]
    assert inline_diff("", "") == []


# 反碎片断言：连续删除多个字,delete 项的数量应为 1
def test_no_fragmentation():
    res = inline_diff("这是第一段,讲问题。", "这是第一段,。")
    deletes = [item for item in res if item["tag"] == "delete"]
    assert len(deletes) == 1
    assert deletes[0]["text"] == "讲问题"


# 英文按整词对齐:function -> functions 不应高亮成"多了个 s"
def test_english_whole_word():
    res = inline_diff("The function is broken", "The functions are broken")
    deletes = [item for item in res if item["tag"] == "delete"]
    inserts = [item for item in res if item["tag"] == "insert"]
    assert any(item["text"] == "function" for item in deletes)
    assert any(item["text"] == "functions" for item in inserts)
    # 不出现只插入单个字符的碎片
    assert all(len(item["text"]) > 1 for item in deletes + inserts)
