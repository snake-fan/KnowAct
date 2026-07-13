# 运行中的 next step

reconstructed map 在运行过程中依然记录在内存中，最好是显示维护一份，通过调用工具进行修改时本地同步更新

修改记录也依然在内存中记录，没有实时更新在 turn 中，一个 turn 应该是一次对话 + 得到回答 + 修改 reconstructed map

已确定保留全图 final reconstruction 与全图评分。Simple LLM Agent 的下一步重点是有限 turn budget 下的真正 active diagnosis：不按 authored node 顺序逐个扫描，而是利用 graph edges 与 node rubrics 生成单个连贯的多节点 Integrated Diagnostic Question。每次 ask decision 记录 private `diagnostic_plan`（primary/secondary targets、目标 mastery boundary、selection reason），回答后允许用同一 visible turn 更新多个确实被展示或有审慎图推断支持的节点。

Mastery calibration 必须逐节点对照 authored rubric。回答正确性、推理、迁移和自我纠错决定 mastery；“不确定”“想再检查”等语言风格主要影响 diagnostic confidence，不能在任务表现已经满足 rubric 时自动把 mastery 下调一级。Graph edge 只提供 soft inference structure，不能机械传播 mastery。


## 测试现有 Simulator 效果，设计调研问卷结构

现有 Simulator 对话模拟先调试好，特别是 profile 生成那一步，需要调优很多，不然后续问卷没法做




## 搭建 tested agent 框架
