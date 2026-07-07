function plot_waveforms(inputFile)
%PLOT_WAVEFORMS 绘制仿真导出的波形。
% 输入 CSV 建议包含 time_s、vin_v、vout_v、iout_a、duty、state。

if nargin < 1
    error("请传入仿真导出的 CSV 文件路径，例如 artifacts/startup_no_load.csv");
end

data = readtable(inputFile);
required = ["time_s", "vout_v", "iout_a", "duty"];
missing = setdiff(required, string(data.Properties.VariableNames));
if ~isempty(missing)
    error("缺少列: %s", strjoin(missing, ", "));
end

figure('Name', inputFile);
tiledlayout(3, 1);

nexttile;
plot(data.time_s, data.vout_v, 'LineWidth', 1.2);
grid on;
ylabel('Vout / V');

nexttile;
plot(data.time_s, data.iout_a, 'LineWidth', 1.2);
grid on;
ylabel('Iout / A');

nexttile;
plot(data.time_s, data.duty, 'LineWidth', 1.2);
grid on;
ylabel('Duty');
xlabel('Time / s');
end
