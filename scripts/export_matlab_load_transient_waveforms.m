repoRoot = fileparts(fileparts(mfilename('fullpath')));
waveDir = fullfile(repoRoot, 'waveforms');

if ~exist(waveDir, 'dir')
    mkdir(waveDir);
end

set_plot_defaults();

baseP = params();

chapter04Pi = simulate_case("chapter04_pi", baseP);

loadTransientP = baseP;
loadTransientP.kp = 0.02;
loadTransientP.ki = 80.0;
loadTransientPi = simulate_case("load_transient_pi", loadTransientP);

largeCapP = loadTransientP;
largeCapP.c_out = 220e-6;
largeCap = simulate_case("large_cap", largeCapP);

dutyLimitP = loadTransientP;
dutyLimitP.duty_max = 0.503;
dutyLimited = simulate_case("duty_limited", dutyLimitP);

write_trace(fullfile(waveDir, '08-matlab-load-transient-trace.csv'), chapter04Pi, loadTransientPi, largeCap, dutyLimited);
summary = build_summary(baseP, chapter04Pi, loadTransientPi, largeCap, dutyLimited);
writetable(summary, fullfile(waveDir, '08-matlab-load-transient-summary.csv'));

plot_overview(fullfile(waveDir, '08-matlab-load-transient-overview.png'), baseP, loadTransientPi);
plot_comparison(fullfile(waveDir, '08-matlab-load-transient-vout-comparison.png'), baseP, chapter04Pi, loadTransientPi, largeCap, dutyLimited);
plot_duty_diagnosis(fullfile(waveDir, '08-matlab-load-transient-duty-diagnosis.png'), baseP, loadTransientPi, dutyLimited);

fprintf('已生成第 8 章负载突变仿真数据与图表。\n');
fprintf('chapter04_pi,undershoot=%.6g,recovery_up_ms=%.6g,overshoot=%.6g,recovery_down_ms=%.6g\n', ...
    metric_value(summary, "chapter04_pi_load_increase_undershoot_v"), ...
    metric_value(summary, "chapter04_pi_load_increase_recovery_1pct_ms"), ...
    metric_value(summary, "chapter04_pi_load_decrease_overshoot_v"), ...
    metric_value(summary, "chapter04_pi_load_decrease_recovery_1pct_ms"));
fprintf('load_transient_pi,undershoot=%.6g,recovery_up_ms=%.6g,overshoot=%.6g,recovery_down_ms=%.6g\n', ...
    metric_value(summary, "load_transient_pi_load_increase_undershoot_v"), ...
    metric_value(summary, "load_transient_pi_load_increase_recovery_1pct_ms"), ...
    metric_value(summary, "load_transient_pi_load_decrease_overshoot_v"), ...
    metric_value(summary, "load_transient_pi_load_decrease_recovery_1pct_ms"));
fprintf('duty_limited,saturation_ms=%.6g,steady_error_before_down=%.6g\n', ...
    metric_value(summary, "duty_limited_heavy_load_saturation_ms"), ...
    metric_value(summary, "duty_limited_error_before_load_decrease_v"));

function P = params()
    P.vin_nom = 24.0;
    P.vref = 12.0;
    P.rload_light = 4.8;
    P.rload_heavy = 2.4;
    P.l_out = 22e-6;
    P.c_out = 100e-6;
    P.r_series = 0.02;
    P.fsw = 200e3;
    P.ts_ctrl = 1 / P.fsw;
    P.substeps = 10;
    P.dt = P.ts_ctrl / P.substeps;
    P.stop_time = 0.030;
    P.load_increase_time = 0.008;
    P.load_decrease_time = 0.016;
    P.kp = 0.05;
    P.ki = 200.0;
    P.duty_feedforward = 0.5;
    P.duty_min = 0.0;
    P.duty_max = 0.65;
    P.settle_band = 0.01 * P.vref;
end

function data = simulate_case(caseName, P)
    n = round(P.stop_time / P.dt) + 1;
    data.time_s = zeros(n, 1);
    data.vin_v = zeros(n, 1);
    data.vout_v = zeros(n, 1);
    data.load_current_a = zeros(n, 1);
    data.load_resistance_ohm = zeros(n, 1);
    data.inductor_current_a = zeros(n, 1);
    data.cap_current_a = zeros(n, 1);
    data.error_v = zeros(n, 1);
    data.duty_raw = zeros(n, 1);
    data.duty_cmd = zeros(n, 1);
    data.integrator = zeros(n, 1);
    data.saturation = zeros(n, 1);
    data.allow_integrate = zeros(n, 1);
    data.is_sample = zeros(n, 1);

    inductorCurrent = P.vref / P.rload_light;
    vout = P.vref;
    integrator = (P.vref + inductorCurrent * P.r_series) / P.vin_nom - P.duty_feedforward;
    error = 0.0;
    dutyRaw = P.duty_feedforward + integrator;
    dutyCmd = clamp(dutyRaw, P.duty_min, P.duty_max);
    saturation = false;
    allowIntegrate = true;

    for idx = 1:n
        time_s = (idx - 1) * P.dt;
        vin = P.vin_nom;
        rload = load_profile(time_s, P);
        isSample = mod(idx - 1, P.substeps) == 0;

        if isSample
            error = P.vref - vout;
            pTerm = P.kp * error;
            dutyRawPre = P.duty_feedforward + pTerm + integrator;

            highSaturation = dutyRawPre > P.duty_max;
            lowSaturation = dutyRawPre < P.duty_min;

            % 限幅时只允许积分项朝退出饱和的方向移动。
            allowIntegrate = (~highSaturation && ~lowSaturation) ...
                || (highSaturation && error < 0) ...
                || (lowSaturation && error > 0);

            if allowIntegrate
                integrator = integrator + P.ki * P.ts_ctrl * error;
            end

            dutyRaw = P.duty_feedforward + pTerm + integrator;
            dutyCmd = clamp(dutyRaw, P.duty_min, P.duty_max);
            saturation = abs(dutyCmd - dutyRaw) > 1e-12;
        end

        loadCurrent = vout / rload;
        capCurrent = inductorCurrent - loadCurrent;
        diDt = (vin * dutyCmd - vout - inductorCurrent * P.r_series) / P.l_out;
        dvDt = capCurrent / P.c_out;
        inductorCurrent = inductorCurrent + diDt * P.dt;
        vout = vout + dvDt * P.dt;

        data.time_s(idx) = time_s;
        data.vin_v(idx) = vin;
        data.vout_v(idx) = vout;
        data.load_current_a(idx) = loadCurrent;
        data.load_resistance_ohm(idx) = rload;
        data.inductor_current_a(idx) = inductorCurrent;
        data.cap_current_a(idx) = capCurrent;
        data.error_v(idx) = error;
        data.duty_raw(idx) = dutyRaw;
        data.duty_cmd(idx) = dutyCmd;
        data.integrator(idx) = integrator;
        data.saturation(idx) = double(saturation);
        data.allow_integrate(idx) = double(allowIntegrate);
        data.is_sample(idx) = double(isSample);
    end

    data.case_id = caseName;
    data.params = P;
end

function rload = load_profile(time_s, P)
    if time_s >= P.load_increase_time && time_s < P.load_decrease_time
        rload = P.rload_heavy;
    else
        rload = P.rload_light;
    end
end

function value = clamp(value, low, high)
    value = min(max(value, low), high);
end

function write_trace(path, varargin)
    fid = fopen(path, 'w');
    cleaner = onCleanup(@() fclose(fid));
    fprintf(fid, 'case,time_s,vin_v,vout_v,load_current_a,load_resistance_ohm,inductor_current_a,cap_current_a,error_v,duty_raw,duty_cmd,integrator,saturation,allow_integrate,is_sample\n');
    for caseIdx = 1:nargin - 1
        write_case(fid, varargin{caseIdx});
    end
end

function write_case(fid, data)
    for idx = 1:numel(data.time_s)
        if data.is_sample(idx) < 0.5
            continue;
        end
        fprintf(fid, '%s,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.0f,%.0f,%.0f\n', ...
            data.case_id, ...
            data.time_s(idx), ...
            data.vin_v(idx), ...
            data.vout_v(idx), ...
            data.load_current_a(idx), ...
            data.load_resistance_ohm(idx), ...
            data.inductor_current_a(idx), ...
            data.cap_current_a(idx), ...
            data.error_v(idx), ...
            data.duty_raw(idx), ...
            data.duty_cmd(idx), ...
            data.integrator(idx), ...
            data.saturation(idx), ...
            data.allow_integrate(idx), ...
            data.is_sample(idx));
    end
end

function summary = build_summary(baseP, varargin)
    metric = strings(0, 1);
    value = zeros(0, 1);
    note = strings(0, 1);

    [metric, value, note] = add_metric(metric, value, note, "vref_v", baseP.vref, "");
    [metric, value, note] = add_metric(metric, value, note, "vin_nom_v", baseP.vin_nom, "");
    [metric, value, note] = add_metric(metric, value, note, "light_load_current_a", baseP.vref / baseP.rload_light, "");
    [metric, value, note] = add_metric(metric, value, note, "heavy_load_current_a", baseP.vref / baseP.rload_heavy, "");
    [metric, value, note] = add_metric(metric, value, note, "load_increase_time_ms", baseP.load_increase_time * 1000, "");
    [metric, value, note] = add_metric(metric, value, note, "load_decrease_time_ms", baseP.load_decrease_time * 1000, "");
    [metric, value, note] = add_metric(metric, value, note, "settle_band_v", baseP.settle_band, "");

    for idx = 1:numel(varargin)
        data = varargin{idx};
        P = data.params;
        prefix = data.case_id;
        metrics = case_metrics(data, P);
        names = fieldnames(metrics);
        for nameIdx = 1:numel(names)
            [metric, value, note] = add_metric(metric, value, note, prefix + "_" + names{nameIdx}, metrics.(names{nameIdx}), "");
        end
        [metric, value, note] = add_metric(metric, value, note, prefix + "_kp", P.kp, "");
        [metric, value, note] = add_metric(metric, value, note, prefix + "_ki", P.ki, "");
        [metric, value, note] = add_metric(metric, value, note, prefix + "_cout_uf", P.c_out * 1e6, "");
        [metric, value, note] = add_metric(metric, value, note, prefix + "_duty_max", P.duty_max, "");
    end

    summary = table(metric, value, note);
end

function metrics = case_metrics(data, P)
    heavyMask = data.time_s >= P.load_increase_time & data.time_s < P.load_decrease_time;
    afterDownMask = data.time_s >= P.load_decrease_time & data.time_s <= P.stop_time;
    beforeDownMask = data.time_s >= (P.load_decrease_time - 0.0005) & data.time_s < P.load_decrease_time;

    minV = min(data.vout_v(heavyMask));
    maxVAfterDown = max(data.vout_v(afterDownMask));

    metrics.load_increase_min_vout_v = minV;
    metrics.load_increase_undershoot_v = P.vref - minV;
    metrics.load_increase_undershoot_percent = (P.vref - minV) / P.vref * 100;
    metrics.load_increase_recovery_1pct_ms = recovery_time_ms(data, P.load_increase_time, P.load_decrease_time, P);
    metrics.load_increase_peak_inductor_current_a = max(data.inductor_current_a(heavyMask));
    metrics.load_increase_peak_duty_cmd = max(data.duty_cmd(heavyMask));
    metrics.load_increase_peak_duty_raw = max(data.duty_raw(heavyMask));
    metrics.heavy_load_saturation_ms = sum(data.saturation(heavyMask) > 0.5) * P.dt * 1000;
    metrics.error_before_load_decrease_v = mean(data.error_v(beforeDownMask));

    metrics.load_decrease_max_vout_v = maxVAfterDown;
    metrics.load_decrease_overshoot_v = maxVAfterDown - P.vref;
    metrics.load_decrease_overshoot_percent = (maxVAfterDown - P.vref) / P.vref * 100;
    metrics.load_decrease_recovery_1pct_ms = recovery_time_ms(data, P.load_decrease_time, P.stop_time, P);
    metrics.load_decrease_min_inductor_current_a = min(data.inductor_current_a(afterDownMask));
    metrics.load_decrease_min_duty_cmd = min(data.duty_cmd(afterDownMask));
    metrics.total_saturation_ms = sum(data.saturation > 0.5) * P.dt * 1000;
end

function value = recovery_time_ms(data, start_s, stop_s, P)
    mask = data.time_s >= start_s & data.time_s < stop_s;
    times = data.time_s(mask);
    err = abs(data.vout_v(mask) - P.vref);
    value = NaN;
    for idx = 1:numel(times)
        if all(err(idx:end) <= P.settle_band)
            value = (times(idx) - start_s) * 1000;
            return;
        end
    end
end

function [metric, value, note] = add_metric(metric, value, note, metricName, metricValue, metricNote)
    metric(end + 1, 1) = metricName;
    value(end + 1, 1) = metricValue;
    note(end + 1, 1) = metricNote;
end

function value = metric_value(summary, name)
    value = summary.value(summary.metric == name);
end

function plot_overview(path, P, data)
    fig = figure('Visible', 'off', 'Color', 'w', 'Position', [90 80 1400 950]);
    tiledlayout(4, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    hold on;
    plot_ms(data, 'vout_v', [0 0.447 0.741], 'Vout');
    yline(P.vref, '--', '12V target', 'Color', [0.35 0.35 0.35], 'HandleVisibility', 'off');
    add_load_events(P);
    title('MATLAB 平均模型：负载 50% -> 100% -> 50% 时的闭环响应');
    ylabel('Vout / V');
    legend('Location', 'northeast');
    grid on;

    nexttile;
    hold on;
    plot_ms(data, 'load_current_a', [0.85 0.325 0.098], 'load current');
    plot_ms(data, 'inductor_current_a', [0.2 0.55 0.30], 'inductor current');
    add_load_events(P);
    ylabel('Current / A');
    legend('Location', 'northeast');
    grid on;

    nexttile;
    hold on;
    plot_ms(data, 'duty_raw', [0.55 0.55 0.55], 'raw duty');
    plot_ms(data, 'duty_cmd', [0 0.447 0.741], 'duty cmd');
    yline(P.duty_max, '--', 'duty max', 'Color', [0.35 0.35 0.35], 'HandleVisibility', 'off');
    add_load_events(P);
    ylabel('Duty');
    legend('Location', 'northeast');
    grid on;

    nexttile;
    hold on;
    plot_ms(data, 'integrator', [0.494 0.184 0.556], 'integrator');
    add_load_events(P);
    ylabel('Integrator');
    xlabel('Time / ms');
    legend('Location', 'southeast');
    grid on;

    add_source_stamp(fig);
    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_comparison(path, P, chapter04Pi, loadTransientPi, largeCap, dutyLimited)
    fig = figure('Visible', 'off', 'Color', 'w', 'Position', [90 80 1400 900]);
    tiledlayout(3, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    hold on;
    plot_ms(chapter04Pi, 'vout_v', [0.55 0.55 0.55], 'chapter 04 PI, 100uF');
    plot_ms(loadTransientPi, 'vout_v', [0 0.447 0.741], 'load transient PI, 100uF');
    plot_ms(largeCap, 'vout_v', [0.2 0.55 0.30], 'load transient PI, 220uF');
    plot_ms(dutyLimited, 'vout_v', [0.85 0.325 0.098], 'duty max too low');
    yline(P.vref, '--', 'Color', [0.35 0.35 0.35], 'HandleVisibility', 'off');
    yline(13.2, ':', '13.2V OVP threshold', 'Color', [0.45 0.45 0.45], 'HandleVisibility', 'off');
    add_load_events(P);
    title('负载突变对比：Vout 下陷深度和恢复时间要分开看');
    ylabel('Vout / V');
    ylim([10.5 13.6]);
    legend('Location', 'northeast');
    grid on;

    nexttile;
    hold on;
    plot_ms(chapter04Pi, 'duty_cmd', [0.55 0.55 0.55], 'chapter 04 PI');
    plot_ms(loadTransientPi, 'duty_cmd', [0 0.447 0.741], 'load transient PI');
    plot_ms(largeCap, 'duty_cmd', [0.2 0.55 0.30], 'large cap');
    plot_ms(dutyLimited, 'duty_cmd', [0.85 0.325 0.098], 'duty limited');
    add_load_events(P);
    ylabel('Duty cmd');
    legend('Location', 'northeast');
    grid on;

    nexttile;
    hold on;
    plot_ms(loadTransientPi, 'load_current_a', [0.85 0.325 0.098], 'load current');
    add_load_events(P);
    ylabel('Load current / A');
    xlabel('Time / ms');
    legend('Location', 'northeast');
    grid on;

    add_source_stamp(fig);
    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_duty_diagnosis(path, P, loadTransientPi, dutyLimited)
    fig = figure('Visible', 'off', 'Color', 'w', 'Position', [90 80 1400 880]);
    tiledlayout(3, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    hold on;
    plot_ms(loadTransientPi, 'vout_v', [0 0.447 0.741], 'normal duty margin');
    plot_ms(dutyLimited, 'vout_v', [0.55 0.55 0.55], 'duty max too low');
    yline(P.vref, '--', 'Color', [0.35 0.35 0.35], 'HandleVisibility', 'off');
    add_load_events(P);
    title('诊断 duty 限幅：Vout 低、raw duty 想上去、cmd duty 卡住，就是执行量不够');
    ylabel('Vout / V');
    legend('Location', 'northeast');
    grid on;

    nexttile;
    hold on;
    plot_ms(dutyLimited, 'duty_raw', [0.85 0.325 0.098], 'raw duty request');
    plot_ms(dutyLimited, 'duty_cmd', [0.1 0.1 0.1], 'limited duty cmd');
    yline(dutyLimited.params.duty_max, '--', 'duty max', 'Color', [0.35 0.35 0.35], 'HandleVisibility', 'off');
    add_load_events(P);
    ylabel('Duty');
    legend('Location', 'northeast');
    grid on;

    nexttile;
    hold on;
    plot_ms(dutyLimited, 'saturation', [0.494 0.184 0.556], 'saturation flag');
    add_load_events(P);
    ylim([-0.08 1.15]);
    ylabel('Saturation');
    xlabel('Time / ms');
    legend('Location', 'northeast');
    grid on;

    add_source_stamp(fig);
    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_ms(data, field, color, name)
    plot(data.time_s * 1000, data.(field), 'LineWidth', 1.65, 'Color', color, 'DisplayName', name);
end

function add_load_events(P)
    xline(P.load_increase_time * 1000, '--', '50% -> 100%', 'Color', [0.35 0.35 0.35], 'HandleVisibility', 'off');
    xline(P.load_decrease_time * 1000, '--', '100% -> 50%', 'Color', [0.45 0.45 0.45], 'HandleVisibility', 'off');
end

function add_source_stamp(fig)
    annotation(fig, 'textbox', [0.72 0.945 0.24 0.025], ...
        'String', 'Source: MATLAB averaged Buck model', ...
        'EdgeColor', 'none', ...
        'HorizontalAlignment', 'right', ...
        'FontSize', 8, ...
        'Color', [0.35 0.35 0.35]);
end

function set_plot_defaults()
    set(groot, 'defaultAxesFontName', 'Microsoft YaHei');
    set(groot, 'defaultTextFontName', 'Microsoft YaHei');
    set(groot, 'defaultAxesXColor', [0.29 0.33 0.39]);
    set(groot, 'defaultAxesYColor', [0.29 0.33 0.39]);
    set(groot, 'defaultAxesGridColor', [0.80 0.84 0.89]);
    set(groot, 'defaultAxesBox', 'off');
    set(groot, 'defaultTextInterpreter', 'none');
    set(groot, 'defaultLegendInterpreter', 'none');
    set(groot, 'defaultAxesTickLabelInterpreter', 'none');
end
