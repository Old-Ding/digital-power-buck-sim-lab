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

plt.rcParams["font.sans-serif"] = [
    "Microsoft YaHei",
    "SimHei",
    "Noto Sans CJK SC",
    "Arial Unicode MS",
    "DejaVu Sans",
]
plt.rcParams["axes.unicode_minus"] = False


def build_output_times(stop=0.01, step=2e-7):
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

    # PLECS Server 对中文路径兼容性不好，所以 RPC 仿真使用 ASCII 临时路径。
    shutil.copy2(model_file, ascii_model)
    return ascii_model


def simulate(ascii_model):
    server = xmlrpc.client.Server(RPC_URL)
    try:
        server.plecs.close(MODEL_NAME)
    except Exception:
        pass

    server.plecs.load(str(ascii_model.with_suffix("")))
    return server.plecs.simulate(
        MODEL_NAME,
        {
            "Name": "open_loop_base",
            "SolverOpts": {"OutputTimes": build_output_times()},
        },
    )


def tail_window(values, times, start=0.008):
    return [value for value, time in zip(values, times) if time >= start]


def write_csv(path, times, vout, il, vds):
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["time_s", "vout_v", "inductor_current_a", "mosfet_vds_v"])
        writer.writerows(zip(times, vout, il, vds))


def read_csv(path):
    times = []
    vout = []
    il = []
    vds = []

    with path.open("r", newline="", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            times.append(float(row["time_s"]))
            vout.append(float(row["vout_v"]))
            il.append(float(row["inductor_current_a"]))
            vds.append(float(row["mosfet_vds_v"]))

    return times, vout, il, vds


def plot_series(path, times, values, title, ylabel, xlim=None):
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=160)
    time_ms = [t * 1000 for t in times]
    ax.plot(time_ms, values, linewidth=1.2)
    ax.set_title(title)
    ax.set_xlabel("时间 / ms")
    ax.set_ylabel(ylabel)
    ax.grid(True, linewidth=0.5, alpha=0.5)
    if xlim is not None:
        ax.set_xlim(xlim)
        visible = [value for t, value in zip(time_ms, values) if xlim[0] <= t <= xlim[1]]
        if visible:
            span = max(visible) - min(visible)
            margin = span * 0.2 if span > 0 else max(abs(visible[0]) * 0.1, 1)
            ax.set_ylim(min(visible) - margin, max(visible) + margin)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_startup_overview(path, times, vout, il):
    time_ms = [t * 1000 for t in times]
    fig, axes = plt.subplots(2, 1, figsize=(9, 5.4), dpi=180, sharex=True)
    fig.patch.set_facecolor("white")

    vout_peak_idx = max(range(len(vout)), key=vout.__getitem__)
    il_peak_idx = max(range(len(il)), key=il.__getitem__)

    for ax in axes:
        ax.axvspan(0, 0.3, color="#fef3c7", alpha=0.55, linewidth=0)
        ax.axvspan(2.0, 3.2, color="#dcfce7", alpha=0.35, linewidth=0)
        ax.grid(True, color="#d1d5db", linewidth=0.6, alpha=0.8)
        ax.set_axisbelow(True)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].plot(time_ms, vout, color="#2563eb", linewidth=1.8, label="Vout")
    axes[0].axhline(12, color="#475569", linestyle="--", linewidth=1.0, label="12 V 目标值")
    axes[0].set_title("开环硬启动暂态")
    axes[0].set_ylabel("Vout / V")
    axes[0].set_ylim(-1, max(vout) * 1.12)
    axes[0].annotate(
        f"峰值 {vout[vout_peak_idx]:.1f} V",
        xy=(time_ms[vout_peak_idx], vout[vout_peak_idx]),
        xytext=(0.42, max(vout) * 0.86),
        arrowprops={"arrowstyle": "->", "color": "#1d4ed8", "linewidth": 1.0},
        color="#1d4ed8",
    )
    axes[0].text(0.03, 0.08, "硬启动区", transform=axes[0].transAxes, color="#92400e")
    axes[0].text(0.67, 0.88, "稳态检查区", transform=axes[0].transAxes, color="#166534")
    axes[0].legend(loc="upper right", frameon=False)

    axes[1].plot(time_ms, il, color="#dc2626", linewidth=1.0, label="IL")
    axes[1].axhline(5, color="#475569", linestyle="--", linewidth=1.0, label="5 A 负载电流")
    axes[1].set_xlabel("时间 / ms")
    axes[1].set_ylabel("IL / A")
    axes[1].set_ylim(-1, max(il) * 1.12)
    axes[1].annotate(
        f"峰值 {il[il_peak_idx]:.1f} A",
        xy=(time_ms[il_peak_idx], il[il_peak_idx]),
        xytext=(0.42, max(il) * 0.86),
        arrowprops={"arrowstyle": "->", "color": "#b91c1c", "linewidth": 1.0},
        color="#b91c1c",
    )
    axes[1].legend(loc="upper right", frameon=False)

    axes[1].set_xlim(0, 3.2)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def write_summary(path, times, vout, il, vds):
    vout_tail = tail_window(vout, times)
    il_tail = tail_window(il, times)
    vds_tail = tail_window(vds, times)

    rows = [
        ["startup_vout_peak_v", max(vout)],
        ["startup_inductor_current_peak_a", max(il)],
        ["vout_avg_v", statistics.fmean(vout_tail)],
        ["vout_ripple_pp_v", max(vout_tail) - min(vout_tail)],
        ["inductor_current_avg_a", statistics.fmean(il_tail)],
        ["inductor_current_ripple_pp_a", max(il_tail) - min(il_tail)],
        ["mosfet_vds_min_v", min(vds_tail)],
        ["mosfet_vds_max_v", max(vds_tail)],
    ]

    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["metric", "value"])
        writer.writerows(rows)

    return dict(rows)


def main():
    repo_root = Path(__file__).resolve().parents[1]
    wave_dir = repo_root / "waveforms"
    wave_dir.mkdir(parents=True, exist_ok=True)
    data_csv = wave_dir / "02-open-loop-data.csv"
    used_cached_data = False

    try:
        ascii_model = prepare_ascii_model(repo_root)
        result = simulate(ascii_model)
    except ConnectionRefusedError:
        if not data_csv.exists():
            print("无法连接 PLECS RPC。请先启动 PLECS_server.exe，确认 1080 端口已监听。", file=sys.stderr)
            return 2
        print("无法连接 PLECS RPC，本次使用已有 CSV 重新生成波形图；未重新运行 PLECS 仿真。", file=sys.stderr)
        used_cached_data = True
        times, vout, il, vds = read_csv(data_csv)
    else:
        times = result["Time"]
        values = result["Values"]
        if len(values) != 3:
            print(f"期望 3 路输出，实际得到 {len(values)} 路。请检查 Probe/Demux/Out 连接。", file=sys.stderr)
            return 3

        vout, il, vds = values
        write_csv(data_csv, times, vout, il, vds)
    summary = write_summary(wave_dir / "02-open-loop-summary.csv", times, vout, il, vds)

    plot_series(wave_dir / "02-open-loop-vout.png", times, vout, "开环 Buck 输出电压", "Vout / V")
    plot_startup_overview(wave_dir / "02-open-loop-startup-overview.png", times, vout, il)
    plot_series(wave_dir / "02-open-loop-il.png", times, il, "稳态电感电流纹波", "IL / A", (9.8, 10.0))
    plot_series(wave_dir / "02-open-loop-mosfet-vds.png", times, vds, "MOSFET Vds 开关波形", "Vds / V", (9.8, 9.85))

    if used_cached_data:
        print("已根据已有开环 Buck CSV 数据重新生成波形图。")
    else:
        print("已导出开环 Buck 仿真数据和波形图。")
    for key, value in summary.items():
        print(f"{key},{value:.6g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
