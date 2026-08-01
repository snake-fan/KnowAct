# Benchmark Question Banks

该目录存放独立、版本化的 benchmark 双语题库 JSON，不存放参与者回答、Simulator
回答或实验运行结果。

## 当前题库

| Domain | Bank ID | 题数 | 概念数 | 参考范围 |
| --- | --- | ---: | ---: | --- |
| Economy | `economy_atomic_v2` | 80 | 22 | CORE *The Economy* 1.0 Units 1–4 |
| ISLP | `islp_atomic_v2` | 80 | 21 | ISLP Chapters 2–3 及官方 Python companion |
| OSTEP | `ostep_atomic_v2` | 80 | 24 | OSTEP CPU virtualization、process API 与 scheduling |

旧的 21 题复合提问版保留在 `archive/islp_bilingual_v1.json`，不参与后端目录发现。

## v2 题目约束

每个题库文件必须包含稳定的 `bank_id`、`version`、`benchmark_domain` 和
`questions`。每道题使用稳定 `question_id`，并在 `prompts.en` 与
`prompts.zh_cn` 中保存语义等价题面；切换语言不得改变题目 identity。

每题还必须满足：

- 只完成一个 `cognitive_operation`，英文和中文题面各只有一个终止问号；
- 英文不超过 55 词和 320 字符，中文不超过 180 字符；
- 至少引用一条已审核来源 `source_reference_ids`；
- 通过 `reviews/{bank_id}.quality_review.json` 中的逐题角色试答审核；
- 题库内容 SHA-256 必须与审核文件绑定，修改题面后必须重新审核。

当前试答回答为 3–23 个英文词，覆盖 L2–L4 认知信号。审核文件只用于 authoring
与加载校验，不通过 participant API 或 tested-agent boundary 返回。

## 验证边界

`expert_review_status` 当前仍为 `pending`。这些题已通过来源、原子性、双语等价性和
简短角色试答的 author-side screening，但这不等于领域专家内容效度、翻译等值、题项
难度、区分度或心理测量效度已经建立。

三个 domain 当前只有 candidate graph 可供概念对齐，因此
`reviewed_target_node_ids` 保持为空。只有 reviewed graph 发布并完成专家绑定后才可填写。

完整方法和来源审核见
[`docs/research/question_bank_authoring/README.md`](../../docs/research/question_bank_authoring/README.md)。
