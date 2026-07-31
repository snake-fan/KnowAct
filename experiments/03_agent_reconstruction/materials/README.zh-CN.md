# 实验 03 材料

[English](README.md)

实验设计已经完成，但正式材料尚未冻结。运行确证性实验代码前，必须冻结以下带版本输入：

- 通过实验 01 或明确替代审核门槛的 reviewed graph；
- 按预定掌握度分层的 reviewed hidden Knowledge Maps；
- 实验 02 中的 Simulator 版本与有效性状态；
- 每个配对条件对应的不可变 Episode Manifest；
- Tested Agent 的 provider、model、temperature、重试策略以及 prompt/代码版本；
- Simulator 的 provider、model、条件与重复 seed 策略；
- 轮次预算与 episode 排除规则；
- 带版本专家题库，之后才能把固定、随机、覆盖贪心或 LLM 题库选择视为正式 runtime kind；
- 分析清单，明确主要对比、bootstrap 分块、多重比较校正、失败处理和预测试/正式样本划分。

工程冒烟测试清单必须标记为 `development`，不得混入确证性结果集。
