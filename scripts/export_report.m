function export_report()
%EXPORT_REPORT 生成测试报告占位文档。
% 真实波形和结论必须来自仿真导出数据，当前脚本只生成报告结构。

repoRoot = fileparts(fileparts(mfilename('fullpath')));
reportPath = fullfile(repoRoot, 'docs', 'test-report.md');

lines = [
    "# 测试报告"
    ""
    "## 摘要"
    ""
    "TODO: 接入仿真结果后填写关键结论。"
    ""
    "## 测试用例"
    ""
    "| 用例 | 工况 | 期望 | 结果 |"
    "| --- | --- | --- | --- |"
    "| startup_no_load | 空载启动 | Vout 平滑上升 | TODO |"
    "| startup_full_load | 满载启动 | 启动电流受控 | TODO |"
    "| load_step_20_to_100 | 负载突变 | 输出恢复稳定 | TODO |"
    "| ocp_fault | 输出过流 | 触发 OCP | TODO |"
    ""
    "## 问题记录"
    ""
    "TODO: 按现象、根因、最小修改、验证结果记录。"
];

writelines(lines, reportPath);
disp("已生成 docs/test-report.md。");
end
