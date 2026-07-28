import sys
import os

def _setup_ansi() -> bool:
    """在 Windows 终端下启用 ANSI 颜色支持；若不支持则降级为无颜色模式。"""
    if sys.platform == "win32":
        # Windows 10+ 可通过 os.system('') 激活 VT100 控制台 ANSI 模式
        ret = os.system("")
        if ret != 0:
            return False
    return True

HAS_COLOR = _setup_ansi()

if HAS_COLOR:
    RESET = "\033[0m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    GREY = "\033[90m"
    # 段内细化：删除文字带下划线，新增文字带加粗
    RED_INLINE = "\033[31m\033[4m"
    GREEN_INLINE = "\033[32m\033[1m"
else:
    RESET = RED = GREEN = YELLOW = GREY = RED_INLINE = GREEN_INLINE = ""


def render(ops: list[dict], a: list[str], b: list[str]) -> None:
    """在终端格式化打印彩色对比结果。"""
    for op in ops:
        op_type = op["op"]

        if op_type == "unchanged":
            old_idx = op["old_idx"]
            new_idx = op["new_idx"]
            text = a[old_idx]
            short_text = text[:20] + ("..." if len(text) > 20 else "")
            print(f"{GREY}  [{old_idx + 1}→{new_idx + 1}]  {short_text}{RESET}")

        elif op_type in ("inserted", "insert"):
            new_idx = op["new_idx"]
            text = b[new_idx]
            print(f"{GREEN}+ [  →{new_idx + 1}] {text}{RESET}")

        elif op_type in ("deleted", "delete"):
            old_idx = op["old_idx"]
            text = a[old_idx]
            print(f"{RED}- [{old_idx + 1}→  ] {text}{RESET}")

        elif op_type == "moved":
            old_idx = op["old_idx"]
            new_idx = op["new_idx"]
            text = b[new_idx]
            print(
                f"{YELLOW}⇅ [{old_idx + 1}→{new_idx + 1}] ⇅ 从第{old_idx + 1}段移至第{new_idx + 1}段: {text}{RESET}"
            )

        elif op_type == "modified":
            old_idx = op["old_idx"]
            new_idx = op["new_idx"]
            inline = op.get("inline", [])

            inline_chunks = []
            for item in inline:
                tag = item["tag"]
                txt = item["text"]
                if tag == "equal":
                    inline_chunks.append(f"{RESET}{txt}")
                elif tag == "delete":
                    inline_chunks.append(f"{RED_INLINE}{txt}{RESET}")
                elif tag == "insert":
                    inline_chunks.append(f"{GREEN_INLINE}{txt}{RESET}")

            inline_str = "".join(inline_chunks)
            print(f"{YELLOW}~ [{old_idx + 1}→{new_idx + 1}] {inline_str}{RESET}")