import zipfile
import xml.etree.ElementTree as ET

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

def extract_paragraphs(docx_path: str) -> list[str]:
    with zipfile.ZipFile(docx_path, 'r') as z:
        xml_bytes = z.read("word/document.xml")

    root = ET.fromstring(xml_bytes)

    body = root.find(W_NS + "body")

    paragraphs = []
    if body is not None:
        for p in body.iter(W_NS + "p"):
            texts = [t.text or "" for t in p.iter(W_NS + "t")]
            para = "".join(texts)
            paragraphs.append(para)

    return paragraphs


if __name__ == "__main__":
    import sys
    for i, para in enumerate(extract_paragraphs(sys.argv[1])):
        print(f"[{i}] {para}")