"""experiments/gen_big_docx.py — 手工拼最小合法 docx,用于性能测试

只用 zipfile 拼 [Content_Types].xml、_rels/.rels、word/document.xml 三个部件,
不引 python-docx(顺手保住零依赖)。生成的 samples/big_*.docx 不进 git。

用法:
  python3 experiments/gen_big_docx.py 500 50 samples/big_a.docx
  python3 experiments/gen_big_docx.py 500 50 samples/big_b.docx --mutate 25
"""
import argparse
import zipfile

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' \
    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">' \
    '<w:body>'
DOC_TAIL = '<w:sectPr/></w:body></w:document>'


def _para_text(i: int, m: int, mutate: bool) -> str:
    # 句状文本(带句号),更贴近真实文档,也能让长段落真正走到句级细化路径
    unit = f"这是第{i}段内容。"
    text = unit * (m // len(unit)) + unit[: m % len(unit)]
    if mutate:
        # 段中间替换 5 个字,相似度仍 > 0.7,会走 modified + 段内细化路径
        mid = len(text) // 2
        text = text[:mid] + "改改改改改" + text[mid + 5:]
    return text


def _para(text: str) -> str:
    return f'<w:p><w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'


def _cell(text: str) -> str:
    return f"<w:tc>{_para(text)}</w:tc>"


def _table(k: int, mutate: bool) -> str:
    """4 行 3 列的小表,表头带编号当指纹;mutate 时改一个数据格。"""
    rows = [
        [f"表{k}姓名", f"表{k}部门", f"表{k}状态"],
        ["张三", "技术部", "在职"],
        ["李四", "运营部" if mutate else "市场部", "在职"],
        ["王五", "人事部", "在职"],
    ]
    trs = "".join(f"<w:tr>{''.join(_cell(c) for c in row)}</w:tr>" for row in rows)
    grid = "<w:tblGrid>" + "<w:gridCol/>" * 3 + "</w:tblGrid>"
    return f"<w:tbl><w:tblPr/>{grid}{trs}</w:tbl>"


def build(out_path: str, n: int, m: int, mutate: int, tables: int) -> None:
    mutate_idxs = set(range(0, n, max(1, n // mutate))) if mutate else set()
    body = "".join(
        _para(_para_text(i, m, i in mutate_idxs))
        for i in range(n)
    )
    # 表格接在段落流后面;改第 2 张表的一个格,模拟"表头指纹不变的行内修改"
    body += "".join(_table(k, mutate and k == 1) for k in range(tables))
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", DOC_HEAD + body + DOC_TAIL)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="生成最小合法 docx 用于性能测试")
    p.add_argument("n", type=int, help="段落数")
    p.add_argument("m", type=int, help="每段字数")
    p.add_argument("out", help="输出路径")
    p.add_argument("--mutate", type=int, default=0, help="改动 K 段(取整分布)")
    p.add_argument("--tables", type=int, default=0, help="段落后追加 N 张 4x3 表格")
    args = p.parse_args()
    build(args.out, args.n, args.m, args.mutate, args.tables)
    print(f"ok: {args.out} ({args.n} 段 × {args.m} 字, mutate={args.mutate}, tables={args.tables})")
