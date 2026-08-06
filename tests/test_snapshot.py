import json
import os
import difflib
from pathlib import Path
from docdiff.core import diff_docx

SAMPLES = Path(__file__).parent.parent / "samples"
GOLDEN = Path(__file__).parent / "golden"
PAIRS = [
    ("old.docx", "old.docx"),
    ("old.docx", "new1.docx"),
    ("old.docx", "new2.docx"),
    ("old.docx", "new3.docx")
]

def _check(old_name, new_name):
    ops = diff_docx(str(SAMPLES / old_name), str(SAMPLES / new_name))
    
    current_text = json.dumps(ops, ensure_ascii=False, indent=2, sort_keys=True)
    golden_path = GOLDEN / f"{old_name}_{new_name}.json"
    
    if os.environ.get("SNAPSHOT_UPDATE"):
        GOLDEN.mkdir(exist_ok=True)
        golden_path.write_text(current_text, encoding="utf-8")
        return

    if not golden_path.exists():
        assert False, f"基准文件不存在: {golden_path.name} -> 提示: 先跑 SNAPSHOT_UPDATE=1"
        
    golden_text = golden_path.read_text(encoding="utf-8")
    
    if current_text != golden_text:
        diff_lines = list(difflib.unified_diff(
            golden_text.splitlines(keepends=True),
            current_text.splitlines(keepends=True),
            fromfile=f"golden/{golden_path.name}",
            tofile="current_output",
            n=5
        ))
        diff_str = "".join(diff_lines)
        assert False, f"快照差异报警 ({old_name} vs {new_name}):\n{diff_str}"

def test_snapshots():
    for old_name, new_name in PAIRS:
        _check(old_name, new_name)