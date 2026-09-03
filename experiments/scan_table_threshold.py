"""experiments/scan_table_threshold.py — 扫参定 TABLE_SIM_THRESHOLD

与 V2-0 的段落阈值扫参同一套方法:
- 正样本:同一张表的四类修订(改格/插行/移行/插列),相似度必须 >= 阈值
- 负样本:无关的表、行序颠倒的表、大部分行重写的表,相似度必须 < 阈值

结论(记录于 commit 与 dev-log):
- 正样本最小 0.750,负样本最大 0.333,可分离区间 (0.333, 0.750]
- 取 0.5:给"半张表被改写仍算同表"留余地,同时拒绝行序颠倒

用法: python3.13 experiments/scan_table_threshold.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # 让 experiments/ 目录外也能直接跑

from docdiff.model import Block
from docdiff.parser import extract_blocks
from docdiff.refine import TABLE_SIM_THRESHOLD, table_similarity

SAMPLES = Path(__file__).parent.parent / "samples"


def tables_of(name: str) -> Block:
    blocks = extract_blocks(str(SAMPLES / f"{name}.docx"))
    tables = [b for b in blocks if b.kind == "table"]
    assert len(tables) == 1, f"{name}.docx 应有 1 张表,实际 {len(tables)}"
    return tables[0]


def main() -> None:
    pos: list[tuple[str, Block, Block]] = [
        (name, tables_of("tbl_old"), tables_of(name))
        for name in ["tbl_new1", "tbl_new2", "tbl_new3", "tbl_new4"]
    ]
    neg: list[tuple[str, Block, Block]] = [
        (
            "无关表",
            Block(kind="table", rows=[["姓名", "部门"], ["张三", "技术部"]]),
            Block(kind="table", rows=[["产品", "价格"], ["咖啡", "25元"]]),
        ),
        (
            "行序颠倒",
            Block(kind="table", rows=[["姓名", "部门"], ["张三", "技术部"], ["李四", "市场部"]]),
            Block(kind="table", rows=[["员工", "部门"], ["李四", "市场部"], ["张三", "技术部"]]),
        ),
        (
            "大部分行重写",
            Block(kind="table", rows=[["姓名", "部门"], ["张三", "技术部"], ["李四", "市场部"], ["王五", "人事部"]]),
            Block(kind="table", rows=[["员工", "部门"], ["赵一", "研发部"], ["钱二", "设计部"], ["孙三", "销售部"]]),
        ),
    ]

    print("逐对相似度:")
    for name, ta, tb in pos:
        print(f"  正 {name:8s} {table_similarity(ta, tb):.3f}")
    for name, ta, tb in neg:
        print(f"  负 {name:8s} {table_similarity(ta, tb):.3f}")

    pos_vals = [table_similarity(ta, tb) for _, ta, tb in pos]
    neg_vals = [table_similarity(ta, tb) for _, ta, tb in neg]
    lo, hi = max(neg_vals), min(pos_vals)
    print(f"\n可分离区间: ({lo:.3f}, {hi:.3f}]")
    assert lo < hi, "正负样本不可分离,阈值无解"
    assert lo < TABLE_SIM_THRESHOLD <= hi, f"{TABLE_SIM_THRESHOLD} 不在可分离区间内"

    # 全阈值扫描:证明区间内每个值都分离干净
    print("\n全阈值扫描(0.30 ~ 0.80, 步长 0.05):")
    t = 0.30
    while t <= 0.80 + 1e-9:
        ok_pos = all(v >= t for v in pos_vals)
        ok_neg = all(v < t for v in neg_vals)
        mark = "✓" if ok_pos and ok_neg else "✗"
        print(f"  {t:.2f}  正全过={ok_pos} 负全拒={ok_neg} {mark}")
        t += 0.05
    print(f"\n结论: 阈值 {TABLE_SIM_THRESHOLD} 分离干净")


if __name__ == "__main__":
    main()
