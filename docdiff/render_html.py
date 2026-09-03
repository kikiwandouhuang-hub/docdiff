import html

from .model import Block, Op


def _row_warnings(op: Op) -> list[str]:
    """收集行级 warning(如列数漂移),按首次出现顺序去重。"""
    warns = []
    for r in op.get("rows", []):
        w = r.get("warning")
        if w and w not in warns:
            warns.append(w)
    return warns


def _count_table_stats(ops: list[Op]) -> tuple[int, int, int]:
    """表格维度统计:(行增, 行删, 格改)。"""
    p = q = r = 0
    for op in ops:
        if op["op"] != "table_modified":
            continue
        for row in op["rows"]:
            if row["op"] == "row_inserted":
                p += 1
            elif row["op"] == "row_deleted":
                q += 1
            elif row["op"] == "row_modified":
                r += sum(1 for c in row.get("cells", []) if c["op"] == "cell_modified")
    return p, q, r


def _table_html(op: Op, side: str, a_block: Block, b_block: Block) -> str:
    """渲染表格的一侧(side: "old" | "new")。三层底色:
    行级整行底色、单元格级格子底色、词级 span 高亮;
    moved 行两侧同色标记并注明来源/去向。"""
    rows_a = a_block.rows
    rows_b = b_block.rows
    side_rows = rows_a if side == "old" else rows_b
    n_cols = len(side_rows[0]) if side_rows else 0

    trs = []
    for r in op["rows"]:
        rop = r["op"]

        # 这一侧不存在的行(插行看旧侧、删行看新侧):补一行斜纹占位
        if (rop == "row_inserted" and side == "old") or (rop == "row_deleted" and side == "new"):
            trs.append(f'<tr class="row-absent"><td colspan="{n_cols}"></td></tr>')
            continue

        src_row = rows_a[r["old_row"]] if side == "old" else rows_b[r["new_row"]]

        if rop != "row_modified":
            tds = [f"<td>{html.escape(c)}</td>" for c in src_row]
            if rop == "row_moved":
                badge = (
                    f'<span class="tag-moved-row">↷ 移至右侧第 {r["new_row"] + 1} 行</span>'
                    if side == "old" else
                    f'<span class="tag-moved-row">↶ 来自左侧第 {r["old_row"] + 1} 行</span>'
                )
                tds[0] = f"<td>{badge}{html.escape(src_row[0])}</td>"
            cls = {
                "row_unchanged": "",
                "row_deleted": "row-del",
                "row_inserted": "row-ins",
                "row_moved": "row-mov",
            }[rop]
            trs.append(f'<tr class="{cls}">{"".join(tds)}</tr>')
            continue

        # row_modified:单元格级底色 + 词级 span
        tds = []
        for c in r["cells"]:
            cop = c["op"]
            if cop == "cell_unchanged":
                idx = c["old_col"] if side == "old" else c["new_col"]
                tds.append(f"<td>{html.escape(src_row[idx])}</td>")
            elif cop == "cell_modified":
                chunks = []
                for item in c["inline"]:
                    tag = item["tag"]
                    txt = html.escape(item["text"])
                    if tag == "equal":
                        chunks.append(txt)
                    elif tag == "delete" and side == "old":
                        chunks.append(f'<span class="token-del">{txt}</span>')
                    elif tag == "insert" and side == "new":
                        chunks.append(f'<span class="token-ins">{txt}</span>')
                tds.append(f'<td class="cell-mod">{"".join(chunks)}</td>')
            elif cop == "cell_deleted":
                if side == "old":
                    txt = html.escape(rows_a[r["old_row"]][c["old_col"]])
                    tds.append(f'<td class="cell-del">{txt}</td>')
                else:
                    tds.append('<td class="cell-absent"></td>')
            else:  # cell_inserted
                if side == "new":
                    txt = html.escape(rows_b[r["new_row"]][c["new_col"]])
                    tds.append(f'<td class="cell-ins">{txt}</td>')
                else:
                    tds.append('<td class="cell-absent"></td>')
        trs.append(f'<tr class="row-mod">{"".join(tds)}</tr>')

    return '<table class="diff-table">' + "".join(trs) + "</table>"


def render(ops: list[Op], a: list[Block], b: list[Block], out_path: str) -> None:
    inserted_cnt = sum(1 for op in ops if op["op"] in ("inserted", "insert"))
    deleted_cnt = sum(1 for op in ops if op["op"] in ("deleted", "delete"))
    modified_cnt = sum(1 for op in ops if op["op"] == "modified")
    moved_cnt = sum(1 for op in ops if op["op"] == "moved")
    table_cnt = sum(1 for op in ops if op["op"] == "table_modified")
    formatted_cnt = sum(1 for op in ops if op["op"] == "formatted")
    total_changes = (
        inserted_cnt + deleted_cnt + modified_cnt + moved_cnt + table_cnt + formatted_cnt
    )
    p, q, r = _count_table_stats(ops)
    stats_text = (
        f"共 {total_changes} 处变更"
        f"({inserted_cnt} 增 {deleted_cnt} 删 {modified_cnt} 改 {moved_cnt} 移"
    )
    if formatted_cnt:
        stats_text += f";格式:{formatted_cnt} 处"
    if table_cnt:
        stats_text += f";表格:{p} 行增 {q} 行删 {r} 格改"
    stats_text += ")"

    rows_html = []
    for op in ops:
        op_type = op["op"]
        old_num = new_num = ""
        left_html = right_html = ""
        left_bg = right_bg = ""

        if op_type == "unchanged":
            old_num = str(op["old_idx"] + 1)
            new_num = str(op["new_idx"] + 1)
            left_html = right_html = html.escape(a[op["old_idx"]].text)
            left_bg = right_bg = "bg-unchanged"

        elif op_type in ("inserted", "insert"):
            new_num = str(op["new_idx"] + 1)
            right_html = html.escape(b[op["new_idx"]].text)
            left_bg = "bg-empty"  # 空白斜线纹理
            right_bg = "bg-inserted"

        elif op_type in ("deleted", "delete"):
            old_num = str(op["old_idx"] + 1)
            left_html = html.escape(a[op["old_idx"]].text)
            left_bg = "bg-deleted"
            right_bg = "bg-empty" # 空白斜线纹理

        elif op_type == "moved":
            old_num = str(op["old_idx"] + 1)
            new_num = str(op["new_idx"] + 1)
            left_badge = f'<div class="tag tag-moved">↷ 移至右侧第 {new_num} 段</div>'
            right_badge = f'<div class="tag tag-moved">↶ 来自左侧第 {old_num} 段</div>'
            left_html = left_badge + html.escape(a[op["old_idx"]].text)
            right_html = right_badge + html.escape(b[op["new_idx"]].text)
            left_bg = right_bg = "bg-moved"
        
        elif op_type == "modified":
            old_num = str(op["old_idx"] + 1)
            new_num = str(op["new_idx"] + 1)
            left_bg = right_bg = "bg-modified"
            
            inline = op.get("inline", [])
            l_chunks, r_chunks = [], []
            for item in inline:
                tag = item["tag"]
                txt = html.escape(item["text"])
                if tag == "equal":
                    l_chunks.append(txt)
                    r_chunks.append(txt)
                elif tag == "delete":
                    l_chunks.append(f'<span class="token-del">{txt}</span>')
                elif tag == "insert":
                    r_chunks.append(f'<span class="token-ins">{txt}</span>')
            
            left_html = "".join(l_chunks)
            right_html = "".join(r_chunks)

        elif op_type == "table_modified":
            old_num = str(op["old_idx"] + 1)
            new_num = str(op["new_idx"] + 1)
            left_block = a[op["old_idx"]]
            right_block = b[op["new_idx"]]
            warn = "⚠ 此表格含合并单元格,当前按展开的单元格近似渲染"
            left_warn = right_warn = ""
            if (left_block.fmt or {}).get("unsupported") == "merged_cells":
                left_warn = f'<div class="table-warn">{warn}</div>'
            if (right_block.fmt or {}).get("unsupported") == "merged_cells":
                right_warn = f'<div class="table-warn">{warn}</div>'
            for row_warn in _row_warnings(op):
                left_warn += f'<div class="table-warn">⚠ {html.escape(row_warn)}</div>'
            left_html = left_warn + _table_html(op, "old", left_block, right_block)
            right_html = right_warn + _table_html(op, "new", left_block, right_block)
            left_bg = right_bg = "bg-modified"

        elif op_type == "formatted":
            old_num = str(op["old_idx"] + 1)
            new_num = str(op["new_idx"] + 1)
            desc = "、".join(f"{c['attr']}: {c['old']} → {c['new']}" for c in op.get("changes", []))
            badge = f'<div class="tag tag-format">格式变更: {desc}</div>'
            left_html = badge + html.escape(a[op["old_idx"]].text)
            right_html = badge + html.escape(b[op["new_idx"]].text)
            left_bg = right_bg = "bg-modified"

        # 拼装优雅的栅格结构
        row_html = f'''
        <div class="diff-row">
            <div class="num {left_bg}">{old_num}</div>
            <div class="code {left_bg}">{left_html}</div>
            <div class="num {right_bg}">{new_num}</div>
            <div class="code {right_bg}">{right_html}</div>
        </div>
        '''
        rows_html.append(row_html)

    # 注入现代 SaaS 风格全套 CSS
    full_html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <title>文档对比报告</title>
    <style>
        :root {{
            --border: #e2e8f0;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --font-sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas,
                monospace;
        }}
        body {{
            font-family: var(--font-sans);
            background-color: #f8fafc;
            color: var(--text-main);
            margin: 0;
            padding: 40px 20px;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: #ffffff;
            border-radius: 12px;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
            overflow: hidden;
            border: 1px solid var(--border);
        }}
        .header {{
            padding: 20px 24px;
            background: #ffffff;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 18px;
            font-weight: 600;
            color: #0f172a;
            letter-spacing: -0.02em;
        }}
        .stats {{
            display: flex;
            gap: 12px;
            font-size: 13px;
            align-items: center;
        }}
        .stat-pill {{
            padding: 4px 12px;
            border-radius: 999px;
            font-weight: 600;
            display: flex;
            align-items: center;
        }}
        .stat-total {{ color: var(--text-muted); font-weight: 500; margin-right: 8px; }}
        .pill-ins {{ background: #dcfce7; color: #166534; }}
        .pill-del {{ background: #fee2e2; color: #991b1b; }}
        .pill-mod {{ background: #fef3c7; color: #92400e; }}
        .pill-mov {{ background: #dbeafe; color: #1e40af; }}
        .pill-fmt {{ background: #ede9fe; color: #5b21b6; }}

        .diff-grid {{
            display: flex;
            flex-direction: column;
        }}
        .diff-row {{
            display: grid;
            grid-template-columns: 50px calc(50% - 50px) 50px calc(50% - 50px);
            border-bottom: 1px solid var(--border);
        }}
        .diff-row:last-child {{ border-bottom: none; }}
        
        .num {{
            padding: 12px 0;
            text-align: center;
            color: var(--text-muted);
            font-family: var(--font-mono);
            font-size: 12px;
            user-select: none;
            border-right: 1px solid var(--border);
        }}
        .num:nth-child(3) {{ border-left: 1px solid var(--border); }}
        
        .code {{
            padding: 12px 20px;
            font-size: 14px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-break: break-word;
        }}

        /* 高级背景调色 */
        .bg-unchanged {{ background: #ffffff; }}
        .bg-inserted {{ background: #f0fdf4; }}
        .bg-deleted {{ background: #fef2f2; }}
        .bg-modified {{ background: #fffbeb; }}
        .bg-moved {{ background: #eff6ff; }}
        
        /* 核心亮点：空白状态的高级斜线纹理 */
        .bg-empty {{ 
            background: #f8fafc;
            background-image: repeating-linear-gradient(
                45deg, transparent, transparent 10px, rgba(0,0,0,0.02) 10px, rgba(0,0,0,0.02) 20px);
        }}

        /* 段内 Inline Token 渲染（圆润质感） */
        .token-ins {{
            background: #bbf7d0;
            color: #166534;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 500;
        }}
        .token-del {{
            background: #fecaca;
            color: #991b1b;
            padding: 2px 6px;
            border-radius: 4px;
            text-decoration: line-through;
        }}

        /* 移动标签 */
        .tag {{
            display: inline-flex;
            align-items: center;
            font-size: 12px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 6px;
            margin-bottom: 6px;
            margin-right: 8px;
        }}
        .tag-moved {{ background: #bfdbfe; color: #1e3a8a; border: 1px solid #93c5fd; }}
        .tag-format {{ background: #ddd6fe; color: #4c1d95; border: 1px solid #c4b5fd; }}

        /* 表格 diff:行级整行底色,单元格级格子底色,词级 span 高亮 */
        .diff-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }}
        .diff-table td {{
            border: 1px solid var(--border);
            padding: 6px 10px;
            line-height: 1.5;
            vertical-align: top;
        }}
        .row-ins td {{ background: #f0fdf4; }}
        .row-del td {{ background: #fef2f2; }}
        .row-mov td {{ background: #eff6ff; }}
        .row-mod td {{ background: #fffbeb; }}
        /* 单元格级底色需要压过行级,选择器带行类提高优先级 */
        .row-mod td.cell-mod {{ background: #fde68a; }}
        .row-mod td.cell-ins {{ background: #bbf7d0; }}
        .row-mod td.cell-del {{ background: #fecaca; }}
        .row-mod td.cell-absent, .row-absent td {{
            background: #f8fafc;
            background-image: repeating-linear-gradient(
                45deg, transparent, transparent 10px, rgba(0,0,0,0.02) 10px, rgba(0,0,0,0.02) 20px);
        }}
        .row-absent td {{ height: 36px; }}
        .tag-moved-row {{
            display: inline-flex;
            align-items: center;
            font-size: 12px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 6px;
            margin-bottom: 4px;
            margin-right: 8px;
            background: #bfdbfe;
            color: #1e3a8a;
            border: 1px solid #93c5fd;
        }}
        .table-warn {{
            background: #fffbeb;
            color: #92400e;
            font-size: 12px;
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid #fde68a;
            margin-bottom: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📑 智能文档对比分析</h1>
            <div class="stats">
                <span class="stat-total">{stats_text}</span>
                <span class="stat-pill pill-ins">+{inserted_cnt} 增</span>
                <span class="stat-pill pill-del">-{deleted_cnt} 删</span>
                <span class="stat-pill pill-mod">~{modified_cnt} 改</span>
                <span class="stat-pill pill-mov">⇅{moved_cnt} 移</span>
                <span class="stat-pill pill-fmt">#{formatted_cnt} 格式</span>
            </div>
        </div>
        <div class="diff-grid">
            {"".join(rows_html)}
        </div>
    </div>
</body>
</html>'''

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(full_html)