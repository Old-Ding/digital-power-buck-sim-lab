repoRoot = fileparts(fileparts(mfilename('fullpath')));
modelDir = fullfile(repoRoot, 'models', 'simulink');
shotDir = fullfile(repoRoot, 'assets', 'screenshots');

if ~exist(modelDir, 'dir')
    mkdir(modelDir);
end

if ~exist(shotDir, 'dir')
    mkdir(shotDir);
end

modelName = 'buck_protection_state_machine_logic';
modelPath = fullfile(modelDir, [modelName '.slx']);
shotPath = fullfile(shotDir, '07-simulink-protection-state-machine-logic.png');

if bdIsLoaded(modelName)
    close_system(modelName, 0);
end
if exist(modelPath, 'file')
    delete(modelPath);
end

new_system(modelName);
open_system(modelName);
set_param(modelName, ...
    'Solver', 'FixedStepDiscrete', ...
    'FixedStep', '5e-5', ...
    'StopTime', '0.018', ...
    'SimulationMode', 'normal');

add_block('simulink/Sources/Constant', [modelName '/ADC measurements Vin Vout Iout Temp'], ...
    'Position', [45 170 185 210], ...
    'Value', '0');

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/protection_check()'], ...
    'Position', [260 140 470 240]);
label_subsystem([modelName '/protection_check()'], ...
    ["OCP: Iout > threshold"; "OVP: Vout > threshold"; "UVLO: Vin < threshold"; "OTP: Temp > threshold"; "Output: one fault code"]);

add_block('simulink/Sources/Constant', [modelName '/ENABLE command'], ...
    'Position', [260 305 390 335], ...
    'Value', '1');

add_block('simulink/Sources/Constant', [modelName '/CLEAR_FAULT command'], ...
    'Position', [260 370 430 400], ...
    'Value', '0');

add_block('simulink/Signal Routing/Mux', [modelName '/command and fault mux'], ...
    'Position', [535 235 570 400], ...
    'Inputs', '3');

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/power_state_machine_step()'], ...
    'Position', [650 220 900 390]);
label_subsystem([modelName '/power_state_machine_step()'], ...
    ["INIT -> IDLE"; "IDLE -> SOFT_START"; "SOFT_START -> RUN"; "fault -> FAULT_LATCH"; "clear -> RECOVERY -> IDLE"]);

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/soft_start_reference()'], ...
    'Position', [650 55 860 145]);
label_subsystem([modelName '/soft_start_reference()'], ...
    ["Runs only in SOFT_START"; "Generates Vref_cmd ramp"; "Does not decide faults"]);

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/voltage_loop_PI()'], ...
    'Position', [950 55 1160 145]);
label_subsystem([modelName '/voltage_loop_PI()'], ...
    ["Input: Vref_cmd and Vout"; "Output: duty candidate"; "No fault threshold checks"]);

add_block('simulink/Signal Routing/Mux', [modelName '/state and duty mux'], ...
    'Position', [985 235 1020 365], ...
    'Inputs', '2');

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/PWM gate'], ...
    'Position', [1100 240 1305 360]);
label_subsystem([modelName '/PWM gate'], ...
    ["RUN/SOFT_START: pass duty"; "IDLE/FAULT/RECOVERY: duty=0"; "Single PWM shutdown exit"]);

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/telemetry log'], ...
    'Position', [1380 240 1575 360]);
label_subsystem([modelName '/telemetry log'], ...
    ["state"; "detected fault"; "latched fault"; "PWM enable"; "duty cmd"]);

style_top_level(modelName);

add_line(modelName, 'ADC measurements Vin Vout Iout Temp/1', 'protection_check()/1', 'autorouting', 'on');
add_line(modelName, 'protection_check()/1', 'command and fault mux/1', 'autorouting', 'on');
add_line(modelName, 'ENABLE command/1', 'command and fault mux/2', 'autorouting', 'on');
add_line(modelName, 'CLEAR_FAULT command/1', 'command and fault mux/3', 'autorouting', 'on');
add_line(modelName, 'command and fault mux/1', 'power_state_machine_step()/1', 'autorouting', 'on');
add_line(modelName, 'power_state_machine_step()/1', 'soft_start_reference()/1', 'autorouting', 'on');
add_line(modelName, 'soft_start_reference()/1', 'voltage_loop_PI()/1', 'autorouting', 'on');
add_line(modelName, 'power_state_machine_step()/1', 'state and duty mux/1', 'autorouting', 'on');
add_line(modelName, 'voltage_loop_PI()/1', 'state and duty mux/2', 'autorouting', 'on');
add_line(modelName, 'state and duty mux/1', 'PWM gate/1', 'autorouting', 'on');
add_line(modelName, 'PWM gate/1', 'telemetry log/1', 'autorouting', 'on');

save_system(modelName, modelPath);
set_param(modelName, 'ZoomFactor', 'FitSystem');
print(['-s' modelName], '-dpng', '-r180', shotPath);
close_system(modelName, 0);

fprintf('已生成保护状态机 Simulink 结构截图: %s\n', shotPath);
fprintf('已保存保护状态机 Simulink 逻辑模型: %s\n', modelPath);

function style_top_level(modelName)
    blocks = find_system(modelName, 'SearchDepth', 1, 'Type', 'Block');
    for idx = 1:numel(blocks)
        try
            set_param(blocks{idx}, 'FontName', 'Microsoft YaHei', 'FontSize', '12');
        catch
        end
    end
    set_block_color([modelName '/protection_check()'], 'lightBlue');
    set_block_color([modelName '/power_state_machine_step()'], 'yellow');
    set_block_color([modelName '/soft_start_reference()'], 'lightGreen');
    set_block_color([modelName '/voltage_loop_PI()'], 'lightGreen');
    set_block_color([modelName '/PWM gate'], 'orange');
    set_block_color([modelName '/telemetry log'], 'lightBlue');
end

function set_block_color(blockPath, color)
    try
        set_param(blockPath, 'BackgroundColor', color);
    catch
    end
end

function label_subsystem(sys, lines)
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

    add_block('simulink/Sources/In1', [sys '/in'], ...
        'Position', [40 95 70 115]);
    add_block('simulink/Sinks/Out1', [sys '/out'], ...
        'Position', [420 95 450 115]);
    add_block('simulink/Commonly Used Blocks/Gain', [sys '/responsibility boundary'], ...
        'Position', [170 85 315 125], ...
        'Gain', '1');
    add_line(sys, 'in/1', 'responsibility boundary/1', 'autorouting', 'on');
    add_line(sys, 'responsibility boundary/1', 'out/1', 'autorouting', 'on');

    set_param([sys '/responsibility boundary'], 'Description', strjoin(lines, newline));
    Simulink.BlockDiagram.arrangeSystem(sys);
end
