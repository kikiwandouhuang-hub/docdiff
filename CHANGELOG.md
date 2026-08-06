# Changelog

## [Unreleased] — v2 开发中

## [0.1.0] — 2026-08-06
### Added
- 段落级 LCS 对齐,解决索引雪崩(new2 验金石:12 段仅报 1 处 inserted)
- 段落移动检测(按文档顺序贪心配对处理重复段落歧义)
- 相似段落配对为 modified(difflib,阈值 0.6)+ 段内细化
- 三种输出:ANSI 终端 / 自包含 HTML / JSON
- 退出码 0/1/2(与 git diff 同款约定)
- 掐头去尾优化 + 坐标系转换
- 11 个测试 + GitHub Actions CI
