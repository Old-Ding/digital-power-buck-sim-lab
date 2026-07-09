repoRoot = fileparts(fileparts(mfilename('fullpath')));
waveDir = fullfile(repoRoot, 'waveforms');

if ~exist(waveDir, 'dir')
    mkdir(waveDir);
end

set_plot_defaults();

P = params();

noLimit = simulate_case('no_limit', P);
limitNoAw = simulate_case('limit_no_aw', P);
limitAw = simulate_case('limit_aw', P);

write_trace(fullfile(waveDir, '05-matlab-duty-limit-anti-windup-trace.csv'), noLimit, limitNoAw, limitAw);
summary = write_summary(fullfile(waveDir, '05-matlab-duty-limit-anti-windup-summary.csv'), P, noLimit, limitNoAw, limitAw);

plot_overview(fullfile(waveDir, '05-matlab-duty-limit-anti-windup-overview.png'), P, noLimit, limitNoAw, limitAw);
plot_integrator(fullfile(waveDir, '05-matlab-integrator-windup-comparison.png'), P, limitNoAw, limitAw);
plot_duty_limit(fullfile(waveDir, '05-matlab-duty-raw-vs-limited.png'), P, limitNoAw, limitAw);
plot_recovery_zoom(fullfile(waveDir, '05-matlab-recovery-after-vin-return.png'), P, limitNoAw, limitAw);

fprintf('已生成第 5 章 duty 限幅和抗积分饱和仿真数据与图表。\n');
fprintf('limit_no_aw,integrator_peak=%.6g,vout_max_after_return=%.6g,saturation_exit_after_return_ms=%.6g\n', ...
    summary.limit_no_aw_integrator_peak, ...
    summary.limit_no_aw_vout_max_after_return_v, ...
    summary.limit_no_aw_saturation_exit_after_return_ms);
fprintf('limit_aw,integrator_peak=%.6g,vout_max_after_return=%.6g,saturation_exit_after_return_ms=%.6g\n', ...
    summary.limit_aw_integrator_peak, ...
    summary.limit_aw_vout_max_after_return_v, ...
    summary.limit_aw_saturation_exit_after_return_ms);

function P = params()
    P.vin_nom = 24.0;
    P.vin_sag = 20.0;
    P.vref = 12.0;
    P.rload = 2.4;
    P.l_out = 22e-6;
    P.c_out = 100e-6;
    P.fsw = 200e3;
    P.ts_ctrl = 1 / P.fsw;
    P.substeps = 10;
    P.dt = P.ts_ctrl / P.substeps;
    P.stop_time = 0.014;
    P.duty_feedforward = 0.5;
    P.r_series = 0.02;
    P.kp = 0.05;
    P.ki = 200.0;
    P.duty_min = 0.05;
    P.duty_max = 0.55;
    P.vin_drop_time = 0.003;
    P.vin_return_time = 0.006;
    nominal_current = P.vref / P.rload;
    P.initial_integrator_trim = (P.vref + nominal_current * P.r_series) / P.vin_nom - P.duty_feedforward;
    P.required_duty_at_vin_sag = (P.vref + nominal_current * P.r_series) / P.vin_sag;
end

function data = simulate_case(mode, P)
    n = round(P.stop_time / P.dt) + 1;
    data.time_s = zeros(n, 1);
    data.vin_v = zeros(n, 1);
    data.vout_v = zeros(n, 1);
    data.inductor_current_a = zeros(n, 1);
    data.error_v = zeros(n, 1);
    data.duty_raw = zeros(n, 1);
    data.duty_cmd = zeros(n, 1);
    data.integrator = zeros(n, 1);
    data.saturation = zeros(n, 1);
    data.allow_integrate = zeros(n, 1);
    data.is_sample = zeros(n, 1);

    inductor_current = P.vref / P.rload;
    vout = P.vref;
    integrator = P.initial_integrator_trim;
    error = 0.0;
    duty_raw = P.duty_feedforward + integrator;
    duty_cmd = duty_raw;
    saturation = false;
    allow_integrate = true;

    if ~strcmp(mode, 'no_limit')
        duty_cmd = clamp(duty_raw, P.duty_min, P.duty_max);
    end

    for idx = 1:n
        time_s = (idx - 1) * P.dt;
        vin = vin_profile(time_s, P);
        is_sample = mod(idx - 1, P.substeps) == 0;

        if is_sample
            error = P.vref - vout;
            p_term = P.kp * error;

            switch mode
                case 'no_limit'
                    integrator = integrator + P.ki * P.ts_ctrl * error;
                    duty_raw = P.duty_feedforward + p_term + integrator;
                    duty_cmd = duty_raw;
                    saturation = false;
                    allow_integrate = true;
                case 'limit_no_aw'
                    integrator = integrator + P.ki * P.ts_ctrl * error;
                    duty_raw = P.duty_feedforward + p_term + integrator;
                    duty_cmd = clamp(duty_raw, P.duty_min, P.duty_max);
                    saturation = abs(duty_cmd - duty_raw) > 1e-12;
                    allow_integrate = true;
                case 'limit_aw'
                    duty_raw_pre = P.duty_feedforward + p_term + integrator;
                    high_saturation = duty_raw_pre > P.duty_max;
                    low_saturation = duty_raw_pre < P.duty_min;

                    % 只在积分项能把输出从饱和方向拉回来时继续积分。
                    allow_integrate = (~high_saturation && ~low_saturation) ...
                        || (high_saturation && error < 0) ...
                        || (low_saturation && error > 0);

                    if allow_integrate
                        integrator = integrator + P.ki * P.ts_ctrl * error;
                    end

                    duty_raw = P.duty_feedforward + p_term + integrator;
                    duty_cmd = clamp(duty_raw, P.duty_min, P.duty_max);
                    saturation = abs(duty_cmd - duty_raw) > 1e-12;
                otherwise
                    error('Unknown mode: %s', mode);
            end
        end

        di_dt = (vin * duty_cmd - vout - inductor_current * P.r_series) / P.l_out;
        dv_dt = (inductor_current - vout / P.rload) / P.c_out;
        inductor_current = inductor_current + di_dt * P.dt;
        vout = vout + dv_dt * P.dt;

        data.time_s(idx) = time_s;
        data.vin_v(idx) = vin;
        data.vout_v(idx) = vout;
        data.inductor_current_a(idx) = inductor_current;
        data.error_v(idx) = error;
        data.duty_raw(idx) = duty_raw;
        data.duty_cmd(idx) = duty_cmd;
        data.integrator(idx) = integrator;
        data.saturation(idx) = double(saturation);
        data.allow_integrate(idx) = double(allow_integrate);
        data.is_sample(idx) = double(is_sample);
    end

    data.mode = mode;
end

function value = vin_profile(time_s, P)
    if time_s >= P.vin_drop_time && time_s < P.vin_return_time
        value = P.vin_sag;
    else
        value = P.vin_nom;
    end
end

function value = clamp(value, low, high)
    value = min(max(value, low), high);
end

function write_trace(path, noLimit, limitNoAw, limitAw)
    fid = fopen(path, 'w');
    cleaner = onCleanup(@() fclose(fid));
    fprintf(fid, 'case,time_s,vin_v,vout_v,inductor_current_a,error_v,duty_raw,duty_cmd,integrator,saturation,allow_integrate,is_sample\n');
    write_case(fid, noLimit);
    write_case(fid, limitNoAw);
    write_case(fid, limitAw);
end

function write_case(fid, data)
    for idx = 1:numel(data.time_s)
        fprintf(fid, '%s,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.0f,%.0f,%.0f\n', ...
            data.mode, ...
            data.time_s(idx), ...
            data.vin_v(idx), ...
            data.vout_v(idx), ...
            data.inductor_current_a(idx), ...
            data.error_v(idx), ...
            data.duty_raw(idx), ...
            data.duty_cmd(idx), ...
            data.integrator(idx), ...
            data.saturation(idx), ...
            data.allow_integrate(idx), ...
            data.is_sample(idx));
    end
end

function summary = write_summary(path, P, noLimit, limitNoAw, limitAw)
    summary.vref_v = P.vref;
    summary.fsw_hz = P.fsw;
    summary.control_period_us = P.ts_ctrl * 1e6;
    summary.kp = P.kp;
    summary.ki = P.ki;
    summary.duty_min = P.duty_min;
    summary.duty_max = P.duty_max;
    summary.duty_feedforward = P.duty_feedforward;
    summary.initial_integrator_trim = P.initial_integrator_trim;
    summary.vin_nom_v = P.vin_nom;
    summary.vin_sag_v = P.vin_sag;
    summary.vin_drop_time_ms = P.vin_drop_time * 1000;
    summary.vin_return_time_ms = P.vin_return_time * 1000;
    summary.required_duty_at_vin_sag = P.required_duty_at_vin_sag;

    summary.no_limit_duty_raw_peak = max(noLimit.duty_raw);
    summary.no_limit_vout_max_after_return_v = max_window(noLimit, 'vout_v', P.vin_return_time, P.stop_time);

    summary.limit_no_aw_vout_min_during_sag_v = min_window(limitNoAw, 'vout_v', P.vin_drop_time, P.vin_return_time);
    summary.limit_no_aw_vout_max_after_return_v = max_window(limitNoAw, 'vout_v', P.vin_return_time, P.stop_time);
    summary.limit_no_aw_integrator_peak = max(limitNoAw.integrator);
    summary.limit_no_aw_duty_raw_peak = max(limitNoAw.duty_raw);
    summary.limit_no_aw_saturation_total_ms = sum(limitNoAw.saturation > 0.5) * P.dt * 1000;
    summary.limit_no_aw_saturation_exit_after_return_ms = saturation_exit_after_return_ms(limitNoAw, P);

    summary.limit_aw_vout_min_during_sag_v = min_window(limitAw, 'vout_v', P.vin_drop_time, P.vin_return_time);
    summary.limit_aw_vout_max_after_return_v = max_window(limitAw, 'vout_v', P.vin_return_time, P.stop_time);
    summary.limit_aw_integrator_peak = max(limitAw.integrator);
    summary.limit_aw_duty_raw_peak = max(limitAw.duty_raw);
    summary.limit_aw_saturation_total_ms = sum(limitAw.saturation > 0.5) * P.dt * 1000;
    summary.limit_aw_saturation_exit_after_return_ms = saturation_exit_after_return_ms(limitAw, P);

    summary.anti_windup_overshoot_reduction_v = ...
        summary.limit_no_aw_vout_max_after_return_v - summary.limit_aw_vout_max_after_return_v;
    summary.anti_windup_integrator_peak_reduction = ...
        summary.limit_no_aw_integrator_peak - summary.limit_aw_integrator_peak;

    names = fieldnames(summary);
    fid = fopen(path, 'w');
    cleaner = onCleanup(@() fclose(fid));
    fprintf(fid, 'metric,value\n');
    for idx = 1:numel(names)
        fprintf(fid, '%s,%.12g\n', names{idx}, summary.(names{idx}));
    end
end

function value = min_window(data, field, start_s, stop_s)
    mask = data.time_s >= start_s & data.time_s < stop_s;
    value = min(data.(field)(mask));
end

function value = max_window(data, field, start_s, stop_s)
    mask = data.time_s >= start_s & data.time_s <= stop_s;
    value = max(data.(field)(mask));
end

function value = saturation_exit_after_return_ms(data, P)
    mask = data.time_s >= P.vin_return_time;
    times = data.time_s(mask);
    saturation = data.saturation(mask) > 0.5;
    value = NaN;
    for idx = 1:numel(times)
        if all(~saturation(idx:end))
            value = (times(idx) - P.vin_return_time) * 1000;
            return;
        end
    end
end

function plot_overview(path, P, noLimit, limitNoAw, limitAw)
    fig = figure('Visible', 'off', 'Color', 'w', 'Position', [100 100 1280 860]);
    tiledlayout(3, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    plot_signal(noLimit.time_s * 1000, noLimit.vout_v, [0.55 0.55 0.55], 'No duty limit');
    hold on;
    plot_signal(limitNoAw.time_s * 1000, limitNoAw.vout_v, [0.85 0.325 0.098], 'Limit only');
    plot_signal(limitAw.time_s * 1000, limitAw.vout_v, [0 0.447 0.741], 'Limit + anti-windup');
    yline(P.vref, '--', 'Color', [0.25 0.25 0.25], 'HandleVisibility', 'off');
    add_events(P);
    title('MATLAB 仿真：duty 限幅后，抗积分饱和明显降低 Vin 恢复后的过冲');
    ylabel('Vout / V');
    legend('Location', 'northeast');
    grid on;

    nexttile;
    plot_signal(limitNoAw.time_s * 1000, limitNoAw.duty_cmd, [0.85 0.325 0.098], 'Limit only duty');
    hold on;
    plot_signal(limitAw.time_s * 1000, limitAw.duty_cmd, [0 0.447 0.741], 'Anti-windup duty');
    yline(P.duty_max, '--', 'Color', [0.25 0.25 0.25], 'HandleVisibility', 'off');
    text(6.25, P.duty_max + 0.006, 'duty max = 0.55', 'Color', [0.25 0.25 0.25]);
    add_events(P);
    ylabel('duty cmd');
    legend('Location', 'southeast');
    grid on;

    nexttile;
    plot_signal(limitAw.time_s * 1000, limitAw.vin_v, [0.494 0.184 0.556], 'Vin');
    add_events(P);
    ylabel('Vin / V');
    xlabel('Time / ms');
    grid on;
    xlim([0 P.stop_time * 1000]);

    add_source_stamp(fig);
    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_integrator(path, P, limitNoAw, limitAw)
    fig = figure('Visible', 'off', 'Color', 'w', 'Position', [100 100 1200 720]);
    tiledlayout(2, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    plot_signal(limitNoAw.time_s * 1000, limitNoAw.integrator, [0.85 0.325 0.098], 'Limit only integrator');
    hold on;
    plot_signal(limitAw.time_s * 1000, limitAw.integrator, [0 0.447 0.741], 'Anti-windup integrator');
    add_saturation_band(P);
    add_events(P);
    title('积分项是有记忆的状态量，限幅时继续累加会形成 windup');
    ylabel('integrator');
    legend('Location', 'northwest');
    grid on;

    nexttile;
    plot_signal(limitNoAw.time_s * 1000, limitNoAw.saturation, [0.85 0.325 0.098], 'Limit only saturation');
    hold on;
    plot_signal(limitAw.time_s * 1000, limitAw.saturation, [0 0.447 0.741], 'Anti-windup saturation');
    add_events(P);
    ylim([-0.08 1.15]);
    ylabel('saturation flag');
    xlabel('Time / ms');
    legend('Location', 'northeast');
    grid on;

    add_source_stamp(fig);
    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_duty_limit(path, P, limitNoAw, limitAw)
    fig = figure('Visible', 'off', 'Color', 'w', 'Position', [100 100 1260 760]);
    tiledlayout(2, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    plot_signal(limitNoAw.time_s * 1000, limitNoAw.duty_raw, [0.85 0.325 0.098], 'raw duty');
    hold on;
    plot_signal(limitNoAw.time_s * 1000, limitNoAw.duty_cmd, [0.1 0.1 0.1], 'limited duty');
    yline(P.duty_max, '--', 'Color', [0.25 0.25 0.25], 'HandleVisibility', 'off');
    add_events(P);
    title('只加 duty 限幅：raw duty 继续上冲，实际 duty 被卡在上限');
    ylabel('limit only');
    legend('Location', 'northwest');
    grid on;

    nexttile;
    plot_signal(limitAw.time_s * 1000, limitAw.duty_raw, [0 0.447 0.741], 'raw duty');
    hold on;
    plot_signal(limitAw.time_s * 1000, limitAw.duty_cmd, [0.1 0.1 0.1], 'limited duty');
    yline(P.duty_max, '--', 'Color', [0.25 0.25 0.25], 'HandleVisibility', 'off');
    add_events(P);
    title('加入抗积分饱和：raw duty 不再远离 duty 上限');
    ylabel('anti-windup');
    xlabel('Time / ms');
    legend('Location', 'northwest');
    grid on;

    add_source_stamp(fig);
    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_recovery_zoom(path, P, limitNoAw, limitAw)
    fig = figure('Visible', 'off', 'Color', 'w', 'Position', [100 100 1200 760]);
    tiledlayout(2, 1, 'TileSpacing', 'compact', 'Padding', 'compact');
    start_ms = (P.vin_return_time - 0.0004) * 1000;
    stop_ms = (P.vin_return_time + 0.0045) * 1000;

    nexttile;
    plot_signal(limitNoAw.time_s * 1000, limitNoAw.vout_v, [0.85 0.325 0.098], 'Limit only');
    hold on;
    plot_signal(limitAw.time_s * 1000, limitAw.vout_v, [0 0.447 0.741], 'Limit + anti-windup');
    yline(P.vref, '--', 'Color', [0.25 0.25 0.25], 'HandleVisibility', 'off');
    xline(P.vin_return_time * 1000, '--', 'Color', [0.35 0.35 0.35], 'HandleVisibility', 'off');
    title('Vin 恢复后，windup 会让 duty 继续顶在上限，造成更高过冲');
    ylabel('Vout / V');
    xlim([start_ms stop_ms]);
    legend('Location', 'northeast');
    grid on;

    nexttile;
    plot_signal(limitNoAw.time_s * 1000, limitNoAw.integrator, [0.85 0.325 0.098], 'Limit only integrator');
    hold on;
    plot_signal(limitAw.time_s * 1000, limitAw.integrator, [0 0.447 0.741], 'Anti-windup integrator');
    xline(P.vin_return_time * 1000, '--', 'Color', [0.35 0.35 0.35], 'HandleVisibility', 'off');
    ylabel('integrator');
    xlabel('Time / ms');
    xlim([start_ms stop_ms]);
    legend('Location', 'northeast');
    grid on;

    add_source_stamp(fig);
    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_signal(x, y, color, name)
    plot(x, y, 'LineWidth', 1.65, 'Color', color, 'DisplayName', name);
end

function add_events(P)
    xline(P.vin_drop_time * 1000, '--', 'Color', [0.35 0.35 0.35], 'HandleVisibility', 'off');
    xline(P.vin_return_time * 1000, '--', 'Color', [0.45 0.45 0.45], 'HandleVisibility', 'off');
end

function add_saturation_band(P)
    ax = gca;
    yl = ylim(ax);
    patch(ax, ...
        [P.vin_drop_time P.vin_return_time P.vin_return_time P.vin_drop_time] * 1000, ...
        [yl(1) yl(1) yl(2) yl(2)], ...
        [0.996 0.906 0.784], ...
        'EdgeColor', 'none', ...
        'FaceAlpha', 0.32, ...
        'HandleVisibility', 'off');
end

function add_source_stamp(fig)
    annotation(fig, 'textbox', [0.74 0.945 0.22 0.025], ...
        'String', 'Source: MATLAB avg model', ...
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
end
