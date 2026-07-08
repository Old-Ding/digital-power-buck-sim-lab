from pathlib import Path
import csv
import os
import shutil
import statistics
import sys
import tempfile
import xmlrpc.client

import matplotlib.pyplot as plt


RPC_URL = "http://localhost:1080/RPC2"
MODEL_NAME = "buck_open_loop_24v_12v"

VIN = 24.0
VOUT = 12.0
IOUT = 5.0
DUTY = VOUT / VIN
RLOAD = VOUT / IOUT

BASE_L = 22e-6
BASE_C = 100e-6
BASE_FSW = 200e3

L_SWEEP = [10e-6, 22e-6, 47e-6]
C_SWEEP = [47e-6, 100e-6, 220e-6]
FSW_SWEEP = [100e3, 200e3, 300e3]

STOP_TIME = 0.01
OUTPUT_STEP = 2e-7
STEADY_START = 0.0098

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


def build_output_times(stop=STOP_TIME, step=OUTPUT_STEP):
    count = int(round(stop / step)) + 1
    return [idx * step for idx in range(count)]


def default_plecs_work_dir(repo_root):
    candidate = repo_root / "artifacts" / "plecs_work"
    try:
        str(candidate).encode("ascii")
    except UnicodeEncodeError:
        return Path(tempfile.gettempdir()) / "digital_power_buck_sim_lab" / "plecs_work"
    return candidate


def prepare_ascii_model(repo_root):
    model_file = repo_root / "models" / "plecs" / f"{MODEL_NAME}.plecs"
    if not model_file.exists():
        raise FileNotFoundError(f"找不到 PLECS 模型: {model_file}")

    work_dir = Path(os.environ.get("PLECS_WORK_DIR", default_plecs_work_dir(repo_root)))
    work_dir.mkdir(parents=True, exist_ok=True)
    ascii_model = work_dir / model_file.name

    # PLECS RPC 对中文路径兼容性不好，所以扫描时复制到 ASCII 工作目录。
    shutil.copy2(model_file, ascii_model)
    return ascii_model


def formula_estimate(l_h, c_f, fsw_hz):
    delta_il = (VIN - VOUT) * DUTY / (l_h * fsw_hz)
    delta_vout = delta_il / (8 * fsw_hz * c_f)
    return delta_il, delta_vout


def case_key(l_h, c_f, fsw_hz):
    return (round(l_h, 12), round(c_f, 12), round(fsw_hz, 3))


def case_label(l_h, c_f, fsw_hz):
    return f"L{l_h * 1e6:.0f}uH_C{c_f * 1e6:.0f}uF_f{fsw_hz / 1000:.0f}k"


def build_cases():
    cases = []

    for l_h in L_SWEEP:
        cases.append(("l_sweep", f"{l_h * 1e6:.0f}uH", l_h, BASE_C, BASE_FSW))

    for c_f in C_SWEEP:
        cases.append(("c_sweep", f"{c_f * 1e6:.0f}uF", BASE_L, c_f, BASE_FSW))

    for fsw_hz in FSW_SWEEP:
        cases.append(("fsw_sweep", f"{fsw_hz / 1000:.0f}kHz", BASE_L, BASE_C, fsw_hz))

    for c_f in C_SWEEP:
        for l_h in L_SWEEP:
            cases.append(("lc_startup_grid", f"L{l_h * 1e6:.0f}uH_C{c_f * 1e6:.0f}uF", l_h, c_f, BASE_FSW))

    return cases


def connect_and_load(ascii_model):
    server = xmlrpc.client.Server(RPC_URL)
    try:
        server.plecs.close(MODEL_NAME)
    except Exception:
        pass
    server.plecs.load(str(ascii_model.with_suffix("")))
    return server


def simulate_case(server, l_h, c_f, fsw_hz):
    result = server.plecs.simulate(
        MODEL_NAME,
        {
            "Name": case_label(l_h, c_f, fsw_hz),
            "ModelVars": {"Lo": l_h, "Co": c_f, "fsw": fsw_hz},
            "SolverOpts": {"OutputTimes": build_output_times()},
        },
    )

    values = result["Values"]
    if len(values) != 3:
        raise RuntimeError(f"期望 3 路输出，实际得到 {len(values)} 路。请检查 Probe/Demux/Out 连接。")

    return {
        "time_s": result["Time"],
        "vout_v": values[0],
        "inductor_current_a": values[1],
        "mosfet_vds_v": values[2],
    }


def tail(values, times, start=STEADY_START):
    return [value for value, time in zip(values, times) if time >= start]


def metrics(trace):
    times = trace["time_s"]
    vout = trace["vout_v"]
    il = trace["inductor_current_a"]
    vds = trace["mosfet_vds_v"]
    vout_tail = tail(vout, times)
    il_tail = tail(il, times)
    vds_tail = tail(vds, times)

    return {
        "startup_vout_peak_v": max(vout),
        "startup_inductor_current_peak_a": max(il),
        "vout_avg_v": statistics.fmean(vout_tail),
        "vout_ripple_pp_v": max(vout_tail) - min(vout_tail),
        "inductor_current_avg_a": statistics.fmean(il_tail),
        "inductor_current_ripple_pp_a": max(il_tail) - min(il_tail),
        "mosfet_vds_min_v": min(vds_tail),
        "mosfet_vds_max_v": max(vds_tail),
    }


def write_summary(path, cases, results):
    fieldnames = [
        "sweep",
        "case",
        "source",
        "vin_v",
        "vout_target_v",
        "iout_target_a",
        "rload_ohm",
        "duty",
        "l_uh",
        "c_uf",
        "fsw_khz",
        "formula_delta_il_a",
        "formula_delta_vout_mv",
        "plecs_startup_vout_peak_v",
        "plecs_startup_inductor_current_peak_a",
        "plecs_vout_avg_v",
        "plecs_vout_ripple_pp_mv",
        "plecs_inductor_current_avg_a",
        "plecs_inductor_current_ripple_pp_a",
        "plecs_mosfet_vds_min_v",
        "plecs_mosfet_vds_max_v",
        "note",
    ]

    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for sweep, name, l_h, c_f, fsw_hz in cases:
            estimate_il, estimate_vout = formula_estimate(l_h, c_f, fsw_hz)
            result = results[case_key(l_h, c_f, fsw_hz)]["metrics"]
            writer.writerow(
                {
                    "sweep": sweep,
                    "case": name,
                    "source": "plecs_rpc_simulation",
                    "vin_v": VIN,
                    "vout_target_v": VOUT,
                    "iout_target_a": IOUT,
                    "rload_ohm": RLOAD,
                    "duty": DUTY,
                    "l_uh": l_h * 1e6,
                    "c_uf": c_f * 1e6,
                    "fsw_khz": fsw_hz / 1000,
                    "formula_delta_il_a": estimate_il,
                    "formula_delta_vout_mv": estimate_vout * 1000,
                    "plecs_startup_vout_peak_v": result["startup_vout_peak_v"],
                    "plecs_startup_inductor_current_peak_a": result["startup_inductor_current_peak_a"],
                    "plecs_vout_avg_v": result["vout_avg_v"],
                    "plecs_vout_ripple_pp_mv": result["vout_ripple_pp_v"] * 1000,
                    "plecs_inductor_current_avg_a": result["inductor_current_avg_a"],
                    "plecs_inductor_current_ripple_pp_a": result["inductor_current_ripple_pp_a"],
                    "plecs_mosfet_vds_min_v": result["mosfet_vds_min_v"],
                    "plecs_mosfet_vds_max_v": result["mosfet_vds_max_v"],
                    "note": "PLECS RPC 真实参数扫描结果",
                }
            )


def write_trace_csv(path, l_h, c_f, fsw_hz, trace):
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(
            [
                "time_s",
                "vout_v",
                "inductor_current_a",
                "mosfet_vds_v",
                "l_h",
                "c_f",
                "fsw_hz",
            ]
        )
        writer.writerows(
            zip(
                trace["time_s"],
                trace["vout_v"],
                trace["inductor_current_a"],
                trace["mosfet_vds_v"],
                [l_h] * len(trace["time_s"]),
                [c_f] * len(trace["time_s"]),
                [fsw_hz] * len(trace["time_s"]),
            )
        )


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


def steady_window(trace, start=0.0098, stop=0.0100):
    times = trace["time_s"]
    indices = [idx for idx, time in enumerate(times) if start <= time <= stop]
    return indices


def plot_l_sweep(path, results):
    fig, ax = plt.subplots(figsize=(10, 5.2))
    fig.patch.set_facecolor("white")
    style_axis(ax)
    colors = ["#f97316", "#2563eb", "#10b981"]

    for color, l_h in zip(colors, L_SWEEP):
        trace = results[case_key(l_h, BASE_C, BASE_FSW)]["trace"]
        indices = steady_window(trace)
        times_us = [(trace["time_s"][idx] - trace["time_s"][indices[0]]) * 1e6 for idx in indices]
        il = [trace["inductor_current_a"][idx] for idx in indices]
        ripple = results[case_key(l_h, BASE_C, BASE_FSW)]["metrics"]["inductor_current_ripple_pp_a"]
        ax.plot(times_us, il, linewidth=1.8, color=color, label=f"{l_h * 1e6:.0f}uH, ΔIL={ripple:.2f}A")

    ax.set_title("PLECS 参数扫描：不同电感值下的稳态电感电流", fontsize=14, weight="bold")
    ax.set_xlabel("局部时间 / us")
    ax.set_ylabel("IL / A")
    ax.legend(frameon=False, loc="upper right")
    save(fig, path)


def plot_c_sweep(path, results):
    fig, ax = plt.subplots(figsize=(10, 5.2))
    fig.patch.set_facecolor("white")
    style_axis(ax)
    colors = ["#f97316", "#2563eb", "#10b981"]

    for color, c_f in zip(colors, C_SWEEP):
        trace = results[case_key(BASE_L, c_f, BASE_FSW)]["trace"]
        indices = steady_window(trace)
        times_us = [(trace["time_s"][idx] - trace["time_s"][indices[0]]) * 1e6 for idx in indices]
        vout_values = [trace["vout_v"][idx] for idx in indices]
        avg = statistics.fmean(vout_values)
        vout_mv = [(value - avg) * 1000 for value in vout_values]
        ripple_mv = results[case_key(BASE_L, c_f, BASE_FSW)]["metrics"]["vout_ripple_pp_v"] * 1000
        ax.plot(times_us, vout_mv, linewidth=1.8, color=color, label=f"{c_f * 1e6:.0f}uF, ΔVout={ripple_mv:.2f}mV")

    ax.set_title("PLECS 参数扫描：不同输出电容下的稳态输出纹波", fontsize=14, weight="bold")
    ax.set_xlabel("局部时间 / us")
    ax.set_ylabel("Vout - 平均值 / mV")
    ax.legend(frameon=False, loc="upper right")
    save(fig, path)


def plot_fsw_sweep(path, results):
    xs = [fsw_hz / 1000 for fsw_hz in FSW_SWEEP]
    il = [results[case_key(BASE_L, BASE_C, fsw_hz)]["metrics"]["inductor_current_ripple_pp_a"] for fsw_hz in FSW_SWEEP]
    vout = [results[case_key(BASE_L, BASE_C, fsw_hz)]["metrics"]["vout_ripple_pp_v"] * 1000 for fsw_hz in FSW_SWEEP]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8))
    fig.patch.set_facecolor("white")
    for ax in axes:
        style_axis(ax)
        ax.set_xlabel("开关频率 fsw / kHz")
        ax.set_xticks(xs)

    axes[0].plot(xs, il, color="#2563eb", marker="o", linewidth=2.4)
    axes[0].fill_between(xs, il, color="#dbeafe", alpha=0.65)
    axes[0].set_title("PLECS：fsw 提高，IL 纹波下降", fontsize=13, weight="bold")
    axes[0].set_ylabel("ΔIL / A")

    axes[1].plot(xs, vout, color="#10b981", marker="o", linewidth=2.4)
    axes[1].fill_between(xs, vout, color="#dcfce7", alpha=0.65)
    axes[1].set_title("PLECS：fsw 提高，输出纹波下降", fontsize=13, weight="bold")
    axes[1].set_ylabel("ΔVout / mV")

    for ax, values, fmt in [(axes[0], il, "{:.2f}A"), (axes[1], vout, "{:.2f}mV")]:
        for x_value, y_value in zip(xs, values):
            ax.text(x_value, y_value + max(values) * 0.04, fmt.format(y_value), ha="center", va="bottom", fontsize=9)

    fig.suptitle("PLECS 参数扫描：开关频率对纹波的影响", fontsize=15, weight="bold")
    save(fig, path)


def plot_lc_startup_map(path, results):
    l_values = L_SWEEP
    c_values = C_SWEEP
    vout_peaks = []
    il_peaks = []

    for c_f in c_values:
        vout_row = []
        il_row = []
        for l_h in l_values:
            result = results[case_key(l_h, c_f, BASE_FSW)]["metrics"]
            vout_row.append(result["startup_vout_peak_v"])
            il_row.append(result["startup_inductor_current_peak_a"])
        vout_peaks.append(vout_row)
        il_peaks.append(il_row)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.patch.set_facecolor("white")
    panels = [
        (axes[0], vout_peaks, "启动 Vout 峰值 / V", "V"),
        (axes[1], il_peaks, "启动 IL 峰值 / A", "A"),
    ]

    for ax, data, title, unit in panels:
        im = ax.imshow(data, cmap="YlGnBu", aspect="auto")
        ax.set_title(title, fontsize=13, weight="bold")
        ax.set_xlabel("电感 L / uH")
        ax.set_ylabel("输出电容 C / uF")
        ax.set_xticks(range(len(l_values)), [f"{value * 1e6:.0f}" for value in l_values])
        ax.set_yticks(range(len(c_values)), [f"{value * 1e6:.0f}" for value in c_values])
        ax.set_xticks([0.5, 1.5], minor=True)
        ax.set_yticks([0.5, 1.5], minor=True)
        ax.grid(which="minor", color="white", linewidth=2.0)
        ax.tick_params(which="minor", bottom=False, left=False)
        flat_values = [value for row in data for value in row]
        text_threshold = min(flat_values) + (max(flat_values) - min(flat_values)) * 0.55
        for row_idx, row in enumerate(data):
            for col_idx, value in enumerate(row):
                text_color = "#f8fafc" if value >= text_threshold else "#0f172a"
                ax.text(col_idx, row_idx, f"{value:.1f}{unit}", ha="center", va="center", color=text_color, fontsize=9)
        for spine in ax.spines.values():
            spine.set_visible(False)
        cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        cbar.set_label(unit)

    fig.suptitle("PLECS 参数扫描：L/C 组合对开环硬启动峰值的影响", fontsize=15, weight="bold")
    save(fig, path)


def run_sweep(repo_root):
    ascii_model = prepare_ascii_model(repo_root)
    server = connect_and_load(ascii_model)
    cases = build_cases()
    results = {}

    for _sweep, _name, l_h, c_f, fsw_hz in cases:
        key = case_key(l_h, c_f, fsw_hz)
        if key in results:
            continue
        print(f"运行 PLECS: {case_label(l_h, c_f, fsw_hz)}")
        trace = simulate_case(server, l_h, c_f, fsw_hz)
        results[key] = {"trace": trace, "metrics": metrics(trace)}

    return cases, results


def main():
    repo_root = Path(__file__).resolve().parents[1]
    wave_dir = repo_root / "waveforms"
    wave_dir.mkdir(parents=True, exist_ok=True)

    try:
        cases, results = run_sweep(repo_root)
    except ConnectionRefusedError:
        print("无法连接 PLECS RPC。请先启动 PLECS_server.exe，再运行本脚本。", file=sys.stderr)
        return 2

    write_summary(wave_dir / "03-plecs-parameter-sweep-summary.csv", cases, results)

    if os.environ.get("EXPORT_PLECS_SWEEP_TRACES") == "1":
        trace_dir = repo_root / "artifacts" / "03_plecs_parameter_sweep_traces"
        trace_dir.mkdir(parents=True, exist_ok=True)
        for key, result in results.items():
            l_h, c_f, fsw_hz = key
            write_trace_csv(trace_dir / f"03-plecs-trace-{case_label(l_h, c_f, fsw_hz)}.csv", l_h, c_f, fsw_hz, result["trace"])

    plot_l_sweep(wave_dir / "03-plecs-inductor-sweep-il.png", results)
    plot_c_sweep(wave_dir / "03-plecs-capacitor-sweep-vout.png", results)
    plot_fsw_sweep(wave_dir / "03-plecs-frequency-sweep.png", results)
    plot_lc_startup_map(wave_dir / "03-plecs-lc-startup-peak-map.png", results)

    base = results[case_key(BASE_L, BASE_C, BASE_FSW)]["metrics"]
    print("已完成 PLECS 参数扫描并导出 CSV 与波形图。")
    print(
        "base,"
        f"plecs_il_ripple_a={base['inductor_current_ripple_pp_a']:.6g},"
        f"plecs_vout_ripple_mv={base['vout_ripple_pp_v'] * 1000:.6g},"
        f"startup_vout_peak_v={base['startup_vout_peak_v']:.6g},"
        f"startup_il_peak_a={base['startup_inductor_current_peak_a']:.6g}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
