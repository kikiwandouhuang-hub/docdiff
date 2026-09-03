"""experiments/gen_fmt_samples.py — 格式变更样本生成器

fmt_new1.docx = old.docx 只把第 4 段(段落四)加粗,文本零改动
fmt_new2.docx = new1.docx 把段落三加粗(文本与格式同时变,验 modified+changes)

只拼 zip,不引 python-docx(保住零依赖)。
用法: python3 experiments/gen_fmt_samples.py
"""
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "samples" / "old.docx"
NEW1 = ROOT / "samples" / "new1.docx"


def _inject_bold(doc_xml: str, marker: str) -> str:
    """把含 marker 文本的段落里所有 run 的 rPr 注入 <w:b/>(整段加粗)。"""
    paras = re.findall(r"<w:p\b.*?</w:p>", doc_xml, re.S)
    for p in paras:
        if marker not in p:
            continue
        # 目标 run 的 rPr 紧跟 <w:r>;pPr 里也有 rPr(段标属性),不能动。
        # 段落可能有多个 run(文本改过的段落常被拆成几段 run),全部加粗
        # 才是"整段加粗",否则指纹会如实报 mixed。
        bolded = p.replace("<w:r><w:rPr>", "<w:r><w:rPr><w:b/><w:bCs/>")
        assert bolded != p, f"未找到可注入的 run rPr: {p[:80]}"
        return doc_xml.replace(p, bolded, 1)
    raise AssertionError(f"样本里没有含 '{marker}' 的段落")


def build(out_path: Path, src: Path, marker: str) -> None:
    with zipfile.ZipFile(src) as z:
        names = z.namelist()
        content = {n: z.read(n) for n in names}
    doc = content["word/document.xml"].decode("utf-8")
    content["word/document.xml"] = _inject_bold(doc, marker).encode("utf-8")
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in content.items():
            z.writestr(n, data)
    print(f"ok: {out_path} ({marker} 段加粗)")


if __name__ == "__main__":
    build(ROOT / "samples" / "fmt_new1.docx", SRC, "段落四")
    build(ROOT / "samples" / "fmt_new2.docx", NEW1, "段落三")
