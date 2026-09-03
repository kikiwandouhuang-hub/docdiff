# Changelog

## [Unreleased] — v2 开发中
### Added
- V2-A 自研词级 LCS 段内细化:零依赖规则分词器(tokenize.py,CJK 逐字 + 拉丁成词)
  + 与领域无关的 seqdiff 通用对齐层 + 词级 inline_diff 替换 difflib
- 长段落两级细化(句级对齐 + 句内词级),规模上限 500_000,全文无句界时 difflib 兜底
- 性能基准(experiments/gen_big_docx.py),数字进 README
### Changed
- 基于扫参实验，将段落相似度配对阈值 (`SIM_THRESHOLD`) 从 0.6 调整为 0.7，以优先控制误配代价。
### Changed
- 引入局部坐标系的位置约束后，远距离误配已被物理拦截，将 `SIM_THRESHOLD` 阈值由 0.7 安全下调至 0.5，大幅降低漏配率。
### Changed
- SIM_THRESHOLD: 0.6 → 0.7 → 0.5 → 0.7
  最终依据为位置约束消融实验(experiments/threshold_sweep.py,n=17)。
  中间的 0.5 基于"位置约束已排除误配干扰"的假设,消融表证伪了该假设:
  位置约束与阈值功能部分重叠,前者降低整体错误代价但不改变最优阈值位置。
## [0.1.0] — 2026-08-06
### Added
- 段落级 LCS 对齐,解决索引雪崩(new2 验金石:12 段仅报 1 处 inserted)
- 段落移动检测(按文档顺序贪心配对处理重复段落歧义)
- 相似段落配对为 modified(difflib,阈值 0.6)+ 段内细化
- 三种输出:ANSI 终端 / 自包含 HTML / JSON
- 退出码 0/1/2(与 git diff 同款约定)
- 掐头去尾优化 + 坐标系转换
- 11 个测试 + GitHub Actions CI
