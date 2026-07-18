# 开发协作沉淀主文件（LoopAgent 思维）

> 本文件由 `scripts/regen_loop_log_index.py` 自动生成索引区与计数表，**禁止手写索引条目、禁止手动改计数表**。
> 沉淀本体按月份分片存储于 `docs/loop_log/YYYY-MM.md`，新沉淀 append 到当月分片即可。
> 校验：`python scripts/check_loop_log.py`（P1 阻断）/ `--strict`（P3 也阻断）。

## 索引区

<!-- AUTOGEN START: loop_log index -->

### 最近 20 条沉淀（按日期倒序）

- [2026-07-16 跨项目工程化资产迁移（2026-07-16，HaloRead → knowtrace 精选脚本 + 路径引用调整 + rules 项目名替换）#book_structure](loop_log/2026-07.md#loop-20260716-e86fa5)
- [2026-07-16 专家团三视角并行审查与 P0/P1/P2 修复（2026-07-16，骨架完整性 + 阿里生态对接 + 知识图谱质量 三路并行审查）#book_structure](loop_log/2026-07.md#loop-20260716-74d525)

### 主题锚点

- `#git_hygiene`：推送/合并/冲突/分支治理/commit 覆盖
- `#reader_interaction`：阅读器/沉浸/翻页/吸底栏/SW 缓存
- `#content_quality`：质检规则/灵魂注入/标题评分
- `#book_structure`：排序/校验/命名/去重/双源同步
- `#deployment`：GitHub Pages/魔搭/.nojekyll/SW
- `#soul_injection`：灵魂注入/章回体/总编Agent
- `#ai_course`：专栏批量生成 / subagent 结果丢失

### 教训计数表（≥3 次且未入 checklist 即触发方案 C，见文件末"方案 C 手册"）

| #lesson slug | 出现次数 | 说明 |
|---|---|---|
| `#git_hygiene`（推送/合并/冲突/分支治理/commit 覆盖） | 0 | — |
| `#reader_interaction`（阅读器/沉浸/翻页/吸底栏/SW 缓存） | 0 | — |
| `#content_quality`（质检规则/灵魂注入/标题评分） | 0 | — |
| `#book_structure`（排序/校验/命名/去重/双源同步） | 2 | — |
| `#deployment`（GitHub Pages/魔搭/.nojekyll/SW） | 0 | — |
| `#soul_injection`（灵魂注入/章回体/总编Agent） | 0 | — |
| `#ai_course`（专栏批量生成 / subagent 结果丢失） | 0 | — |

> 共 2 条沉淀，按月份分片存储于 `docs/loop_log/`。

<!-- AUTOGEN END: loop_log index -->

## 方案 C 手册（同一 slug 出现 ≥3 次且未入 checklist 时触发）

方案 C 是「沉淀 → 规则 / checklist / Skill」的升级路径。当某个 `#lesson` slug 在分片中出现 ≥3 次且未声明 `已入checklist: yes`，意味着该类问题反复出现、仅靠记录无法收敛，需要升级为可执行的规则或 checklist 项。

### 触发条件

- `python scripts/check_loop_log.py` 输出 `[P3] #lesson slug 'xxx' 出现 N 次（≥3），但未在任一分片中声明'已入checklist: yes'，建议触发方案 C`

### 升级路径

| 升级目标 | 适用场景 | 产出物 |
|---|---|---|
| `.trae/rules/*.md` | 跨项目通用、需强制执行的开发流程规则 | 新增/更新规则文件 |
| `.trae/checklists/*.md` | 项目特定的合并前/部署前检查清单 | 新增/更新 checklist 条目 |
| `.trae/skills/*/SKILL.md` | 需要被 Agent 主动触发的复合能力 | 新增 Skill |
| `src/utils/quality.py` | 可机器校验的内容质量规则 | 新增校验函数 |

### 操作步骤

1. 在当月分片对应沉淀块末尾追加 `已入checklist: yes`，标记已升级。
2. 选择升级目标（rules / checklists / skills / quality.py），按目标规范产出新规则/条目/Skill/校验函数。
3. 重新运行 `python scripts/regen_loop_log_index.py` 更新主文件计数表。
4. 运行 `python scripts/check_loop_log.py` 确认 P3 告警消失。
