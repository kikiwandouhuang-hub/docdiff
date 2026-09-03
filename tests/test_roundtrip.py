"""V2-D 往返自验证:--embed-text 生成的 JSON 必须真的自包含。

验收标准(手册 4.2):直接从 docx 渲染的 HTML 和"JSON 往返后再渲染"的 HTML
逐字节一致——这证明渲染层只依赖 (ops, blocks),不依赖 docx。
"""
import json
import subprocess
import sys
from pathlib import Path

from docdiff import SCHEMA, __version__
from docdiff.cli import build_envelope
from docdiff.core import diff_docx
from docdiff.model import block_from_dict
from docdiff.parser import extract_blocks
from docdiff.render_html import render as render_html

SAMPLES = Path(__file__).parent.parent / "samples"
PAIRS = [
    ("old.docx", "new1.docx"),
    ("tbl_old.docx", "tbl_new1.docx"),
    ("tbl_old.docx", "tbl_new3.docx"),
]


def _roundtrip(old_name: str, new_name: str) -> tuple[str, str]:
    """直接渲染 -> a.html;JSON 信封往返 -> b.html。返回两者内容。"""
    old = str(SAMPLES / old_name)
    new = str(SAMPLES / new_name)
    a = extract_blocks(old)
    b = extract_blocks(new)
    ops = diff_docx(old, new)

    render_html(ops, a, b, "/tmp/docdiff_a.html")
    envelope = build_envelope(old, new, ops, a, b, embed=True)
    envelope = json.loads(json.dumps(envelope, ensure_ascii=False))
    a2 = [block_from_dict(d) for d in envelope["old"]["blocks"]]
    b2 = [block_from_dict(d) for d in envelope["new"]["blocks"]]
    render_html(envelope["ops"], a2, b2, "/tmp/docdiff_b.html")

    return (
        Path("/tmp/docdiff_a.html").read_text(encoding="utf-8"),
        Path("/tmp/docdiff_b.html").read_text(encoding="utf-8"),
    )


def test_roundtrip_html_identical():
    for old, new in PAIRS:
        html_a, html_b = _roundtrip(old, new)
        assert html_a == html_b, f"{old} vs {new}: JSON 往返后的 HTML 不一致"


# ---- 信封结构 ----

def test_envelope_structure():
    old = str(SAMPLES / "old.docx")
    new = str(SAMPLES / "old.docx")
    a = extract_blocks(old)
    b = extract_blocks(new)
    ops = diff_docx(old, new)

    light = build_envelope(old, new, ops, a, b, embed=False)
    assert light["schema"] == SCHEMA
    assert light["tool_version"] == __version__
    assert light["old"]["path"] == old and light["new"]["path"] == new
    assert light["old"]["blocks"] == [] and light["new"]["blocks"] == []  # 默认轻量
    assert light["stats"]["total"] == 0
    assert light["ops"] == ops

    full = build_envelope(old, new, ops, a, b, embed=True)
    assert len(full["old"]["blocks"]) == len(a)
    assert full["old"]["blocks"][0]["kind"] == "paragraph"
    # 不变量:total == 各分量之和
    parts = sum(v for k, v in full["stats"].items() if k != "total")
    assert full["stats"]["total"] == parts


def test_envelope_table_stats():
    old = str(SAMPLES / "tbl_old.docx")
    new = str(SAMPLES / "tbl_new2.docx")
    a = extract_blocks(old)
    b = extract_blocks(new)
    ops = diff_docx(old, new)
    env = build_envelope(old, new, ops, a, b, embed=True)
    assert env["stats"]["table_modified"] == 1
    assert env["stats"]["total"] == 1


# ---- CLI 端到端:手册 4.2 的 shell 管线 ----

def _run_cli(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "docdiff.cli", *argv],
        capture_output=True, text=True,
    )


def test_cli_shell_pipeline_roundtrip(tmp_path):
    old = str(SAMPLES / "tbl_old.docx")
    new = str(SAMPLES / "tbl_new1.docx")
    a_html = tmp_path / "a.html"
    b_html = tmp_path / "b.html"
    d_json = tmp_path / "d.json"

    r = _run_cli(old, new, "--html", str(a_html))
    assert r.returncode == 1  # 有差异
    r = _run_cli(old, new, "--json", "--embed-text")
    assert r.returncode == 1
    d_json.write_text(r.stdout, encoding="utf-8")
    r = _run_cli("--from-json", str(d_json), "--html", str(b_html))
    assert r.returncode == 1
    assert a_html.read_text(encoding="utf-8") == b_html.read_text(encoding="utf-8")


def test_cli_from_json_without_embed_fails_clearly(tmp_path):
    old = str(SAMPLES / "old.docx")
    new = str(SAMPLES / "new1.docx")
    d_json = tmp_path / "d.json"
    r = _run_cli(old, new, "--json")
    d_json.write_text(r.stdout, encoding="utf-8")

    r = _run_cli("--from-json", str(d_json), "--html", str(tmp_path / "b.html"))
    assert r.returncode == 2
    assert "no_embedded_text" in r.stderr
    assert "embed-text" in r.stderr  # 提示解决方式,而不是崩


def test_cli_from_json_terminal_renders(tmp_path):
    old = str(SAMPLES / "tbl_old.docx")
    new = str(SAMPLES / "tbl_new2.docx")
    d_json = tmp_path / "d.json"
    r = _run_cli(old, new, "--json", "--embed-text")
    d_json.write_text(r.stdout, encoding="utf-8")
    r = _run_cli("--from-json", str(d_json))
    assert r.returncode == 1
    assert "表格" in r.stdout
