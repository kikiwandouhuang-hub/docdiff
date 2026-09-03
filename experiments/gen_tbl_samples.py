"""experiments/gen_tbl_samples.py — 生成 V2-C 表格验金石(五份 docx)

手工拼 XML 而不是开 Word,保证内容可控、可复现:
- tbl_old.docx   12 段照旧,第 6 段后插入 4 行 × 3 列表格(第 1 行表头)
- tbl_new1.docx  改单元格:李四的部门 市场部 -> 运营部
- tbl_new2.docx  插行:张三后插入赵六一整行
- tbl_new3.docx  移动行:最后一行(王五)剪切到张三后面
- tbl_new4.docx  插列(负样本):整表新增第 4 列"状态",期望合理失败

用法: python3 experiments/gen_tbl_samples.py
"""
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # 让 experiments/ 目录外也能直接跑

from docdiff.parser import extract_paragraphs

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
SAMPLES = Path(__file__).parent.parent / "samples"

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

TABLE_OLD = [
    ["姓名", "部门", "备注"],
    ["张三", "技术部", "负责核心模块"],
    ["李四", "市场部", "负责对外宣传"],
    ["王五", "人事部", "负责招聘培训"],
]

TABLE_NEW1 = [r[:] for r in TABLE_OLD]
TABLE_NEW1[2][1] = "运营部"  # 李四的部门

TABLE_NEW2 = TABLE_OLD[:2] + [["赵六", "财务部", "负责预算管理"]] + TABLE_OLD[2:]  # 插行

TABLE_NEW3 = [TABLE_OLD[0], TABLE_OLD[1], TABLE_OLD[3], TABLE_OLD[2]]  # 王五上移

TABLE_NEW4 = [r + [v] for r, v in zip(TABLE_OLD, ["状态", "在职", "在职", "在职"], strict=True)]  # 插列


def _para(text: str) -> str:
    return f'<w:p><w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'


def _cell(text: str) -> str:
    return f"<w:tc>{_para(text)}</w:tc>"


def _table(rows: list[list[str]]) -> str:
    grid = "<w:tblGrid>" + "<w:gridCol/>" * len(rows[0]) + "</w:tblGrid>"
    body = "".join(
        "<w:tr>" + "".join(_cell(c) for c in row) + "</w:tr>" for row in rows
    )
    return (
        "<w:tbl>"
        '<w:tblPr><w:tblW w:w="0" w:type="auto"/></w:tblPr>'
        f"{grid}{body}"
        "</w:tbl>"
    )


def build(out_path: Path, paras: list[str], table_rows: list[list[str]]) -> None:
    # 第 6 段后插入表格:前 6 段 + 表格 + 后 6 段
    first = "".join(_para(p) for p in paras[:6])
    rest = "".join(_para(p) for p in paras[6:])
    doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W}"><w:body>'
        f"{first}{_table(table_rows)}{rest}"
        "<w:sectPr/></w:body></w:document>"
    )
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", doc)


if __name__ == "__main__":
    paras = extract_paragraphs(str(SAMPLES / "old.docx"))
    build(SAMPLES / "tbl_old.docx", paras, TABLE_OLD)
    build(SAMPLES / "tbl_new1.docx", paras, TABLE_NEW1)
    build(SAMPLES / "tbl_new2.docx", paras, TABLE_NEW2)
    build(SAMPLES / "tbl_new3.docx", paras, TABLE_NEW3)
    build(SAMPLES / "tbl_new4.docx", paras, TABLE_NEW4)
    print("ok: tbl_old / tbl_new1 / tbl_new2 / tbl_new3 / tbl_new4 已生成")
