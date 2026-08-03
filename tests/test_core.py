from pathlib import Path
from docdiff.parser import extract_paragraphs
from docdiff.core import diff_docx

SAMPLES = Path(__file__).parent.parent / "samples"
OLD = str(SAMPLES / "old.docx")
NEW1 = str(SAMPLES / "new1.docx")
NEW2 = str(SAMPLES / "new2.docx")
NEW3 = str(SAMPLES / "new3.docx")

def assert_indices_complete(old_path, new_path):
    """核心不变量：旧文档每个段落只有四种下场，新文档同理，所以每个下标必须恰好出现一次。"""
    a = extract_paragraphs(old_path)
    b = extract_paragraphs(new_path)
    ops = diff_docx(old_path, new_path)
    
    old_idxs = []
    new_idxs = []
    
    for op in ops:
        if op.get("old_idx") is not None:
            old_idxs.append(op["old_idx"])
        if op.get("new_idx") is not None:
            new_idxs.append(op["new_idx"])
            
    assert sorted(old_idxs) == list(range(len(a)))
    assert sorted(new_idxs) == list(range(len(b)))

def test_identical():
    a = extract_paragraphs(OLD)
    ops = diff_docx(OLD, OLD)
    
    assert all(op["op"] == "unchanged" for op in ops)
    assert len(ops) == len(a)
    
    assert_indices_complete(OLD, OLD)

def test_new1_modified():
    a = extract_paragraphs(OLD)
    b = extract_paragraphs(NEW1)
    ops = diff_docx(OLD, NEW1)
    
    modified_ops = [op for op in ops if op["op"] == "modified"]
    assert len(modified_ops) == 1
    
    mod_op = modified_ops[0]
    assert "inline" in mod_op
    
    old_idx = mod_op["old_idx"]
    new_idx = mod_op["new_idx"]
    assert a[old_idx] != b[new_idx]
    
    assert_indices_complete(OLD, NEW1)

def test_new2_head_insert():
    a = extract_paragraphs(OLD)
    ops = diff_docx(OLD, NEW2)
    
    inserted_ops = [op for op in ops if op["op"] == "inserted"]
    unchanged_ops = [op for op in ops if op["op"] == "unchanged"]
    
    assert len(inserted_ops) == 1
    assert inserted_ops[0]["new_idx"] == 0
    assert len(unchanged_ops) == len(a)
    
    assert_indices_complete(OLD, NEW2)

def test_new3_moved():
    a = extract_paragraphs(OLD)
    b = extract_paragraphs(NEW3)
    ops = diff_docx(OLD, NEW3)
    
    moved_ops = [op for op in ops if op["op"] == "moved"]
    assert len(moved_ops) == 1
    
    moved_op = moved_ops[0]
    assert a[moved_op["old_idx"]] == b[moved_op["new_idx"]]
    
    assert sum(1 for op in ops if op["op"] in ("deleted", "inserted")) == 0
    
    assert_indices_complete(OLD, NEW3)

def test_inline_only_on_modified():
    pairs = [
        (OLD, OLD),
        (OLD, NEW1),
        (OLD, NEW2),
        (OLD, NEW3)
    ]
    
    for old_path, new_path in pairs:
        ops = diff_docx(old_path, new_path)
        for op in ops:
            if "inline" in op:
                assert op["op"] == "modified"
            if op["op"] == "modified":
                assert "inline" in op
        
        assert_indices_complete(old_path, new_path)