from __future__ import annotations

import csv
import os
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt

from run_host_build_tests import compiler_family, compiler_version, find_compiler, run_command


ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "artifacts" / "host-build" / "chapter17"
WAVE_DIR = ROOT / "waveforms"
REPORT_DIR = ROOT / "reports"

COMMON_SOURCES = [
    ROOT / "src" / "digital_power_adc_map.c",
    ROOT / "src" / "digital_power_control_fixed.c",
    ROOT / "src" / "digital_power_pwm_map.c",
    ROOT / "src" / "digital_power_control_isr.c",
    ROOT / "src" / "digital_power_firmware.c",
    ROOT / "tests" / "fake_digital_power_hal.c",
]

EVENT_COLUMNS = [
    "pwm_update",
    "adc_read",
    "pwm_disable",
    "pwm_write",
    "communication",
    "storage",
    "critical_enter",
    "critical_exit",
]


def compile_command(compiler: str, hint: str, sources: list[Path], output: Path) -> list[str]:
    family = compiler_family(compiler, hint)
    includes = [ROOT / "src", ROOT / "tests"]
    include_args: list[str] = []
    for include in includes:
        include_args.extend(["-I", str(include)])
    if family == "zig":
        return [compiler, "cc", "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror", *include_args, *map(str, sources), "-o", str(output)]
    if family == "msvc":
        msvc_includes = [f"/I{include}" for include in includes]
        return [compiler, "/nologo", "/O2", "/W4", "/WX", *msvc_includes, *map(str, sources), f"/Fe:{output}"]
    return [compiler, "-std=c99", "-O2", "-Wall", "-Wextra", "-Werror", *include_args, *map(str, sources), "-o", str(output)]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def phase_events(events: list[dict[str, str]], phase: str) -> list[str]:
    return [row["event"] for row in events if row["phase"] == phase]


def state_by_phase(states: list[dict[str, str]], phase: str) -> dict[str, str]:
    return next(row for row in states if row["phase"] == phase)


def metric(case_id: str, name: str, value: float, expected: float, passed: bool, note: str) -> dict[str, object]:
    return {
        "case": case_id,
        "metric": name,
        "value": value,
        "expected": expected,
        "status": "PASS" if passed else "FAIL",
        "note": note,
    }


def build_ownership(events: list[dict[str, str]]) -> list[dict[str, object]]:
    groups = {
        "control_isr": [row for row in events if row["phase"].endswith("_isr")],
        "background": [row for row in events if row["phase"] == "background"],
        "shared_exchange": [row for row in events if row["phase"].startswith("command_") or row["phase"] == "telemetry_read"],
    }
    rows: list[dict[str, object]] = []
    for task, task_events in groups.items():
        counts = Counter(row["event"] for row in task_events)
        rows.append({"task": task, **{name: counts[name] for name in EVENT_COLUMNS}})
    return rows


def build_metrics(events: list[dict[str, str]], states: list[dict[str, str]], unit_output: str) -> list[dict[str, object]]:
    metrics: list[dict[str, object]] = []
    isr_events = [row["event"] for row in events if row["phase"].endswith("_isr")]
    realtime_only = not any(event in ("communication", "storage", "critical_enter", "critical_exit") for event in isr_events)
    background_ok = phase_events(events, "background") == ["communication", "storage"]
    normal_ok = phase_events(events, "startup_isr") == ["pwm_update", "adc_read", "pwm_write"]
    ocp_ok = phase_events(events, "ocp_isr") == ["pwm_update", "adc_read", "pwm_disable", "pwm_write"]
    adc_failure_ok = phase_events(events, "adc_failure_isr") == ["pwm_update", "adc_read", "pwm_disable", "pwm_write"]
    command_sections_ok = all(
        phase_events(events, phase) == ["critical_enter", "critical_exit"]
        for phase in ("command_enable", "command_disable", "command_restart")
    )
    telemetry_section_ok = phase_events(events, "telemetry_read") == ["critical_enter", "critical_exit"]

    command_disable = state_by_phase(states, "command_disable")
    disable_isr = state_by_phase(states, "disable_isr")
    disable_boundary_ok = (
        command_disable["active_command_enable"] == "1"
        and command_disable["pending_command_enable"] == "0"
        and command_disable["command_pending"] == "1"
        and disable_isr["active_command_enable"] == "0"
        and disable_isr["command_pending"] == "0"
        and disable_isr["hal_active_enable"] == "0"
    )
    restart_queue = state_by_phase(states, "restart_queue_isr")
    restart_apply = state_by_phase(states, "restart_apply_isr")
    restart_sync_ok = restart_queue["hal_active_enable"] == "0" and restart_queue["hal_pending_enable"] == "1" and restart_apply["hal_active_enable"] == "1"
    failure_state = state_by_phase(states, "adc_failure_isr")
    failure_visible = failure_state["adc_sample_valid"] == "0" and failure_state["hal_active_enable"] == "0"
    background_state = state_by_phase(states, "background")
    apply_state = state_by_phase(states, "apply_isr")
    background_no_control = background_state["control_cycles"] == apply_state["control_cycles"]

    checks = [
        ("ownership", "isr_realtime_operations_only", realtime_only, "ISR 事件中不得出现通信、存储或后台临界区"),
        ("ownership", "background_services_only", background_ok, "后台步骤只调用通信与存储服务"),
        ("normal_isr", "normal_hal_order", normal_ok, "正常周期按更新、ADC、PWM 预装载顺序调用 HAL"),
        ("ocp_isr", "disable_precedes_preload_write", ocp_ok, "OCP 立即关断必须先于预装载写入"),
        ("adc_failure", "adc_failure_fail_safe_order", adc_failure_ok, "ADC 读取失败时立即关断并写入关闭预装载"),
        ("shared_exchange", "commands_use_critical_section", command_sections_ok, "后台命令使用短临界区完整发布"),
        ("shared_exchange", "telemetry_copy_uses_critical_section", telemetry_section_ok, "后台遥测读取使用短临界区复制快照"),
        ("command_boundary", "disable_commits_at_next_isr", disable_boundary_ok, "后台 disable 命令只在下一 ISR 边界提交"),
        ("command_boundary", "restart_waits_for_pwm_update", restart_sync_ok, "重新使能先写 pending，再由更新事件生效"),
        ("adc_failure", "failure_visible_and_pwm_off", failure_visible, "ADC 无效状态进入遥测且硬件 PWM 关闭"),
        ("background", "background_does_not_advance_control", background_no_control, "后台步骤不得推进控制周期"),
    ]
    for case_id, name, passed, note in checks:
        metrics.append(metric(case_id, name, 1.0 if passed else 0.0, 1.0, passed, note))

    for line in unit_output.splitlines():
        parts = line.strip().split(",", 1)
        if len(parts) == 2 and parts[0] in ("PASS", "FAIL"):
            passed = parts[0] == "PASS"
            metrics.append(metric("firmware_unit_tests", parts[1], 1.0 if passed else 0.0, 1.0, passed, "C 固件分层单元测试"))
    return metrics


def plot_event_trace(path: Path, events: list[dict[str, str]]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    phases: list[str] = []
    for row in events:
        if row["phase"] not in phases:
            phases.append(row["phase"])
    colors = {
        "pwm_update": "#0f766e",
        "adc_read": "#2563eb",
        "pwm_disable": "#be123c",
        "pwm_write": "#d97706",
        "communication": "#7c3aed",
        "storage": "#475569",
        "critical_enter": "#64748b",
        "critical_exit": "#94a3b8",
    }
    fig, ax = plt.subplots(figsize=(12.0, 7.4))
    for y, phase in enumerate(phases):
        phase_rows = [row for row in events if row["phase"] == phase]
        for row in phase_rows:
            x = int(row["event_order"])
            event = row["event"]
            ax.scatter(x, y, s=115, color=colors[event], edgecolor="white", linewidth=0.8, zorder=3)
            ax.text(x + 0.08, y, event, va="center", fontsize=8)
        if len(phase_rows) > 1:
            ax.plot([0, len(phase_rows) - 1], [y, y], color="#cbd5e1", linewidth=1.2, zorder=1)
    ax.set_yticks(range(len(phases)))
    ax.set_yticklabels(phases)
    ax.invert_yaxis()
    ax.set_xlim(-0.15, max(int(row["event_order"]) for row in events) + 0.65)
    ax.set_xlabel("同一阶段内的 HAL 调用顺序")
    ax.set_title("假 HAL 记录的真实调用事件", loc="left")
    ax.grid(True, axis="x", alpha=0.25)
    fig.suptitle("第 17 章：实时、后台和共享交换的调用边界", fontsize=15)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_ownership(path: Path, ownership: list[dict[str, object]]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    labels = [str(row["task"]) for row in ownership]
    matrix = [[int(row[event]) for event in EVENT_COLUMNS] for row in ownership]
    fig, ax = plt.subplots(figsize=(12.0, 4.8))
    image = ax.imshow(matrix, cmap="Blues", aspect="auto", vmin=0)
    for y, row in enumerate(matrix):
        for x, value in enumerate(row):
            ax.text(x, y, str(value), ha="center", va="center", color="white" if value >= 4 else "#172033", fontsize=10)
    ax.set_xticks(range(len(EVENT_COLUMNS)))
    ax.set_xticklabels(EVENT_COLUMNS, rotation=25, ha="right")
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels)
    ax.set_title("事件计数来自回放 CSV；0 表示该职责层没有调用该操作", loc="left")
    fig.colorbar(image, ax=ax, label="调用次数")
    fig.suptitle("第 17 章：任务职责矩阵", fontsize=15)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.93))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_report(path: Path, metrics: list[dict[str, object]], compiler_display: str, unit_output: str, replay_output: str) -> None:
    passes = sum(row["status"] == "PASS" for row in metrics)
    fails = sum(row["status"] == "FAIL" for row in metrics)
    lines = [
        "# 第 17 章报告：实时/后台任务与 HAL 适配边界",
        "",
        "本报告由 `scripts/run_firmware_layering_tests.py` 生成。HAL 调用顺序、命令边界和任务归属来自真实编译执行的 C 固件编排层与假硬件适配器。",
        "",
        "## 摘要",
        "",
        f"- 编译器：`{compiler_display}`",
        f"- 指标：PASS {passes} / FAIL {fails}",
        "",
        "```text",
        unit_output,
        "```",
        "",
        "```text",
        replay_output,
        "```",
        "",
        "## 指标",
        "",
        "| 场景 | 指标 | 实际值 | 期望 | 状态 | 说明 |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in metrics:
        lines.append(f"| `{row['case']}` | `{row['metric']}` | {float(row['value']):.6g} | {float(row['expected']):.6g} | {row['status']} | {row['note']} |")
    lines.extend([
        "",
        "## 证据边界",
        "",
        "假 HAL 可以验证谁调用 ADC/PWM、调用先后和共享数据边界。它没有具体 MCU 寄存器地址、DMA 标志、NVIC 配置或 Flash 驱动，因此本报告属于平台无关固件集成证据，不等于目标板外设已经工作。",
        "",
    ])
    text = "\n".join(lines).replace("\r\n", "\n").replace("\r", "\n")
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(text.replace("\n", "\r\n"))


def main() -> int:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    WAVE_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    compiler, hint = find_compiler()
    if compiler is None:
        print("summary,BLOCKED,未找到 C 编译器")
        return 2
    version = compiler_version(compiler, hint)
    compiler_display = f"{hint} {version}" if version else hint

    unit_exe = BUILD_DIR / ("digital_power_firmware_tests.exe" if os.name == "nt" else "digital_power_firmware_tests")
    replay_exe = BUILD_DIR / ("digital_power_firmware_replay.exe" if os.name == "nt" else "digital_power_firmware_replay")
    for label, source, output in (
        ("unit", ROOT / "tests" / "test_digital_power_firmware.c", unit_exe),
        ("replay", ROOT / "tests" / "replay_digital_power_firmware.c", replay_exe),
    ):
        code, build_output = run_command(compile_command(compiler, hint, [*COMMON_SOURCES, source], output), BUILD_DIR)
        if code != 0:
            print(build_output)
            print(f"summary,FAIL,{label}_build_exit_code={code}")
            return 1

    unit_code, unit_output = run_command([str(unit_exe)], BUILD_DIR)
    if unit_code != 0:
        print(unit_output)
        return 1
    event_path = WAVE_DIR / "17-hal-events.csv"
    state_path = WAVE_DIR / "17-firmware-states.csv"
    replay_code, replay_output = run_command([str(replay_exe), str(event_path), str(state_path)], BUILD_DIR)
    if replay_code != 0:
        print(replay_output)
        return 1

    events = read_csv(event_path)
    states = read_csv(state_path)
    ownership = build_ownership(events)
    metrics = build_metrics(events, states, unit_output)
    write_rows(WAVE_DIR / "17-task-ownership.csv", ownership)
    write_rows(WAVE_DIR / "17-layering-summary.csv", metrics)
    plot_event_trace(WAVE_DIR / "17-hal-call-order.png", events)
    plot_ownership(WAVE_DIR / "17-task-ownership.png", ownership)
    write_report(REPORT_DIR / "17-firmware-layering-report.md", metrics, compiler_display, unit_output, replay_output)

    passes = sum(row["status"] == "PASS" for row in metrics)
    fails = sum(row["status"] == "FAIL" for row in metrics)
    print("已生成第 17 章固件分层、HAL 调用和共享数据证据。")
    print(f"summary,pass={passes},fail={fails},phases={len(states)},events={len(events)}")
    print(f"toolchain,{hint},{compiler_display}")
    print("ownership,isr=update+adc+pwm,background=communication+storage,shared=critical_sections")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
