import zipfile
import xml.etree.ElementTree as ET

from .model import Block

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _read_body(docx_path: str):
    with zipfile.ZipFile(docx_path, 'r') as z:
        xml_bytes = z.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    return root.find(W_NS + "body")


def _paragraph_text(p) -> str:
    """把一个 w:p 下所有 w:t 拼起来。
    这里用 iter 是**对的**:段落内部的 run 嵌套(w:hyperlink / w:ins 里的 run)
    都应该被拼进来。递归在段落内是特性,在 body 层是 bug。
    """
    texts = [t.text or "" for t in p.iter(W_NS + "t")]
    return "".join(texts)


def _run_fmt(rpr) -> dict:
    """单个 run 的格式指纹,只取五项(bold/italic/underline/size/color)。
    V2 只做直接格式:样式继承(w:pStyle -> styles.xml)不解析,这是已知边界。"""
    fmt = {"bold": False, "italic": False, "underline": None, "size": None, "color": None}
    if rpr is None:
        return fmt
    for child in rpr:
        tag = child.tag
        if tag == W_NS + "b":
            # <w:b/> 即开;显式 w:val="0"/"false" 是关(覆盖样式继承时会出现)
            val = child.get(W_NS + "val")
            fmt["bold"] = val not in ("0", "false", "off")
        elif tag == W_NS + "i":
            val = child.get(W_NS + "val")
            fmt["italic"] = val not in ("0", "false", "off")
        elif tag == W_NS + "u":
            # val 缺省为 single;<w:u w:val="none"/> 是"无下划线"
            val = child.get(W_NS + "val", "single")
            fmt["underline"] = None if val in ("none", "0") else val
        elif tag == W_NS + "sz":
            val = child.get(W_NS + "val")
            # w:sz 单位是半磅:val=24 才是 12pt,必须除 2
            fmt["size"] = int(val) / 2 if val else None
        elif tag == W_NS + "color":
            fmt["color"] = child.get(W_NS + "val")
    return fmt


def _fmt_fingerprint(p) -> dict | None:
    """段落的格式指纹:取多数 run 的值;run 间不一致时记 mixed=True。
    没有 run 的段落(空段)返回 None,不参与格式对比。"""
    run_fmts = [_run_fmt(r.find(W_NS + "rPr")) for r in p.findall(W_NS + "r")]
    if not run_fmts:
        return None
    out = {}
    for attr in ("bold", "italic", "underline", "size", "color"):
        values = [f[attr] for f in run_fmts]
        if all(v == values[0] for v in values):
            out[attr] = values[0]
        else:
            # 多数值;并列时取先出现的 run 的值(dict.fromkeys 保序去重)
            out[attr] = max(dict.fromkeys(values), key=values.count)
            out["mixed"] = True
    out.setdefault("mixed", False)
    return out


def _parse_paragraph(p) -> Block:
    return Block(kind="paragraph", text=_paragraph_text(p), fmt=_fmt_fingerprint(p))


def _cell_text(tc) -> str:
    """单元格内可能有多个段落,用换行连接。"""
    paras = [_paragraph_text(p) for p in tc.findall(W_NS + "p")]
    return "\n".join(paras)


def _has_merged_cells(tc) -> bool:
    """检测 w:gridSpan(横向合并)或 w:vMerge(纵向合并)。"""
    tc_pr = tc.find(W_NS + "tcPr")
    if tc_pr is None:
        return False
    return (
        tc_pr.find(W_NS + "gridSpan") is not None
        or tc_pr.find(W_NS + "vMerge") is not None
    )


def _parse_table(tbl) -> Block:
    # findall 不递归,避开嵌套表格
    rows = []
    has_merged = False
    for tr in tbl.findall(W_NS + "tr"):
        cells = []
        for tc in tr.findall(W_NS + "tc"):
            cells.append(_cell_text(tc))
            if _has_merged_cells(tc):
                has_merged = True
        rows.append(cells)
    block = Block(kind="table", rows=rows)
    if has_merged:
        # 知道自己的边界并说出来,比假装支持强
        block.fmt = {"unsupported": "merged_cells"}
    return block


def extract_blocks(docx_path: str) -> list[Block]:
    """v2 主接口:按文档顺序输出段落/表格 Block 列表。
    与 v1 最关键的区别:只遍历 body 的**直接子节点**——
    v1 的 body.iter(w:p) 是递归的,会把表格单元格里的段落混进段落流。
    """
    body = _read_body(docx_path)
    blocks = []
    if body is None:
        return blocks
    for child in body:
        if child.tag == W_NS + "p":
            blocks.append(_parse_paragraph(child))
        elif child.tag == W_NS + "tbl":
            blocks.append(_parse_table(child))
        # 其他(sectPr / sdt / bookmarkStart 等)先忽略
    return blocks


def extract_paragraphs(docx_path: str) -> list[str]:
    """v1 兼容层 —— 不要删。
    现有的 render_term / render_html 和测试全靠它。
    """
    return [b.text for b in extract_blocks(docx_path) if b.kind == "paragraph"]


if __name__ == "__main__":
    import sys
    for i, block in enumerate(extract_blocks(sys.argv[1])):
        if block.kind == "table":
            print(f"[{i}] TABLE {len(block.rows)}x{len(block.rows[0]) if block.rows else 0}")
        else:
            print(f"[{i}] {block.text}")
