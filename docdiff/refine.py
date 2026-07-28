from difflib import SequenceMatcher

SIM_THRESHOLD = 0.6

def pair_modified(ops: list[dict], a: list[str], b: list[str]) -> list[dict]:
    deleted_ops = []
    inserted_ops = []

    for op in ops:
        if op["op"] in ("deleted", "delete"):
            deleted_ops.append(op)
        elif op["op"] in ("inserted", "insert"):
            inserted_ops.append(op)

    matched_old_ids = set()
    matched_new_ids = set()
    matched_pairs = {}

    for ins_op in inserted_ops:
        new_idx = ins_op["new_idx"]
        new_text = b[new_idx]
        best_sim = 0.0
        best_del_op = None

        for del_op in deleted_ops:
            old_idx = del_op["old_idx"]
            if id(del_op) in matched_old_ids:
                continue

            old_text = a[old_idx]
            sim = SequenceMatcher(None, old_text, new_text).ratio()

            if sim > best_sim:
                best_sim = sim
                best_del_op = del_op

        if best_sim >= SIM_THRESHOLD and best_del_op is not None:
            matched_old_ids.add(id(best_del_op))
            matched_new_ids.add(id(ins_op))
            matched_pairs[id(best_del_op)] = {
                "op": "modified",
                "old_idx": best_del_op["old_idx"],
                "new_idx": new_idx
            }

    new_ops = []
    for op in ops:
        op_id = id(op)
        if op_id in matched_pairs:
            new_ops.append(matched_pairs[op_id])
        elif op_id in matched_new_ids:
            continue
        else:
            new_ops.append(op)

    return new_ops


def inline_diff(old_text: str, new_text: str) -> list[dict]:
    matcher = SequenceMatcher(None, old_text, new_text)
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