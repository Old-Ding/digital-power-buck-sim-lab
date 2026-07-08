from pathlib import Path
import csv
import math

import matplotlib.pyplot as plt


VIN_NOM = 24.0
VIN_STEP = 20.0
VREF = 12.0
IOUT_NOM = 5.0
RLOAD_NOM = VREF / IOUT_NOM
RLOAD_STEP = VREF / 7.5

L_OUT = 22e-6
C_OUT = 100e-6
FSW = 200e3
TS_CTRL = 1 / FSW
SUBSTEPS = 20
DT = TS_CTRL / SUBSTEPS
STOP_TIME = 0.012

DUTY_FEEDFORWARD = VREF / VIN_NOM
R_SERIES = 0.02
KP = 0.05
KI = 200.0

VIN_STEP_TIME = 0.003
LOAD_STEP_TIME = 0.007

plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["axes.edgecolor"] = "#cbd5e1"
plt.rcParams["axes.labelcolor"] = "#334155"
plt.rcParams["xtick.color"] = "#475569"
plt.rcParams["ytick.color"] = "#475569"
plt.rcParams["text.color"] = "#1f2937"


def initial_integrator_trim():
    nominal_current = VREF / RLOAD_NOM
    required_duty = (VREF + nominal_current * R_SERIES) / VIN_NOM
    return required_duty - DUTY_FEEDFORWARD


def case_vin(time_s):
    return VIN_NOM if time_s < VIN_STEP_TIME else VIN_STEP


def case_rload(time_s, enable_load_step):
    if enable_load_step and time_s >= LOAD_STEP_TIME:
        return RLOAD_STEP
    return RLOAD_NOM


def simulate(mode, enable_load_step):
    steps = int(round(STOP_TIME / DT)) + 1
    inductor_current = VREF / RLOAD_NOM
    vout = VREF
    integrator = initial_integrator_trim()
    duty = DUTY_FEEDFORWARD + integrator

    rows = []

    for step_idx in range(steps):
        time_s = step_idx * DT
        vin = case_vin(time_s)
        rload = case_rload(time_s, enable_load_step)

        if step_idx % SUBSTEPS == 0:
            error = VREF - vout
            if mode == "pi":
                integrator += KI * TS_CTRL * error
            duty = DUTY_FEEDFORWARD + KP * error + integrator

        # 这里故意不加入抗积分饱和；第 5 章再处理 duty 限幅和积分器边界。
        di_dt = (vin * duty - vout - inductor_current * R_SERIES) / L_OUT
        dv_dt = (inductor_current - vout / rload) / C_OUT
        inductor_current += di_dt * DT
        vout += dv_dt * DT

        rows.append(
            {
                "time_s": time_s,
                "mode": mode,
                "vin_v": vin,
                "rload_ohm": rload,
                "load_current_a": vout / rload,
                "vout_v": vout,
                "inductor_current_a": inductor_current,
                "error_v": VREF - vout,
                "duty": duty,
                "integrator": integrator,
                "is_sample": 1 if step_idx % SUBSTEPS == 0 else 0,
            }
        )

    return rows


def within_window(rows, start_s, stop_s):
    return [row for row in rows if start_s <= row["time_s"] <= stop_s]


def settling_time_ms(rows, start_s, stop_s, target=VREF, band=0.12):
    window = within_window(rows, start_s, stop_s)
    for idx, row in enumerate(window):
        rest = window[idx:]
        if rest and all(abs(item["vout_v"] - target) <= band for item in rest):
            return (row["time_s"] - start_s) * 1000
    return ""


def min_max(rows, key, start_s=0.0, stop_s=STOP_TIME):
    values = [row[key] for row in within_window(rows, start_s, stop_s)]
    return min(values), max(values)


def write_trace(path, rows):
    fieldnames = [
        "time_s",
        "mode",
        "vin_v",
        "rload_ohm",
        "load_current_a",
        "vout_v",
        "inductor_current_a",
        "error_v",
        "duty",
        "integrator",
        "is_sample",
    ]
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_summary(path, p_rows, pi_rows):
    p_after = within_window(p_rows, 0.0055, 0.0068)
    pi_after = within_window(pi_rows, 0.0055, 0.0068)
    pi_load_after = within_window(pi_rows, 0.0105, STOP_TIME)

    pi_vout_min_input, pi_vout_max_input = min_max(pi_rows, "vout_v", VIN_STEP_TIME, LOAD_STEP_TIME)
    pi_vout_min_load, pi_vout_max_load = min_max(pi_rows, "vout_v", LOAD_STEP_TIME, STOP_TIME)
    duty_min, duty_max = min_max(pi_rows, "duty", 0.0, STOP_TIME)

    rows = [
        ["vref_v", VREF],
        ["fsw_hz", FSW],
        ["control_period_us", TS_CTRL * 1e6],
        ["kp", KP],
        ["ki", KI],
        ["duty_feedforward", DUTY_FEEDFORWARD],
        ["initial_integrator_trim", initial_integrator_trim()],
        ["vin_step_from_v", VIN_NOM],
        ["vin_step_to_v", VIN_STEP],
        ["load_step_from_a", VREF / RLOAD_NOM],
        ["load_step_to_a", VREF / RLOAD_STEP],
        ["p_only_vout_after_vin_step_v", sum(row["vout_v"] for row in p_after) / len(p_after)],
        ["pi_vout_after_vin_step_v", sum(row["vout_v"] for row in pi_after) / len(pi_after)],
        ["pi_vout_after_load_step_v", sum(row["vout_v"] for row in pi_load_after) / len(pi_load_after)],
        ["pi_input_step_vout_min_v", pi_vout_min_input],
        ["pi_input_step_vout_max_v", pi_vout_max_input],
        ["pi_load_step_vout_min_v", pi_vout_min_load],
        ["pi_load_step_vout_max_v", pi_vout_max_load],
        ["pi_duty_min", duty_min],
        ["pi_duty_max", duty_max],
        ["pi_input_step_settling_ms_1pct", settling_time_ms(pi_rows, VIN_STEP_TIME, LOAD_STEP_TIME)],
        ["pi_load_step_settling_ms_1pct", settling_time_ms(pi_rows, LOAD_STEP_TIME, STOP_TIME)],
    ]

    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["metric", "value"])
        writer.writerows(rows)

    return dict(rows)


def time_ms(rows):
    return [row["time_s"] * 1000 for row in rows]


def style_axis(ax):
    ax.set_facecolor("white")
    ax.grid(True, color="#e2e8f0", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def add_event_lines(ax, include_load=True):
    ax.axvline(VIN_STEP_TIME * 1000, color="#475569", linestyle="--", linewidth=1.0)
    ax.text(VIN_STEP_TIME * 1000 + 0.08, ax.get_ylim()[1] * 0.96, "Vin 24V->20V", color="#475569", fontsize=9, va="top")
    if include_load:
        ax.axvline(LOAD_STEP_TIME * 1000, color="#64748b", linestyle="--", linewidth=1.0)
        ax.text(LOAD_STEP_TIME * 1000 + 0.08, ax.get_ylim()[1] * 0.96, "负载 5A->7.5A", color="#64748b", fontsize=9, va="top")


def plot_p_vs_pi(path, p_rows, pi_rows):
    fig, axes = plt.subplots(2, 1, figsize=(10, 6.2), sharex=True)
    fig.patch.set_facecolor("white")

    for ax in axes:
        style_axis(ax)
        ax.axvspan(VIN_STEP_TIME * 1000, STOP_TIME * 1000, color="#fef3c7", alpha=0.42, linewidth=0)

    axes[0].plot(time_ms(p_rows), [row["vout_v"] for row in p_rows], color="#f97316", linewidth=1.7, label="P-only")
    axes[0].plot(time_ms(pi_rows), [row["vout_v"] for row in pi_rows], color="#2563eb", linewidth=1.9, label="PI")
    axes[0].axhline(VREF, color="#334155", linestyle="--", linewidth=1.0, label="12V 目标")
    axes[0].set_title("只用 P 会留下稳态误差，PI 用积分项把误差推回 0", fontsize=14, weight="bold")
    axes[0].set_ylabel("Vout / V")
    axes[0].legend(frameon=False, loc="lower right")

    axes[1].plot(time_ms(p_rows), [row["duty"] for row in p_rows], color="#f97316", linewidth=1.7, label="P-only duty")
    axes[1].plot(time_ms(pi_rows), [row["duty"] for row in pi_rows], color="#2563eb", linewidth=1.9, label="PI duty")
    axes[1].set_ylabel("duty")
    axes[1].set_xlabel("时间 / ms")
    axes[1].legend(frameon=False, loc="lower right")

    for ax in axes:
        add_event_lines(ax, include_load=False)
        ax.set_xlim(0, 7)

    save(fig, path)


def plot_pi_transient(path, pi_rows):
    fig, axes = plt.subplots(3, 1, figsize=(10.5, 7.2), sharex=True)
    fig.patch.set_facecolor("white")

    for ax in axes:
        style_axis(ax)
        ax.axvspan(VIN_STEP_TIME * 1000, VIN_STEP_TIME * 1000 + 1.6, color="#fef3c7", alpha=0.45, linewidth=0)
        ax.axvspan(LOAD_STEP_TIME * 1000, LOAD_STEP_TIME * 1000 + 1.6, color="#dcfce7", alpha=0.40, linewidth=0)

    axes[0].plot(time_ms(pi_rows), [row["vout_v"] for row in pi_rows], color="#2563eb", linewidth=1.8)
    axes[0].axhline(VREF, color="#334155", linestyle="--", linewidth=1.0)
    axes[0].set_title("离散 PI 电压环：输入扰动和负载扰动下的输出恢复", fontsize=14, weight="bold")
    axes[0].set_ylabel("Vout / V")

    axes[1].plot(time_ms(pi_rows), [row["duty"] for row in pi_rows], color="#0f766e", linewidth=1.8)
    axes[1].set_ylabel("duty")

    axes[2].plot(time_ms(pi_rows), [row["vin_v"] for row in pi_rows], color="#7c3aed", linewidth=1.6, label="Vin")
    axes[2].plot(time_ms(pi_rows), [row["load_current_a"] for row in pi_rows], color="#dc2626", linewidth=1.6, label="Iout")
    axes[2].set_ylabel("扰动量")
    axes[2].set_xlabel("时间 / ms")
    axes[2].legend(frameon=False, loc="upper right")

    for ax in axes:
        add_event_lines(ax, include_load=True)
        ax.set_xlim(0, STOP_TIME * 1000)

    save(fig, path)


def plot_error_integrator(path, pi_rows):
    fig, axes = plt.subplots(2, 1, figsize=(10, 5.8), sharex=True)
    fig.patch.set_facecolor("white")

    for ax in axes:
        style_axis(ax)
        ax.axvline(VIN_STEP_TIME * 1000, color="#475569", linestyle="--", linewidth=1.0)
        ax.axvline(LOAD_STEP_TIME * 1000, color="#64748b", linestyle="--", linewidth=1.0)

    axes[0].plot(time_ms(pi_rows), [row["error_v"] for row in pi_rows], color="#dc2626", linewidth=1.7)
    axes[0].axhline(0, color="#334155", linewidth=0.9)
    axes[0].set_title("误差 e[k] 与积分项 xI[k] 是 PI 调试时必须观测的变量", fontsize=14, weight="bold")
    axes[0].set_ylabel("error / V")

    axes[1].plot(time_ms(pi_rows), [row["integrator"] for row in pi_rows], color="#2563eb", linewidth=1.7)
    axes[1].set_ylabel("integrator")
    axes[1].set_xlabel("时间 / ms")
    axes[1].set_xlim(0, STOP_TIME * 1000)

    save(fig, path)


def plot_sampling_points(path, pi_rows):
    start_s = VIN_STEP_TIME - 80e-6
    stop_s = VIN_STEP_TIME + 260e-6
    window = within_window(pi_rows, start_s, stop_s)
    samples = [row for row in window if row["is_sample"] == 1]

    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    fig.patch.set_facecolor("white")
    style_axis(ax)
    ax.plot(time_ms(window), [row["vout_v"] for row in window], color="#94a3b8", linewidth=1.3, label="平均模型连续响应")
    ax.scatter(time_ms(samples), [row["vout_v"] for row in samples], color="#2563eb", s=28, label="控制器采样点 Ts=5us", zorder=3)
    ax.axvline(VIN_STEP_TIME * 1000, color="#475569", linestyle="--", linewidth=1.0)
    ax.set_title("数字控制器只在采样点更新 duty，不是连续时间每一刻都计算", fontsize=14, weight="bold")
    ax.set_xlabel("时间 / ms")
    ax.set_ylabel("Vout / V")
    ax.legend(frameon=False, loc="lower left")
    save(fig, path)


def main():
    repo_root = Path(__file__).resolve().parents[1]
    wave_dir = repo_root / "waveforms"
    wave_dir.mkdir(parents=True, exist_ok=True)

    p_rows = simulate("p", enable_load_step=False)
    pi_rows_no_load = simulate("pi", enable_load_step=False)
    pi_rows = simulate("pi", enable_load_step=True)

    write_trace(wave_dir / "04-discrete-pi-control-trace.csv", pi_rows)
    summary = write_summary(wave_dir / "04-discrete-pi-control-summary.csv", p_rows, pi_rows)

    plot_p_vs_pi(wave_dir / "04-p-only-vs-pi-vin-step.png", p_rows, pi_rows_no_load)
    plot_pi_transient(wave_dir / "04-pi-vin-load-transient.png", pi_rows)
    plot_error_integrator(wave_dir / "04-pi-error-integrator.png", pi_rows)
    plot_sampling_points(wave_dir / "04-pi-sampling-points.png", pi_rows)

    print("已生成第 4 章离散 PI 控制仿真数据和图表。")
    print(
        "pi,"
        f"kp={KP:.6g},"
        f"ki={KI:.6g},"
        f"control_period_us={TS_CTRL * 1e6:.6g},"
        f"duty_max={summary['pi_duty_max']:.6g},"
        f"input_step_settling_ms={summary['pi_input_step_settling_ms_1pct']},"
        f"load_step_settling_ms={summary['pi_load_step_settling_ms_1pct']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
