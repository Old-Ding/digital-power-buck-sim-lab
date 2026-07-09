repoRoot = fileparts(fileparts(mfilename('fullpath')));
modelDir = fullfile(repoRoot, 'models', 'simulink');
shotDir = fullfile(repoRoot, 'assets', 'screenshots');

if ~exist(modelDir, 'dir')
    mkdir(modelDir);
end

if ~exist(shotDir, 'dir')
    mkdir(shotDir);
end

modelName = 'buck_load_transient_testbench';
modelPath = fullfile(modelDir, [modelName '.slx']);
shotPath = fullfile(shotDir, '08-simulink-load-transient-testbench.png');

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
    'StopTime', '0.024', ...
    'SimulationMode', 'normal');

add_block('simulink/Sources/Constant', [modelName '/RUN state'], ...
    'Position', [45 95 130 125], ...
    'Value', '1');

add_block('simulink/Sources/Constant', [modelName '/Vref 12V'], ...
    'Position', [45 205 130 235], ...
    'Value', '12');

add_block('simulink/Sources/Step', [modelName '/Load step 50pct to 100pct at 8ms'], ...
    'Position', [45 315 220 345], ...
    'Time', '0.008', ...
    'Before', '2.5', ...
    'After', '5');

add_block('simulink/Sources/Step', [modelName '/Load step 100pct to 50pct at 16ms'], ...
    'Position', [45 385 220 415], ...
    'Time', '0.016', ...
    'Before', '0', ...
    'After', '-2.5');

add_block('simulink/Math Operations/Sum', [modelName '/Iload profile'], ...
    'Position', [295 335 340 405], ...
    'Inputs', '++');

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/load_transient_case()'], ...
    'Position', [425 300 675 430]);
label_subsystem([modelName '/load_transient_case()'], ...
    ["Light load: 2.5A"; "Heavy load: 5A"; "Step up at 8ms"; "Step down at 16ms"; "Output: Rload(t) or Iload(t)"]);

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/voltage_loop_PI()'], ...
    'Position', [425 135 675 245]);
label_subsystem([modelName '/voltage_loop_PI()'], ...
    ["Input: Vref and Vout"; "Kp = 0.02"; "Ki = 80"; "Output: raw duty request"], 2, 1);

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/duty_limit_anti_windup()'], ...
    'Position', [780 130 1045 250]);
label_subsystem([modelName '/duty_limit_anti_windup()'], ...
    ["Clamp duty command"; "Keep raw duty observable"; "Hold integrator when saturated"; "Output: duty_cmd and saturation"]);

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/RUN state PWM gate'], ...
    'Position', [1140 115 1375 250]);
label_subsystem([modelName '/RUN state PWM gate'], ...
    ["RUN: pass duty"; "Fault or idle: duty = 0"; "This chapter keeps state in RUN"; "Protection was covered in chapter 7"], 2, 1);

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/averaged Buck plant'], ...
    'Position', [1465 205 1745 365]);
label_subsystem([modelName '/averaged Buck plant'], ...
    ["Vin = 24V"; "L = 22uH"; "C = 100uF"; "Rload changes with step"; "Outputs: Vout, IL, cap current"], 2, 1);

add_block('simulink/Signal Routing/Goto', [modelName '/goto Vout feedback'], ...
    'Position', [1810 205 1910 235], ...
    'GotoTag', 'Vout_fb');

add_block('simulink/Signal Routing/From', [modelName '/Vout feedback'], ...
    'Position', [275 185 365 215], ...
    'GotoTag', 'Vout_fb');

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/load transient metrics'], ...
    'Position', [1465 450 1745 570]);
label_subsystem([modelName '/load transient metrics'], ...
    ["Vout undershoot"; "Vout overshoot"; "1 percent recovery time"; "duty saturation time"; "peak inductor current"], 3, 0);

add_block('simulink/Sinks/Scope', [modelName '/Scope Vout Iload duty IL'], ...
    'Position', [1810 340 1945 405]);

style_top_level(modelName);

add_line(modelName, 'Load step 50pct to 100pct at 8ms/1', 'Iload profile/1', 'autorouting', 'on');
add_line(modelName, 'Load step 100pct to 50pct at 16ms/1', 'Iload profile/2', 'autorouting', 'on');
add_line(modelName, 'Iload profile/1', 'load_transient_case()/1', 'autorouting', 'on');
add_line(modelName, 'Vref 12V/1', 'voltage_loop_PI()/1', 'autorouting', 'on');
add_line(modelName, 'Vout feedback/1', 'voltage_loop_PI()/2', 'autorouting', 'on');
add_line(modelName, 'voltage_loop_PI()/1', 'duty_limit_anti_windup()/1', 'autorouting', 'on');
add_line(modelName, 'duty_limit_anti_windup()/1', 'RUN state PWM gate/1', 'autorouting', 'on');
add_line(modelName, 'RUN state/1', 'RUN state PWM gate/2', 'autorouting', 'on');
add_line(modelName, 'RUN state PWM gate/1', 'averaged Buck plant/1', 'autorouting', 'on');
add_line(modelName, 'load_transient_case()/1', 'averaged Buck plant/2', 'autorouting', 'on');
add_line(modelName, 'averaged Buck plant/1', 'goto Vout feedback/1', 'autorouting', 'on');
add_line(modelName, 'averaged Buck plant/1', 'load transient metrics/1', 'autorouting', 'on');
add_line(modelName, 'load_transient_case()/1', 'load transient metrics/2', 'autorouting', 'on');
add_line(modelName, 'duty_limit_anti_windup()/1', 'load transient metrics/3', 'autorouting', 'on');
add_line(modelName, 'averaged Buck plant/1', 'Scope Vout Iload duty IL/1', 'autorouting', 'on');

save_system(modelName, modelPath);
set_param(modelName, 'ZoomFactor', 'FitSystem');
print(['-s' modelName], '-dpng', '-r180', shotPath);
close_system(modelName, 0);

fprintf('已生成负载突变 Simulink 测试台截图: %s\n', shotPath);
fprintf('已保存负载突变 Simulink 测试台模型: %s\n', modelPath);

function style_top_level(modelName)
    blocks = find_system(modelName, 'SearchDepth', 1, 'Type', 'Block');
    for idx = 1:numel(blocks)
        try
            set_param(blocks{idx}, 'FontName', 'Microsoft YaHei', 'FontSize', '12');
        catch
        end
    end
    set_block_color([modelName '/load_transient_case()'], 'orange');
    set_block_color([modelName '/voltage_loop_PI()'], 'lightGreen');
    set_block_color([modelName '/duty_limit_anti_windup()'], 'yellow');
    set_block_color([modelName '/RUN state PWM gate'], 'lightBlue');
    set_block_color([modelName '/averaged Buck plant'], 'cyan');
    set_block_color([modelName '/load transient metrics'], 'lightBlue');
end

function set_block_color(blockPath, color)
    try
        set_param(blockPath, 'BackgroundColor', color);
    catch
    end
end

function label_subsystem(sys, lines, inputCount, outputCount)
    if nargin < 3
        inputCount = 1;
    end
    if nargin < 4
        outputCount = 1;
    end
    open_system(sys);
    try
        set_param(sys, 'ContentPreviewEnabled', 'off');
    catch
    end
    try
        delete_line(sys, 'In1/1', 'Out1/1');
    catch
    end
    try
        delete_block([sys '/In1']);
        delete_block([sys '/Out1']);
    catch
    end

    for idx = 1:inputCount
        add_block('simulink/Sources/In1', [sys '/in' num2str(idx)], ...
            'Position', [40 55 + idx * 45 70 75 + idx * 45]);
    end
    for idx = 1:outputCount
        add_block('simulink/Sinks/Out1', [sys '/out' num2str(idx)], ...
            'Position', [435 55 + idx * 45 465 75 + idx * 45]);
    end
    add_block('simulink/Commonly Used Blocks/Gain', [sys '/responsibility boundary'], ...
        'Position', [170 83 325 127], ...
        'Gain', '1');
    if inputCount > 0 && outputCount > 0
        add_line(sys, 'in1/1', 'responsibility boundary/1', 'autorouting', 'on');
        add_line(sys, 'responsibility boundary/1', 'out1/1', 'autorouting', 'on');
    end

    set_param([sys '/responsibility boundary'], 'Description', strjoin(lines, newline));
    Simulink.BlockDiagram.arrangeSystem(sys);
end
