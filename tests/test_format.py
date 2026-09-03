"""V2-E 格式变更检测:formatted op、退出码两种模式、指纹的多数规则。"""
import subprocess
import sys
import xml.etree.ElementTree as ET

from docdiff.core import diff_docx
from docdiff.parser import _fmt_fingerprint, _run_fmt, W_NS
from docdiff.refine import fmt_changes

S = "samples/"


def _run_cli(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "docdiff.cli", *argv],
        capture_output=True, text=True,
    )


# ---- 集成:两种退出码模式(手册 5.1 检查点) ----

def test_pure_format_change_reports_formatted():
    ops = diff_docx(S + "old.docx", S + "fmt_new1.docx")
    formatted = [op for op in ops if op["op"] == "formatted"]
    assert len(formatted) == 1
    assert formatted[0]["old_idx"] == 3  # 第 4 段
    assert formatted[0]["changes"] == [{"attr": "bold", "old": False, "new": True}]
    # 其余 11 段仍是 unchanged:格式指纹没有引发假报警
    assert sum(1 for op in ops if op["op"] == "unchanged") == 11


def test_default_exit_zero_with_hint():
    r = _run_cli(S + "old.docx", S + "fmt_new1.docx")
    assert r.returncode == 0  # 内容没变,默认不算差异
    assert "内容一致,存在 1 处格式差异" in r.stdout
    assert "--check-format" in r.stdout


def test_check_format_exit_one():
    r = _run_cli(S + "old.docx", S + "fmt_new1.docx", "--check-format")
    assert r.returncode == 1
    # 纳入判定后不再打印"内容一致"提示
    assert "内容一致" not in r.stdout


def test_text_and_format_change_reports_modified_with_changes():
    ops = diff_docx(S + "old.docx", S + "fmt_new2.docx")
    modified = [op for op in ops if op["op"] == "modified"]
    assert len(modified) == 1  # 段落三:文本与格式同时变
    assert modified[0]["changes"] == [{"attr": "bold", "old": False, "new": True}]
    assert "inline" in modified[0]  # 文本差异照常段内细化
    assert not any(op["op"] == "formatted" for op in ops)


# ---- 指纹单元测试 ----

def _p(xml_fragment: str):
    """用字符串拼一个段落 XML,喂给 _fmt_fingerprint。"""
    body = (
        '<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        + xml_fragment + "</w:p>"
    )
    return ET.fromstring(body)


def test_run_fmt_basics():
    # 空 rPr -> 全默认
    assert _run_fmt(None) == {
        "bold": False, "italic": False, "underline": None, "size": None, "color": None,
    }
    rpr = _p("<w:rPr/>").find(W_NS + "rPr")
    assert _run_fmt(rpr)["bold"] is False


def test_run_fmt_full_attrs():
    rpr = _p(
        '<w:rPr><w:b/><w:i/><w:u w:val="double"/>'
        '<w:sz w:val="24"/><w:color w:val="FF0000"/></w:rPr>'
    ).find(W_NS + "rPr")
    fmt = _run_fmt(rpr)
    assert fmt == {
        "bold": True, "italic": True, "underline": "double", "size": 12.0, "color": "FF0000",
    }


def test_run_fmt_half_point_size():
    # w:sz 单位是半磅:val=24 是 12pt,val=21 是 10.5pt
    rpr = _p('<w:rPr><w:sz w:val="21"/></w:rPr>').find(W_NS + "rPr")
    assert _run_fmt(rpr)["size"] == 10.5


def test_run_fmt_explicit_false_and_none_underline():
    # <w:b w:val="0"/> 是显式关;<w:u w:val="none"/> 是"无下划线"
    rpr = _p(
        '<w:rPr><w:b w:val="0"/><w:u w:val="none"/></w:rPr>'
    ).find(W_NS + "rPr")
    fmt = _run_fmt(rpr)
    assert fmt["bold"] is False and fmt["underline"] is None


def test_fmt_fingerprint_majority_and_mixed():
    # run1 加粗、run2/run3 不加粗 -> 多数 False + mixed=True
    p = _p(
        "<w:r><w:rPr><w:b/></w:rPr></w:r>"
        "<w:r><w:rPr/></w:r>"
        "<w:r><w:rPr/></w:r>"
    )
    fmt = _fmt_fingerprint(p)
    assert fmt["bold"] is False
    assert fmt["mixed"] is True


def test_fmt_fingerprint_unanimous_not_mixed():
    p = _p("<w:r><w:rPr><w:b/></w:rPr></w:r>" "<w:r><w:rPr><w:b/></w:rPr></w:r>")
    fmt = _fmt_fingerprint(p)
    assert fmt["bold"] is True and fmt["mixed"] is False


def test_fmt_fingerprint_no_runs_is_none():
    assert _fmt_fingerprint(_p("<w:pPr/>")) is None


def test_fmt_changes():
    a = {"bold": False, "italic": False, "underline": None, "size": 12.0, "color": "1F1F1F"}
    b = {"bold": True, "italic": False, "underline": "single", "size": 14.0, "color": "1F1F1F"}
    changes = fmt_changes(a, b)
    assert changes == [
        {"attr": "bold", "old": False, "new": True},
        {"attr": "underline", "old": None, "new": "single"},
        {"attr": "size", "old": 12.0, "new": 14.0},
    ]
    assert fmt_changes(a, a) == []
    assert fmt_changes(None, b) == []  # 无指纹不比较(空段/表格)
