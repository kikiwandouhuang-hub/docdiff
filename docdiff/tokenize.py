"""tokenize.py — 零依赖规则分词器"""

_CJK_RANGES = [
    (0x3000, 0x303F),  # CJK 标点(、。《》)
    (0x3040, 0x30FF),  # 日文假名
    (0x3400, 0x4DBF),  # 汉字扩展 A
    (0x4E00, 0x9FFF),  # 基本汉字
    (0xAC00, 0xD7AF),  # 韩文音节
    (0xFF00, 0xFFEF),  # 全角字符
]

_WORD_CHARS = "_'-"


def _is_cjk(ch: str) -> bool:
    """判断是否 CJK 字符(含中日韩文字与全角标点)。"""
    code = ord(ch)
    return any(lo <= code <= hi for lo, hi in _CJK_RANGES)


def tokenize(text: str) -> list[str]:
    """把文本切成 token 列表。四条规则:
      1. CJK 字符 -> 每个字一个 token
      2. 连续的 [A-Za-z0-9_'-] -> 合成一个 token(英文单词、数字、缩写)
      3. 其余 ASCII 标点 -> 各自一个 token
      4. 连续空白 -> 折叠成一个 " " token
    不变量: "".join(tokenize(t)) 与 t 的差异只在空白折叠上。
    """
    out = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            # 吃掉连续空白,折叠成一个空格
            while i < n and text[i].isspace():
                i += 1
            out.append(" ")
            continue
        if _is_cjk(ch):
            out.append(ch)
            i += 1
            continue
        if ch.isalnum() or ch in _WORD_CHARS:
            j = i
            # 注意: isalnum() 对汉字也返回 True,必须排除 CJK,
            # 否则 "extract_paragraphs函数" 会被吞成一个 token
            while j < n and not _is_cjk(text[j]) and (
                text[j].isalnum() or text[j] in _WORD_CHARS
            ):
                j += 1
            out.append(text[i:j])
            i = j
            continue
        out.append(ch)
        i += 1
    return out


if __name__ == "__main__":
    for t in ["这是第一段,讲背景。",
              "调用 extract_paragraphs() 函数,返回 list[str]。",
              "Hello  world, it's a test-case 123."]:
        print(tokenize(t))
