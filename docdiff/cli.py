import argparse
import sys
import json
from .parser import extract_blocks
from .core import diff_docx
from .render_term import render as render_term
from .render_html import render as render_html

def main():
    parser = argparse.ArgumentParser(
        description="docdiff - Office-CLI 风格的 Word 文档对比工具"
    )
    parser.add_argument("old", help="旧文档路径 (.docx)")
    parser.add_argument("new", help="新文档路径 (.docx)")
    
    parser.add_argument(
        "--html", 
        help="输出为自包含的 HTML 报告，并指定保存路径（例如：out.html）"
    )
    
    # 新增 --json 参数（开关类型的 flag）
    parser.add_argument(
        "--json", 
        action="store_true",
        help="以 JSON 格式将变更列表输出到标准输出 (stdout)"
    )

    args = parser.parse_args()

    try:
        # 提取并对比文档
        a = extract_blocks(args.old)
        b = extract_blocks(args.new)
        ops = diff_docx(args.old, args.new)
        # 渲染层目前只吃段落文本(V2-C 表格渲染时升级为 Block)
        texts_a = [x.text for x in a]
        texts_b = [x.text for x in b]

        # 判断是否有真正的变更（存在不是 unchanged 的操作）
        has_diff = any(op["op"] != "unchanged" for op in ops)

        # 路由输出模式
        if args.json:
            # 纯数据模式，不再输出其他人话提示
            print(json.dumps(ops, ensure_ascii=False, indent=2))
        elif args.html:
            render_html(ops, texts_a, texts_b, args.html)
            print(f"✅ HTML 对比报告已成功生成：{args.html}")
        else:
            render_term(ops, texts_a, texts_b)
            
        # 根据是否有变更返回退出码（0 无差异，1 有差异）
        sys.exit(1 if has_diff else 0)
            
    except FileNotFoundError as e:
        # 文件不存在时的专属 JSON 报错结构，输出到 stderr
        err_obj = {
            "error": f"file not found: {e.filename}", 
            "code": "file_not_found", 
            "suggestion": "检查路径是否拼写正确"
        }
        print(json.dumps(err_obj, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)
        
    except Exception as e:
        # 其他未捕获异常的兜底
        err_obj = {
            "error": str(e), 
            "code": "unexpected_error", 
            "suggestion": "请确保输入的是有效的 .docx 格式文件"
        }
        print(json.dumps(err_obj, ensure_ascii=False), file=sys.stderr)
        sys.exit(2)

if __name__ == "__main__":
    main()