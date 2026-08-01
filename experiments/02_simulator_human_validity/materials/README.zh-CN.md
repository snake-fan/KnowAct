# 实验 02 材料

[English](README.md)

## 当前主流程材料

- [`benchmark/question_banks/`](../../../benchmark/question_banks/README.md)：
  独立版本化的 Economy、ISLP、OSTEP 中英文题库；每个领域 80 道原子题，每位参与者
  抽取 20 题；
- [`participant_information_and_consent.zh-CN.md`](participant_information_and_consent.zh-CN.md)：
  参与者说明与知情同意模板；
- [`session_script.zh-CN.md`](session_script.zh-CN.md)：自动化会话的主持与故障处理口径；
- [`data_dictionary.zh-CN.md`](data_dictionary.zh-CN.md)：会话、问答、自评和访问等级。

Profile 表单、Map 逐节点修订、问题抽样、回答对照和五项自评已集成在独立的
`simulator-test-frontend/`，不再要求研究者手工搬运 CSV，也不向参与者暴露内部
research workbench。

## 题库约定

题库作为 benchmark artifact 存储，独立于前端代码、实验专属材料和参与者会话。
每道题必须具有稳定 `question_id`、概念键、题型、单一认知操作、已接受来源引用以及
语义等价的英文和中文题面。语言切换不改变问题身份。只有审核文件完整覆盖全部题目、
逐题包含能体现认知信号的简短角色试答、且内容哈希与题库一致时，后端才接纳该题库。

当前 `reviewed_target_node_ids` 尚未完成正式图谱绑定。因此，题库可用于开发和 pilot，
但 author-side 来源/角色试答筛选不等于领域专家或心理测量验证，不能被描述为已经完成
内容效度验证。

## 暂不进入主流程的遗留材料

以下材料保留用于未来扩展，不是当前参与者会话的必需输入：

- `question_set_a_islp_draft.csv`、`question_set_b_islp_draft.csv`；
- `leakage_challenge_suite.csv`；
- `condition_manifest_template.json`、`randomization_manifest_template.csv`；
- `self_fidelity_rating_form.csv` 的旧十项量表；
- `blinded_expert_rating_form.csv`。

专家盲评接入时，应从已保存会话生成新的去标识化盲评包，不应直接把隐藏 Map、
参与者自评或 debug trace 提供给评分者。

## 使用顺序

1. 完成伦理审批并冻结同意书版本；
2. 审核双语题意，并绑定当前 reviewed graph 节点；
3. 对 Profile、Map 和五项自评进行认知访谈；
4. 运行端到端 pilot，检查断点恢复、技术失败和数据导出；
5. 冻结正式题库、graph、provider/model 与抽样规则；
6. 才开始正式收集。

同意记录、联系方式、链接密钥和原始回答不得提交到仓库。
