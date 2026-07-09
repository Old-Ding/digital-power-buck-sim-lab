repoRoot = fileparts(fileparts(mfilename('fullpath')));
waveDir = fullfile(repoRoot, 'waveforms');

if ~exist(waveDir, 'dir')
    mkdir(waveDir);
end

set_plot_defaults();

P = params();

idealP = P;
idealP.case_id = "ideal_adc";
idealP.adc_noise_enabled = false;
idealP.filter_mode = "none";
idealP.filter_delay_s = 0;
ideal = simulate_case(idealP, 9);

noisyP = P;
noisyP.case_id = "noisy_adc";
noisyP.adc_noise_enabled = true;
noisyP.filter_mode = "none";
noisyP.filter_delay_s = 0;
noisy = simulate_case(noisyP, 9);

movingAvgP = P;
movingAvgP.case_id = "moving_average_4";
movingAvgP.adc_noise_enabled = true;
movingAvgP.filter_mode = "moving_average_4";
movingAvgP.filter_delay_s = ((P.moving_average_points - 1) / 2) * P.ts_ctrl;
movingAvg = simulate_case(movingAvgP, 9);

iirP = P;
iirP.case_id = "iir_alpha_0p25";
iirP.adc_noise_enabled = true;
iirP.filter_mode = "iir_alpha_0p25";
iirP.filter_delay_s = ((1 - P.iir_alpha) / P.iir_alpha) * P.ts_ctrl;
iir = simulate_case(iirP, 9);

cases = {ideal, noisy, movingAvg, iir};
write_trace(fullfile(waveDir, '09-matlab-adc-noise-duty-jitter-trace.csv'), cases{:});
summary = build_summary(P, cases{:});
writetable(summary, fullfile(waveDir, '09-matlab-adc-noise-duty-jitter-summary.csv'));

plot_overview(fullfile(waveDir, '09-matlab-adc-noise-duty-jitter-overview.png'), P, noisy);
plot_comparison(fullfile(waveDir, '09-matlab-adc-noise-duty-jitter-comparison.png'), P, cases{:});
plot_filter_tradeoff(fullfile(waveDir, '09-matlab-adc-noise-filter-tradeoff.png'), P, noisy, movingAvg, iir);

fprintf('已生成第 9 章 ADC 噪声与 duty 抖动仿真数据与图表。\n');
fprintf('noisy_adc,duty_rms_jitter=%.6g,equiv_pwm_rms_jitter_ns=%.6g,measured_noise_rms_mv=%.6g\n', ...
    metric_value(summary, "noisy_adc_duty_cmd_rms_jitter"), ...
    metric_value(summary, "noisy_adc_equivalent_pwm_rms_jitter_ns"), ...
    metric_value(summary, "noisy_adc_vout_measured_rms_noise_mv"));
fprintf('moving_average_4,duty_rms_jitter=%.6g,reduction_pct=%.6g,delay_us=%.6g\n', ...
    metric_value(summary, "moving_average_4_duty_cmd_rms_jitter"), ...
    metric_value(summary, "moving_average_4_duty_jitter_reduction_percent"), ...
    metric_value(summary, "moving_average_4_filter_delay_us"));
fprintf('iir_alpha_0p25,duty_rms_jitter=%.6g,reduction_pct=%.6g,delay_us=%.6g\n', ...
    metric_value(summary, "iir_alpha_0p25_duty_cmd_rms_jitter"), ...
    metric_value(summary, "iir_alpha_0p25_duty_jitter_reduction_percent"), ...
    metric_value(summary, "iir_alpha_0p25_filter_delay_us"));

function P = params()
    P.vin_nom = 24.0;
    P.vref = 12.0;
    P.rload = 2.4;
    P.l_out = 22e-6;
    P.c_out = 100e-6;
    P.r_series = 0.02;
    P.fsw = 200e3;
    P.ts_ctrl = 1 / P.fsw;
    P.substeps = 10;
    P.dt = P.ts_ctrl / P.substeps;
    P.stop_time = 0.020;
    P.analysis_start_s = 0.005;
    P.kp = 0.02;
    P.ki = 80.0;
    P.duty_feedforward = 0.5;
    P.duty_min = 0.05;
    P.duty_max = 0.65;
    P.adc_bits = 12;
    P.adc_full_scale_v = 16.0;
    P.adc_lsb_v = P.adc_full_scale_v / (2 ^ P.adc_bits);
    P.adc_noise_rms_v = 0.015;
    P.moving_average_points = 4;
    P.iir_alpha = 0.25;
    nominalCurrent = P.vref / P.rload;
    P.initial_integrator_trim = (P.vref + nominalCurrent * P.r_series) / P.vin_nom - P.duty_feedforward;
end

function data = simulate_case(P, seed)
    rng(seed, 'twister');

    n = round(P.stop_time / P.dt) + 1;
    data.time_s = zeros(n, 1);
    data.vout_actual_v = zeros(n, 1);
    data.vout_adc_v = zeros(n, 1);
    data.vout_measured_v = zeros(n, 1);
    data.adc_error_v = zeros(n, 1);
    data.inductor_current_a = zeros(n, 1);
    data.error_v = zeros(n, 1);
    data.duty_raw = zeros(n, 1);
    data.duty_cmd = zeros(n, 1);
    data.integrator = zeros(n, 1);
    data.saturation = zeros(n, 1);
    data.allow_integrate = zeros(n, 1);
    data.is_sample = zeros(n, 1);

    inductorCurrent = P.vref / P.rload;
    vout = P.vref;
    integrator = P.initial_integrator_trim;
    error = 0;
    dutyRaw = P.duty_feedforward + integrator;
    dutyCmd = clamp(dutyRaw, P.duty_min, P.duty_max);
    saturation = false;
    allowIntegrate = true;

    movingBuffer = P.vref * ones(P.moving_average_points, 1);
    movingIndex = 1;
    iirState = P.vref;
    voutAdc = P.vref;
    voutMeasured = P.vref;
    adcError = 0;

    for idx = 1:n
        time_s = (idx - 1) * P.dt;
        isSample = mod(idx - 1, P.substeps) == 0;

        if isSample
            voutAdc = sample_adc(vout, P);
            adcError = voutAdc - vout;

            switch P.filter_mode
                case "none"
                    voutMeasured = voutAdc;
                case "moving_average_4"
                    movingBuffer(movingIndex) = voutAdc;
                    movingIndex = movingIndex + 1;
                    if movingIndex > P.moving_average_points
                        movingIndex = 1;
                    end
                    voutMeasured = mean(movingBuffer);
                case "iir_alpha_0p25"
                    iirState = P.iir_alpha * voutAdc + (1 - P.iir_alpha) * iirState;
                    voutMeasured = iirState;
                otherwise
                    error('Unknown filter mode: %s', P.filter_mode);
            end

            error = P.vref - voutMeasured;
            pTerm = P.kp * error;
            dutyRawPre = P.duty_feedforward + pTerm + integrator;

            highSaturation = dutyRawPre > P.duty_max;
            lowSaturation = dutyRawPre < P.duty_min;

            % 只有职责层是积分器更新：限幅时只允许误差把积分项往退出饱和方向拉。
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

        loadCurrent = vout / P.rload;
        diDt = (P.vin_nom * dutyCmd - vout - inductorCurrent * P.r_series) / P.l_out;
        dvDt = (inductorCurrent - loadCurrent) / P.c_out;
        inductorCurrent = inductorCurrent + diDt * P.dt;
        vout = vout + dvDt * P.dt;

        data.time_s(idx) = time_s;
        data.vout_actual_v(idx) = vout;
        data.vout_adc_v(idx) = voutAdc;
        data.vout_measured_v(idx) = voutMeasured;
        data.adc_error_v(idx) = adcError;
        data.inductor_current_a(idx) = inductorCurrent;
        data.error_v(idx) = error;
        data.duty_raw(idx) = dutyRaw;
        data.duty_cmd(idx) = dutyCmd;
        data.integrator(idx) = integrator;
        data.saturation(idx) = double(saturation);
        data.allow_integrate(idx) = double(allowIntegrate);
        data.is_sample(idx) = double(isSample);
    end

    data.case_id = P.case_id;
    data.params = P;
end

function value = sample_adc(vout, P)
    if P.adc_noise_enabled
        analogValue = vout + P.adc_noise_rms_v * randn();
    else
        analogValue = vout;
    end

    adcCode = round(clamp(analogValue, 0, P.adc_full_scale_v) / P.adc_lsb_v);
    value = adcCode * P.adc_lsb_v;
end

function value = clamp(value, low, high)
    value = min(max(value, low), high);
end

function write_trace(path, varargin)
    fid = fopen(path, 'w');
    cleaner = onCleanup(@() fclose(fid));
    fprintf(fid, 'case,time_s,vout_actual_v,vout_adc_v,vout_measured_v,adc_error_v,inductor_current_a,error_v,duty_raw,duty_cmd,integrator,saturation,allow_integrate,is_sample\n');
    for caseIdx = 1:numel(varargin)
        write_case(fid, varargin{caseIdx});
    end
end

function write_case(fid, data)
    for idx = 1:numel(data.time_s)
        if data.is_sample(idx) < 0.5
            continue;
        end
        fprintf(fid, '%s,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.10g,%.0f,%.0f,%.0f\n', ...
            data.case_id, ...
            data.time_s(idx), ...
            data.vout_actual_v(idx), ...
            data.vout_adc_v(idx), ...
            data.vout_measured_v(idx), ...
            data.adc_error_v(idx), ...
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

function summary = build_summary(baseP, varargin)
    metric = strings(0, 1);
    value = zeros(0, 1);
    note = strings(0, 1);

    [metric, value, note] = add_metric(metric, value, note, "vref_v", baseP.vref, "");
    [metric, value, note] = add_metric(metric, value, note, "vin_nom_v", baseP.vin_nom, "");
    [metric, value, note] = add_metric(metric, value, note, "fsw_hz", baseP.fsw, "");
    [metric, value, note] = add_metric(metric, value, note, "control_period_us", baseP.ts_ctrl * 1e6, "");
    [metric, value, note] = add_metric(metric, value, note, "adc_bits", baseP.adc_bits, "");
    [metric, value, note] = add_metric(metric, value, note, "adc_full_scale_v", baseP.adc_full_scale_v, "output-voltage equivalent full-scale");
    [metric, value, note] = add_metric(metric, value, note, "adc_lsb_mv", baseP.adc_lsb_v * 1e3, "output-voltage equivalent LSB");
    [metric, value, note] = add_metric(metric, value, note, "adc_noise_rms_mv", baseP.adc_noise_rms_v * 1e3, "Gaussian noise before quantization");
    [metric, value, note] = add_metric(metric, value, note, "analysis_start_ms", baseP.analysis_start_s * 1000, "");

    noisyJitter = NaN;
    for idx = 1:numel(varargin)
        data = varargin{idx};
        if data.case_id == "noisy_adc"
            metrics = case_metrics(data);
            noisyJitter = metrics.duty_cmd_rms_jitter;
            break;
        end
    end

    for idx = 1:numel(varargin)
        data = varargin{idx};
        metrics = case_metrics(data);
        names = fieldnames(metrics);
        for nameIdx = 1:numel(names)
            [metric, value, note] = add_metric(metric, value, note, data.case_id + "_" + names{nameIdx}, metrics.(names{nameIdx}), "");
        end

        if ~isnan(noisyJitter) && data.case_id ~= "noisy_adc"
            reduction = (1 - metrics.duty_cmd_rms_jitter / noisyJitter) * 100;
            [metric, value, note] = add_metric(metric, value, note, data.case_id + "_duty_jitter_reduction_percent", reduction, "relative to noisy_adc");
        elseif data.case_id == "noisy_adc"
            [metric, value, note] = add_metric(metric, value, note, data.case_id + "_duty_jitter_reduction_percent", 0, "baseline");
        end
    end

    summary = table(metric, value, note);
end

function metrics = case_metrics(data)
    P = data.params;
    mask = data.time_s >= P.analysis_start_s & data.is_sample > 0.5;
    actual = data.vout_actual_v(mask);
    measured = data.vout_measured_v(mask);
    adcError = data.vout_adc_v(mask) - actual;
    measurementError = measured - actual;
    errorSignal = data.error_v(mask);
    dutyRaw = data.duty_raw(mask);
    dutyCmd = data.duty_cmd(mask);

    metrics.vout_measured_rms_noise_mv = rms_local(measurementError) * 1e3;
    metrics.adc_raw_rms_noise_mv = rms_local(adcError) * 1e3;
    metrics.error_rms_mv = rms_local(errorSignal) * 1e3;
    metrics.vout_actual_rms_jitter_mv = std(actual) * 1e3;
    metrics.duty_raw_rms_jitter = std(dutyRaw);
    metrics.duty_cmd_rms_jitter = std(dutyCmd);
    metrics.duty_cmd_peak_to_peak = max(dutyCmd) - min(dutyCmd);
    metrics.equivalent_pwm_rms_jitter_ns = metrics.duty_cmd_rms_jitter * P.ts_ctrl * 1e9;
    metrics.equivalent_pwm_peak_to_peak_ns = metrics.duty_cmd_peak_to_peak * P.ts_ctrl * 1e9;
    metrics.duty_cmd_mean = mean(dutyCmd);
    metrics.duty_cmd_min = min(dutyCmd);
    metrics.duty_cmd_max = max(dutyCmd);
    metrics.filter_delay_us = P.filter_delay_s * 1e6;
end

function value = rms_local(x)
    value = sqrt(mean(x .^ 2));
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
    fig = figure('Visible', 'off', 'Color', 'w', 'Position', [80 80 1400 900]);
    tiledlayout(3, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    hold on;
    plot_ms(data, 'vout_actual_v', [0.10 0.38 0.66], 'actual Vout');
    plot_ms(data, 'vout_measured_v', [0.85 0.325 0.098], 'ADC measured Vout');
    yline(P.vref, '--', '12V target', 'Color', [0.35 0.35 0.35], 'HandleVisibility', 'off');
    title('ADC 采样噪声进入反馈链路：真实 Vout 很平，测量值在抖');
    ylabel('Vout / V');
    xlim([6 9]);
    legend('Location', 'northeast');
    grid on;

    nexttile;
    hold on;
    plot_ms(data, 'error_v', [0.494 0.184 0.556], 'error = Vref - Vmeas');
    yline(0, '--', 'Color', [0.35 0.35 0.35], 'HandleVisibility', 'off');
    ylabel('Error / V');
    xlim([6 9]);
    legend('Location', 'northeast');
    grid on;

    nexttile;
    hold on;
    plot_ms(data, 'duty_raw', [0.55 0.55 0.55], 'raw duty');
    plot_ms(data, 'duty_cmd', [0.10 0.38 0.66], 'duty cmd');
    ylabel('Duty');
    xlabel('Time / ms');
    xlim([6 9]);
    legend('Location', 'northeast');
    grid on;

    add_source_stamp(fig);
    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_comparison(path, P, ideal, noisy, movingAvg, iir)
    fig = figure('Visible', 'off', 'Color', 'w', 'Position', [80 80 1400 950]);
    tiledlayout(3, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    hold on;
    plot_ms(ideal, 'duty_cmd', [0.55 0.55 0.55], 'ideal ADC');
    plot_ms(noisy, 'duty_cmd', [0.85 0.325 0.098], 'noisy ADC');
    plot_ms(movingAvg, 'duty_cmd', [0.10 0.38 0.66], 'moving average 4');
    plot_ms(iir, 'duty_cmd', [0.20 0.55 0.30], 'IIR alpha 0.25');
    title('同一组 ADC 噪声下，不同测量链路对应的 duty 抖动');
    ylabel('Duty cmd');
    xlim([6 10]);
    legend('Location', 'northeast');
    grid on;

    labels = categorical({'ideal', 'noisy', 'MA4', 'IIR'});
    labels = reordercats(labels, {'ideal', 'noisy', 'MA4', 'IIR'});
    jitter = [case_metrics(ideal).duty_cmd_rms_jitter, ...
        case_metrics(noisy).duty_cmd_rms_jitter, ...
        case_metrics(movingAvg).duty_cmd_rms_jitter, ...
        case_metrics(iir).duty_cmd_rms_jitter];
    pwmNs = jitter * P.ts_ctrl * 1e9;

    nexttile;
    bar(labels, jitter, 0.58, 'FaceColor', [0.10 0.38 0.66]);
    ylabel('RMS duty jitter');
    grid on;

    nexttile;
    bar(labels, pwmNs, 0.58, 'FaceColor', [0.20 0.55 0.30]);
    ylabel('Equivalent PWM RMS jitter / ns');
    xlabel('Case');
    grid on;

    add_source_stamp(fig);
    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_filter_tradeoff(path, P, noisy, movingAvg, iir)
    fig = figure('Visible', 'off', 'Color', 'w', 'Position', [80 80 1400 920]);
    tiledlayout(3, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    hold on;
    plot_ms(noisy, 'vout_measured_v', [0.85 0.325 0.098], 'no filter');
    plot_ms(movingAvg, 'vout_measured_v', [0.10 0.38 0.66], 'moving average 4');
    plot_ms(iir, 'vout_measured_v', [0.20 0.55 0.30], 'IIR alpha 0.25');
    yline(P.vref, '--', 'Color', [0.35 0.35 0.35], 'HandleVisibility', 'off');
    title('滤波能压低测量噪声，但会把反馈信号变慢');
    ylabel('Vmeas / V');
    xlim([6 9]);
    legend('Location', 'northeast');
    grid on;

    nexttile;
    hold on;
    plot_ms(noisy, 'duty_cmd', [0.85 0.325 0.098], 'no filter duty');
    plot_ms(movingAvg, 'duty_cmd', [0.10 0.38 0.66], 'moving average duty');
    plot_ms(iir, 'duty_cmd', [0.20 0.55 0.30], 'IIR duty');
    ylabel('Duty cmd');
    xlim([6 9]);
    legend('Location', 'northeast');
    grid on;

    nexttile;
    names = categorical({'no filter', 'MA4', 'IIR'});
    names = reordercats(names, {'no filter', 'MA4', 'IIR'});
    errorRms = [case_metrics(noisy).error_rms_mv, ...
        case_metrics(movingAvg).error_rms_mv, ...
        case_metrics(iir).error_rms_mv];
    delayUs = [case_metrics(noisy).filter_delay_us, ...
        case_metrics(movingAvg).filter_delay_us, ...
        case_metrics(iir).filter_delay_us];
    yyaxis left;
    bar(names, errorRms, 0.5, 'FaceColor', [0.10 0.38 0.66]);
    ylabel('Error RMS / mV');
    yyaxis right;
    plot(names, delayUs, '-o', 'LineWidth', 1.7, 'Color', [0.85 0.325 0.098], 'MarkerFaceColor', [0.85 0.325 0.098]);
    ylabel('Approx. filter delay / us');
    xlabel('Measurement path');
    grid on;

    add_source_stamp(fig);
    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_ms(data, field, color, name)
    sampleMask = data.is_sample > 0.5;
    plot(data.time_s(sampleMask) * 1000, data.(field)(sampleMask), ...
        'LineWidth', 1.55, 'Color', color, 'DisplayName', name);
end

function add_source_stamp(fig)
    annotation(fig, 'textbox', [0.70 0.945 0.26 0.025], ...
        'String', 'Source: MATLAB averaged Buck + ADC model', ...
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
