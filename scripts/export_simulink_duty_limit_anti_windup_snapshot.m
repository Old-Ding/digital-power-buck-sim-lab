repoRoot = fileparts(fileparts(mfilename('fullpath')));
modelDir = fullfile(repoRoot, 'models', 'simulink');
shotDir = fullfile(repoRoot, 'assets', 'screenshots');

if ~exist(modelDir, 'dir')
    mkdir(modelDir);
end

if ~exist(shotDir, 'dir')
    mkdir(shotDir);
end

modelName = 'buck_duty_limit_anti_windup_logic';
modelPath = fullfile(modelDir, [modelName '.slx']);
shotPath = fullfile(shotDir, '05-simulink-duty-limit-anti-windup-logic.png');

if bdIsLoaded(modelName)
    close_system(modelName, 0);
end
if exist(modelPath, 'file')
    delete(modelPath);
end

new_system(modelName);
open_system(modelName);
set_param(modelName, ...
    'Solver', 'ode4', ...
    'FixedStep', '5e-7', ...
    'StopTime', '0.014', ...
    'SimulationMode', 'normal');

add_block('simulink/Sources/Constant', [modelName '/Vref 12V'], ...
    'Position', [55 110 125 140], ...
    'Value', '12');

add_block('simulink/Signal Routing/From', [modelName '/Vout feedback'], ...
    'Position', [55 185 125 215], ...
    'GotoTag', 'Vout_fb');

add_block('simulink/Math Operations/Sum', [modelName '/error = Vref - Vout'], ...
    'Position', [190 125 230 175], ...
    'Inputs', '+-');

add_block('simulink/Commonly Used Blocks/Gain', [modelName '/Kp'], ...
    'Position', [295 95 365 125], ...
    'Gain', '0.05');

add_block('simulink/Discrete/Discrete-Time Integrator', [modelName '/Integrator xI'], ...
    'Position', [295 170 395 220], ...
    'gainval', '200', ...
    'SampleTime', '5e-6', ...
    'InitialCondition', '0.0041667');

add_block('simulink/Sources/Constant', [modelName '/Dff 0.5'], ...
    'Position', [295 260 365 290], ...
    'Value', '0.5');

add_block('simulink/Math Operations/Sum', [modelName '/raw duty = Dff + P + I'], ...
    'Position', [475 135 520 205], ...
    'Inputs', '+++');

add_block('simulink/Discontinuities/Saturation', [modelName '/Duty saturation 0.05..0.55'], ...
    'Position', [605 150 735 190], ...
    'UpperLimit', '0.55', ...
    'LowerLimit', '0.05');

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/Anti-windup gate'], ...
    'Position', [570 255 760 355]);
build_gate_subsystem([modelName '/Anti-windup gate']);

add_block('simulink/Sources/Constant', [modelName '/Vin 24V base'], ...
    'Position', [830 65 920 95], ...
    'Value', '24');

add_block('simulink/Sources/Step', [modelName '/Vin drop -4V at 3ms'], ...
    'Position', [830 115 960 145], ...
    'Time', '0.003', ...
    'Before', '0', ...
    'After', '-4');

add_block('simulink/Sources/Step', [modelName '/Vin return +4V at 6ms'], ...
    'Position', [830 165 975 195], ...
    'Time', '0.006', ...
    'Before', '0', ...
    'After', '4');

add_block('simulink/Math Operations/Sum', [modelName '/Vin profile 24-20-24'], ...
    'Position', [1035 105 1080 175], ...
    'Inputs', '+++');

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/Averaged Buck plant'], ...
    'Position', [830 265 1085 390]);
build_plant_placeholder([modelName '/Averaged Buck plant']);

add_block('simulink/Signal Routing/Goto', [modelName '/goto Vout feedback'], ...
    'Position', [1160 300 1240 330], ...
    'GotoTag', 'Vout_fb');

add_line(modelName, 'Vref 12V/1', 'error = Vref - Vout/1', 'autorouting', 'on');
add_line(modelName, 'Vout feedback/1', 'error = Vref - Vout/2', 'autorouting', 'on');
add_line(modelName, 'error = Vref - Vout/1', 'Kp/1', 'autorouting', 'on');
add_line(modelName, 'error = Vref - Vout/1', 'Integrator xI/1', 'autorouting', 'on');
add_line(modelName, 'Kp/1', 'raw duty = Dff + P + I/1', 'autorouting', 'on');
add_line(modelName, 'Integrator xI/1', 'raw duty = Dff + P + I/2', 'autorouting', 'on');
add_line(modelName, 'Dff 0.5/1', 'raw duty = Dff + P + I/3', 'autorouting', 'on');
add_line(modelName, 'raw duty = Dff + P + I/1', 'Duty saturation 0.05..0.55/1', 'autorouting', 'on');
add_line(modelName, 'raw duty = Dff + P + I/1', 'Anti-windup gate/1', 'autorouting', 'on');
add_line(modelName, 'Duty saturation 0.05..0.55/1', 'Anti-windup gate/2', 'autorouting', 'on');
add_line(modelName, 'error = Vref - Vout/1', 'Anti-windup gate/3', 'autorouting', 'on');
add_line(modelName, 'Vin 24V base/1', 'Vin profile 24-20-24/1', 'autorouting', 'on');
add_line(modelName, 'Vin drop -4V at 3ms/1', 'Vin profile 24-20-24/2', 'autorouting', 'on');
add_line(modelName, 'Vin return +4V at 6ms/1', 'Vin profile 24-20-24/3', 'autorouting', 'on');
add_line(modelName, 'Vin profile 24-20-24/1', 'Averaged Buck plant/1', 'autorouting', 'on');
add_line(modelName, 'Duty saturation 0.05..0.55/1', 'Averaged Buck plant/2', 'autorouting', 'on');
add_line(modelName, 'Averaged Buck plant/1', 'goto Vout feedback/1', 'autorouting', 'on');

save_system(modelName, modelPath);
set_param(modelName, 'ZoomFactor', 'FitSystem');
print(['-s' modelName], '-dpng', '-r180', shotPath);
close_system(modelName, 0);

fprintf('已生成 duty 限幅和抗积分饱和 Simulink 逻辑截图: %s\n', shotPath);
fprintf('已保存 Simulink 逻辑模型: %s\n', modelPath);

function build_gate_subsystem(sys)
    open_system(sys);
    delete_line(sys, 'In1/1', 'Out1/1');
    delete_block([sys '/In1']);
    delete_block([sys '/Out1']);

    add_block('simulink/Sources/In1', [sys '/raw duty'], ...
        'Position', [45 50 75 70]);
    add_block('simulink/Sources/In1', [sys '/limited duty'], ...
        'Position', [45 115 75 135]);
    add_block('simulink/Sources/In1', [sys '/error'], ...
        'Position', [45 180 75 200]);
    add_block('simulink/Math Operations/Subtract', [sys '/raw - limited'], ...
        'Position', [145 80 185 120]);
    add_block('simulink/Ports & Subsystems/Subsystem', [sys '/conditional integration rule'], ...
        'Position', [250 80 450 175]);
    build_rule_placeholder([sys '/conditional integration rule']);
    add_block('simulink/Sinks/Out1', [sys '/allow integrator update'], ...
        'Position', [535 115 565 135]);

    add_line(sys, 'raw duty/1', 'raw - limited/1', 'autorouting', 'on');
    add_line(sys, 'limited duty/1', 'raw - limited/2', 'autorouting', 'on');
    add_line(sys, 'raw - limited/1', 'conditional integration rule/1', 'autorouting', 'on');
    add_line(sys, 'error/1', 'conditional integration rule/2', 'autorouting', 'on');
    add_line(sys, 'conditional integration rule/1', 'allow integrator update/1', 'autorouting', 'on');

    Simulink.BlockDiagram.arrangeSystem(sys);
    close_system(sys);
end

function build_plant_placeholder(sys)
    open_system(sys);
    delete_line(sys, 'In1/1', 'Out1/1');
    delete_block([sys '/In1']);
    delete_block([sys '/Out1']);

    add_block('simulink/Sources/In1', [sys '/Vin'], ...
        'Position', [45 70 75 90]);
    add_block('simulink/Sources/In1', [sys '/duty cmd'], ...
        'Position', [45 145 75 165]);
    add_block('simulink/Ports & Subsystems/Subsystem', [sys '/22uH 100uF average plant'], ...
        'Position', [180 80 400 175]);
    build_average_plant_placeholder([sys '/22uH 100uF average plant']);
    add_block('simulink/Sinks/Out1', [sys '/Vout'], ...
        'Position', [500 115 530 135]);

    add_line(sys, 'Vin/1', '22uH 100uF average plant/1', 'autorouting', 'on');
    add_line(sys, 'duty cmd/1', '22uH 100uF average plant/2', 'autorouting', 'on');
    add_line(sys, '22uH 100uF average plant/1', 'Vout/1', 'autorouting', 'on');

    Simulink.BlockDiagram.arrangeSystem(sys);
    close_system(sys);
end

function build_rule_placeholder(sys)
    open_system(sys);
    delete_line(sys, 'In1/1', 'Out1/1');
    delete_block([sys '/In1']);
    delete_block([sys '/Out1']);

    add_block('simulink/Sources/In1', [sys '/raw duty minus limited duty'], ...
        'Position', [45 60 75 80]);
    add_block('simulink/Sources/In1', [sys '/error sign'], ...
        'Position', [45 130 75 150]);
    add_block('simulink/Sources/Constant', [sys '/allow if not saturated or error unwinds'], ...
        'Position', [185 90 390 125], ...
        'Value', '1');
    add_block('simulink/Sinks/Out1', [sys '/allow update'], ...
        'Position', [465 95 495 115]);

    add_line(sys, 'allow if not saturated or error unwinds/1', 'allow update/1', 'autorouting', 'on');

    Simulink.BlockDiagram.arrangeSystem(sys);
    close_system(sys);
end

function build_average_plant_placeholder(sys)
    open_system(sys);
    delete_line(sys, 'In1/1', 'Out1/1');
    delete_block([sys '/In1']);
    delete_block([sys '/Out1']);

    add_block('simulink/Sources/In1', [sys '/Vin'], ...
        'Position', [45 55 75 75]);
    add_block('simulink/Sources/In1', [sys '/duty'], ...
        'Position', [45 125 75 145]);
    add_block('simulink/Math Operations/Product', [sys '/Vin times duty'], ...
        'Position', [150 80 190 125]);
    add_block('simulink/Sinks/Out1', [sys '/Vout'], ...
        'Position', [290 95 320 115]);

    add_line(sys, 'Vin/1', 'Vin times duty/1', 'autorouting', 'on');
    add_line(sys, 'duty/1', 'Vin times duty/2', 'autorouting', 'on');
    add_line(sys, 'Vin times duty/1', 'Vout/1', 'autorouting', 'on');

    Simulink.BlockDiagram.arrangeSystem(sys);
    close_system(sys);
end
