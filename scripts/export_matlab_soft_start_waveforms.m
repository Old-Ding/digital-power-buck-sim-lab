repoRoot = fileparts(fileparts(mfilename('fullpath')));
waveDir = fullfile(repoRoot, 'waveforms');

if ~exist(waveDir, 'dir')
    mkdir(waveDir);
end

set_plot_defaults();

P = params();

stepRef = simulate_case('step_12v', 0.0, P);
ramp2ms = simulate_case('ramp_2ms', 0.002, P);
ramp5ms = simulate_case('ramp_5ms', 0.005, P);
sweep = run_ramp_sweep(P);

write_trace(fullfile(waveDir, '06-matlab-soft-start-trace.csv'), stepRef, ramp2ms, ramp5ms);
summary = write_summary(fullfile(waveDir, '06-matlab-soft-start-summary.csv'), P, stepRef, ramp2ms, ramp5ms);
write_sweep(fullfile(waveDir, '06-matlab-soft-start-ramp-sweep.csv'), sweep);

plot_overview(fullfile(waveDir, '06-matlab-soft-start-overview.png'), P, stepRef, ramp2ms, ramp5ms);
plot_current_stress(fullfile(waveDir, '06-matlab-soft-start-current-stress.png'), P, stepRef, ramp2ms, ramp5ms);
plot_tracking(fullfile(waveDir, '06-matlab-soft-start-tracking-error.png'), P, stepRef, ramp2ms, ramp5ms);
plot_sweep(fullfile(waveDir, '06-matlab-soft-start-ramp-sweep.png'), sweep);

fprintf('已生成第 6 章软启动仿真数据与图表。\n');
fprintf('step_12v,peak_vout=%.6g,peak_il=%.6g,saturation_ms=%.6g\n', ...
    summary.step_12v_peak_vout_v, ...
    summary.step_12v_peak_inductor_current_a, ...
    summary.step_12v_saturation_total_ms);
fprintf('ramp_5ms,peak_vout=%.6g,peak_il=%.6g,saturation_ms=%.6g\n', ...
    summary.ramp_5ms_peak_vout_v, ...
    summary.ramp_5ms_peak_inductor_current_a, ...
    summary.ramp_5ms_saturation_total_ms);

function P = params()
    P.vin_nom = 24.0;
    P.vref_target = 12.0;
    P.rload = 2.4;
    P.l_out = 22e-6;
    P.c_out = 100e-6;
    P.fsw = 200e3;
    P.ts_ctrl = 1 / P.fsw;
    P.substeps = 10;
    P.dt = P.ts_ctrl / P.substeps;
    P.stop_time = 0.018;
    P.r_series = 0.02;
    P.kp = 0.05;
    P.ki = 200.0;
    P.duty_min = 0.0;
    P.duty_max = 0.55;
    P.settle_band = 0.01 * P.vref_target;
end

function data = simulate_case(mode, ramp_time_s, P)
    n = round(P.stop_time / P.dt) + 1;
    data.time_s = zeros(n, 1);
    data.vin_v = zeros(n, 1);
    data.vref_cmd_v = zeros(n, 1);
    data.vout_v = zeros(n, 1);
    data.inductor_current_a = zeros(n, 1);
    data.error_v = zeros(n, 1);
    data.duty_feedforward = zeros(n, 1);
    data.duty_raw = zeros(n, 1);
    data.duty_cmd = zeros(n, 1);
    data.integrator = zeros(n, 1);
    data.saturation = zeros(n, 1);
    data.allow_integrate = zeros(n, 1);
    data.is_sample = zeros(n, 1);

    inductor_current = 0.0;
    vout = 0.0;
    integrator = 0.0;
    error = 0.0;
    duty_feedforward = 0.0;
    duty_raw = 0.0;
    duty_cmd = 0.0;
    saturation = false;
    allow_integrate = true;

    for idx = 1:n
        time_s = (idx - 1) * P.dt;
        vin = P.vin_nom;
        is_sample = mod(idx - 1, P.substeps) == 0;
        vref_cmd = vref_profile(time_s, ramp_time_s, P);

        if is_sample
            error = vref_cmd - vout;
            duty_feedforward = feedforward_duty(vref_cmd, P);
            p_term = P.kp * error;
            duty_raw_pre = duty_feedforward + p_term + integrator;

            high_saturation = duty_raw_pre > P.duty_max;
            low_saturation = duty_raw_pre < P.duty_min;

            % 积分只在能退出饱和方向时更新，避免启动阶段 windup。
            allow_integrate = (~high_saturation && ~low_saturation) ...
                || (high_saturation && error < 0) ...
                || (low_saturation && error > 0);

            if allow_integrate
                integrator = integrator + P.ki * P.ts_ctrl * error;
            end

            duty_raw = duty_feedforward + p_term + integrator;
            duty_cmd = clamp(duty_raw, P.duty_min, P.duty_max);
            saturation = abs(duty_cmd - duty_raw) > 1e-12;
        end

        di_dt = (vin * duty_cmd - vout - inductor_current * P.r_series) / P.l_out;
        next_inductor_current = inductor_current + di_dt * P.dt;
        % 启动阶段按非同步 Buck 近似处理，电感电流不允许反向。
        next_inductor_current = max(0.0, next_inductor_current);
        dv_dt = (next_inductor_current - vout / P.rload) / P.c_out;
        inductor_current = next_inductor_current;
        vout = vout + dv_dt * P.dt;

        data.time_s(idx) = time_s;
        data.vin_v(idx) = vin;
        data.vref_cmd_v(idx) = vref_cmd;
        data.vout_v(idx) = vout;
        data.inductor_current_a(idx) = inductor_current;
        data.error_v(idx) = error;
        data.duty_feedforward(idx) = duty_feedforward;
        data.duty_raw(idx) = duty_raw;
        data.duty_cmd(idx) = duty_cmd;
        data.integrator(idx) = integrator;
        data.saturation(idx) = double(saturation);
        data.allow_integrate(idx) = double(allow_integrate);
        data.is_sample(idx) = double(is_sample);
    end

    data.mode = mode;
    data.ramp_time_s = ramp_time_s;
end

function value = vref_profile(time_s, ramp_time_s, P)
    if ramp_time_s <= 0
        value = P.vref_target;
    else
        value = min(P.vref_target, P.vref_target * time_s / ramp_time_s);
    end
end

function value = feedforward_duty(vref_cmd, P)
    estimated_current = vref_cmd / P.rload;
    value = (vref_cmd + estimated_current * P.r_series) / P.vin_nom;
end

function value = clamp(value, low, high)
    value = min(max(value, low), high);
end

function sweep = run_ramp_sweep(P)
    rampTimes = [0.0 0.001 0.002 0.003 0.005 0.008 0.010]';
    sweep.ramp_time_ms = rampTimes * 1000;
    sweep.peak_vout_v = zeros(numel(rampTimes), 1);
    sweep.peak_inductor_current_a = zeros(numel(rampTimes), 1);
    sweep.saturation_total_ms = zeros(numel(rampTimes), 1);
    sweep.time_to_95pct_ms = zeros(numel(rampTimes), 1);
    sweep.settle_time_ms = zeros(numel(rampTimes), 1);

    for idx = 1:numel(rampTimes)
        data = simulate_case(sprintf('ramp_%gms', rampTimes(idx) * 1000), rampTimes(idx), P);
        metrics = case_metrics(data, P);
        sweep.peak_vout_v(idx) = metrics.peak_vout_v;
        sweep.peak_inductor_current_a(idx) = metrics.peak_inductor_current_a;
        sweep.saturation_total_ms(idx) = metrics.saturation_total_ms;
        sweep.time_to_95pct_ms(idx) = metrics.time_to_95pct_ms;
        sweep.settle_time_ms(idx) = metrics.settle_time_ms;
    end
end

function write_trace(path, stepRef, ramp2ms, ramp5ms)
    fid = fopen(path, 'w');
    cleaner = onCleanup(@() fclose(fid));
    fprintf(fid, 'case,time_s,vin_v,vref_cmd_v,vout_v,inductor_current_a,error_v,duty_feedforward,duty_raw,duty_cmd,integrator,saturation,allow_integrate,is_sample\n');
    write_case(fid, stepRef);
    write_case(fid, ramp2ms);
    write_case(fid, ramp5ms);
end

function write_case(fid, data)
    for idx = 1:numel(data.time_s)
        if data.is_sample(idx) < 0.5
            continue;
        end
        fprintf(fid, '%s,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.0f,%.0f,%.0f\n', ...
            data.mode, ...
            data.time_s(idx), ...
            data.vin_v(idx), ...
            data.vref_cmd_v(idx), ...
            data.vout_v(idx), ...
            data.inductor_current_a(idx), ...
            data.error_v(idx), ...
            data.duty_feedforward(idx), ...
            data.duty_raw(idx), ...
            data.duty_cmd(idx), ...
            data.integrator(idx), ...
            data.saturation(idx), ...
            data.allow_integrate(idx), ...
            data.is_sample(idx));
    end
end

function summary = write_summary(path, P, stepRef, ramp2ms, ramp5ms)
    summary.vref_target_v = P.vref_target;
    summary.vin_nom_v = P.vin_nom;
    summary.fsw_hz = P.fsw;
    summary.control_period_us = P.ts_ctrl * 1e6;
    summary.kp = P.kp;
    summary.ki = P.ki;
    summary.duty_min = P.duty_min;
    summary.duty_max = P.duty_max;
    summary.ramp_2ms_time_ms = 2;
    summary.ramp_5ms_time_ms = 5;

    summary = append_case_summary(summary, 'step_12v', stepRef, P);
    summary = append_case_summary(summary, 'ramp_2ms', ramp2ms, P);
    summary = append_case_summary(summary, 'ramp_5ms', ramp5ms, P);

    summary.ramp_5ms_peak_current_reduction_a = ...
        summary.step_12v_peak_inductor_current_a - summary.ramp_5ms_peak_inductor_current_a;
    summary.ramp_5ms_vout_overshoot_reduction_v = ...
        summary.step_12v_overshoot_v - summary.ramp_5ms_overshoot_v;

    names = fieldnames(summary);
    fid = fopen(path, 'w');
    cleaner = onCleanup(@() fclose(fid));
    fprintf(fid, 'metric,value\n');
    for idx = 1:numel(names)
        fprintf(fid, '%s,%.12g\n', names{idx}, summary.(names{idx}));
    end
end

function summary = append_case_summary(summary, prefix, data, P)
    metrics = case_metrics(data, P);
    fields = fieldnames(metrics);
    for idx = 1:numel(fields)
        summary.([prefix '_' fields{idx}]) = metrics.(fields{idx});
    end
end

function metrics = case_metrics(data, P)
    metrics.ramp_time_ms = data.ramp_time_s * 1000;
    metrics.peak_vout_v = max(data.vout_v);
    metrics.overshoot_v = max(0, metrics.peak_vout_v - P.vref_target);
    metrics.peak_inductor_current_a = max(data.inductor_current_a);
    metrics.peak_duty_cmd = max(data.duty_cmd);
    metrics.peak_duty_raw = max(data.duty_raw);
    metrics.integrator_peak = max(data.integrator);
    metrics.saturation_total_ms = sum(data.saturation > 0.5) * P.dt * 1000;
    metrics.max_abs_tracking_error_v = max(abs(data.vref_cmd_v - data.vout_v));
    metrics.time_to_95pct_ms = first_crossing_ms(data, 0.95 * P.vref_target);
    metrics.settle_time_ms = settle_time_ms(data, P);
end

function value = first_crossing_ms(data, threshold)
    idx = find(data.vout_v >= threshold, 1, 'first');
    if isempty(idx)
        value = NaN;
    else
        value = data.time_s(idx) * 1000;
    end
end

function value = settle_time_ms(data, P)
    target_reached_time = data.ramp_time_s;
    mask = data.time_s >= target_reached_time;
    times = data.time_s(mask);
    err = abs(data.vout_v(mask) - P.vref_target);
    value = NaN;
    for idx = 1:numel(times)
        if all(err(idx:end) <= P.settle_band)
            value = times(idx) * 1000;
            return;
        end
    end
end

function write_sweep(path, sweep)
    fid = fopen(path, 'w');
    cleaner = onCleanup(@() fclose(fid));
    fprintf(fid, 'ramp_time_ms,peak_vout_v,peak_inductor_current_a,saturation_total_ms,time_to_95pct_ms,settle_time_ms\n');
    for idx = 1:numel(sweep.ramp_time_ms)
        fprintf(fid, '%.12g,%.12g,%.12g,%.12g,%.12g,%.12g\n', ...
            sweep.ramp_time_ms(idx), ...
            sweep.peak_vout_v(idx), ...
            sweep.peak_inductor_current_a(idx), ...
            sweep.saturation_total_ms(idx), ...
            sweep.time_to_95pct_ms(idx), ...
            sweep.settle_time_ms(idx));
    end
end

function plot_overview(path, P, stepRef, ramp2ms, ramp5ms)
    fig = figure('Visible', 'off', 'Position', [80 80 1400 980]);
    tiledlayout(4, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    hold on;
    plot_ms(stepRef, 'vref_cmd_v', '--', 'Color', [0.45 0.45 0.45], 'LineWidth', 1.4);
    plot_ms(stepRef, 'vout_v', '-', 'Color', [0.45 0.45 0.45], 'LineWidth', 1.5);
    plot_ms(ramp2ms, 'vout_v', '-', 'Color', [0.8500 0.3250 0.0980], 'LineWidth', 1.5);
    plot_ms(ramp5ms, 'vout_v', '-', 'Color', [0 0.4470 0.7410], 'LineWidth', 1.5);
    yline(P.vref_target, '--', '12V target', 'Color', [0.5 0.5 0.5]);
    ylabel('Vout / V');
    title('MATLAB 仿真：软启动把 12V 参考值从阶跃变成斜坡');
    legend('Step Vref', 'Step output', '2ms soft-start output', '5ms soft-start output', 'Location', 'southeast');
    grid on;

    nexttile;
    hold on;
    plot_ms(stepRef, 'vref_cmd_v', '--', 'Color', [0.45 0.45 0.45], 'LineWidth', 1.4);
    plot_ms(ramp2ms, 'vref_cmd_v', '-', 'Color', [0.8500 0.3250 0.0980], 'LineWidth', 1.5);
    plot_ms(ramp5ms, 'vref_cmd_v', '-', 'Color', [0 0.4470 0.7410], 'LineWidth', 1.5);
    ylabel('Vref cmd / V');
    legend('Step 12V', '2ms ramp', '5ms ramp', 'Location', 'southeast');
    grid on;

    nexttile;
    hold on;
    plot_ms(stepRef, 'inductor_current_a', '-', 'Color', [0.45 0.45 0.45], 'LineWidth', 1.5);
    plot_ms(ramp2ms, 'inductor_current_a', '-', 'Color', [0.8500 0.3250 0.0980], 'LineWidth', 1.5);
    plot_ms(ramp5ms, 'inductor_current_a', '-', 'Color', [0 0.4470 0.7410], 'LineWidth', 1.5);
    yline(P.vref_target / P.rload, '--', '5A load current', 'Color', [0.5 0.5 0.5]);
    ylabel('IL / A');
    legend('Step 12V', '2ms ramp', '5ms ramp', 'Location', 'northeast');
    grid on;

    nexttile;
    hold on;
    plot_ms(stepRef, 'duty_cmd', '-', 'Color', [0.45 0.45 0.45], 'LineWidth', 1.5);
    plot_ms(ramp2ms, 'duty_cmd', '-', 'Color', [0.8500 0.3250 0.0980], 'LineWidth', 1.5);
    plot_ms(ramp5ms, 'duty_cmd', '-', 'Color', [0 0.4470 0.7410], 'LineWidth', 1.5);
    yline(P.duty_max, '--', 'duty max', 'Color', [0.5 0.5 0.5]);
    ylabel('duty cmd');
    xlabel('Time / ms');
    legend('Step 12V', '2ms ramp', '5ms ramp', 'Location', 'northeast');
    grid on;

    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_current_stress(path, P, stepRef, ramp2ms, ramp5ms)
    fig = figure('Visible', 'off', 'Position', [80 80 1400 760]);
    tiledlayout(2, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    hold on;
    plot_ms(stepRef, 'inductor_current_a', '-', 'Color', [0.45 0.45 0.45], 'LineWidth', 1.6);
    plot_ms(ramp2ms, 'inductor_current_a', '-', 'Color', [0.8500 0.3250 0.0980], 'LineWidth', 1.6);
    plot_ms(ramp5ms, 'inductor_current_a', '-', 'Color', [0 0.4470 0.7410], 'LineWidth', 1.6);
    xlim([0 8]);
    ylabel('IL / A');
    title('启动电感电流峰值对比：斜坡越慢，启动应力越低');
    legend('Step 12V', '2ms ramp', '5ms ramp', 'Location', 'northeast');
    grid on;

    nexttile;
    hold on;
    plot_ms(stepRef, 'saturation', '-', 'Color', [0.45 0.45 0.45], 'LineWidth', 1.4);
    plot_ms(ramp2ms, 'saturation', '-', 'Color', [0.8500 0.3250 0.0980], 'LineWidth', 1.4);
    plot_ms(ramp5ms, 'saturation', '-', 'Color', [0 0.4470 0.7410], 'LineWidth', 1.4);
    xlim([0 8]);
    ylim([-0.1 1.1]);
    ylabel('saturation flag');
    xlabel('Time / ms');
    legend('Step 12V', '2ms ramp', '5ms ramp', 'Location', 'northeast');
    grid on;

    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_tracking(path, P, stepRef, ramp2ms, ramp5ms)
    fig = figure('Visible', 'off', 'Position', [80 80 1400 760]);
    tiledlayout(2, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    hold on;
    plot(stepRef.time_s * 1000, stepRef.vref_cmd_v - stepRef.vout_v, '-', 'Color', [0.45 0.45 0.45], 'LineWidth', 1.5);
    plot(ramp2ms.time_s * 1000, ramp2ms.vref_cmd_v - ramp2ms.vout_v, '-', 'Color', [0.8500 0.3250 0.0980], 'LineWidth', 1.5);
    plot(ramp5ms.time_s * 1000, ramp5ms.vref_cmd_v - ramp5ms.vout_v, '-', 'Color', [0 0.4470 0.7410], 'LineWidth', 1.5);
    yline(0, '--', 'Color', [0.5 0.5 0.5]);
    ylabel('Vref - Vout / V');
    title('软启动不是让误差消失，而是让误差按可控斜率进入控制器');
    legend('Step 12V', '2ms ramp', '5ms ramp', 'Location', 'northeast');
    grid on;

    nexttile;
    hold on;
    plot_ms(stepRef, 'integrator', '-', 'Color', [0.45 0.45 0.45], 'LineWidth', 1.5);
    plot_ms(ramp2ms, 'integrator', '-', 'Color', [0.8500 0.3250 0.0980], 'LineWidth', 1.5);
    plot_ms(ramp5ms, 'integrator', '-', 'Color', [0 0.4470 0.7410], 'LineWidth', 1.5);
    ylabel('integrator');
    xlabel('Time / ms');
    legend('Step 12V', '2ms ramp', '5ms ramp', 'Location', 'northeast');
    grid on;

    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_sweep(path, sweep)
    fig = figure('Visible', 'off', 'Position', [80 80 1350 760]);
    tiledlayout(2, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    plot(sweep.ramp_time_ms, sweep.peak_inductor_current_a, '-o', 'LineWidth', 1.8, 'MarkerSize', 6);
    ylabel('Peak IL / A');
    title('软启动斜坡时间扫描：启动越慢，电流峰值越低，但到达 12V 越晚');
    grid on;

    nexttile;
    hold on;
    plot(sweep.ramp_time_ms, sweep.time_to_95pct_ms, '-o', 'LineWidth', 1.8, 'MarkerSize', 6);
    plot(sweep.ramp_time_ms, sweep.settle_time_ms, '-s', 'LineWidth', 1.8, 'MarkerSize', 6);
    xlabel('Soft-start ramp time / ms');
    ylabel('Time / ms');
    legend('Time to 95% Vout', '1% settling time', 'Location', 'northwest');
    grid on;

    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_ms(data, field, lineStyle, varargin)
    plot(data.time_s * 1000, data.(field), lineStyle, varargin{:});
end

function set_plot_defaults()
    set(groot, 'defaultAxesFontName', 'Microsoft YaHei');
    set(groot, 'defaultTextFontName', 'Microsoft YaHei');
    set(groot, 'defaultAxesFontSize', 11);
    set(groot, 'defaultLineLineWidth', 1.4);
    set(groot, 'defaultAxesGridAlpha', 0.18);
end
