import difflib
from collections.abc import Sequence
from typing import Any

from .model import CELL_SEP, Block, FmtDict, Op
from .seqdiff import diff_ops as seq_diff_ops
from .tokenize import tokenize

SIM_THRESHOLD = 0.7
POSITION_WINDOW = 2
# 表格身份配对的相似度阈值,由 experiments/scan_table_threshold.py 扫参确定:
# 正样本(同表四类修订)最小 0.750,负样本(无关表/行序颠倒/大部分行重写)最大 0.333,
# 0.5 落在可分离区间中央,给"半张表被改写仍算同表"留了余地。
TABLE_SIM_THRESHOLD = 0.5

# 词级 LCS 的规模上限(len(ta) * len(tb))。
# 超过则先走句级两级细化;句级也切不开(全文一句)时退回 difflib 兜底。
# 理由:diff 工具卡住比 diff 得不够漂亮严重得多。
MAX_TOKEN_PRODUCT = 500_000

def _anchors(ops: list[Op]) -> list[tuple[int, int]]:
    res: list[tuple[int, int]] = []
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

def _lcs_coverage(seq_a: list[str], seq_b: list[str]) -> float:
    """2*LCS/(m+n):行序敏感的相似度。

    选它而不是 Jaccard 的原因:Jaccard 对行序不敏感,两张行序完全颠倒的表
    会被判成相同;LCS 覆盖率把行序计入,而且顺手复用了 seqdiff。
    """
    if not seq_a and not seq_b:
        return 1.0
    if not seq_a or not seq_b:
        return 0.0
    ops = seq_diff_ops(seq_a, seq_b)
    lcs_len = sum(1 for op in ops if op["op"] == "unchanged")
    return 2.0 * lcs_len / (len(seq_a) + len(seq_b))

def _columns(rows: list[list[str]]) -> list[list[str]]:
    """行转列;参差行补空串,防御性处理。"""
    n = max((len(r) for r in rows), default=0)
    return [[r[i] if i < len(r) else "" for r in rows] for i in range(n)]

def table_similarity(ta: Block, tb: Block) -> float:
    """两张表的相似度:行级 LCS 覆盖率(行序敏感)。

    列数不同(插列/删列)时行键整体错位,行级覆盖率必然为 0,
    此时转置到列视角再算一次 —— 插列是表结构变更的常见形态,
    列级 LCS 依然保持列序敏感,没有退回 Jaccard。
    """
    row_cov = _lcs_coverage(
        [CELL_SEP.join(r) for r in ta.rows],
        [CELL_SEP.join(r) for r in tb.rows],
    )
    if row_cov >= TABLE_SIM_THRESHOLD:
        return row_cov
    n_a = max((len(r) for r in ta.rows), default=0)
    n_b = max((len(r) for r in tb.rows), default=0)
    if n_a != n_b:
        return _lcs_coverage(
            [CELL_SEP.join(c) for c in _columns(ta.rows)],
            [CELL_SEP.join(c) for c in _columns(tb.rows)],
        )
    return row_cov

def _pair_sim(xa: Block | str, xb: Block | str) -> float | None:
    """配对相似度:段落按文本比,表格按行级 LCS 覆盖率比;跨 kind 永不配对。"""
    if isinstance(xa, Block) and isinstance(xb, Block):
        if xa.kind == xb.kind == "table":
            return table_similarity(xa, xb)
        if xa.kind != xb.kind:
            return None
    key_a = xa if isinstance(xa, str) else xa.key()
    key_b = xb if isinstance(xb, str) else xb.key()
    return difflib.SequenceMatcher(None, key_a, key_b).ratio()

def pair_modified(ops: list[Op], a: Sequence[Block | str], b: Sequence[Block | str]) -> list[Op]:
    """把 deleted+inserted 对按相似度合并为 modified。

    a / b 兼容两种载荷:v1 的 list[str](段落键)与 v2 的 list[Block];
    表格对的相似度用 table_similarity,阈值用 TABLE_SIM_THRESHOLD。
    """
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

            sim = _pair_sim(a[old_idx], b[new_idx])
            if sim is None:
                continue
            xa = a[old_idx]
            is_table = isinstance(xa, Block) and xa.kind == "table"
            threshold = TABLE_SIM_THRESHOLD if is_table else SIM_THRESHOLD
            if sim >= threshold:
                candidates.append((sim, d_op, i_op))

    candidates.sort(key=lambda x: x[0], reverse=True)

    used_old = set()
    used_new = set()
    mod_ops = []

    for _sim, d_op, i_op in candidates:
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

# ---------------------------------------------------------------------------
# 段内词级细化(v2 自研,替换 v1 的 difflib)
# 输出契约与 v1 完全一致: [{"tag": "equal"|"delete"|"insert", "text": str}, ...]
# ---------------------------------------------------------------------------

def _merge_adjacent(items: list[dict[str, str]]) -> list[dict[str, str]]:
    """合并相邻同 tag 项。
    token 级会产出几十个碎片({"delete":"讲"},{"delete":"问"}...),
    合并后是 {"delete":"讲问题"},渲染出来才不是一串闪烁的色块。
    """
    merged: list[dict[str, str]] = []
    for item in items:
        if merged and merged[-1]["tag"] == item["tag"]:
            merged[-1]["text"] += item["text"]
        else:
            merged.append({"tag": item["tag"], "text": item["text"]})
    return merged

def _tokens_diff(ta: list[str], tb: list[str]) -> list[dict[str, str]]:
    """token 列表 -> 契约格式(含碎片合并)。"""
    ops = seq_diff_ops(ta, tb)
    items = []
    for op in ops:
        if op["op"] == "unchanged":
            items.append({"tag": "equal", "text": ta[op["old_idx"]]})
        elif op["op"] == "deleted":
            items.append({"tag": "delete", "text": ta[op["old_idx"]]})
        else:
            items.append({"tag": "insert", "text": tb[op["new_idx"]]})
    return _merge_adjacent(items)

def _fallback_diff(old_text: str, new_text: str) -> list[dict[str, str]]:
    """difflib 兜底(v1 实现原样保留),用于超长段落的最终降级。"""
    matcher = difflib.SequenceMatcher(None, old_text, new_text)
    inline_ops: list[dict[str, str]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
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

_SENTENCE_BOUNDARIES = "。!?;\n.!?;"

def _split_sentences(text: str) -> list[str]:
    """切句,保留分隔符,否则拼不回原文。"""
    out = []
    buf = []
    for ch in text:
        buf.append(ch)
        if ch in _SENTENCE_BOUNDARIES:
            out.append("".join(buf))
            buf = []
    if buf:
        out.append("".join(buf))
    return out

def _diff_pair(old_text: str, new_text: str) -> list[dict[str, str]]:
    """对一个(句)对做词级细化;自身超规模时退回 difflib,防递归放大。"""
    ta, tb = tokenize(old_text), tokenize(new_text)
    if len(ta) * len(tb) <= MAX_TOKEN_PRODUCT:
        return _tokens_diff(ta, tb)
    return _fallback_diff(old_text, new_text)

def _sentence_diff(old_text: str, new_text: str) -> list[dict[str, str]]:
    """长段落降级路径:先按句子对齐,再对配对上的句子对做词级细化。
    修订的真实形态是"改了某几句",句级对齐把 dp 表从 字数×字数 降到
    句数×句数 加 若干 句内词数×词数,典型输入下结果与全词级完全一致。
    """
    sa = _split_sentences(old_text)
    sb = _split_sentences(new_text)
    # 切句没切开(全文一句) -> 句级路径帮不上忙,直接兜底
    if len(sa) <= 1 and len(sb) <= 1:
        return _fallback_diff(old_text, new_text)

    ops = seq_diff_ops(sa, sb)
    items: list[dict[str, str]] = []
    i = 0
    while i < len(ops):
        if ops[i]["op"] == "unchanged":
            items.append({"tag": "equal", "text": sa[ops[i]["old_idx"]]})
            i += 1
        elif ops[i]["op"] == "deleted":
            # 收集连续的 deleted / inserted 句段,两两配成"替换对"做词级细化
            dels = []
            while i < len(ops) and ops[i]["op"] == "deleted":
                dels.append(sa[ops[i]["old_idx"]])
                i += 1
            inss = []
            while i < len(ops) and ops[i]["op"] == "inserted":
                inss.append(sb[ops[i]["new_idx"]])
                i += 1
            pair_n = min(len(dels), len(inss))
            for k in range(pair_n):
                items.extend(_diff_pair(dels[k], inss[k]))
            for rest in dels[pair_n:]:
                items.append({"tag": "delete", "text": rest})
            for rest in inss[pair_n:]:
                items.append({"tag": "insert", "text": rest})
        else:
            items.append({"tag": "insert", "text": sb[ops[i]["new_idx"]]})
            i += 1
    return _merge_adjacent(items)

def inline_diff(old_text: str, new_text: str) -> list[dict[str, str]]:
    """段内词级差异。契约与 v1 完全一致。"""
    ta, tb = tokenize(old_text), tokenize(new_text)
    if len(ta) * len(tb) <= MAX_TOKEN_PRODUCT:
        return _tokens_diff(ta, tb)
    return _sentence_diff(old_text, new_text)


def fmt_changes(fmt_a: FmtDict | None, fmt_b: FmtDict | None) -> list[dict[str, Any]]:
    """格式指纹对比,输出 [{"attr","old","new"},...]。None 视为无指纹不比较。"""
    if not fmt_a or not fmt_b:
        return []
    out: list[dict[str, Any]] = []
    for attr in ("bold", "italic", "underline", "size", "color"):
        if fmt_a.get(attr) != fmt_b.get(attr):
            out.append({"attr": attr, "old": fmt_a.get(attr), "new": fmt_b.get(attr)})
    return out
