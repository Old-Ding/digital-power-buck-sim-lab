from pathlib import Path
import csv
import math

import matplotlib.pyplot as plt


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


def estimate(l_h, c_f, fsw_hz):
    delta_il = (VIN - VOUT) * DUTY / (l_h * fsw_hz)
    delta_vout = delta_il / (8 * fsw_hz * c_f)
    lc_freq = 1 / (2 * math.pi * math.sqrt(l_h * c_f))
    return {
        "delta_il_a": delta_il,
        "delta_il_percent_iout": delta_il / IOUT * 100,
        "delta_vout_mv": delta_vout * 1000,
        "inductor_current_min_a": IOUT - delta_il / 2,
        "lc_natural_frequency_hz": lc_freq,
        "lc_period_us": 1 / lc_freq * 1e6,
    }


def read_existing_plecs_summary(repo_root):
    summary_path = repo_root / "waveforms" / "02-open-loop-summary.csv"
    if not summary_path.exists():
        return {}

    with summary_path.open("r", newline="", encoding="utf-8") as fp:
        return {row["metric"]: float(row["value"]) for row in csv.DictReader(fp)}


def add_sweep_rows(rows, sweep_name, values):
    for case_name, l_h, c_f, fsw_hz in values:
        result = estimate(l_h, c_f, fsw_hz)
        rows.append(
            {
                "sweep": sweep_name,
                "case": case_name,
                "source": "formula_estimate",
                "vin_v": VIN,
                "vout_v": VOUT,
                "iout_a": IOUT,
                "rload_ohm": RLOAD,
                "duty": DUTY,
                "l_uh": l_h * 1e6,
                "c_uf": c_f * 1e6,
                "fsw_khz": fsw_hz / 1000,
                **result,
                "existing_plecs_il_ripple_pp_a": "",
                "existing_plecs_vout_ripple_pp_mv": "",
                "existing_plecs_startup_vout_peak_v": "",
                "existing_plecs_startup_il_peak_a": "",
                "note": "公式估算，未重新运行 PLECS 参数扫描",
            }
        )


def build_rows(existing):
    rows = []
    base = estimate(BASE_L, BASE_C, BASE_FSW)
    rows.append(
        {
            "sweep": "base_compare",
            "case": "22uH_100uF_200kHz",
            "source": "formula_estimate_and_existing_plecs",
            "vin_v": VIN,
            "vout_v": VOUT,
            "iout_a": IOUT,
            "rload_ohm": RLOAD,
            "duty": DUTY,
            "l_uh": BASE_L * 1e6,
            "c_uf": BASE_C * 1e6,
            "fsw_khz": BASE_FSW / 1000,
            **base,
            "existing_plecs_il_ripple_pp_a": existing.get("inductor_current_ripple_pp_a", ""),
            "existing_plecs_vout_ripple_pp_mv": existing.get("vout_ripple_pp_v", "") * 1000
            if "vout_ripple_pp_v" in existing
            else "",
            "existing_plecs_startup_vout_peak_v": existing.get("startup_vout_peak_v", ""),
            "existing_plecs_startup_il_peak_a": existing.get("startup_inductor_current_peak_a", ""),
            "note": "公式估算与第二章已有 PLECS 基准结果对照",
        }
    )

    add_sweep_rows(
        rows,
        "l_sweep",
        [(f"{l_h * 1e6:.0f}uH", l_h, BASE_C, BASE_FSW) for l_h in L_SWEEP],
    )
    add_sweep_rows(
        rows,
        "c_sweep",
        [(f"{c_f * 1e6:.0f}uF", BASE_L, c_f, BASE_FSW) for c_f in C_SWEEP],
    )
    add_sweep_rows(
        rows,
        "fsw_sweep",
        [(f"{fsw_hz / 1000:.0f}kHz", BASE_L, BASE_C, fsw_hz) for fsw_hz in FSW_SWEEP],
    )
    return rows


def write_summary(path, rows):
    fieldnames = [
        "sweep",
        "case",
        "source",
        "vin_v",
        "vout_v",
        "iout_a",
        "rload_ohm",
        "duty",
        "l_uh",
        "c_uf",
        "fsw_khz",
        "delta_il_a",
        "delta_il_percent_iout",
        "delta_vout_mv",
        "inductor_current_min_a",
        "lc_natural_frequency_hz",
        "lc_period_us",
        "existing_plecs_il_ripple_pp_a",
        "existing_plecs_vout_ripple_pp_mv",
        "existing_plecs_startup_vout_peak_v",
        "existing_plecs_startup_il_peak_a",
        "note",
    ]

    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


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


def annotate_points(ax, xs, ys, fmt, dy):
    for x, y in zip(xs, ys):
        ax.text(x, y + dy, fmt.format(y), ha="center", va="bottom", fontsize=9, color="#334155")


def plot_base_compare(path, existing):
    formula = estimate(BASE_L, BASE_C, BASE_FSW)
    plecs_il = existing.get("inductor_current_ripple_pp_a")
    plecs_vout_mv = existing.get("vout_ripple_pp_v", 0) * 1000 if "vout_ripple_pp_v" in existing else None

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    fig.patch.set_facecolor("white")
    pairs = [
        (axes[0], "电感电流纹波", "A", formula["delta_il_a"], plecs_il),
        (axes[1], "输出电压纹波", "mV", formula["delta_vout_mv"], plecs_vout_mv),
    ]
    colors = ["#2563eb", "#10b981"]

    for ax, title, unit, formula_value, plecs_value in pairs:
        style_axis(ax)
        values = [formula_value, plecs_value if plecs_value is not None else 0]
        bars = ax.bar(["公式估算", "PLECS 基准"], values, color=colors, width=0.54)
        ax.set_title(title, fontsize=13, weight="bold")
        ax.set_ylabel(unit)
        ymax = max(values) * 1.28 if max(values) > 0 else 1
        ax.set_ylim(0, ymax)
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + ymax * 0.035,
                f"{value:.3g}",
                ha="center",
                va="bottom",
                fontsize=10,
                color="#334155",
            )
        if plecs_value is not None:
            error = (plecs_value - formula_value) / formula_value * 100
            ax.text(
                0.5,
                ymax * 0.12,
                f"差异 {error:+.1f}%",
                ha="center",
                va="center",
                fontsize=10,
                color="#475569",
            )

    fig.suptitle("基准参数：公式估算 vs PLECS 基准结果", fontsize=15, weight="bold")
    save(fig, path)


def plot_l_sweep(path):
    xs = [l_h * 1e6 for l_h in L_SWEEP]
    ys = [estimate(l_h, BASE_C, BASE_FSW)["delta_il_a"] for l_h in L_SWEEP]
    mins = [estimate(l_h, BASE_C, BASE_FSW)["inductor_current_min_a"] for l_h in L_SWEEP]
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    fig.patch.set_facecolor("white")
    style_axis(ax)
    ax.plot(xs, ys, color="#2563eb", linewidth=2.4, marker="o", markersize=7)
    ax.fill_between(xs, ys, color="#dbeafe", alpha=0.65)
    ax.axhline(1.5, color="#f97316", linestyle="--", linewidth=1.4, label="30% 纹波目标：1.5A")
    ax.scatter([22], [estimate(BASE_L, BASE_C, BASE_FSW)["delta_il_a"]], color="#dc2626", s=90, zorder=3, label="基准 22uH")
    annotate_points(ax, xs, ys, "{:.2f}A", 0.12)
    for x, i_min in zip(xs, mins):
        ax.text(x, 0.1, f"Imin {i_min:.2f}A", ha="center", va="bottom", fontsize=9, color="#64748b")
    ax.set_title("电感越大，电感电流纹波越小", fontsize=14, weight="bold")
    ax.set_xlabel("电感 L / uH")
    ax.set_ylabel("ΔIL 峰峰值 / A")
    ax.set_xticks(xs)
    ax.legend(frameon=False, loc="upper right")
    save(fig, path)


def plot_c_sweep(path):
    xs = [c_f * 1e6 for c_f in C_SWEEP]
    ys = [estimate(BASE_L, c_f, BASE_FSW)["delta_vout_mv"] for c_f in C_SWEEP]
    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    fig.patch.set_facecolor("white")
    style_axis(ax)
    bars = ax.bar([str(int(x)) for x in xs], ys, color=["#f97316", "#2563eb", "#10b981"], width=0.56)
    ax.axhline(10, color="#64748b", linestyle="--", linewidth=1.2, label="10mV 参考线")
    ymax = max(ys) * 1.3
    ax.set_ylim(0, ymax)
    for bar, value in zip(bars, ys):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + ymax * 0.035,
            f"{value:.2f}mV",
            ha="center",
            va="bottom",
            fontsize=10,
            color="#334155",
        )
    ax.set_title("电容越大，理想电容纹波越小", fontsize=14, weight="bold")
    ax.set_xlabel("输出电容 C / uF")
    ax.set_ylabel("ΔVout 估算峰峰值 / mV")
    ax.legend(frameon=False, loc="upper right")
    save(fig, path)


def plot_fsw_sweep(path):
    xs = [fsw_hz / 1000 for fsw_hz in FSW_SWEEP]
    il = [estimate(BASE_L, BASE_C, fsw_hz)["delta_il_a"] for fsw_hz in FSW_SWEEP]
    vout = [estimate(BASE_L, BASE_C, fsw_hz)["delta_vout_mv"] for fsw_hz in FSW_SWEEP]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    fig.patch.set_facecolor("white")

    for ax in axes:
        style_axis(ax)
        ax.set_xlabel("开关频率 fsw / kHz")
        ax.set_xticks(xs)

    axes[0].plot(xs, il, color="#2563eb", marker="o", linewidth=2.4)
    axes[0].fill_between(xs, il, color="#dbeafe", alpha=0.65)
    annotate_points(axes[0], xs, il, "{:.2f}A", 0.08)
    axes[0].set_title("fsw 提高，IL 纹波下降", fontsize=13, weight="bold")
    axes[0].set_ylabel("ΔIL / A")

    axes[1].plot(xs, vout, color="#10b981", marker="o", linewidth=2.4)
    axes[1].fill_between(xs, vout, color="#dcfce7", alpha=0.65)
    annotate_points(axes[1], xs, vout, "{:.2f}mV", 0.45)
    axes[1].set_title("fsw 提高，电容纹波也下降", fontsize=13, weight="bold")
    axes[1].set_ylabel("ΔVout / mV")

    fig.suptitle("开关频率不是越高越好，还要考虑开关损耗和实现难度", fontsize=15, weight="bold")
    save(fig, path)


def plot_lc_map(path):
    l_values = L_SWEEP
    c_values = C_SWEEP
    data = [[estimate(l_h, c_f, BASE_FSW)["lc_natural_frequency_hz"] / 1000 for l_h in l_values] for c_f in c_values]

    fig, ax = plt.subplots(figsize=(8.8, 5.2))
    fig.patch.set_facecolor("white")
    im = ax.imshow(data, cmap="YlGnBu", aspect="auto")
    ax.set_title("LC 自然频率估算：硬启动会激励这个二阶网络", fontsize=14, weight="bold")
    ax.set_xlabel("电感 L / uH")
    ax.set_ylabel("输出电容 C / uF")
    ax.set_xticks(range(len(l_values)), [f"{value * 1e6:.0f}" for value in l_values])
    ax.set_yticks(range(len(c_values)), [f"{value * 1e6:.0f}" for value in c_values])
    ax.set_xticks([0.5, 1.5], minor=True)
    ax.set_yticks([0.5, 1.5], minor=True)
    ax.grid(which="minor", color="white", linewidth=2.0)
    ax.tick_params(which="minor", bottom=False, left=False)

    for row_idx, row in enumerate(data):
        for col_idx, value in enumerate(row):
            text_color = "#f8fafc" if value >= 4.5 else "#0f172a"
            ax.text(col_idx, row_idx, f"{value:.1f}kHz", ha="center", va="center", color=text_color, fontsize=10)

    for spine in ax.spines.values():
        spine.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("自然频率 / kHz")
    save(fig, path)


def main():
    repo_root = Path(__file__).resolve().parents[1]
    wave_dir = repo_root / "waveforms"
    wave_dir.mkdir(parents=True, exist_ok=True)

    existing = read_existing_plecs_summary(repo_root)
    rows = build_rows(existing)
    write_summary(wave_dir / "03-parameter-sweep-summary.csv", rows)

    plot_base_compare(wave_dir / "03-base-estimate-vs-plecs.png", existing)
    plot_l_sweep(wave_dir / "03-inductor-sweep.png")
    plot_c_sweep(wave_dir / "03-capacitor-sweep.png")
    plot_fsw_sweep(wave_dir / "03-frequency-sweep.png")
    plot_lc_map(wave_dir / "03-lc-natural-frequency-map.png")

    print("已生成第三章公式估算 CSV 和图表。")
    print("说明：本脚本没有重新运行 PLECS 参数扫描，只读取第二章已有 PLECS 汇总数据做基准对照。")
    for row in rows:
        if row["sweep"] == "base_compare":
            print(
                "base,"
                f"formula_il_ripple_a={row['delta_il_a']:.6g},"
                f"formula_vout_ripple_mv={row['delta_vout_mv']:.6g},"
                f"plecs_il_ripple_a={row['existing_plecs_il_ripple_pp_a']},"
                f"plecs_vout_ripple_mv={row['existing_plecs_vout_ripple_pp_mv']}"
            )
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
