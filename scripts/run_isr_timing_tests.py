from __future__ import annotations

import csv
import os
from pathlib import Path

import matplotlib.pyplot as plt

from run_host_build_tests import compiler_family, compiler_version, find_compiler, run_command


ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "artifacts" / "host-build" / "chapter16"
WAVE_DIR = ROOT / "waveforms"
REPORT_DIR = ROOT / "reports"
CONTROL_PERIOD_NS = 5000.0
TARGET_ISR_BUDGET_NS = 3500.0

COMMON_SOURCES = [
    ROOT / "src" / "digital_power_adc_map.c",
    ROOT / "src" / "digital_power_control_fixed.c",
    ROOT / "src" / "digital_power_pwm_map.c",
    ROOT / "src" / "digital_power_control_isr.c",
]

BUDGET_ROWS = [
    {"stage": "更新事件与入口", "budget_ns": 250.0, "kind": "ISR"},
    {"stage": "ADC 快照与映射", "budget_ns": 700.0, "kind": "ISR"},
    {"stage": "定点控制与保护", "budget_ns": 1700.0, "kind": "ISR"},
    {"stage": "PWM 排队与关断", "budget_ns": 500.0, "kind": "ISR"},
    {"stage": "状态快照与退出", "budget_ns": 350.0, "kind": "ISR"},
    {"stage": "抖动与抢占余量", "budget_ns": 1500.0, "kind": "reserve"},
]


def compile_command(compiler: str, hint: str, sources: list[Path], output: Path) -> list[str]:
    family = compiler_family(compiler, hint)
    include = ROOT / "src"
    if family == "zig":
        return [compiler, "cc", "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror", "-I", str(include), *map(str, sources), "-o", str(output)]
    if family == "msvc":
        return [compiler, "/nologo", "/O2", "/W4", "/WX", f"/I{include}", *map(str, sources), f"/Fe:{output}"]
    return [compiler, "-std=c99", "-O2", "-D_POSIX_C_SOURCE=200809L", "-Wall", "-Wextra", "-Werror", "-I", str(include), *map(str, sources), "-o", str(output)]


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_sequence(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", newline="", encoding="utf-8") as file:
        for raw in csv.DictReader(file):
            row: dict[str, object] = {"scenario": raw["scenario"]}
            for name in (
                "cycle",
                "invocation",
                "active_compare_before_update",
                "active_compare_after_update",
                "pending_compare_after_control",
                "state",
                "active_fault",
                "latched_fault",
            ):
                row[name] = int(raw[name])
            for name in ("vin_v", "vout_v", "iout_a", "temperature_c", "duty_cmd"):
                row[name] = float(raw[name])
            for name in (
                "active_pwm_enable",
                "pwm_enable_command",
                "adc_input_clamped",
                "adc_physical_clamped",
                "arithmetic_overflow",
            ):
                row[name] = raw[name] == "1"
            rows.append(row)
    return rows


def read_timing(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", newline="", encoding="utf-8") as file:
        for raw in csv.DictReader(file):
            rows.append({
                "batch": int(raw["batch"]),
                "iterations": int(raw["iterations"]),
                "elapsed_ns": int(raw["elapsed_ns"]),
                "ns_per_call": float(raw["ns_per_call"]),
                "checksum": int(raw["checksum"]),
            })
    return rows


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] * (1.0 - fraction) + ordered[high] * fraction


def metric(case_id: str, name: str, value: float, limit: float, status: str, note: str) -> dict[str, object]:
    return {"case": case_id, "metric": name, "value": value, "limit": limit, "status": status, "note": note}


def build_metrics(sequence: list[dict[str, object]], timing: list[dict[str, object]], unit_output: str) -> list[dict[str, object]]:
    metrics: list[dict[str, object]] = []
    first = sequence[0]
    one_cycle_ok = all(
        int(sequence[index]["active_compare_after_update"]) == int(sequence[index - 1]["pending_compare_after_control"])
        for index in range(1, len(sequence))
    )
    initial_update_ok = (
        int(first["active_compare_before_update"]) == 0
        and int(first["active_compare_after_update"]) == 85
    )
    ocp_rows = [row for row in sequence if row["scenario"] == "ocp"]
    immediate_off_ok = bool(ocp_rows) and all(
        not bool(row["active_pwm_enable"]) and not bool(row["pwm_enable_command"])
        for row in ocp_rows
    )
    clear_row = next(row for row in sequence if row["scenario"] == "clear_fault")
    restart_row = next(row for row in sequence if row["scenario"] == "restart")
    restart_waits_ok = (
        not bool(clear_row["active_pwm_enable"])
        and bool(clear_row["pwm_enable_command"])
        and bool(restart_row["active_pwm_enable"])
    )
    clean_rows = [row for row in sequence if row["scenario"] in ("normal", "restart")]
    clean_mapping_ok = all(
        not bool(row["adc_input_clamped"])
        and not bool(row["adc_physical_clamped"])
        and not bool(row["arithmetic_overflow"])
        for row in clean_rows
    )

    metrics.extend([
        metric("isr_sequence", "initial_update_applies_preload", 1.0 if initial_update_ok else 0.0, 1.0, "PASS" if initial_update_ok else "FAIL", "中断入口先应用上一周期预装载值"),
        metric("isr_sequence", "one_cycle_compare_latency", 1.0 if one_cycle_ok else 0.0, 1.0, "PASS" if one_cycle_ok else "FAIL", "本周期计算的 compare 在下一更新事件生效"),
        metric("ocp", "active_pwm_disable_immediate", 1.0 if immediate_off_ok else 0.0, 1.0, "PASS" if immediate_off_ok else "FAIL", "OCP 周期内立即清除 active enable"),
        metric("fault_clear", "restart_waits_for_update", 1.0 if restart_waits_ok else 0.0, 1.0, "PASS" if restart_waits_ok else "FAIL", "重新使能等待下一更新事件"),
        metric("normal", "mapping_and_arithmetic_clean", 1.0 if clean_mapping_ok else 0.0, 1.0, "PASS" if clean_mapping_ok else "FAIL", "正常输入无钳位和整数溢出"),
    ])

    budget_total = sum(float(row["budget_ns"]) for row in BUDGET_ROWS if row["kind"] == "ISR")
    reserve = CONTROL_PERIOD_NS - budget_total
    metrics.append(metric("target_budget", "allocated_isr_ns", budget_total, TARGET_ISR_BUDGET_NS, "PASS" if budget_total <= TARGET_ISR_BUDGET_NS else "FAIL", "目标 MCU 的中断执行预算，不是主机实测值"))
    metrics.append(metric("target_budget", "reserve_ns", reserve, CONTROL_PERIOD_NS - TARGET_ISR_BUDGET_NS, "PASS" if reserve >= CONTROL_PERIOD_NS - TARGET_ISR_BUDGET_NS else "FAIL", "为中断延迟、抖动和高优先级抢占保留的余量"))

    timing_values = [float(row["ns_per_call"]) for row in timing]
    for name, value in (
        ("host_batch_p50_ns_per_call", percentile(timing_values, 0.50)),
        ("host_batch_p95_ns_per_call", percentile(timing_values, 0.95)),
        ("host_batch_p99_ns_per_call", percentile(timing_values, 0.99)),
        ("host_batch_max_ns_per_call", max(timing_values)),
    ):
        metrics.append(metric("host_benchmark", name, value, CONTROL_PERIOD_NS, "INFO", "主机批次均摊耗时，仅用于回归，不判定 MCU 5us 截止时间"))

    for line in unit_output.splitlines():
        parts = line.strip().split(",", 1)
        if len(parts) == 2 and parts[0] in ("PASS", "FAIL"):
            passed = parts[0] == "PASS"
            metrics.append(metric("isr_unit_tests", parts[1], 1.0 if passed else 0.0, 1.0, "PASS" if passed else "FAIL", "C 中断编排单元测试"))
    return metrics


def plot_sequence(path: Path, rows: list[dict[str, object]]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    x = [int(row["cycle"]) for row in rows]
    fig, axes = plt.subplots(2, 1, figsize=(11.5, 7.2), sharex=True)
    axes[0].step(x, [int(row["active_compare_after_update"]) for row in rows], where="post", color="#0f766e", linewidth=2.0, label="更新后 active compare")
    axes[0].step(x, [int(row["pending_compare_after_control"]) for row in rows], where="post", color="#d97706", linewidth=2.0, label="本周期 pending compare")
    axes[0].set_ylabel("timer counts")
    axes[0].set_title("上一周期结果先生效，本周期结果排队到下一次更新", loc="left")
    axes[0].legend()
    axes[0].grid(True, alpha=0.25)

    axes[1].step(x, [1 if bool(row["pwm_enable_command"]) else 0 for row in rows], where="post", color="#64748b", linewidth=1.8, label="控制器 enable 命令")
    axes[1].step(x, [1 if bool(row["active_pwm_enable"]) else 0 for row in rows], where="post", color="#be123c", linewidth=2.0, label="有效 PWM enable")
    axes[1].set_ylabel("enable")
    axes[1].set_yticks([0, 1])
    axes[1].set_xlabel("控制中断周期")
    axes[1].set_title("OCP 立即关断；清故障后的重新使能等待更新事件", loc="left")
    axes[1].legend()
    axes[1].grid(True, alpha=0.25)

    for row in rows:
        axes[1].text(int(row["cycle"]), -0.16, str(row["scenario"]), ha="center", va="top", fontsize=8, rotation=20)
    fig.suptitle("第 16 章：控制中断的单周期数据流", fontsize=15)
    fig.tight_layout(rect=(0.0, 0.04, 1.0, 0.95))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_budget_and_timing(path: Path, timing: list[dict[str, object]]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.6))
    colors = ["#0f766e", "#2563eb", "#d97706", "#be123c", "#64748b", "#cbd5e1"]
    left = 0.0
    for row, color in zip(BUDGET_ROWS, colors):
        width_us = float(row["budget_ns"]) / 1000.0
        axes[0].barh([0], [width_us], left=left, height=0.42, color=color, label=f"{row['stage']} {width_us:.2f}us")
        if width_us >= 0.45:
            axes[0].text(left + width_us / 2.0, 0, f"{width_us:.2f}", ha="center", va="center", fontsize=8, color="white" if row["kind"] == "ISR" else "#334155")
        left += width_us
    axes[0].axvline(TARGET_ISR_BUDGET_NS / 1000.0, color="#111827", linestyle="--", linewidth=1.2, label="ISR 目标上限 3.5us")
    axes[0].set_xlim(0.0, CONTROL_PERIOD_NS / 1000.0)
    axes[0].set_yticks([])
    axes[0].set_title("目标 MCU 时间预算（设计值）", loc="left")
    axes[0].legend(fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.10), ncol=2)
    axes[0].grid(True, axis="x", alpha=0.25)

    batches = [int(row["batch"]) for row in timing]
    values = [float(row["ns_per_call"]) for row in timing]
    p50 = percentile(values, 0.50)
    p99 = percentile(values, 0.99)
    axes[1].plot(batches, values, color="#2563eb", linewidth=1.0, alpha=0.8, label="每批均摊 ns/call")
    axes[1].axhline(p50, color="#0f766e", linestyle="--", linewidth=1.2, label=f"P50 {p50:.1f}ns")
    axes[1].axhline(p99, color="#be123c", linestyle=":", linewidth=1.4, label=f"P99 {p99:.1f}ns")
    axes[1].set_xlabel("主机基准批次")
    axes[1].set_ylabel("每次调用均摊耗时 / ns")
    axes[1].set_title("Windows 主机回归基准（INFO）", loc="left")
    axes[1].legend(fontsize=8)
    axes[1].grid(True, alpha=0.25)
    fig.suptitle("第 16 章：目标预算与主机实测必须分开解释", fontsize=15)
    fig.tight_layout(rect=(0.0, 0.18, 1.0, 0.94))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_report(path: Path, metrics: list[dict[str, object]], compiler_display: str, unit_output: str, replay_output: str, benchmark_output: str) -> None:
    passes = sum(row["status"] == "PASS" for row in metrics)
    fails = sum(row["status"] == "FAIL" for row in metrics)
    infos = sum(row["status"] == "INFO" for row in metrics)
    lines = [
        "# 第 16 章报告：控制 ISR 执行顺序与时间预算",
        "",
        "本报告由 `scripts/run_isr_timing_tests.py` 生成。顺序与故障行为来自真实编译执行的 C 编排层；主机计时只作为回归信息。",
        "",
        "## 摘要",
        "",
        f"- 编译器：`{compiler_display}`",
        f"- 指标：PASS {passes} / FAIL {fails} / INFO {infos}",
        f"- 控制周期：{CONTROL_PERIOD_NS / 1000.0:.1f} us",
        f"- ISR 目标预算：{TARGET_ISR_BUDGET_NS / 1000.0:.1f} us",
        "",
        "```text",
        unit_output,
        "```",
        "",
        "```text",
        replay_output,
        benchmark_output,
        "```",
        "",
        "## 指标",
        "",
        "| 场景 | 指标 | 实际值 | 限制/参考 | 状态 | 说明 |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in metrics:
        lines.append(f"| `{row['case']}` | `{row['metric']}` | {float(row['value']):.6g} | {float(row['limit']):.6g} | {row['status']} | {row['note']} |")
    lines.extend([
        "",
        "## 证据边界",
        "",
        "顺序测试可以判断上一周期 compare 是否先应用、OCP 是否在同一次调用中关闭 active enable。3.5 us 是目标分配预算，Windows 主机批次耗时是回归基线；只有目标 MCU 构建后的周期计数器或示波器测量才能判断 5 us 截止时间是否满足。",
        "",
    ])
    text = "\n".join(lines).replace("\r\n", "\n").replace("\r", "\n")
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(text.replace("\n", "\r\n"))


def main() -> int:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    WAVE_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    write_rows(WAVE_DIR / "16-isr-budget.csv", BUDGET_ROWS)

    compiler, hint = find_compiler()
    if compiler is None:
        print("summary,BLOCKED,未找到 C 编译器")
        return 2
    version = compiler_version(compiler, hint)
    compiler_display = f"{hint} {version}" if version else hint

    programs = {
        "unit": (ROOT / "tests" / "test_digital_power_control_isr.c", BUILD_DIR / ("digital_power_control_isr_tests.exe" if os.name == "nt" else "digital_power_control_isr_tests")),
        "replay": (ROOT / "tests" / "replay_digital_power_control_isr.c", BUILD_DIR / ("digital_power_control_isr_replay.exe" if os.name == "nt" else "digital_power_control_isr_replay")),
        "benchmark": (ROOT / "tests" / "benchmark_digital_power_control_isr.c", BUILD_DIR / ("digital_power_control_isr_benchmark.exe" if os.name == "nt" else "digital_power_control_isr_benchmark")),
    }
    for label, (program_source, exe_path) in programs.items():
        code, output = run_command(compile_command(compiler, hint, [*COMMON_SOURCES, program_source], exe_path), BUILD_DIR)
        if code != 0:
            print(output)
            print(f"summary,FAIL,{label}_build_exit_code={code}")
            return 1

    unit_code, unit_output = run_command([str(programs["unit"][1])], BUILD_DIR)
    if unit_code != 0:
        print(unit_output)
        return 1
    sequence_path = WAVE_DIR / "16-isr-sequence.csv"
    replay_code, replay_output = run_command([str(programs["replay"][1]), str(sequence_path)], BUILD_DIR)
    if replay_code != 0:
        print(replay_output)
        return 1
    timing_path = WAVE_DIR / "16-isr-host-timing.csv"
    benchmark_code, benchmark_output = run_command([str(programs["benchmark"][1]), str(timing_path)], BUILD_DIR)
    if benchmark_code != 0:
        print(benchmark_output)
        return 1

    sequence = read_sequence(sequence_path)
    timing = read_timing(timing_path)
    metrics = build_metrics(sequence, timing, unit_output)
    write_rows(WAVE_DIR / "16-isr-summary.csv", metrics)
    plot_sequence(WAVE_DIR / "16-isr-sequence.png", sequence)
    plot_budget_and_timing(WAVE_DIR / "16-isr-budget-and-host-timing.png", timing)
    write_report(REPORT_DIR / "16-isr-timing-report.md", metrics, compiler_display, unit_output, replay_output, benchmark_output)

    passes = sum(row["status"] == "PASS" for row in metrics)
    fails = sum(row["status"] == "FAIL" for row in metrics)
    infos = sum(row["status"] == "INFO" for row in metrics)
    timing_values = [float(row["ns_per_call"]) for row in timing]
    print("已生成第 16 章 ISR 顺序、预算和主机回归证据。")
    print(f"summary,pass={passes},fail={fails},info={infos},cycles={len(sequence)},batches={len(timing)}")
    print(f"toolchain,{hint},{compiler_display}")
    print(f"target,period_ns={CONTROL_PERIOD_NS:.0f},isr_budget_ns={TARGET_ISR_BUDGET_NS:.0f},reserve_ns={CONTROL_PERIOD_NS - TARGET_ISR_BUDGET_NS:.0f}")
    print(f"host,p50_ns={percentile(timing_values, 0.50):.3f},p99_ns={percentile(timing_values, 0.99):.3f},max_ns={max(timing_values):.3f}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
