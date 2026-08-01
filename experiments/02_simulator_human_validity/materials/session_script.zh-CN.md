# Simulator Test 自动化会话脚本

[English](session_script.md)

## 会话前

- 确认同意书版本和伦理审批；
- 分配匿名参与者代码，不在系统中输入姓名或联系方式；
- 确认所选 reviewed graph、双语题库、provider/model 和抽样规则已冻结；
- 检查私有结果目录的访问控制和断点恢复；
- 向参与者说明：实验评价的是 Simulator，不是参与者，答错、部分理解和“不知道”
  都是有效数据。

## 阶段 1：Profile

在独立部署的 Simulator Test 参与者应用中输入相关背景、经历、目标与表达偏好，生成
Profile Context。请参与者逐项修订，确认无误后再提交。

Profile 确认后不原地覆盖；若需实质重做，使用新的匿名用户 ID。

## 阶段 2：Knowledge Map

基于 confirmed Profile 和 reviewed graph 生成 Candidate Map。让参与者逐节点检查并修订
掌握度、误解、不确定边界和可选说明。参与者确认后，系统发布新的不可变
participant-reviewed map，并单独保存修订轨迹。

主持人不得替参与者选择更“理想”的掌握度。

## 阶段 3：20 道题与自评

选择语言和双语题库，创建会话。系统保存抽样 seed，并抽取 20 道不重复问题。

每道题严格按照以下顺序：

1. 参与者独立作答；
2. 提交后，后端先保存真人回答；
3. SAGE 对同一问题生成回答；
4. 前端并排显示两份回答；
5. 参与者完成五项 1--5 分自评、总体替代判断和可选说明；
6. 保存后进入下一题。

不得在参与者作答前展示 Simulator 回答。不要向参与者展示 hidden map、evidence ID、
blueprint 或 debug trace。

## 中断与技术失败

中途退出时不要重建会话；从已保存 session 继续。Simulator 生成失败时保留真人回答和
错误记录，修复 provider 后重试当前题。不要用人工文本伪造 Simulator 回答。

## 结束

只有 20 道题都具备真人回答、Simulator 回答和自评时，系统才允许完成会话。再次说明
数据退出方式，并将同意/身份链接信息与实验回答分开保存。

专家盲评不在参与者会话中执行；后续只能从已保存问答对生成独立、去标识化的盲评包。
