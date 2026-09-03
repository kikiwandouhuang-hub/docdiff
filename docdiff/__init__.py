"""docdiff — .docx 结构感知对比工具。"""

__version__ = "0.2.0"

# JSON 输出的 schema 版本:消费方靠它判断格式。
# 从第一次输出 JSON 起就带上,以后改格式时旧消费方能识别。
SCHEMA = "docdiff/2"
