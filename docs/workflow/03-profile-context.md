# Workflow 3: Profile Context Authoring and Confirmation

## 目标与位置

Profile Context 将 benchmark author 提供的粗略用户描述变成结构化、可读的合成用户背景。它为 map generation 提供一致的 persona 输入，并在 simulator 中仅影响措辞风格；它不含 node-level mastery，也不参与评分。

```text
rough user description -> candidate profile-context run -> structural validation
-> author edit (optional) -> explicit confirmation -> users/{user_id}/profile_context.json
```

## 设计亮点

### 在接触知识图谱之前生成 persona

Profile Context Agent 只能看到 rough description、benchmark domain 和可选 domain summary，不能看到 graph nodes、rubrics 或 edges。这防止 persona 被反向填充成“恰好解释预设知识状态”的伪装输入。

### 结构化而轻量

固定字段为 `summary`、`background`、`prior_experience`、`goals`、`preferences`。校验关注非空摘要、背景和目标、domain identity 以及禁止额外字段，而不以脆弱文本规则评判 persona 的“真实性”。

### 确认后不可变

candidate run 用 `run_id`，确认时才赋予正式 `user_id`。候选草稿可以原位编辑；一经确认即发布 immutable snapshot，任何改动都使用新的 `user_id`，从而不改变已生成 map 或 episode 的身份基础。

## 关键边界

- confirmed context 绑定 domain，不绑定 graph version，可复用于同一 domain 的后续 reviewed graph。
- candidate profile run 至多确认一次，避免多个 user id 指向同一草稿。
- map generation 接收 confirmed snapshot；runtime Tested Agent 不可见该 artifact。
