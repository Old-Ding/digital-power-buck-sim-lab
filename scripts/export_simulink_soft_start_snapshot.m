repoRoot = fileparts(fileparts(mfilename('fullpath')));
modelDir = fullfile(repoRoot, 'models', 'simulink');
shotDir = fullfile(repoRoot, 'assets', 'screenshots');

if ~exist(modelDir, 'dir')
    mkdir(modelDir);
end

if ~exist(shotDir, 'dir')
    mkdir(shotDir);
end

modelName = 'buck_soft_start_logic';
modelPath = fullfile(modelDir, [modelName '.slx']);
shotPath = fullfile(shotDir, '06-simulink-soft-start-logic.png');

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
    'StopTime', '0.018', ...
    'SimulationMode', 'normal');

add_block('simulink/Sources/Constant', [modelName '/Target Vref 12V'], ...
    'Position', [45 90 135 120], ...
    'Value', '12');

add_block('simulink/Sources/Ramp', [modelName '/Soft-start ramp 0..12V'], ...
    'Position', [45 155 155 185], ...
    'slope', '12/0.005', ...
    'start', '0', ...
    'InitialOutput', '0');

add_block('simulink/Discontinuities/Saturation', [modelName '/Vref clamp 0..12V'], ...
    'Position', [210 145 330 195], ...
    'UpperLimit', '12', ...
    'LowerLimit', '0');

add_block('simulink/Signal Routing/From', [modelName '/Vout feedback'], ...
    'Position', [45 255 125 285], ...
    'GotoTag', 'Vout_fb');

add_block('simulink/Math Operations/Sum', [modelName '/error = Vref_cmd - Vout'], ...
    'Position', [410 175 455 235], ...
    'Inputs', '+-');

add_block('simulink/Commonly Used Blocks/Gain', [modelName '/Kp 0.05'], ...
    'Position', [530 145 610 175], ...
    'Gain', '0.05');

add_block('simulink/Discrete/Discrete-Time Integrator', [modelName '/Integrator xI'], ...
    'Position', [530 230 640 280], ...
    'gainval', '200', ...
    'SampleTime', '5e-6', ...
    'InitialCondition', '0');

add_block('simulink/Commonly Used Blocks/Gain', [modelName '/Vref feedforward 1over24'], ...
    'Position', [520 70 660 105], ...
    'Gain', '1/24');

add_block('simulink/Math Operations/Sum', [modelName '/raw duty = Dff + P + I'], ...
    'Position', [760 145 810 225], ...
    'Inputs', '+++');

add_block('simulink/Discontinuities/Saturation', [modelName '/Duty saturation 0..0.55'], ...
    'Position', [900 165 1040 205], ...
    'UpperLimit', '0.55', ...
    'LowerLimit', '0');

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/Anti-windup gate'], ...
    'Position', [870 255 1070 360]);
build_gate_subsystem([modelName '/Anti-windup gate']);

add_block('simulink/Sources/Constant', [modelName '/Vin 24V'], ...
    'Position', [1125 110 1195 140], ...
    'Value', '24');

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/Averaged Buck plant'], ...
    'Position', [1125 195 1385 325]);
build_plant_placeholder([modelName '/Averaged Buck plant']);

add_block('simulink/Signal Routing/Goto', [modelName '/goto Vout feedback'], ...
    'Position', [1460 235 1540 265], ...
    'GotoTag', 'Vout_fb');

add_block('simulink/Sinks/Scope', [modelName '/Scope: Vref Vout duty IL'], ...
    'Position', [1460 95 1565 160]);

add_line(modelName, 'Soft-start ramp 0..12V/1', 'Vref clamp 0..12V/1', 'autorouting', 'on');
add_line(modelName, 'Vref clamp 0..12V/1', 'error = Vref_cmd - Vout/1', 'autorouting', 'on');
add_line(modelName, 'Vout feedback/1', 'error = Vref_cmd - Vout/2', 'autorouting', 'on');
add_line(modelName, 'Vref clamp 0..12V/1', 'Vref feedforward 1over24/1', 'autorouting', 'on');
add_line(modelName, 'error = Vref_cmd - Vout/1', 'Kp 0.05/1', 'autorouting', 'on');
add_line(modelName, 'error = Vref_cmd - Vout/1', 'Integrator xI/1', 'autorouting', 'on');
add_line(modelName, 'Vref feedforward 1over24/1', 'raw duty = Dff + P + I/1', 'autorouting', 'on');
add_line(modelName, 'Kp 0.05/1', 'raw duty = Dff + P + I/2', 'autorouting', 'on');
add_line(modelName, 'Integrator xI/1', 'raw duty = Dff + P + I/3', 'autorouting', 'on');
add_line(modelName, 'raw duty = Dff + P + I/1', 'Duty saturation 0..0.55/1', 'autorouting', 'on');
add_line(modelName, 'raw duty = Dff + P + I/1', 'Anti-windup gate/1', 'autorouting', 'on');
add_line(modelName, 'Duty saturation 0..0.55/1', 'Anti-windup gate/2', 'autorouting', 'on');
add_line(modelName, 'error = Vref_cmd - Vout/1', 'Anti-windup gate/3', 'autorouting', 'on');
add_line(modelName, 'Vin 24V/1', 'Averaged Buck plant/1', 'autorouting', 'on');
add_line(modelName, 'Duty saturation 0..0.55/1', 'Averaged Buck plant/2', 'autorouting', 'on');
add_line(modelName, 'Averaged Buck plant/1', 'goto Vout feedback/1', 'autorouting', 'on');

save_system(modelName, modelPath);
set_param(modelName, 'ZoomFactor', 'FitSystem');
print(['-s' modelName], '-dpng', '-r180', shotPath);
close_system(modelName, 0);

fprintf('已生成软启动 Simulink 逻辑截图: %s\n', shotPath);
fprintf('已保存软启动 Simulink 逻辑模型: %s\n', modelPath);

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

function build_plant_placeholder(sys)
    open_system(sys);
    delete_line(sys, 'In1/1', 'Out1/1');
    delete_block([sys '/In1']);
    delete_block([sys '/Out1']);

    add_block('simulink/Sources/In1', [sys '/Vin'], ...
        'Position', [45 55 75 75]);
    add_block('simulink/Sources/In1', [sys '/duty cmd'], ...
        'Position', [45 125 75 145]);
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
