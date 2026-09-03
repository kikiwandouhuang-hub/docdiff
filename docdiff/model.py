"""model.py — 文档的中间表示
v1: list[str],一个字符串 = 一个段落
v2: list[Block],Block 可以是段落也可以是表格
"""
from dataclasses import dataclass, field

CELL_SEP = "\x1f"  # 单元分隔符:不用 "|",因为单元格内容里可能真有竖线


@dataclass
class Block:
    kind: str                          # "paragraph" | "table"
    text: str = ""                     # paragraph 的比较键
    rows: list[list[str]] = field(default_factory=list)   # table 专用:二维单元格文本
    style: str | None = None           # w:pStyle,V2-E 会用
    fmt: dict | None = None            # 格式指纹,V2-E 会用

    def key(self) -> str:
        """Block 参与文档级 LCS 时的比较键。
        paragraph -> text
        table     -> "TBL:" + 首行拼接(表头行当表格的指纹)
        """
        if self.kind == "table":
            if self.rows:
                return "TBL:" + CELL_SEP.join(self.rows[0])
            return "TBL:"
        return self.text

    def __eq__(self, other) -> bool:
        """比较 kind 和 key()。
        注意:这里**不比较全部单元格** —— 表格内容改了但表头没变,
        我们希望文档级 LCS 认为"是同一个表格",然后交给表格内部 diff 处理。
        表格的相等性是"身份相等"而不是"内容相等"。
        """
        if not isinstance(other, Block):
            return NotImplemented
        return self.kind == other.kind and self.key() == other.key()

    def __hash__(self) -> int:
        return hash((self.kind, self.key()))


def block_to_dict(b: Block) -> dict:
    """JSON 序列化(--embed-text 把 blocks 完整写进信封)。"""
    return {
        "kind": b.kind,
        "text": b.text,
        "rows": b.rows,
        "style": b.style,
        "fmt": b.fmt,
    }


def block_from_dict(d: dict) -> Block:
    """从 JSON 还原 Block(--from-json 反向渲染用)。"""
    return Block(
        kind=d["kind"],
        text=d.get("text", ""),
        rows=d.get("rows", []),
        style=d.get("style"),
        fmt=d.get("fmt"),
    )
