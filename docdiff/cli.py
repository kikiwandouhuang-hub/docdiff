import argparse
import sys
from .parser import extract_paragraphs
from .core import diff_docx
from .render_term import render


def main():
    parser = argparse.ArgumentParser(
        description="docdiff - Office-CLI 风格的 Word 文档对比工具"
    )
    parser.add_argument("old", help="旧文档路径 (.docx)")
    parser.add_argument("new", help="新文档路径 (.docx)")

    args = parser.parse_args()

    try:
        a = extract_paragraphs(args.old)
        b = extract_paragraphs(args.new)
        ops = diff_docx(args.old, args.new)
        render(ops, a, b)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()