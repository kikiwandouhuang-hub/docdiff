import argparse
import json
import sys
from typing import Any

from . import SCHEMA, __version__
from .core import diff_docx
from .model import Block, Op, block_from_dict, block_to_dict
from .parser import extract_blocks
from .render_html import render as render_html
from .render_term import render as render_term


def _stats(ops: list[Op]) -> dict[str, int]:
    """文档级变更统计。total 恒等于各分量之和,这是一个不变量。"""
    stats = {
        "inserted": sum(1 for op in ops if op["op"] in ("inserted", "insert")),
        "deleted": sum(1 for op in ops if op["op"] in ("deleted", "delete")),
        "modified": sum(1 for op in ops if op["op"] == "modified"),
        "moved": sum(1 for op in ops if op["op"] == "moved"),
        "table_modified": sum(1 for op in ops if op["op"] == "table_modified"),
        "formatted": sum(1 for op in ops if op["op"] == "formatted"),
    }
    stats["total"] = sum(stats.values())
    return stats


def build_envelope(
    old_path: str, new_path: str, ops: list[Op], a: list[Block], b: list[Block],
    embed: bool,
) -> dict[str, Any]:
    """JSON 信封。默认轻量(blocks 留空),--embed-text 时自包含。"""
    return {
        "schema": SCHEMA,
        "tool_version": __version__,
        "old": {"path": old_path, "blocks": [block_to_dict(x) for x in a] if embed else []},
        "new": {"path": new_path, "blocks": [block_to_dict(x) for x in b] if embed else []},
        "stats": _stats(ops),
        "ops": ops,
    }


def _error(msg: str, code: str, suggestion: str) -> None:
    err_obj = {"error": msg, "code": code, "suggestion": suggestion}
    print(json.dumps(err_obj, ensure_ascii=False), file=sys.stderr)
    sys.exit(2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="docdiff - Office-CLI 风格的 Word 文档对比工具"
    )
    parser.add_argument("old", nargs="?", help="旧文档路径 (.docx)")
    parser.add_argument("new", nargs="?", help="新文档路径 (.docx)")

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
    parser.add_argument(
        "--embed-text",
        action="store_true",
        help="与 --json 连用:把 old/new 的 blocks 完整序列化进信封,使输出自包含"
    )
    parser.add_argument(
        "--from-json",
        metavar="FILE",
        help="从 --json --embed-text 生成的 JSON 反向渲染(--html 或终端)"
    )
    parser.add_argument(
        "--check-format",
        action="store_true",
        help="把格式变更(formatted)纳入差异判定,退出码语义与 CI 对齐"
    )

    args = parser.parse_args()

    if args.embed_text and not args.json:
        _error("--embed-text 只能与 --json 连用", "bad_flags",
               "用 `docdiff OLD NEW --json --embed-text` 生成自包含 JSON")
    if args.from_json and (args.old or args.new):
        _error("--from-json 不能与文档路径参数同时使用", "bad_flags",
               "要么给两份 .docx 对比,要么从 JSON 反向渲染,二选一")
    if args.from_json and args.json:
        _error("--from-json 与 --json 不能连用", "bad_flags",
               "--from-json 是反向渲染入口,输出走 --html 或终端")
    if not args.from_json and not (args.old and args.new):
        _error("缺少文档路径参数", "missing_args",
               "用法: docdiff OLD.docx NEW.docx,或用 --from-json FILE")

    try:
        if args.from_json:
            with open(args.from_json, encoding="utf-8") as f:
                envelope = json.load(f)
            if envelope.get("schema") != SCHEMA:
                _error(f"JSON schema 不匹配: 期望 {SCHEMA},实际 {envelope.get('schema')}",
                       "schema_mismatch", "请用当前版本重新生成 JSON")
            a = [block_from_dict(d) for d in envelope["old"].get("blocks", [])]
            b = [block_from_dict(d) for d in envelope["new"].get("blocks", [])]
            if not a and not b:
                # 空文档与"没嵌入文本"无法区分,报错提示而不是输出空渲染
                _error("JSON 未嵌入文本,无法反向渲染", "no_embedded_text",
                       "生成时加 --embed-text: docdiff OLD NEW --json --embed-text")
            ops = envelope["ops"]
        else:
            # 提取并对比文档
            a = extract_blocks(args.old)
            b = extract_blocks(args.new)
            ops = diff_docx(args.old, args.new)

        # 退出码契约:diff 的粒度是产品决策。CI 里最常见的诉求是"内容变了吗",
        # 所以 formatted 默认不计入差异判定;--check-format 把它纳入(opt-in)。
        formatted_cnt = sum(1 for op in ops if op["op"] == "formatted")
        if args.check_format:
            has_diff = any(op["op"] != "unchanged" for op in ops)
        else:
            has_diff = any(op["op"] not in ("unchanged", "formatted") for op in ops)

        # 路由输出模式
        if args.json and not args.from_json:
            envelope = build_envelope(args.old, args.new, ops, a, b, args.embed_text)
            print(json.dumps(envelope, ensure_ascii=False, indent=2))
        elif args.html:
            render_html(ops, a, b, args.html)
            print(f"✅ HTML 对比报告已成功生成：{args.html}")
        else:
            render_term(ops, a, b)
            if not has_diff and formatted_cnt:
                print(f"内容一致,存在 {formatted_cnt} 处格式差异(用 --check-format 纳入判定)")

        # 根据是否有变更返回退出码（0 无差异，1 有差异）
        sys.exit(1 if has_diff else 0)

    except FileNotFoundError as e:
        # 文件不存在时的专属 JSON 报错结构，输出到 stderr
        _error(f"file not found: {e.filename}", "file_not_found", "检查路径是否拼写正确")

    except Exception as e:
        # 其他未捕获异常的兜底
        _error(str(e), "unexpected_error", "请确保输入的是有效的 .docx 格式文件")


if __name__ == "__main__":
    main()
