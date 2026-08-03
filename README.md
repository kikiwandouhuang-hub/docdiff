# docdiff

[![Tests](https://github.com/kikiwandouhuang-hub/docdiff/actions/workflows/test.yml/badge.svg)](https://github.com/kikiwandouhuang-hub/docdiff/actions)

## §1 简介

> Office-CLI 时代缺失的那条 `diff` 命令——对比两份 `.docx` 文档，输出结构感知、能识别移动、且“说人话”的变更报告。

![终端效果展示](docs/screenshots/term-all.png)
![HTML 效果展示](docs/screenshots/html-new1.png)

---

## §2 Why：为什么需要 docdiff？

在对比文档时，如果使用传统的“按行号（Index-based）”逐行对比方法，会遇到一个致命痛点——**索引雪崩**。

假设你有一份 12 段的文档，仅在开头插入 1 个新段落。朴素对比会报出 12 段全部删除 + 13 段全部新增，共 25 处变更。正确答案显然应该是 1 处。

**docdiff 的解法：LCS 算法**
本工具采用 LCS 动态规划对齐段落，从全局视角寻找两份文档的“最大共识骨架”。对于 `new2.docx` 的首段插入测试，算法能够精准滤出这唯一的 1 个 `inserted`，其余后续段落依然被稳稳判定为 `unchanged`，解决了索引错位带来的雪崩问题。

![new2 验金石输出——12 段中仅 1 处 inserted](docs/screenshots/term-new2.png)

上图即 new2 实验的实际输出：12 段中 11 段 unchanged，唯一的 1 处 inserted 精准定位在开头。

---

## §3 核心架构

项目采用三层解耦架构。通过统一的变更操作列表（`ops`）作为中间表示——它是 Python 原生的 `list[dict]` 结构，只有在终端执行 `--json` 时才会被序列化。这种彻底的解耦带来的实证是：**Week 2 到 Week 3 先后加了终端、HTML、JSON 三种输出，算法层一行代码没改。**

![架构图](docs/architecture.png)

---

## §4 安装与使用

### 环境准备
核心代码仅依赖 Python 3.10+ 环境，**运行时零第三方依赖**（`zipfile` / `xml` / `difflib` / `argparse` 全是标准库）。

```bash
git clone https://github.com/kikiwandouhuang-hub/docdiff.git
cd docdiff
```

### 命令示例

**1. 默认输出（终端彩色对比）**
最直观的 CLI 体验，在终端内渲染增删改移。
```bash
python3 -m docdiff.cli samples/old.docx samples/new1.docx
```

**2. HTML 报告输出（生成双栏高亮网页）**
生成一个内联了 CSS、完全自包含的 `.html` 单文件，双击即可在浏览器中优雅审阅。
```bash
python3 -m docdiff.cli samples/old.docx samples/new3.docx --html out.html
```

**3. JSON 数据输出（便于流水线集成）**
输出纯结构化数据，供其他程序消费。
```bash
python3 -m docdiff.cli samples/old.docx samples/new1.docx --json
```

### 退出码 (Exit Codes)
与 `git diff` 同款约定，对 CI/CD 极度友好：
| 退出码 | 含义 | 说明 |
|:---:|---|---|
| `0` | **无差异** | 两份文档的内容在段落级别完全一致。 |
| `1` | **有差异** | 检测到文档存在实质性变更（增、删、改、移）。 |
| `2` | **执行错误** | 抛出结构化报错（如：文件不存在 `file_not_found`），输出至 `stderr`。 |

![退出码验证](docs/screenshots/exit-codes.png)

---

## §5 Roadmap

目前的 MVP 版本已跑通了稳定可靠的段落级/词级管线，未来的演进方向包括：
- [1] **表格 Diff**：解析 `<w:tbl>`，支持单元格级别的增删改追踪。 `P0`
- [2] **格式变更检测**：不仅对比纯文本，还能识别加粗、标红、字体放大等样式变化。 `P1`
- [3] **Redline 修订模式**：逆向生成一份带“Word 原生修订标记”的 `.docx` 成果文件。 `P1`
- [4] **xlsx 公式对比**：跨界扩展，支持对 Excel 隐藏的底层公式变更进行比对。 `P2`
- [5] **三方 Merge / Blame**：支持类似 Git 的 `3-way merge` 和历史溯源功能。 `P2`
- [6] **MCP 模式接入**：与大模型（LLM）协议打通，提供基于变更日志的自动摘要与解读。 `P2`

---

## §6 设计决策与踩坑记录

在开发过程中，我做出了一些影响深远的技术取舍：

1. **为什么绝不用 `<w:r>` (Run) 作为对比单位？**
   在解剖 OOXML 时发现，Word 内部对 `<w:r>` 的切分极其“随性”（常常因为拼写检查或字体微调，将一句话切得稀碎）。拿 Run 做对比会导致满屏的“假变更”。因此我坚决在解析器层将 `<w:p>`（段落）内部所有的文本强行拼合成完整字符串。
2. **掐头去尾优化的收益**
   在处理真实文档时，我剥离了首尾相同的段落，仅对中间差异区跑 LCS。这一操作在数学上是安全的（公共前缀必然属于某个最优 LCS），但收益巨大：它将动态规划矩阵的大小从 $m \times n$ 极速压缩，极大降低了时间与空间复杂度。
3. **`ops` 采用纯索引级表示设计**
   变更操作列表 `ops` 字典中仅存储 `old_idx` 和 `new_idx` 下标，不携带原文。这在节省内存消耗的同时，渲染器依然可以通过传入的 `a`, `b` 列表按索引完成精准取词，完全没有破坏三层架构的解耦性。
4. **重复段落的贪心配对**
   如果文档中有多个完全相同的段落发生了移动，该如何映射来源？我在 `detect_moves` 中引入了“按文档顺序贪心配对”策略。这确保了算法底层的“不变量”（每个下标仅出现一次）不被破坏，同时在视觉渲染上最符合人类直觉。
   下图为 new3 验金石的 HTML 输出，moved 标注清晰可见：
   ![new3 moved 标注](docs/screenshots/html-new3.png)
5. **相似度阈值的取舍与段内 Diff**
   为了将“一删一增”合并为“修改（modified）”，在 `refine.py` 中使用了 `difflib.SequenceMatcher`。经过样本实测，将 `SIM_THRESHOLD` 设为 `0.6` 能够平衡“微调修改”和“重写了一段全新的话”之间的界限。值得一提的是，MVP 阶段的段内 diff 同样暂时基于 `difflib` 提供词/字符级差异比对，在 v2 版本中，计划将这部分替换为自研的精细化词级 LCS 算法。