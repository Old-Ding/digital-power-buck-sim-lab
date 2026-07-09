repoRoot = fileparts(fileparts(mfilename('fullpath')));
waveDir = fullfile(repoRoot, 'waveforms');

if ~exist(waveDir, 'dir')
    mkdir(waveDir);
end

set_plot_defaults();

P = params();
runFault = simulate_run_fault(P);
clearWhileFault = simulate_clear_while_fault(P);
priorityCases = run_priority_cases(P);

writetable(runFault, fullfile(waveDir, '07-matlab-protection-state-machine-trace.csv'));
writetable(clearWhileFault, fullfile(waveDir, '07-matlab-protection-clear-while-fault-trace.csv'));
writetable(priorityCases, fullfile(waveDir, '07-matlab-protection-priority-cases.csv'));

summary = build_summary(P, runFault, clearWhileFault, priorityCases);
writetable(summary, fullfile(waveDir, '07-matlab-protection-state-machine-summary.csv'));

plot_run_fault(fullfile(waveDir, '07-matlab-protection-state-machine-overview.png'), runFault);
plot_clear_while_fault(fullfile(waveDir, '07-matlab-protection-latch-clear.png'), clearWhileFault);
plot_priority(fullfile(waveDir, '07-matlab-protection-priority.png'), priorityCases);

fprintf('已生成第 7 章保护状态机故障注入数据与图表。\n');
fprintf('run_fault,first_fault_ms=%.6g,pwm_off_delay_us=%.6g,latched_fault=%s\n', ...
    summary.value(strcmp(summary.metric, "run_fault_first_fault_ms")), ...
    summary.value(strcmp(summary.metric, "run_fault_pwm_off_delay_us")), ...
    summary.note(strcmp(summary.metric, "run_fault_latched_fault")));
fprintf('clear_while_fault,ignored_clear_ms=%.6g,recovery_ms=%.6g\n', ...
    summary.value(strcmp(summary.metric, "clear_while_fault_ignored_clear_ms")), ...
    summary.value(strcmp(summary.metric, "clear_while_fault_recovery_ms")));

function P = params()
    P.ts = 50e-6;
    P.stop_time = 0.024;
    P.vtarget = 12.0;
    P.soft_start_time = 0.005;
    P.vin_nom = 24.0;
    P.iout_nom = 5.0;
    P.temp_nom = 35.0;
    P.uvlo_v = 18.0;
    P.ovp_v = 13.2;
    P.ocp_a = 6.5;
    P.otp_c = 95.0;
end

function data = simulate_run_fault(P)
    data = simulate_case("run_ocp_fault", P, @run_fault_measurements, @run_fault_command);

    function m = run_fault_measurements(t, ~)
        m.vin_v = P.vin_nom;
        m.vout_v = P.vtarget;
        m.iout_a = P.iout_nom;
        m.temperature_c = P.temp_nom;
        if t >= 0.008 && t < 0.009
            m.iout_a = 7.2;
        end
    end

    function command = run_fault_command(t, ~)
        if abs(t - 0.012) < P.ts / 2
            command = "CLEAR_FAULT";
        elseif t >= 0.0005 && (t < 0.011 || t >= 0.014)
            command = "ENABLE";
        else
            command = "NONE";
        end
    end
end

function data = simulate_clear_while_fault(P)
    data = simulate_case("clear_while_ovp_active", P, @clear_fault_measurements, @clear_fault_command);

    function m = clear_fault_measurements(t, ~)
        m.vin_v = P.vin_nom;
        m.vout_v = P.vtarget;
        m.iout_a = P.iout_nom;
        m.temperature_c = P.temp_nom;
        if t >= 0.006 && t < 0.011
            m.vout_v = 14.0;
        end
    end

    function command = clear_fault_command(t, ~)
        if abs(t - 0.008) < P.ts / 2 || abs(t - 0.012) < P.ts / 2
            command = "CLEAR_FAULT";
        elseif t >= 0.0005
            command = "ENABLE";
        else
            command = "NONE";
        end
    end
end

function data = simulate_case(caseName, P, measurement_fn, command_fn)
    n = round(P.stop_time / P.ts) + 1;
    time_s = zeros(n, 1);
    case_id = strings(n, 1);
    command = strings(n, 1);
    state_name = strings(n, 1);
    fault_detected = strings(n, 1);
    fault_latched = strings(n, 1);
    vin_v = zeros(n, 1);
    vout_v = zeros(n, 1);
    iout_a = zeros(n, 1);
    temperature_c = zeros(n, 1);
    vref_cmd_v = zeros(n, 1);
    duty_cmd = zeros(n, 1);
    pwm_enable = zeros(n, 1);
    soft_start_elapsed_ms = zeros(n, 1);
    state_code = zeros(n, 1);
    fault_detected_code = zeros(n, 1);
    fault_latched_code = zeros(n, 1);

    state = "INIT";
    latched = "NONE";
    softElapsed = 0.0;

    for idx = 1:n
        t = (idx - 1) * P.ts;
        m = measurement_fn(t, state);
        detected = protection_check(m, P);
        cmd = command_fn(t, state);
        [state, latched, softElapsed] = state_machine_step(state, latched, softElapsed, cmd, detected, P);
        [vref, duty, pwm] = output_control(state, softElapsed, P);

        time_s(idx) = t;
        case_id(idx) = caseName;
        command(idx) = cmd;
        state_name(idx) = state;
        fault_detected(idx) = detected;
        fault_latched(idx) = latched;
        vin_v(idx) = m.vin_v;
        vout_v(idx) = m.vout_v;
        iout_a(idx) = m.iout_a;
        temperature_c(idx) = m.temperature_c;
        vref_cmd_v(idx) = vref;
        duty_cmd(idx) = duty;
        pwm_enable(idx) = pwm;
        soft_start_elapsed_ms(idx) = softElapsed * 1000;
        state_code(idx) = state_to_code(state);
        fault_detected_code(idx) = fault_to_code(detected);
        fault_latched_code(idx) = fault_to_code(latched);
    end

    data = table(case_id, time_s, command, state_name, state_code, fault_detected, ...
        fault_detected_code, fault_latched, fault_latched_code, vin_v, vout_v, ...
        iout_a, temperature_c, vref_cmd_v, duty_cmd, pwm_enable, ...
        soft_start_elapsed_ms);
end

function fault = protection_check(m, P)
    % 故障优先级集中在保护层，状态机只消费保护层给出的唯一故障码。
    if m.iout_a > P.ocp_a
        fault = "OCP";
    elseif m.vout_v > P.ovp_v
        fault = "OVP";
    elseif m.vin_v < P.uvlo_v
        fault = "UVLO";
    elseif m.temperature_c > P.otp_c
        fault = "OTP";
    else
        fault = "NONE";
    end
end

function [state, latched, softElapsed] = state_machine_step(state, latched, softElapsed, command, detected, P)
    if detected ~= "NONE"
        state = "FAULT_LATCH";
        latched = detected;
        softElapsed = 0.0;
        return;
    end

    switch state
        case "INIT"
            state = "IDLE";
            softElapsed = 0.0;
        case "IDLE"
            softElapsed = 0.0;
            if command == "ENABLE"
                state = "SOFT_START";
            end
        case "SOFT_START"
            if command == "NONE"
                state = "IDLE";
                softElapsed = 0.0;
            else
                softElapsed = min(P.soft_start_time, softElapsed + P.ts);
                if softElapsed >= P.soft_start_time
                    state = "RUN";
                end
            end
        case "RUN"
            if command == "NONE"
                state = "IDLE";
                softElapsed = 0.0;
            end
        case "FAULT_LATCH"
            softElapsed = 0.0;
            if command == "CLEAR_FAULT"
                state = "RECOVERY";
                latched = "NONE";
            end
        case "RECOVERY"
            state = "IDLE";
            softElapsed = 0.0;
        otherwise
            state = "INIT";
            latched = "NONE";
            softElapsed = 0.0;
    end
end

function [vref, duty, pwm] = output_control(state, softElapsed, P)
    switch state
        case "SOFT_START"
            vref = min(P.vtarget, P.vtarget * softElapsed / P.soft_start_time);
            duty = vref / P.vin_nom;
            pwm = 1;
        case "RUN"
            vref = P.vtarget;
            duty = P.vtarget / P.vin_nom;
            pwm = 1;
        otherwise
            vref = 0.0;
            duty = 0.0;
            pwm = 0;
    end
end

function cases = run_priority_cases(P)
    ids = ["normal"; "uvlo_only"; "ovp_only"; "ocp_only"; "otp_only"; ...
        "ocp_ovp_uvlo"; "ovp_uvlo"; "uvlo_otp"];
    vin_v = [24; 16; 24; 24; 24; 16; 16; 16];
    vout_v = [12; 12; 14; 12; 12; 14; 14; 12];
    iout_a = [5; 5; 5; 7.2; 5; 7.2; 5; 5];
    temperature_c = [35; 35; 35; 35; 105; 35; 35; 105];
    detected_fault = strings(numel(ids), 1);
    detected_fault_code = zeros(numel(ids), 1);

    for idx = 1:numel(ids)
        m.vin_v = vin_v(idx);
        m.vout_v = vout_v(idx);
        m.iout_a = iout_a(idx);
        m.temperature_c = temperature_c(idx);
        detected_fault(idx) = protection_check(m, P);
        detected_fault_code(idx) = fault_to_code(detected_fault(idx));
    end

    cases = table(ids, vin_v, vout_v, iout_a, temperature_c, ...
        detected_fault, detected_fault_code, ...
        'VariableNames', {'case_id', 'vin_v', 'vout_v', 'iout_a', ...
        'temperature_c', 'detected_fault', 'detected_fault_code'});
end

function summary = build_summary(P, runFault, clearWhileFault, priorityCases)
    metrics = strings(0, 1);
    values = zeros(0, 1);
    notes = strings(0, 1);

    [metrics, values, notes] = add_metric(metrics, values, notes, "soft_start_time_ms", P.soft_start_time * 1000, "");
    [metrics, values, notes] = add_metric(metrics, values, notes, "ocp_threshold_a", P.ocp_a, "");
    [metrics, values, notes] = add_metric(metrics, values, notes, "ovp_threshold_v", P.ovp_v, "");
    [metrics, values, notes] = add_metric(metrics, values, notes, "uvlo_threshold_v", P.uvlo_v, "");

    firstFaultIdx = find(runFault.fault_detected ~= "NONE", 1, 'first');
    firstPwmOffIdx = find(runFault.time_s >= runFault.time_s(firstFaultIdx) & runFault.pwm_enable == 0, 1, 'first');
    recoveryIdx = find(runFault.state_name == "RECOVERY", 1, 'first');
    rerunIdx = find(runFault.time_s > 0.014 & runFault.state_name == "RUN", 1, 'first');
    [metrics, values, notes] = add_metric(metrics, values, notes, "run_fault_first_fault_ms", runFault.time_s(firstFaultIdx) * 1000, "");
    [metrics, values, notes] = add_metric(metrics, values, notes, "run_fault_pwm_off_delay_us", (runFault.time_s(firstPwmOffIdx) - runFault.time_s(firstFaultIdx)) * 1e6, "");
    [metrics, values, notes] = add_metric(metrics, values, notes, "run_fault_recovery_ms", runFault.time_s(recoveryIdx) * 1000, "");
    [metrics, values, notes] = add_metric(metrics, values, notes, "run_fault_rerun_ms", runFault.time_s(rerunIdx) * 1000, "");
    [metrics, values, notes] = add_metric(metrics, values, notes, "run_fault_latched_fault", NaN, runFault.fault_latched(firstFaultIdx));

    firstOvpIdx = find(clearWhileFault.fault_detected == "OVP", 1, 'first');
    ignoredClearIdx = find(clearWhileFault.command == "CLEAR_FAULT" & clearWhileFault.fault_detected == "OVP", 1, 'first');
    clearRecoveryIdx = find(clearWhileFault.state_name == "RECOVERY", 1, 'first');
    [metrics, values, notes] = add_metric(metrics, values, notes, "clear_while_fault_first_ovp_ms", clearWhileFault.time_s(firstOvpIdx) * 1000, "");
    [metrics, values, notes] = add_metric(metrics, values, notes, "clear_while_fault_ignored_clear_ms", clearWhileFault.time_s(ignoredClearIdx) * 1000, "");
    [metrics, values, notes] = add_metric(metrics, values, notes, "clear_while_fault_recovery_ms", clearWhileFault.time_s(clearRecoveryIdx) * 1000, "");

    combined = priorityCases.detected_fault(priorityCases.case_id == "ocp_ovp_uvlo");
    ovpUvlo = priorityCases.detected_fault(priorityCases.case_id == "ovp_uvlo");
    [metrics, values, notes] = add_metric(metrics, values, notes, "priority_ocp_ovp_uvlo", NaN, combined);
    [metrics, values, notes] = add_metric(metrics, values, notes, "priority_ovp_uvlo", NaN, ovpUvlo);

    summary = table(metrics, values, notes, 'VariableNames', {'metric', 'value', 'note'});
end

function [metrics, values, notes] = add_metric(metrics, values, notes, metric, value, note)
    metrics(end + 1, 1) = metric;
    values(end + 1, 1) = value;
    notes(end + 1, 1) = note;
end

function plot_run_fault(path, data)
    fig = figure('Visible', 'off', 'Position', [80 80 1450 980]);
    tiledlayout(4, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    stairs(data.time_s * 1000, data.state_code, 'LineWidth', 1.8);
    format_state_axis();
    title('MATLAB 故障注入：RUN 状态出现 OCP 后进入 FAULT LATCH');
    grid on;

    nexttile;
    hold on;
    stairs(data.time_s * 1000, data.fault_detected_code, 'LineWidth', 1.6);
    stairs(data.time_s * 1000, data.fault_latched_code, '--', 'LineWidth', 1.6);
    format_fault_axis();
    ylabel('fault code');
    legend('detected fault', 'latched fault', 'Location', 'northeast');
    grid on;

    nexttile;
    hold on;
    stairs(data.time_s * 1000, data.pwm_enable, 'LineWidth', 1.6);
    stairs(data.time_s * 1000, data.duty_cmd, '--', 'LineWidth', 1.6);
    ylim([-0.05 1.05]);
    ylabel('PWM / duty');
    legend('PWM enable', 'duty cmd', 'Location', 'northeast');
    grid on;

    nexttile;
    hold on;
    plot(data.time_s * 1000, data.vref_cmd_v, 'LineWidth', 1.6);
    stairs(data.time_s * 1000, double(data.command == "ENABLE"), '--', 'LineWidth', 1.2);
    stairs(data.time_s * 1000, double(data.command == "CLEAR_FAULT"), ':', 'LineWidth', 1.8);
    ylabel('Vref / command');
    xlabel('Time / ms');
    legend('Vref cmd', 'enable command', 'clear command', 'Location', 'southeast');
    grid on;

    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_clear_while_fault(path, data)
    fig = figure('Visible', 'off', 'Position', [80 80 1450 850]);
    tiledlayout(3, 1, 'TileSpacing', 'compact', 'Padding', 'compact');

    nexttile;
    hold on;
    plot(data.time_s * 1000, data.vout_v, 'LineWidth', 1.6);
    yline(13.2, '--', 'OVP threshold', 'Color', [0.5 0.5 0.5]);
    title('MATLAB 故障注入：故障仍存在时，CLEAR FAULT 不解除锁存');
    ylabel('Vout / V');
    grid on;

    nexttile;
    hold on;
    stairs(data.time_s * 1000, data.fault_detected_code, 'LineWidth', 1.6);
    stairs(data.time_s * 1000, data.fault_latched_code, '--', 'LineWidth', 1.6);
    format_fault_axis();
    ylabel('fault code');
    legend('detected fault', 'latched fault', 'Location', 'northeast');
    grid on;

    nexttile;
    hold on;
    stairs(data.time_s * 1000, data.state_code, 'LineWidth', 1.8);
    stairs(data.time_s * 1000, double(data.command == "CLEAR_FAULT") * 5, ':', 'LineWidth', 1.8);
    format_state_axis();
    xlabel('Time / ms');
    legend('state', 'clear command marker', 'Location', 'southeast');
    grid on;

    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function plot_priority(path, cases)
    fig = figure('Visible', 'off', 'Position', [80 80 1450 680]);
    bar(cases.detected_fault_code, 0.62);
    tickLabels = replace(cases.case_id, "_", " ");
    set(gca, 'XTick', 1:numel(cases.case_id), 'XTickLabel', tickLabels);
    xtickangle(25);
    format_fault_axis();
    ylabel('detected fault');
    title('保护检测优先级：OCP -> OVP -> UVLO -> OTP');
    grid on;

    for idx = 1:numel(cases.case_id)
        text(idx, cases.detected_fault_code(idx) + 0.15, cases.detected_fault(idx), ...
            'HorizontalAlignment', 'center', 'FontSize', 10);
    end

    exportgraphics(fig, path, 'Resolution', 180);
    close(fig);
end

function format_state_axis()
    ylim([-0.2 5.2]);
    yticks(0:5);
    yticklabels({'INIT', 'IDLE', 'SOFT_START', 'RUN', 'FAULT_LATCH', 'RECOVERY'});
    ylabel('state');
end

function format_fault_axis()
    ylim([-0.2 4.4]);
    yticks(0:4);
    yticklabels({'NONE', 'OCP', 'OVP', 'UVLO', 'OTP'});
end

function code = state_to_code(state)
    switch state
        case "INIT"
            code = 0;
        case "IDLE"
            code = 1;
        case "SOFT_START"
            code = 2;
        case "RUN"
            code = 3;
        case "FAULT_LATCH"
            code = 4;
        case "RECOVERY"
            code = 5;
        otherwise
            code = -1;
    end
end

function code = fault_to_code(fault)
    switch fault
        case "NONE"
            code = 0;
        case "OCP"
            code = 1;
        case "OVP"
            code = 2;
        case "UVLO"
            code = 3;
        case "OTP"
            code = 4;
        otherwise
            code = -1;
    end
end

function set_plot_defaults()
    set(groot, 'defaultAxesFontName', 'Microsoft YaHei');
    set(groot, 'defaultTextFontName', 'Microsoft YaHei');
    set(groot, 'defaultAxesFontSize', 11);
    set(groot, 'defaultLineLineWidth', 1.4);
    set(groot, 'defaultAxesGridAlpha', 0.18);
    set(groot, 'defaultTextInterpreter', 'none');
    set(groot, 'defaultLegendInterpreter', 'none');
    set(groot, 'defaultAxesTickLabelInterpreter', 'none');
end
