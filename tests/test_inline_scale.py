from docdiff.refine import inline_diff

# 规模上限:超过 MAX_TOKEN_PRODUCT(500_000)后走句级两级细化或 difflib 兜底。
# 这里用 800×800 字的输入触发两条降级路径。


def _make_para(n_sent: int) -> str:
    """n_sent 个句子,每个约 20 字。"""
    return "".join(f"这是第{i}句,用来测试长段落的句级对齐路径。" for i in range(n_sent))


# 用例 1:句级路径 —— 长段落只改中间一句,修改应被精确定位
def test_sentence_path_precise():
    old = _make_para(40)  # 800+ 字,token 积 > 500_000
    new = old.replace("这是第20句", "这是第二十句")
    res = inline_diff(old, new)

    deletes = [it for it in res if it["tag"] == "delete"]
    inserts = [it for it in res if it["tag"] == "insert"]
    # 只改了一句,且定位到词级:delete/insert 各恰好一块("20" 是独立数字 token)
    assert len(deletes) == 1 and len(inserts) == 1
    assert deletes[0]["text"] == "20"
    assert inserts[0]["text"] == "二十"


# 用例 2:全文一句(切句切不开)—— difflib 兜底,不崩、不卡、可重建原文
def test_single_sentence_fallback():
    old = "字" * 800   # 无任何句边界
    new = old[:400] + "改" + old[401:]
    res = inline_diff(old, new)

    assert sum(1 for it in res if it["tag"] == "delete") >= 1
    assert sum(1 for it in res if it["tag"] == "insert") >= 1


# 往返不变量(三条路径通用):equal+delete 按序拼接 = 旧文本,equal+insert = 新文本
def test_roundtrip_invariant_all_paths():
    pairs = [
        ("甲乙丙丁戊", "甲己丙丁戊"),                       # 词级路径
        ("The function is broken", "The functions are broken"),
        ("", "abc"),                                       # 空边
        (_make_para(40), _make_para(40).replace("第20句", "第二十句")),   # 句级路径
        ("字" * 800, "字" * 400 + "改" + "字" * 399),       # difflib 兜底
    ]
    for old, new in pairs:
        items = inline_diff(old, new)
        old_rebuilt = "".join(it["text"] for it in items if it["tag"] in ("equal", "delete"))
        new_rebuilt = "".join(it["text"] for it in items if it["tag"] in ("equal", "insert"))
        assert old_rebuilt == old, f"旧文本重建失败: {old[:30]}..."
        assert new_rebuilt == new, f"新文本重建失败: {new[:30]}..."
