# 实验 02 数据字典

[English](data_dictionary.md)

## 标识符层级

| 字段 | 含义 | 发布等级 |
| --- | --- | --- |
| `study_id` | 冻结的协议实例 | 公开 |
| `participant_code` | 匿名参与者标识符 | 受限 |
| `linkage_key` | 单独保存的身份到代码映射 | 私有；绝不作为模型输入 |
| `question_id` | 冻结的 Set A 或 Set B 条目 | 获批发布后公开 |
| `condition_id` | 冻结的 Simulator 条件 | 公开 |
| `seed` | 重复生成 seed 或日程索引 | 揭盲前受限 |
| `answer_artifact_id` | 内部真人或 Simulator 回答标识符 | 受限 |
| `presentation_id` | 盲评条目标识符 | 揭盲前受限 |
| `rater_code` | 匿名专家评分者标识符 | 受限 |

## 核心数据表

### 参与者画像

包含问卷回答和参与者确认的 Profile Context。

不得包含姓名、联系方式或精确的机构/雇主信息。

### 真人回答

每次“参与者—问题”作答占一行。记录逐字文本、时间、跳过/拒答状态与收集顺序。

Set A 与 Set B 必须能够明确区分。

### Human Reviewed Map

包含经审核的节点状态、仅指向 Set A 的证据引用、修正历史与未解决状态。

Set B 数据绝不能进入此表。

### Simulator 回答

每个“参与者—问题—条件—seed”占一行。失败与 fallback 行也必须保留。

原始隐藏上下文、blueprint 与 debug trace 作为独立受限产物保存，不发送给评分者。

### 评分

参与者自我忠实度评分与专家评分使用不同的数据表。

只有在两类评分数据均冻结后，才可关联揭盲密钥。

## 缺失值词表

分析导出中应使用显式取值，不使用空字符串：

- `not_applicable`
- `not_asked`
- `participant_skipped`
- `participant_withdrew`
- `technical_failure`
- `generation_failure`
- `fallback_answer`
- `unratable`
- `unresolved_map_state`

除非预注册明确规定，否则不得把跳过回答转换为 L0，也不得把生成失败转换为较低的自我忠实度评分。

## 可见性与发布等级

- **公开：** 协议、空白量表、冻结题目文本、聚合统计和获批的去标识化片段；
- **受限：** 参与者代码、原始回答、Profile Context、Reviewed Map、评分、随机化与揭盲密钥；
- **私有：** 同意记录、联系方式、链接密钥与退出日志；
- **仅 Simulator：** hidden map/evidence、blueprint 与原始隐藏 debug trace。

私有和受限的原始数据不得提交到本仓库。
