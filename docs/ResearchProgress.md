# 运行中的 next step

reconstructed map 在运行过程中依然记录在内存中，最好是显示维护一份，通过调用工具进行修改时本地同步更新

修改记录也依然在内存中记录，没有实时更新在 turn 中，一个 turn 应该是一次对话 + 得到回答 + 修改 reconstructed map


## 测试现有 Simulator 效果，设计调研问卷结构

现有 Simulator 对话模拟先调试好，特别是 profile 生成那一步，需要调优很多，不然后续问卷没法做




## 搭建 tested agent 框架
