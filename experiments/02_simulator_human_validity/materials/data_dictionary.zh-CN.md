# 实验 02 数据字典

[English](data_dictionary.md)

## 标识符

| 字段 | 含义 | 发布等级 |
| --- | --- | --- |
| `participant_code` | 匿名参与者代码 | 受限 |
| `profile_id` | 参与者确认的 Profile Context | 受限 |
| `map_id` | 参与者确认的 reviewed Knowledge Map | 受限 |
| `session_id` | 一次可恢复的 Simulator Test 会话 | 受限 |
| `question_bank_id` / `question_bank_version` | 冻结题库身份 | 公开 |
| `question_id` | 双语题目的稳定身份 | 获批后公开 |
| `sampling_seed` | 20 题抽样与顺序的复现依据 | 受限 |
| `blind_review_status` | 是否已进入后续专家盲评 | 受限 |

## 会话级数据

会话保存 participant、domain、confirmed graph/profile/map identity、语言、provider、
题库版本、抽样 seed、20 道题及固定顺序、创建/更新时间和完成状态。

Profile、Map 和原始回答属于参与者数据。姓名、联系方式、机构精确名称和身份链接密钥
不得写入会话。

## 问题级数据

每个 `question_result` 保存：

- `question_id`、题面和原始抽样顺序；
- 参与者回答及提交时间；
- Simulator 回答、coarse observation、warning、生成错误和隐藏 trace 引用；
- 五项 1--5 自评；
- `direct_use | minor_bias | major_revision | not_representative` 总体判断；
- 可选自由文本说明；
- `blind_review_status = pending`，直到后续盲评阶段另行更新。

五项自评分别是核心内容、知识水平、能力边界、表达方式和整体代表性。未经 instrument
验证，不应默认合成为单一总分。

## Map 修订数据

`map_reviews/{map_id}.json` 保存原始 Candidate Map identity、逐节点参与者修订和最终
reviewed map identity。最终 map 中用于 Simulator 的 `self_report` evidence 为
`simulator_only`，不得出现在盲评包。

## 缺失和失败

- 参与者未答：保留未完成状态，不生成 Simulator 回答；
- Simulator 失败：保留真人回答和 `simulator_error`，允许重试；
- 未完成自评：会话保持 `in_progress`；
- 只有 20 题全部完整时，才标记 `completed`。

不得把跳过回答转换为 L0，也不得把生成失败自动转换为低分。

## 可见性与发布

- **公开：** 协议、题库定义、空白量表、聚合统计和获批的去标识化片段；
- **受限：** participant code、Profile、Map、原始回答、会话、自评和抽样 seed；
- **私有：** 同意记录、联系方式、身份链接密钥和退出日志；
- **仅 Simulator：** hidden map/evidence、blueprint 和隐藏 debug trace。

私有和受限原始数据不得提交到仓库。专家盲评包必须使用新的 presentation ID，并排除
participant code、Profile、Map、自评与 debug trace。
