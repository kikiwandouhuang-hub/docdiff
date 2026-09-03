import re

from docdiff.tokenize import _is_cjk, tokenize


def _normalize_ws(text: str) -> str:
    """把所有连续空白折叠成单个空格——tokenize 的往返不变量以此为基准。"""
    return re.sub(r"\s+", " ", text)


# 用例 1：往返一致 —— 与原文的差异只在空白折叠上
def test_roundtrip():
    texts = [
        "这是第一段,讲背景。",
        "调用 extract_paragraphs() 函数,返回 list[str]。",
        "Hello  world, it's a test-case 123.",
        "他\n\n说\t了。",
        "中英混排 mix 123-45 和 list[str] 都要对。",
    ]
    for t in texts:
        assert "".join(tokenize(t)) == _normalize_ws(t)


# 用例 2：空字符串
def test_empty():
    assert tokenize("") == []


# 用例 3：纯中文 —— 每个汉字一个 token,全角标点独立
def test_pure_cjk():
    assert tokenize("这是第一段") == ["这", "是", "第", "一", "段"]
    assert tokenize("讲背景。") == ["讲", "背", "景", "。"]


# 用例 4：中英混排 —— 拉丁连续成词,CJK 逐字,ASCII 标点独立
def test_mixed():
    assert tokenize("调用 extract_paragraphs() 函数") == [
        "调", "用", " ", "extract_paragraphs", "(", ")", " ", "函", "数",
    ]
    assert tokenize("list[str]") == ["list", "[", "str", "]"]
    # 英文与中文紧贴时也必须分开(isalnum 对汉字为 True 的回归保护)
    assert tokenize("extract_paragraphs函数") == ["extract_paragraphs", "函", "数"]


# 附带：_is_cjk 的区间判断
def test_is_cjk_ranges():
    assert _is_cjk("汉") and _is_cjk("。") and _is_cjk("Ａ")
    assert not _is_cjk("a") and not _is_cjk(".") and not _is_cjk(" ")
