repoRoot = fileparts(fileparts(mfilename('fullpath')));
modelDir = fullfile(repoRoot, 'models', 'simulink');
shotDir = fullfile(repoRoot, 'assets', 'screenshots');

if ~exist(modelDir, 'dir')
    mkdir(modelDir);
end

if ~exist(shotDir, 'dir')
    mkdir(shotDir);
end

modelName = 'buck_adc_noise_duty_jitter_logic';
modelPath = fullfile(modelDir, [modelName '.slx']);
shotPath = fullfile(shotDir, '09-simulink-adc-noise-duty-jitter-logic.png');

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
    'StopTime', '0.020', ...
    'SimulationMode', 'normal');

add_block('simulink/Signal Routing/From', [modelName '/Vout actual feedback'], ...
    'Position', [45 245 155 275], ...
    'GotoTag', 'Vout_actual');

add_block('simulink/Sources/Constant', [modelName '/Vref 12V'], ...
    'Position', [600 120 680 150], ...
    'Value', '12');

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/ADC front end'], ...
    'Position', [230 185 480 330]);
label_subsystem([modelName '/ADC front end'], ...
    ["Sample Vout at 200kHz"; "12-bit ADC, 16V full-scale"; "Add Gaussian noise"; "Quantize to ADC code"; "Output: Vout_adc"], 1, 1);

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/measurement filter option'], ...
    'Position', [560 185 835 330]);
label_subsystem([modelName '/measurement filter option'], ...
    ["Bypass"; "Moving average, N = 4"; "IIR: alpha = 0.25"; "Filter delay is observable"; "Output: Vout_meas"], 1, 1);

add_block('simulink/Math Operations/Sum', [modelName '/error = Vref - Vmeas'], ...
    'Position', [920 220 970 280], ...
    'Inputs', '+-');

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/voltage_loop_PI()'], ...
    'Position', [1060 175 1325 330]);
label_subsystem([modelName '/voltage_loop_PI()'], ...
    ["Input: filtered Vout"; "Kp = 0.02"; "Ki = 80"; "Integrator keeps noise memory"; "Output: raw duty"], 1, 1);

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/duty_limit_anti_windup()'], ...
    'Position', [1410 175 1705 330]);
label_subsystem([modelName '/duty_limit_anti_windup()'], ...
    ["Clamp duty: 0.05..0.65"; "Keep raw duty observable"; "Expose saturation flag"; "Only this layer owns duty limit"], 1, 1);

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/PWM duty update'], ...
    'Position', [1790 190 2035 315]);
label_subsystem([modelName '/PWM duty update'], ...
    ["Ts = 5us"; "Duty command is held"; "Switching comparator not modeled here"; "Equivalent jitter = duty jitter x Ts"], 1, 1);

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/averaged Buck plant'], ...
    'Position', [2135 170 2435 340]);
label_subsystem([modelName '/averaged Buck plant'], ...
    ["Vin = 24V"; "Load = 5A"; "L = 22uH"; "C = 100uF"; "Output: actual Vout and IL"], 1, 2);

add_block('simulink/Signal Routing/Goto', [modelName '/goto Vout actual'], ...
    'Position', [2505 210 2615 240], ...
    'GotoTag', 'Vout_actual');

add_block('simulink/Ports & Subsystems/Subsystem', [modelName '/jitter metrics'], ...
    'Position', [1410 445 1730 610]);
label_subsystem([modelName '/jitter metrics'], ...
    ["Measured noise RMS"; "Error RMS"; "Duty RMS jitter"; "Duty peak-to-peak"; "Equivalent PWM jitter in ns"], 4, 1);

add_block('simulink/Sinks/Scope', [modelName '/Scope Vout error duty'], ...
    'Position', [2135 445 2295 510]);

style_top_level(modelName);

add_line(modelName, 'Vout actual feedback/1', 'ADC front end/1', 'autorouting', 'on');
add_line(modelName, 'ADC front end/1', 'measurement filter option/1', 'autorouting', 'on');
add_line(modelName, 'measurement filter option/1', 'error = Vref - Vmeas/2', 'autorouting', 'on');
add_line(modelName, 'Vref 12V/1', 'error = Vref - Vmeas/1', 'autorouting', 'on');
add_line(modelName, 'error = Vref - Vmeas/1', 'voltage_loop_PI()/1', 'autorouting', 'on');
add_line(modelName, 'voltage_loop_PI()/1', 'duty_limit_anti_windup()/1', 'autorouting', 'on');
add_line(modelName, 'duty_limit_anti_windup()/1', 'PWM duty update/1', 'autorouting', 'on');
add_line(modelName, 'PWM duty update/1', 'averaged Buck plant/1', 'autorouting', 'on');
add_line(modelName, 'averaged Buck plant/1', 'goto Vout actual/1', 'autorouting', 'on');

add_line(modelName, 'Vout actual feedback/1', 'jitter metrics/1', 'autorouting', 'on');
add_line(modelName, 'measurement filter option/1', 'jitter metrics/2', 'autorouting', 'on');
add_line(modelName, 'error = Vref - Vmeas/1', 'jitter metrics/3', 'autorouting', 'on');
add_line(modelName, 'duty_limit_anti_windup()/1', 'jitter metrics/4', 'autorouting', 'on');
add_line(modelName, 'averaged Buck plant/1', 'Scope Vout error duty/1', 'autorouting', 'on');

save_system(modelName, modelPath);
set_param(modelName, 'ZoomFactor', 'FitSystem');
print(['-s' modelName], '-dpng', '-r180', shotPath);
close_system(modelName, 0);

fprintf('已生成 ADC 噪声与 duty 抖动 Simulink 逻辑截图: %s\n', shotPath);
fprintf('已保存 ADC 噪声与 duty 抖动 Simulink 模型: %s\n', modelPath);

function style_top_level(modelName)
    blocks = find_system(modelName, 'SearchDepth', 1, 'Type', 'Block');
    for idx = 1:numel(blocks)
        try
            set_param(blocks{idx}, 'FontName', 'Microsoft YaHei', 'FontSize', '12');
        catch
        end
    end
    set_block_color([modelName '/ADC front end'], 'orange');
    set_block_color([modelName '/measurement filter option'], 'yellow');
    set_block_color([modelName '/voltage_loop_PI()'], 'lightGreen');
    set_block_color([modelName '/duty_limit_anti_windup()'], 'yellow');
    set_block_color([modelName '/PWM duty update'], 'lightBlue');
    set_block_color([modelName '/averaged Buck plant'], 'cyan');
    set_block_color([modelName '/jitter metrics'], 'lightBlue');
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

    displayText = strjoin(lines, newline);
    set_param([sys '/responsibility boundary'], 'Description', displayText);
    try
        set_param(sys, 'AttributesFormatString', displayText);
    catch
    end
    Simulink.BlockDiagram.arrangeSystem(sys);
end
