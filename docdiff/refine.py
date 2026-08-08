import difflib

SIM_THRESHOLD = 0.7
POSITION_WINDOW = 2

def _anchors(ops: list[dict]) -> list[tuple[int, int]]:
    res = []
    for op in ops:
        if op["op"] == "unchanged":
            res.append((op["old_idx"], op["new_idx"]))
    res.sort(key=lambda x: x[0])
    return res

def _expected_new_idx(old_idx: int, anchors: list[tuple[int, int]]) -> int:
    best_a_old = -1
    best_a_new = -1
    for a_old, a_new in anchors:
        if a_old < old_idx:
            best_a_old = a_old
            best_a_new = a_new
        else:
            break
            
    if best_a_old == -1:
        return old_idx
        
    return best_a_new + (old_idx - best_a_old)

def pair_modified(ops: list[dict], a: list[str], b: list[str]) -> list[dict]:
    anchors = _anchors(ops)
    
    deleted = [op for op in ops if op["op"] == "deleted"]
    inserted = [op for op in ops if op["op"] == "inserted"]
    
    candidates = []
    for d_op in deleted:
        old_idx = d_op["old_idx"]
        for i_op in inserted:
            new_idx = i_op["new_idx"]
            
            dist = abs(new_idx - _expected_new_idx(old_idx, anchors))
            if dist > POSITION_WINDOW:
                continue
                
            sim = difflib.SequenceMatcher(None, a[old_idx], b[new_idx]).ratio()
            if sim >= SIM_THRESHOLD:
                candidates.append((sim, d_op, i_op))
                
    candidates.sort(key=lambda x: x[0], reverse=True)
    
    used_old = set()
    used_new = set()
    mod_ops = []
    
    for sim, d_op, i_op in candidates:
        old_idx = d_op["old_idx"]
        new_idx = i_op["new_idx"]
        
        if old_idx in used_old or new_idx in used_new:
            continue
            
        used_old.add(old_idx)
        used_new.add(new_idx)
        
        mod_ops.append({
            "op": "modified",
            "old_idx": old_idx,
            "new_idx": new_idx
        })
        
    out_ops = []
    for op in ops:
        if op["op"] == "deleted" and op["old_idx"] in used_old:
            continue
        if op["op"] == "inserted" and op["new_idx"] in used_new:
            continue
        out_ops.append(op)
        
    out_ops.extend(mod_ops)
    out_ops.sort(key=lambda x: (x.get("old_idx", float("inf")), x.get("new_idx", float("inf"))))
    
    return out_ops

def inline_diff(old_text: str, new_text: str) -> list[dict]:
    matcher = difflib.SequenceMatcher(None, old_text, new_text)
    opcodes = matcher.get_opcodes()
    inline_ops = []
    
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            inline_ops.append({"tag": "equal", "text": old_text[i1:i2]})
        elif tag == "delete":
            inline_ops.append({"tag": "delete", "text": old_text[i1:i2]})
        elif tag == "insert":
            inline_ops.append({"tag": "insert", "text": new_text[j1:j2]})
        elif tag == "replace":
            inline_ops.append({"tag": "delete", "text": old_text[i1:i2]})
            inline_ops.append({"tag": "insert", "text": new_text[j1:j2]})
            
    return inline_ops