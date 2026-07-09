repoRoot = fileparts(fileparts(mfilename('fullpath')));
waveDir = fullfile(repoRoot, 'waveforms');
modelDir = fullfile(repoRoot, 'models', 'simulink');

if ~exist(waveDir, 'dir')
    mkdir(waveDir);
end

run(fullfile(repoRoot, 'scripts', 'export_simulink_discrete_pi_snapshot.m'));

modelName = 'buck_discrete_pi_voltage_loop';
modelPath = fullfile(modelDir, [modelName '.slx']);

load_system(modelPath);
ensure_to_workspace(modelName);

set_param(modelName, ...
    'StopTime', '0.012', ...
    'ReturnWorkspaceOutputs', 'on');

kiPath = [modelName '/Discrete PI voltage controller/Ki accumulator'];

set_param(kiPath, 'gainval', '1e-12');
pOnly = run_case(modelName);

set_param(kiPath, 'gainval', '200');
piCase = run_case(modelName);

save_system(modelName, modelPath);
close_system(modelName, 0);

write_trace(fullfile(waveDir, '04-simulink-discrete-pi-control-trace.csv'), piCase);
summary = write_summary(fullfile(waveDir, '04-simulink-discrete-pi-control-summary.csv'), pOnly, piCase);

plot_p_vs_pi(fullfile(waveDir, '04-simulink-p-only-vs-pi-vin-step.png'), pOnly, piCase);
plot_pi_transient(fullfile(waveDir, '04-simulink-pi-vin-load-transient.png'), piCase);
plot_error_integrator(fullfile(waveDir, '04-simulink-pi-error-integrator.png'), piCase);
plot_sampling_points(fullfile(waveDir, '04-simulink-pi-sampling-points.png'), piCase);

fprintf('已运行 Simulink 离散 PI 模型并导出第 4 章主波形。\n');
fprintf('pi,kp=0.05,ki=200,control_period_us=5,duty_max=%.6g,input_step_settling_ms=%.6g,load_step_settling_ms=%.6g\n', ...
    summary.pi_duty_max, summary.pi_input_step_settling_ms_1pct, summary.pi_load_step_settling_ms_1pct);

function ensure_to_workspace(modelName)
    blockPath = [modelName '/Waveform export'];
    if ~isempty(find_system(modelName, 'SearchDepth', 1, 'Name', 'Waveform export'))
        delete_block(blockPath);
    end

    add_block('simulink/Sinks/To Workspace', blockPath, ...
        'Position', [1415 325 1530 360], ...
        'VariableName', 'sim_waveforms', ...
        'SaveFormat', 'Structure With Time');
    add_line(modelName, 'Scope mux/1', 'Waveform export/1', 'autorouting', 'on');
end

function data = run_case(modelName)
    simOut = sim(modelName);
    raw = simOut.get('sim_waveforms');
    values = raw.signals.values;
    data.time_s = raw.time(:);
    data.vout_v = values(:, 1);
    data.duty = values(:, 2);
    data.error_v = values(:, 3);
    data.integrator = values(:, 4);
    data.inductor_current_a = values(:, 5);
    data.load_current_a = values(:, 6);
    data.vin_v = 24 + (data.time_s >= 0.003) .* (20 - 24);
    data.rload_ohm = 2.4 + (data.time_s >= 0.007) .* (1.6 - 2.4);
end

function write_trace(path, data)
    fid = fopen(path, 'w');
    cleaner = onCleanup(@() fclose(fid));
    fprintf(fid, 'time_s,vin_v,rload_ohm,load_current_a,vout_v,inductor_current_a,error_v,duty,integrator\n');
    for idx = 1:numel(data.time_s)
        fprintf(fid, '%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g\n', ...
            data.time_s(idx), data.vin_v(idx), data.rload_ohm(idx), data.load_current_a(idx), ...
            data.vout_v(idx), data.inductor_current_a(idx), data.error_v(idx), ...
            data.duty(idx), data.integrator(idx));
    end
end

function summary = write_summary(path, pOnly, piCase)
    summary.vref_v = 12.0;
    summary.fsw_hz = 200000.0;
    summary.control_period_us = 5.0;
    summary.kp = 0.05;
    summary.ki = 200.0;
    summary.duty_feedforward = 0.5;
    summary.initial_integrator_trim = 0.0041667;
    summary.vin_step_from_v = 24.0;
    summary.vin_step_to_v = 20.0;
    summary.load_step_from_a = 5.0;
    summary.load_step_to_a = 7.5;
    summary.p_only_vout_after_vin_step_v = mean_window(pOnly, 'vout_v', 0.0055, 0.0068);
    summary.pi_vout_after_vin_step_v = mean_window(piCase, 'vout_v', 0.0055, 0.0068);
    summary.pi_vout_after_load_step_v = mean_window(piCase, 'vout_v', 0.0105, 0.012);
    summary.pi_input_step_vout_min_v = min_window(piCase, 'vout_v', 0.003, 0.007);
    summary.pi_input_step_vout_max_v = max_window(piCase, 'vout_v', 0.003, 0.007);
    summary.pi_load_step_vout_min_v = min_window(piCase, 'vout_v', 0.007, 0.012);
    summary.pi_load_step_vout_max_v = max_window(piCase, 'vout_v', 0.007, 0.012);
    summary.pi_duty_min = min(piCase.duty);
    summary.pi_duty_max = max(piCase.duty);
    summary.pi_input_step_settling_ms_1pct = settling_ms(piCase, 0.003, 0.007, 12.0, 0.12);
    summary.pi_load_step_settling_ms_1pct = settling_ms(piCase, 0.007, 0.012, 12.0, 0.12);

    names = fieldnames(summary);
    fid = fopen(path, 'w');
    cleaner = onCleanup(@() fclose(fid));
    fprintf(fid, 'metric,value\n');
    for idx = 1:numel(names)
        fprintf(fid, '%s,%.12g\n', names{idx}, summary.(names{idx}));
    end
end

function value = mean_window(data, field, startS, stopS)
    mask = data.time_s >= startS & data.time_s <= stopS;
    value = mean(data.(field)(mask));
end

function value = min_window(data, field, startS, stopS)
    mask = data.time_s >= startS & data.time_s <= stopS;
    value = min(data.(field)(mask));
end

function value = max_window(data, field, startS, stopS)
    mask = data.time_s >= startS & data.time_s <= stopS;
    value = max(data.(field)(mask));
end

function value = settling_ms(data, startS, stopS, target, band)
    mask = data.time_s >= startS & data.time_s <= stopS;
    times = data.time_s(mask);
    vout = data.vout_v(mask);
    value = NaN;
    for idx = 1:numel(times)
        if all(abs(vout(idx:end) - target) <= band)
            value = (times(idx) - startS) * 1000;
            return;
        end
    end
end

function plot_p_vs_pi(path, pOnly, piCase)
    fig = figure('Visible', 'off', 'Color', 'w', 'Position', [100 100 1200 760]);
    tiledlayout(2, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    plot_signal(pOnly.time_s * 1000, pOnly.vout_v, [0.929 0.475 0.188], 'P-only');
    hold on;
    plot_signal(piCase.time_s * 1000, piCase.vout_v, [0 0.447 0.741], 'PI');
    yline(12, '--', 'Color', [0.25 0.25 0.25], 'HandleVisibility', 'off');
    xline(3, '--', 'Color', [0.35 0.35 0.35], 'HandleVisibility', 'off');
    text(6.55, 12.08, '12V target', 'Color', [0.25 0.25 0.25]);
    text(3.08, 12.36, 'Vin 24V->20V', 'Color', [0.35 0.35 0.35]);
    title('Simulink 仿真：P-only 留下稳态误差，PI 消除稳态误差');
    ylabel('Vout / V');
    xlim([0 7]);
    legend('Location', 'southeast');
    grid on;

    nexttile;
    plot_signal(pOnly.time_s * 1000, pOnly.duty, [0.929 0.475 0.188], 'P-only duty');
    hold on;
    plot_signal(piCase.time_s * 1000, piCase.duty, [0 0.447 0.741], 'PI duty');
    xline(3, '--', 'Color', [0.35 0.35 0.35], 'HandleVisibility', 'off');
    text(3.08, 0.618, 'Vin 24V->20V', 'Color', [0.35 0.35 0.35]);
    ylabel('duty');
    xlabel('Time / ms');
    xlim([0 7]);
    legend('Location', 'southeast');
    grid on;

    add_source_stamp(fig);
    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_pi_transient(path, piCase)
    fig = figure('Visible', 'off', 'Color', 'w', 'Position', [100 100 1260 860]);
    tiledlayout(3, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    plot_signal(piCase.time_s * 1000, piCase.vout_v, [0 0.447 0.741], 'Vout');
    yline(12, '--', 'Color', [0.25 0.25 0.25], 'HandleVisibility', 'off');
    text(10.1, 12.12, '12V target', 'Color', [0.25 0.25 0.25]);
    add_events();
    title('Simulink 仿真：离散 PI 在输入扰动和负载扰动下的输出恢复');
    ylabel('Vout / V');
    xlim([0 12]);
    grid on;

    nexttile;
    plot_signal(piCase.time_s * 1000, piCase.duty, [0.0 0.5 0.45], 'duty');
    add_events();
    ylabel('duty');
    xlim([0 12]);
    grid on;

    nexttile;
    plot_signal(piCase.time_s * 1000, piCase.vin_v, [0.494 0.184 0.556], 'Vin');
    hold on;
    plot_signal(piCase.time_s * 1000, piCase.load_current_a, [0.85 0.325 0.098], 'Iout');
    add_events();
    ylabel('Vin / V, Iout / A');
    xlabel('Time / ms');
    xlim([0 12]);
    legend('Location', 'northeast');
    grid on;

    add_source_stamp(fig);
    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_error_integrator(path, piCase)
    fig = figure('Visible', 'off', 'Color', 'w', 'Position', [100 100 1200 700]);
    tiledlayout(2, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    plot_signal(piCase.time_s * 1000, piCase.error_v, [0.85 0.325 0.098], 'error');
    yline(0, '-', 'Color', [0.25 0.25 0.25], 'HandleVisibility', 'off');
    add_events();
    title('Simulink 仿真：error 与 integrator 是 PI 调试必须观测的状态量');
    ylabel('error / V');
    xlim([0 12]);
    grid on;

    nexttile;
    plot_signal(piCase.time_s * 1000, piCase.integrator, [0 0.447 0.741], 'integrator');
    add_events();
    ylabel('integrator');
    xlabel('Time / ms');
    xlim([0 12]);
    grid on;

    add_source_stamp(fig);
    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_sampling_points(path, piCase)
    startS = 0.003 - 80e-6;
    stopS = 0.003 + 260e-6;
    mask = piCase.time_s >= startS & piCase.time_s <= stopS;
    sampleTimes = startS:5e-6:stopS;
    sampleVout = interp1(piCase.time_s, piCase.vout_v, sampleTimes);

    fig = figure('Visible', 'off', 'Color', 'w', 'Position', [100 100 1100 620]);
    plot_signal(piCase.time_s(mask) * 1000, piCase.vout_v(mask), [0.45 0.45 0.45], 'Simulink continuous solver output');
    hold on;
    scatter(sampleTimes * 1000, sampleVout, 28, [0 0.447 0.741], 'filled', 'DisplayName', 'Controller sample Ts=5us');
    xline(3, '--', 'Color', [0.35 0.35 0.35], 'HandleVisibility', 'off');
    text(3.02, max(piCase.vout_v(mask)) - 0.05, 'Vin 24V->20V', 'Color', [0.35 0.35 0.35]);
    title('Simulink 仿真：数字控制器只在采样点更新 duty');
    xlabel('Time / ms');
    ylabel('Vout / V');
    legend('Location', 'southwest');
    grid on;

    add_source_stamp(fig);
    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_signal(x, y, color, name)
    plot(x, y, 'LineWidth', 1.6, 'Color', color, 'DisplayName', name);
end

function add_source_stamp(fig)
    annotation(fig, 'textbox', [0.72 0.945 0.26 0.025], ...
        'String', 'Source: Simulink Scope mux', ...
        'EdgeColor', 'none', ...
        'HorizontalAlignment', 'right', ...
        'FontSize', 8, ...
        'Color', [0.35 0.35 0.35]);
end

function add_events()
    xline(3, '--', 'Color', [0.35 0.35 0.35], 'HandleVisibility', 'off');
    xline(7, '--', 'Color', [0.45 0.45 0.45], 'HandleVisibility', 'off');
end
