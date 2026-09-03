from docdiff.model import Block


# Block.key() 的四种情形
def test_key_paragraph():
    assert Block(kind="paragraph", text="第一段").key() == "第一段"


def test_key_table_uses_header():
    b = Block(kind="table", rows=[
        ["姓名", "部门", "备注"],
        ["张三", "技术部", ""],
    ])
    assert b.key() == "TBL:姓名\x1f部门\x1f备注"
    # 内容变了但表头没变 -> key 不变
    b2 = Block(kind="table", rows=[
        ["姓名", "部门", "备注"],
        ["李四", "市场部", "新员工"],
    ])
    assert b2.key() == b.key()


def test_key_empty_table():
    assert Block(kind="table", rows=[]).key() == "TBL:"


def test_key_different_tables():
    b1 = Block(kind="table", rows=[["A", "B"]])
    b2 = Block(kind="table", rows=[["X", "Y"]])
    assert b1.key() != b2.key()


# 表格 __eq__ 语义:身份相等(表头同)而非内容相等
def test_table_eq_identity_not_content():
    b1 = Block(kind="table", rows=[
        ["姓名", "部门"],
        ["张三", "技术部"],
    ])
    b2 = Block(kind="table", rows=[
        ["姓名", "部门"],
        ["李四", "市场部"],  # 内容完全不同
    ])
    # 表头相同 -> 文档级 LCS 认为"是同一个表格",内部差异交给 tablediff
    assert b1 == b2


def test_table_eq_different_header():
    b1 = Block(kind="table", rows=[["姓名", "部门"]])
    b2 = Block(kind="table", rows=[["员工", "部门"]])
    assert b1 != b2


def test_table_eq_cross_kind():
    b1 = Block(kind="table", rows=[["姓名"]])
    b2 = Block(kind="paragraph", text="TBL:姓名")
    # 段落文本恰好与表格 key 撞车时,kind 也要不同
    assert b1 != b2
