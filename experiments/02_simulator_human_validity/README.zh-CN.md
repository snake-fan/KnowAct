# 实验 02：Simulator 个人一致性

[English](README.md)

## 目的

本实验验证：参与者亲自确认 Profile Context 和 Knowledge Map 后，SAGE
Simulator 对相同问题的回答在多大程度上代表参与者本人。

当前主实验只收集参与者自评。专家盲评将在问答对保存后作为独立阶段执行；
泄漏挑战、复杂消融以及 agent 排名迁移不进入当前参与者流程。

## 自动化流程

```text
个人 Profile 输入、生成、修订与确认
  -> Knowledge Map 生成、逐节点修订与确认
  -> 从独立双语题库抽取 20 道题
  -> 每题先提交参与者回答，再生成 Simulator 回答
  -> 对照两份回答完成五项自评
  -> 保存可恢复的私有实验会话
  -> 后续导出独立专家盲评包
```

参与者入口是独立应用
[`simulator-test-frontend/`](../../simulator-test-frontend/README.zh-CN.md)。
它可以独立部署，不包含内部 research workbench；每题完成后立即保存，可使用恢复码
继续未完成会话。

## 状态

| 组成部分 | 状态 |
| --- | --- |
| 简化主协议 | 已实现 |
| 前后端自动化流程 | 已实现 |
| 独立双语题库 | Economy、ISLP、OSTEP 各含 80 道原子配对题，并有内容哈希绑定的逐题角色试答审核 |
| 每人抽取 20 题 | 已实现，保存抽样 seed 与顺序 |
| 参与者五项自评 | 已集成，尚待认知访谈与 pilot |
| 专家盲评 | 后续阶段，尚未接入主流程 |
| 真人数据与实验结果 | 尚未收集 |

## 内容

- [`design/experimental_design.md`](design/experimental_design.md)：简化后的中文主协议；
- [`materials/README.zh-CN.md`](materials/README.zh-CN.md)：题库、参与者材料和遗留材料说明；
- [`results/README.zh-CN.md`](results/README.zh-CN.md)：私有会话位置、结果状态和发布边界。

## 正式收集门槛

当前实现可以用于开发联调和 pilot。正式收集前仍须：

1. 完成伦理审批或等效本地审查；
2. 将题库概念绑定到当前 reviewed graph，并由领域专家审核内容和中英文等价性；当前
   来源与角色试答筛选仍只是 author-side screening；
3. 对 Profile、Map 修订和五项自评界面做认知访谈及 pilot；
4. 冻结题库版本、graph 版本、provider/model、抽样规则和排除规则。

在真人数据分析完成前，只能声称实验流程已经实现，不能声称 Simulator 已获得
真人有效性支持。
