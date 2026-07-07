function run_test_matrix()
%RUN_TEST_MATRIX 生成第一版测试矩阵。
% 这个脚本先维护测试定义，不伪造仿真结果；模型接好后再在这里加入 sim 调用。

repoRoot = fileparts(fileparts(mfilename('fullpath')));
artifactDir = fullfile(repoRoot, 'artifacts');
if ~exist(artifactDir, 'dir')
    mkdir(artifactDir);
end

cases = [
    make_case("startup_no_load", 24, 0.0, "空载启动", "Vout 平滑上升，无过冲")
    make_case("startup_full_load", 24, 5.0, "满载启动", "启动电流受控")
    make_case("load_step_20_to_100", 24, 5.0, "20% 到 100% 负载突变", "输出下陷可恢复")
    make_case("load_step_100_to_20", 24, 1.0, "100% 到 20% 负载突变", "输出过冲可恢复")
    make_case("input_step_low", 18, 5.0, "输入电压降到 18V", "不触发 UVLO，输出保持")
    make_case("input_uvlo", 15, 2.0, "输入欠压", "触发 UVLO 并关断 PWM")
    make_case("ocp_fault", 24, 7.0, "输出过流", "触发 OCP 并锁存故障")
    make_case("ovp_fault", 24, 1.0, "输出过压注入", "触发 OVP 并锁存故障")
];

T = struct2table(cases);
writetable(T, fullfile(artifactDir, 'test_matrix.csv'));
save(fullfile(artifactDir, 'test_matrix.mat'), 'cases');

disp("已生成 artifacts/test_matrix.csv。接入 PLECS/Simulink 后，在本脚本中补充仿真运行和结果导出。");
end

function item = make_case(id, vin, loadCurrent, scenario, expected)
item = struct( ...
    'id', id, ...
    'vin_v', vin, ...
    'load_current_a', loadCurrent, ...
    'scenario', scenario, ...
    'expected', expected, ...
    'status', "TODO");
end
