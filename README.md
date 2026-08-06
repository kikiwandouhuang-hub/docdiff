# docdiff

[![Tests](https://github.com/kikiwandouhuang-hub/docdiff/actions/workflows/test.yml/badge.svg)](https://github.com/kikiwandouhuang-hub/docdiff/actions)

## 简介

> Office-CLI 时代缺失的那条 diff 命令——对比两份 .docx 文档，输出结构感知、能识别移动、且简洁易懂的变更报告。

![终端效果展示](docs/screenshots/term-all.png)
![HTML 效果展示](docs/screenshots/html-new1.png)

---

## Why: 为什么需要 docdiff？

在对比文档时，如果使用传统的基于行号逐行对比方法，常会遇到一个致命痛点——索引雪崩。

假设你有一份 12 段的文档，仅在开头插入 1 个新段落。由于逐位置比较时后续内容全部错位，每处错位都会被记为一删一增，朴素对比会报出 12 段全部删除加上 13 段全部新增，共 25 处变更。正确答案显然应该是 1 处。

**docdiff 的解法：LCS 算法**
本工具采用 LCS 动态规划对齐段落，从全局视角寻找两份文档的最大共识骨架。对于 new2.docx 的首段插入测试，算法能够滤出这唯一的 1 个 inserted，其余后续段落依然被稳稳判定为 unchanged，解决了索引错位带来的雪崩问题。

![new2 验金石输出——12 段中仅 1 处 inserted](docs/screenshots/term-new2.png)

上图即 new2 实验的输出：12 段中 11 段 unchanged，唯一的 1 处 inserted 定位在开头。

---

## 核心架构

项目采用三层解耦架构。通过统一的变更操作列表 ops 作为中间表示——它是 Python 原生的字典列表结构，只有在终端执行 `--json` 时才会被序列化。这种彻底的解耦带来的实证是：Week 2 到 Week 3 先后加了终端、HTML、JSON 三种输出，算法层一行代码没改。

![架构图](docs/architecture.png)

---

## 安装与使用

### 环境准备
核心代码仅依赖 Python 3.10 及以上环境，运行时零第三方依赖，zipfile、xml、difflib、argparse 全是标准库。

```bash
git clone https://github.com/kikiwandouhuang-hub/docdiff.git
cd docdiff
```

### 命令示例

**1. 默认终端彩色输出**
直观的 CLI 体验，在终端内渲染增删改移。
```bash
python3 -m docdiff.cli samples/old.docx samples/new1.docx
```

**2. HTML 报告输出**
生成一个内联了 CSS、完全自包含的 .html 单文件，双击即可在浏览器中审阅。
```bash
python3 -m docdiff.cli samples/old.docx samples/new3.docx --html out.html
```

**3. JSON 数据输出**
输出纯结构化数据，供其他程序消费。
```bash
python3 -m docdiff.cli samples/old.docx samples/new1.docx --json
```

### 退出码
与 git diff 同款约定，对 CI/CD 友好：
| 退出码 | 含义 | 说明 |
|:---:|---|---|
| `0` | **无差异** | 两份文档的内容在段落级别完全一致。 |
| `1` | **有差异** | 检测到文档存在实质性变更。 |
| `2` | **执行错误** | 抛出结构化报错输出至 stderr。 |

![退出码验证](docs/screenshots/exit-codes.png)

---

## Roadmap

目前的 MVP 版本已跑通了稳定可靠的段落级与词级管线，未来的演进方向包括：
- [ ] 表格 Diff：解析 tbl 标签，支持单元格级别的增删改追踪。 P0
- [ ] 格式变更检测：不仅对比纯文本，还能识别加粗、标红、字体放大等样式变化。 P1
- [ ] Redline 修订模式：逆向生成一份带 Word 原生修订标记的 .docx 成果文件。 P1
- [ ] 序列化原文：新增 `--json --embed-text` 参数，把新旧原文一并序列化。 P2
- [ ] xlsx 公式对比：跨界扩展，支持对 Excel 隐藏的底层公式变更进行比对。 P2
- [ ] 三方 Merge 与 Blame：支持类似 Git 的三方合并和历史溯源功能。 P2
- [ ] MCP 模式接入：与大语言模型协议打通，提供基于变更日志的自动摘要与解读。 P2

---

## 设计决策与踩坑记录

在开发过程中，我做出了一些影响深远的技术取舍：

1. **为什么不用 Run 节点作为对比单位？**
   在解剖 OOXML 时发现，Word 内部对 Run 节点的切分极其随性，常常因为拼写检查或字体微调，将一句话切得稀碎。拿 Run 节点做对比会导致满屏的假变更。因此我坚决在解析器层将段落内部所有的文本强行拼合成完整字符串。
2. **掐头去尾优化的真实收益**
   在处理真实文档时，我剥离了首尾相同的段落，仅对中间差异区跑 LCS。这一操作在数学上是安全的，因为公共前缀必然属于某个最优解。最坏情况下的复杂度上限不变，依然是 m 乘 n 的规模；但真实文档绝大部分段落未变，dp 表实际只覆盖差异区，计算量大幅下降。
3. **操作列表采用纯索引级表示设计**
   变更操作列表 ops 字典中仅存储 old_idx 和 new_idx 下标，不携带原文。这在节省内存消耗的同时，渲染器依然可以通过传入的文本列表按索引完成取词，没有破坏三层架构的解耦性。这是索引级表示的边界：JSON 输出不能脱离原文独立复用。
4. **重复段落的贪心配对**
   如果文档中有多个相同的段落发生了移动，该如何映射来源？我在 detect_moves 中引入了按文档顺序贪心配对策略。这确保了算法底层每个下标仅出现一次的不变量不被破坏，同时在视觉渲染上符合人类直觉。
   下图为 new3 验金石的 HTML 输出，moved 标注清晰可见：
   ![new3 moved 标注](docs/screenshots/html-new3.png)
   5. **相似度阈值的取舍与能力边界**
   相似度阈值最终取 0.7。我曾用 15 组标注样本做过扫参实验，发现在 0.05 至 0.90 的整个范围内总错误数几乎不变，这说明字符级相似度本身无法分离修改与无关两类样本，两者的取值区间存在结构性重叠。因此该阈值并非按绝对最优选取，而是基于误配代价远高于漏配的原则进行了偏保守取值，毕竟工具凭空捏造一次假变更比漏报一次修改严重得多。真正的改进将来自后续引入的位置邻近性约束，而非无意义地继续调优阈值。此外，同义改写级别的配对已超出纯字符级度量的能力边界，目前将其明确列入系统的已知局限中。