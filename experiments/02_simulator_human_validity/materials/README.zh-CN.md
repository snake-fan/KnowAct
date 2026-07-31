# 实验 02 材料

[English](README.md)

本目录把 `../design/experimental_design.md` 的预注册式协议落实为可执行材料。

## 参与者与主持材料

- [`participant_information_and_consent.zh-CN.md`](participant_information_and_consent.zh-CN.md)：参与者说明与知情同意模板；
- [`session_script.zh-CN.md`](session_script.zh-CN.md)：主持人口径与会话顺序；
- `profile_context_questionnaire.csv`：仅收集 Simulator 所需的最小 Profile Context；
- `human_map_review_form.csv`：参与者确认或修正由 Set A 形成的 Knowledge Map；
- `self_fidelity_rating_form.csv`：参与者评价 Simulator 回答是否代表自己。

## 题集与安全挑战

- `question_set_a_islp_draft.csv`：用于建立 Human Reviewed Map 的 21 道诊断题草案；
- `question_set_b_islp_draft.csv`：用于留出验证的 21 道诊断题草案；
- `leakage_challenge_suite.csv`：用于直接字段、跨节点、注入与内部产物泄漏测试。

A/B 题集是草案，`target_node_id` 尚未绑定。在专家审核、图谱绑定、认知访谈和预测试前，不得视为已验证量表。

## 盲评与随机化

- `blinded_expert_rating_form.csv`：专家对真人、SAGE、基线和消融回答进行盲评；
- `randomization_manifest_template.csv`：记录参与者级顺序、分配与盲法；
- `condition_manifest_template.json`：冻结条件、provider/model、prompt、seed 与 fallback；
- [`data_dictionary.zh-CN.md`](data_dictionary.zh-CN.md)：字段、受控取值与访问分级。

## 使用顺序

1. 用当前 reviewed graph 版本替换所有 `[BIND_*]` 值。
2. 请领域专家审核题目、锚点和泄漏挑战。
3. 对说明、题目与量表进行认知访谈。
4. 运行预测试，冻结保留、修改与排除决定。
5. 生成正式随机化与条件清单。
6. 只在伦理审批和预注册完成后开始正式收集。

同意记录、联系方式、链接密钥和原始回答不得提交到仓库。
