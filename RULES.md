# 云脉·智诊伴学 · 协作规则同步副本

> 本文件由 `python scripts/sync_rules.py` 从 `.trae/rules/` 自动同步生成，禁止手写。

## 一、默认协作流程

收到开发类需求后，按以下五步执行，不可跳步：

1. **重述需求**：一句话重述用户意图，确认理解一致。
2. **生成计划并等确认**：列出核心目标 / 步骤 / 涉及文件 / 风险点 / 验证方式，等用户确认后再执行。
3. **执行**：开始前必读 loop_log（Grep 检索 `docs/loop_log/` 历史教训）；优先复用现有能力；能并行尽量并行。
4. **自检**：对照 `.trae/checklists/dev-checklist.md` 逐项检查；`check_book_structure --strict` + `pytest` + 回归集必须全过。
5. **沉淀**：本次改动是否暴露新共性问题？是否需要更新 rules / checklist / loop_log？

## 二、关键纪律

- 不在用户确认前改代码
- 不假装 Skill 可以调度 sub-agents（路径 C 用 Task 工具，路径 A 单 Agent 串行，路径 B Python 引擎）
- 不破坏现有体系
- 不过度工程化
- 不跳过沉淀
- 禁止以"问题非本次引入"为由跳过修复
- 禁止在存在任何校验问题时执行 push/merge（含 P2）

## 三、合并前必过门禁

```bash
python scripts/check_book_structure.py --output content --strict
pytest -q
bash tests/run_regression_suite.sh
```

## 四、push 前必校验提交信息

```bash
python scripts/validate_commit_messages.py origin/master..HEAD
```

标题与正文均须中文，且准确概括当前修改。

## 五、loop_log 沉淀

- 只 append 到当月分片 `docs/loop_log/YYYY-MM.md`
- 主文件索引由 `scripts/regen_loop_log_index.py` 自动生成，禁止手写
- 写入后运行 `python scripts/check_loop_log.py` 校验
- #lesson slug 受控清单：`git_hygiene` / `reader_interaction` / `content_quality` / `book_structure` / `deployment` / `soul_injection` / `ai_course`

详细规则见 `.trae/rules/dev-workflow.md` 与 `.trae/rules/bug-reporting.md`。
