import html

def render(ops: list[dict], a: list[str], b: list[str], out_path: str) -> None:
    inserted_cnt = sum(1 for op in ops if op["op"] in ("inserted", "insert"))
    deleted_cnt = sum(1 for op in ops if op["op"] in ("deleted", "delete"))
    modified_cnt = sum(1 for op in ops if op["op"] == "modified")
    moved_cnt = sum(1 for op in ops if op["op"] == "moved")
    total_changes = inserted_cnt + deleted_cnt + modified_cnt + moved_cnt

    rows_html = []
    for op in ops:
        op_type = op["op"]
        old_num = new_num = ""
        left_html = right_html = ""
        left_bg = right_bg = ""

        if op_type == "unchanged":
            old_num = str(op["old_idx"] + 1)
            new_num = str(op["new_idx"] + 1)
            left_html = right_html = html.escape(a[op["old_idx"]])
            left_bg = right_bg = "bg-unchanged"
        
        elif op_type in ("inserted", "insert"):
            new_num = str(op["new_idx"] + 1)
            right_html = html.escape(b[op["new_idx"]])
            left_bg = "bg-empty"  # 空白斜线纹理
            right_bg = "bg-inserted"
        
        elif op_type in ("deleted", "delete"):
            old_num = str(op["old_idx"] + 1)
            left_html = html.escape(a[op["old_idx"]])
            left_bg = "bg-deleted"
            right_bg = "bg-empty" # 空白斜线纹理
        
        elif op_type == "moved":
            old_num = str(op["old_idx"] + 1)
            new_num = str(op["new_idx"] + 1)
            left_badge = f'<div class="tag tag-moved">↷ 移至右侧第 {new_num} 段</div>'
            right_badge = f'<div class="tag tag-moved">↶ 来自左侧第 {old_num} 段</div>'
            left_html = left_badge + html.escape(a[op["old_idx"]])
            right_html = right_badge + html.escape(b[op["new_idx"]])
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
            --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
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
            background-image: repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(0,0,0,0.02) 10px, rgba(0,0,0,0.02) 20px);
        }}

        /* 段内 Inline Token 渲染（圆润质感） */
        .token-ins {{ background: #bbf7d0; color: #166534; padding: 2px 6px; border-radius: 4px; font-weight: 500; }}
        .token-del {{ background: #fecaca; color: #991b1b; padding: 2px 6px; border-radius: 4px; text-decoration: line-through; }}

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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📑 智能文档对比分析</h1>
            <div class="stats">
                <span class="stat-total">共发现 {total_changes} 处核心变更</span>
                <span class="stat-pill pill-ins">+{inserted_cnt} 增</span>
                <span class="stat-pill pill-del">-{deleted_cnt} 删</span>
                <span class="stat-pill pill-mod">~{modified_cnt} 改</span>
                <span class="stat-pill pill-mov">⇅{moved_cnt} 移</span>
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