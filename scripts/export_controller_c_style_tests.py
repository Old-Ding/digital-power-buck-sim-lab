from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
WAVE_DIR = ROOT / "waveforms"
REPORT_DIR = ROOT / "reports"


class ControlState(IntEnum):
    IDLE = 0
    SOFT_START = 1
    RUN = 2
    FAULT = 3


class FaultCode(IntEnum):
    NONE = 0
    OCP = 1
    OVP = 2
    UVLO = 3
    OTP = 4


@dataclass
class Config:
    ts_ctrl_s: float = 5.0e-6
    substeps: int = 10
    vin_nom_v: float = 24.0
    vref_final_v: float = 12.0
    soft_start_ramp_v_per_s: float = 300.0
    kp: float = 0.05
    ki: float = 80.0
    duty_feedforward: float = 0.5
    duty_min: float = 0.0
    duty_max: float = 0.65
    adc_iir_alpha: float = 1.0
    ocp_threshold_a: float = 6.5
    ovp_threshold_v: float = 13.2
    uvlo_threshold_v: float = 18.0
    otp_threshold_c: float = 100.0
    l_out_h: float = 22.0e-6
    c_out_f: float = 100.0e-6
    r_series_ohm: float = 0.02

    @property
    def dt_s(self) -> float:
        return self.ts_ctrl_s / self.substeps


@dataclass
class Context:
    state: ControlState = ControlState.IDLE
    latched_fault: FaultCode = FaultCode.NONE
    vout_filter_v: float = 12.0
    vref_cmd_v: float = 0.0
    integrator: float = 0.0
    last_error_v: float = 0.0
    tick_count: int = 0


@dataclass
class Input:
    enable: bool
    clear_fault: bool
    vin_v: float
    vout_adc_v: float
    iout_a: float
    temperature_c: float


def clamp(value: float, low: float, high: float) -> float:
    return min(max(value, low), high)


def detect_fault(cfg: Config, inp: Input, vout_meas_v: float) -> FaultCode:
    if inp.iout_a >= cfg.ocp_threshold_a:
        return FaultCode.OCP
    if vout_meas_v >= cfg.ovp_threshold_v:
        return FaultCode.OVP
    if inp.vin_v <= cfg.uvlo_threshold_v:
        return FaultCode.UVLO
    if inp.temperature_c >= cfg.otp_threshold_c:
        return FaultCode.OTP
    return FaultCode.NONE


def update_state(ctx: Context, cfg: Config, inp: Input, active_fault: FaultCode) -> None:
    if active_fault != FaultCode.NONE:
        ctx.latched_fault = active_fault
        ctx.state = ControlState.FAULT
        return

    if ctx.state == ControlState.FAULT:
        if inp.clear_fault:
            ctx.latched_fault = FaultCode.NONE
            ctx.state = ControlState.SOFT_START if inp.enable else ControlState.IDLE
            ctx.vref_cmd_v = 0.0
            ctx.integrator = 0.0
        return

    if not inp.enable:
        ctx.state = ControlState.IDLE
        ctx.vref_cmd_v = 0.0
        ctx.integrator = 0.0
        return

    if ctx.state == ControlState.IDLE:
        ctx.state = ControlState.SOFT_START

    if ctx.state == ControlState.SOFT_START and ctx.vref_cmd_v >= cfg.vref_final_v:
        ctx.state = ControlState.RUN


def controller_step(ctx: Context, cfg: Config, inp: Input) -> dict[str, float | int | bool]:
    ctx.tick_count += 1
    alpha = clamp(cfg.adc_iir_alpha, 0.0, 1.0)
    ctx.vout_filter_v = alpha * inp.vout_adc_v + (1.0 - alpha) * ctx.vout_filter_v

    active_fault = detect_fault(cfg, inp, ctx.vout_filter_v)
    update_state(ctx, cfg, inp, active_fault)

    if ctx.state == ControlState.SOFT_START:
        ctx.vref_cmd_v = clamp(
            ctx.vref_cmd_v + cfg.soft_start_ramp_v_per_s * cfg.ts_ctrl_s,
            0.0,
            cfg.vref_final_v,
        )
    elif ctx.state == ControlState.RUN:
        ctx.vref_cmd_v = cfg.vref_final_v

    error_v = ctx.vref_cmd_v - ctx.vout_filter_v
    p_term = cfg.kp * error_v
    feedforward_scale = ctx.vref_cmd_v / cfg.vref_final_v if cfg.vref_final_v > 0.0 else 0.0
    duty_feedforward_cmd = cfg.duty_feedforward * clamp(feedforward_scale, 0.0, 1.0)
    duty_raw = duty_feedforward_cmd + p_term + ctx.integrator
    saturation = duty_raw > cfg.duty_max or duty_raw < cfg.duty_min
    allow_integrate = (
        not saturation
        or (duty_raw > cfg.duty_max and error_v < 0.0)
        or (duty_raw < cfg.duty_min and error_v > 0.0)
    )

    if ctx.state == ControlState.RUN and allow_integrate:
        ctx.integrator += cfg.ki * cfg.ts_ctrl_s * error_v

    duty_raw = duty_feedforward_cmd + p_term + ctx.integrator
    duty_cmd = clamp(duty_raw, cfg.duty_min, cfg.duty_max)
    saturation = abs(duty_cmd - duty_raw) > 1e-12

    pwm_enable = ctx.state in (ControlState.SOFT_START, ControlState.RUN) and ctx.latched_fault == FaultCode.NONE
    if not pwm_enable:
        duty_cmd = 0.0

    ctx.last_error_v = error_v

    return {
        "state": int(ctx.state),
        "active_fault": int(active_fault),
        "latched_fault": int(ctx.latched_fault),
        "pwm_enable": pwm_enable,
        "vout_meas_v": ctx.vout_filter_v,
        "vref_cmd_v": ctx.vref_cmd_v,
        "error_v": error_v,
        "p_term": p_term,
        "integrator": ctx.integrator,
        "duty_raw": duty_raw,
        "duty_cmd": duty_cmd,
        "saturation": saturation,
        "allow_integrate": allow_integrate,
    }


def load_resistance(case_id: str, time_s: float) -> float:
    if case_id == "load_step_50_100_50" and 0.050 <= time_s < 0.064:
        return 2.4
    if case_id == "load_step_50_100_50":
        return 4.8
    return 2.4


def injected_fault_current(case_id: str, time_s: float, load_current_a: float) -> float:
    if case_id == "ocp_latch_clear" and 0.052 <= time_s < 0.058:
        return 7.2
    return load_current_a


def vin_profile(case_id: str, time_s: float, cfg: Config) -> float:
    if case_id == "uvlo_blocks_pwm" and 0.052 <= time_s < 0.058:
        return 16.0
    return cfg.vin_nom_v


def clear_fault_cmd(case_id: str, time_s: float) -> bool:
    if case_id == "ocp_latch_clear":
        return 0.056 <= time_s < 0.0565 or 0.062 <= time_s < 0.0625
    if case_id == "uvlo_blocks_pwm":
        return 0.062 <= time_s < 0.0625
    return False


def simulate_case(case_id: str, stop_time_s: float, cfg: Config) -> list[dict[str, float | int | bool | str]]:
    ctx, vout_v, inductor_current_a = initial_conditions(case_id, cfg)
    rows: list[dict[str, float | int | bool | str]] = []

    steps = int(stop_time_s / cfg.dt_s) + 1
    last_output = None

    for idx in range(steps):
        time_s = idx * cfg.dt_s
        rload = load_resistance(case_id, time_s)
        load_current_a = vout_v / rload if rload > 0 else 0.0
        vin_v = vin_profile(case_id, time_s, cfg)

        if idx % cfg.substeps == 0:
            inp = Input(
                enable=True,
                clear_fault=clear_fault_cmd(case_id, time_s),
                vin_v=vin_v,
                vout_adc_v=vout_v,
                iout_a=injected_fault_current(case_id, time_s, load_current_a),
                temperature_c=45.0,
            )
            last_output = controller_step(ctx, cfg, inp)

            row = {
                "case": case_id,
                "time_s": time_s,
                "vin_v": vin_v,
                "vout_v": vout_v,
                "load_current_a": load_current_a,
                "inductor_current_a": inductor_current_a,
                "load_resistance_ohm": rload,
                **last_output,
            }
            rows.append(row)

        duty = float(last_output["duty_cmd"]) if last_output else 0.0
        di_dt = (vin_v * duty - vout_v - inductor_current_a * cfg.r_series_ohm) / cfg.l_out_h
        dv_dt = (inductor_current_a - load_current_a) / cfg.c_out_f
        inductor_current_a = max(0.0, inductor_current_a + di_dt * cfg.dt_s)
        vout_v += dv_dt * cfg.dt_s

    return rows


def initial_conditions(case_id: str, cfg: Config) -> tuple[Context, float, float]:
    if case_id == "soft_start_40ms":
        return Context(vout_filter_v=0.0), 0.0, 0.0

    rload = load_resistance(case_id, 0.0)
    vout_v = cfg.vref_final_v
    inductor_current_a = vout_v / rload
    integrator = (vout_v + inductor_current_a * cfg.r_series_ohm) / cfg.vin_nom_v - cfg.duty_feedforward
    ctx = Context(
        state=ControlState.RUN,
        latched_fault=FaultCode.NONE,
        vout_filter_v=vout_v,
        vref_cmd_v=cfg.vref_final_v,
        integrator=integrator,
    )
    return ctx, vout_v, inductor_current_a


def first_time(rows: list[dict], predicate) -> float | None:
    for row in rows:
        if predicate(row):
            return float(row["time_s"])
    return None


def recovery_time_ms(rows: list[dict], start_s: float, vref: float, band_v: float) -> float | None:
    tail = [row for row in rows if float(row["time_s"]) >= start_s]
    for index, row in enumerate(tail):
        if all(abs(float(item["vout_v"]) - vref) <= band_v for item in tail[index:]):
            return (float(row["time_s"]) - start_s) * 1000.0
    return None


def build_summary(all_rows: dict[str, list[dict]], cfg: Config) -> list[dict[str, str | float]]:
    summary: list[dict[str, str | float]] = []

    steady = all_rows["steady_12v"]
    steady_tail = [row for row in steady if float(row["time_s"]) >= 0.056]
    steady_vout = float(np.mean([float(row["vout_v"]) for row in steady_tail]))
    steady_duty = float(np.mean([float(row["duty_cmd"]) for row in steady_tail]))
    steady_pass = abs(steady_vout - cfg.vref_final_v) <= 0.12 and all(int(row["state"]) == int(ControlState.RUN) for row in steady_tail[-100:])
    summary.append(metric_row("steady_12v", "tail_vout_mean_v", steady_vout, "PASS" if steady_pass else "FAIL", "56ms 后 Vout 均值进入 1% 带内"))
    summary.append(metric_row("steady_12v", "tail_duty_mean", steady_duty, "INFO", "稳态 duty 约等于 Vin 到 Vout 比值加损耗补偿"))

    soft = all_rows["soft_start_40ms"]
    soft_peak = max(float(row["vout_v"]) for row in soft)
    soft_run_time = first_time(soft, lambda row: int(row["state"]) == int(ControlState.RUN))
    soft_pass = soft_peak <= 12.35 and soft_run_time is not None and 38.5 <= soft_run_time * 1000.0 <= 42.0
    summary.append(metric_row("soft_start_40ms", "vout_peak_v", soft_peak, "PASS" if soft_pass else "FAIL", "软启动峰值不过高，并在约 40ms 进入 RUN"))
    summary.append(metric_row("soft_start_40ms", "first_run_time_ms", soft_run_time * 1000.0 if soft_run_time is not None else math.nan, "INFO", "RUN 首次出现时间"))

    load = all_rows["load_step_50_100_50"]
    up = [row for row in load if 0.050 <= float(row["time_s"]) < 0.064]
    down = [row for row in load if float(row["time_s"]) >= 0.064]
    undershoot = cfg.vref_final_v - min(float(row["vout_v"]) for row in up)
    overshoot = max(float(row["vout_v"]) for row in down) - cfg.vref_final_v
    rec_up = recovery_time_ms([row for row in load if 0.050 <= float(row["time_s"]) < 0.064], 0.050, cfg.vref_final_v, 0.12)
    rec_down = recovery_time_ms(down, 0.064, cfg.vref_final_v, 0.12)
    load_pass = undershoot <= 1.2 and overshoot <= 1.2 and rec_up is not None
    summary.append(metric_row("load_step_50_100_50", "undershoot_v", undershoot, "PASS" if load_pass else "FAIL", "50% 到 100% 负载上跳下陷"))
    summary.append(metric_row("load_step_50_100_50", "overshoot_v", overshoot, "INFO", "100% 到 50% 负载下跳过冲"))
    summary.append(metric_row("load_step_50_100_50", "recovery_up_ms", rec_up if rec_up is not None else math.nan, "INFO", "上跳后回到 1% 带内时间"))
    summary.append(metric_row("load_step_50_100_50", "recovery_down_ms", rec_down if rec_down is not None else math.nan, "INFO", "下跳后回到 1% 带内时间"))

    ocp = all_rows["ocp_latch_clear"]
    first_fault = first_time(ocp, lambda row: int(row["latched_fault"]) == int(FaultCode.OCP))
    clear_while_fault = [row for row in ocp if 0.056 <= float(row["time_s"]) < 0.0565]
    after_clear = [row for row in ocp if float(row["time_s"]) >= 0.0625]
    ocp_pwm_off = all(not bool(row["pwm_enable"]) and float(row["duty_cmd"]) == 0.0 for row in ocp if 0.0525 <= float(row["time_s"]) < 0.058)
    ocp_stays_latched = all(int(row["latched_fault"]) == int(FaultCode.OCP) for row in clear_while_fault)
    ocp_restarts = any(
        int(row["latched_fault"]) == int(FaultCode.NONE)
        and int(row["state"]) in (int(ControlState.SOFT_START), int(ControlState.RUN))
        for row in after_clear
    )
    ocp_pass = first_fault is not None and ocp_pwm_off and ocp_stays_latched and ocp_restarts
    summary.append(metric_row("ocp_latch_clear", "first_ocp_time_ms", first_fault * 1000.0 if first_fault is not None else math.nan, "PASS" if ocp_pass else "FAIL", "OCP 锁存、关 PWM、故障未消失时不能清除，故障消失后 clear 进入重启路径"))

    uvlo = all_rows["uvlo_blocks_pwm"]
    uvlo_window = [row for row in uvlo if 0.0525 <= float(row["time_s"]) < 0.058]
    uvlo_faulted = any(int(row["latched_fault"]) == int(FaultCode.UVLO) for row in uvlo_window)
    uvlo_pwm_off = all(not bool(row["pwm_enable"]) and float(row["duty_cmd"]) == 0.0 for row in uvlo_window)
    uvlo_pass = uvlo_faulted and uvlo_pwm_off
    summary.append(metric_row("uvlo_blocks_pwm", "uvlo_pwm_off", 1.0 if uvlo_pwm_off else 0.0, "PASS" if uvlo_pass else "FAIL", "Vin 低于 UVLO 时 PWM 统一出口关断"))

    pass_count = sum(1 for row in summary if row["status"] == "PASS")
    fail_count = sum(1 for row in summary if row["status"] == "FAIL")
    summary.append(metric_row("all", "pass_count", pass_count, "INFO", "PASS 行数"))
    summary.append(metric_row("all", "fail_count", fail_count, "INFO", "FAIL 行数"))
    return summary


def metric_row(case: str, metric: str, value: float, status: str, note: str) -> dict[str, str | float]:
    return {"case": case, "metric": metric, "value": value, "status": status, "note": note}


def write_trace(path: Path, all_rows: dict[str, list[dict]]) -> None:
    fieldnames = [
        "case",
        "time_s",
        "vin_v",
        "vout_v",
        "load_current_a",
        "inductor_current_a",
        "load_resistance_ohm",
        "state",
        "active_fault",
        "latched_fault",
        "pwm_enable",
        "vout_meas_v",
        "vref_cmd_v",
        "error_v",
        "p_term",
        "integrator",
        "duty_raw",
        "duty_cmd",
        "saturation",
        "allow_integrate",
    ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rows in all_rows.values():
            writer.writerows(rows)


def write_summary(path: Path, summary: list[dict[str, str | float]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["case", "metric", "value", "status", "note"])
        writer.writeheader()
        writer.writerows(summary)


def write_report(path: Path, summary: list[dict[str, str | float]], cfg: Config) -> None:
    lines = [
        "# 第 10 章测试报告：C 风格控制器场景验证",
        "",
        "本报告由 `scripts/export_controller_c_style_tests.py` 生成，验证对象是 `src/digital_power_control.c/.h` 对应的固定周期控制器接口和同等离散算法测试台。",
        "",
        "## 参数",
        "",
        "| 参数 | 数值 |",
        "| --- | --- |",
        f"| 控制周期 | {cfg.ts_ctrl_s * 1e6:.3f} us |",
        f"| 目标输出 | {cfg.vref_final_v:.3f} V |",
        f"| 软启动斜率 | {cfg.soft_start_ramp_v_per_s:.1f} V/s |",
        f"| PI 参数 | Kp = {cfg.kp:.4g}, Ki = {cfg.ki:.4g} |",
        f"| duty 限幅 | {cfg.duty_min:.3f} - {cfg.duty_max:.3f} |",
        f"| ADC IIR alpha | {cfg.adc_iir_alpha:.3f} |",
        f"| OCP / OVP / UVLO | {cfg.ocp_threshold_a:.2f} A / {cfg.ovp_threshold_v:.2f} V / {cfg.uvlo_threshold_v:.2f} V |",
        "",
        "## 场景结果",
        "",
        "| 场景 | 指标 | 数值 | 状态 | 说明 |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for row in summary:
        value = row["value"]
        if isinstance(value, float):
            value_text = "NaN" if math.isnan(value) else f"{value:.6g}"
        else:
            value_text = str(value)
        lines.append(f"| `{row['case']}` | `{row['metric']}` | {value_text} | {row['status']} | {row['note']} |")

    lines.extend(
        [
            "",
            "## 边界",
            "",
            "本报告验证固定周期控制器的数据流、状态机、限幅、软启动和故障锁存逻辑。当前环境没有 C 编译器，因此本报告不声明完成 MCU 编译、定点化、寄存器驱动或 HIL 验证。",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def plot_scenarios(path: Path, all_rows: dict[str, list[dict]], cfg: Config) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, axes = plt.subplots(4, 1, figsize=(13.5, 9.5), sharex=False)
    cases = ["soft_start_40ms", "load_step_50_100_50", "ocp_latch_clear", "uvlo_blocks_pwm"]
    colors = ["#1f77b4", "#e4572e", "#2e8b57", "#7a3e9d"]

    for ax, case, color in zip(axes, cases, colors):
        rows = all_rows[case]
        t_ms = np.array([float(row["time_s"]) * 1000.0 for row in rows])
        vout = np.array([float(row["vout_v"]) for row in rows])
        duty = np.array([float(row["duty_cmd"]) for row in rows])
        state = np.array([int(row["state"]) for row in rows])
        fault = np.array([int(row["latched_fault"]) for row in rows])

        ax.plot(t_ms, vout, color=color, linewidth=1.6, label="Vout")
        ax.axhline(cfg.vref_final_v, color="#666666", linestyle="--", linewidth=0.9)
        ax.set_ylabel(f"{case}\nVout / V")
        ax.grid(True, alpha=0.28)
        ax2 = ax.twinx()
        ax2.plot(t_ms, duty, color="#555555", linewidth=1.1, alpha=0.72, label="duty")
        ax2.step(t_ms, state / 10.0, where="post", color="#0b7285", linewidth=1.0, alpha=0.65, label="state/10")
        ax2.step(t_ms, fault / 10.0, where="post", color="#a61e4d", linewidth=1.0, alpha=0.65, label="fault/10")
        ax2.set_ylabel("duty/state")

    axes[0].set_title("C 风格控制器场景测试：软启动、负载突变、OCP 锁存、UVLO 关断")
    axes[-1].set_xlabel("Time / ms")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_telemetry(path: Path, all_rows: dict[str, list[dict]], cfg: Config) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    rows = all_rows["load_step_50_100_50"]
    t_ms = np.array([float(row["time_s"]) * 1000.0 for row in rows])
    signals = {
        "error_v": np.array([float(row["error_v"]) for row in rows]),
        "integrator": np.array([float(row["integrator"]) for row in rows]),
        "duty_raw": np.array([float(row["duty_raw"]) for row in rows]),
        "duty_cmd": np.array([float(row["duty_cmd"]) for row in rows]),
        "saturation": np.array([1.0 if bool(row["saturation"]) else 0.0 for row in rows]),
    }

    fig, axes = plt.subplots(3, 1, figsize=(13.5, 8.0), sharex=True)
    axes[0].plot(t_ms, signals["error_v"], color="#7a3e9d", linewidth=1.4)
    axes[0].axhline(0.0, color="#666666", linestyle="--", linewidth=0.9)
    axes[0].set_ylabel("error / V")
    axes[0].set_title("负载突变场景 telemetry：error、integrator、raw duty、cmd duty 必须可观测")

    axes[1].plot(t_ms, signals["integrator"], color="#2e8b57", linewidth=1.4)
    axes[1].set_ylabel("integrator")

    axes[2].plot(t_ms, signals["duty_raw"], color="#777777", linewidth=1.2, label="raw duty")
    axes[2].plot(t_ms, signals["duty_cmd"], color="#1f77b4", linewidth=1.5, label="duty cmd")
    axes[2].step(t_ms, signals["saturation"] * 0.1 + cfg.duty_min, where="post", color="#e4572e", linewidth=1.0, label="saturation marker")
    axes[2].set_ylabel("duty")
    axes[2].set_xlabel("Time / ms")
    axes[2].legend(loc="best")

    for ax in axes:
        ax.axvline(50.0, color="#666666", linestyle="--", linewidth=0.8)
        ax.axvline(64.0, color="#666666", linestyle="--", linewidth=0.8)
        ax.grid(True, alpha=0.28)

    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_report(path: Path, summary: list[dict[str, str | float]]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    pass_count = sum(1 for row in summary if row["status"] == "PASS")
    fail_count = sum(1 for row in summary if row["status"] == "FAIL")
    info_count = sum(1 for row in summary if row["status"] == "INFO")
    fig, ax = plt.subplots(figsize=(8.0, 4.8))
    ax.bar(["PASS", "FAIL", "INFO"], [pass_count, fail_count, info_count], color=["#2e8b57", "#c92a2a", "#1f77b4"])
    ax.set_title("第 10 章场景测试报告汇总")
    ax.set_ylabel("Rows")
    ax.grid(axis="y", alpha=0.25)
    for idx, value in enumerate([pass_count, fail_count, info_count]):
        ax.text(idx, value + 0.05, str(value), ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(path, dpi=180)
    plt.close(fig)


def main() -> None:
    WAVE_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    cfg = Config()
    cases = {
        "steady_12v": 0.075,
        "soft_start_40ms": 0.065,
        "load_step_50_100_50": 0.092,
        "ocp_latch_clear": 0.088,
        "uvlo_blocks_pwm": 0.082,
    }
    all_rows = {case: simulate_case(case, stop, cfg) for case, stop in cases.items()}
    summary = build_summary(all_rows, cfg)

    write_trace(WAVE_DIR / "10-controller-c-style-trace.csv", all_rows)
    write_summary(WAVE_DIR / "10-controller-c-style-summary.csv", summary)
    write_report(REPORT_DIR / "10-controller-c-style-test-report.md", summary, cfg)
    plot_scenarios(WAVE_DIR / "10-controller-c-style-scenarios.png", all_rows, cfg)
    plot_telemetry(WAVE_DIR / "10-controller-c-style-telemetry.png", all_rows, cfg)
    plot_report(WAVE_DIR / "10-controller-c-style-pass-fail.png", summary)

    pass_count = sum(1 for row in summary if row["status"] == "PASS")
    fail_count = sum(1 for row in summary if row["status"] == "FAIL")
    steady_vout = next(row for row in summary if row["case"] == "steady_12v" and row["metric"] == "tail_vout_mean_v")["value"]
    load_undershoot = next(row for row in summary if row["case"] == "load_step_50_100_50" and row["metric"] == "undershoot_v")["value"]
    ocp_time = next(row for row in summary if row["case"] == "ocp_latch_clear" and row["metric"] == "first_ocp_time_ms")["value"]

    print("已生成第 10 章 C 风格控制器测试数据、图表和报告。")
    print(f"summary,pass_count={pass_count},fail_count={fail_count}")
    print(f"steady_12v,tail_vout_mean_v={steady_vout:.6g}")
    print(f"load_step_50_100_50,undershoot_v={load_undershoot:.6g}")
    print(f"ocp_latch_clear,first_ocp_time_ms={ocp_time:.6g}")


if __name__ == "__main__":
    main()
