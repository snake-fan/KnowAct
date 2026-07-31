# 实验 03 结果

[English](README.md)

确证性知识地图重建实验尚未运行。

Runtime 为每个 Episode Run 写入一个独立目录：

```text
results/runs/{run_id}/
├── episode_manifest_snapshot.json
├── turns/
├── transcript.json
├── working_map.json
├── agent_tool_trace.json
├── agent_output.json
└── scoring_report.json
```

运行可恢复时可能存在 `checkpoint.json`；成功完成后该文件会被移除。生成的运行目录已被 Git 忽略。

未来的聚合输出应分为：

- `analysis/`：可复现、去标识化的表格与统计产物；
- `reports/`：可用于论文的聚合报告；
- `raw/` 或 `private/`：不得提交的受限数据。

空目录、通过的单元测试或完成的工程冒烟运行，都不能解释为方法间的比较证据。
