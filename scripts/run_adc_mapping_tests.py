from __future__ import annotations

import argparse
import csv
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import matplotlib.pyplot as plt

from run_host_build_tests import compiler_family, compiler_version, find_compiler, run_command


ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "artifacts" / "host-build" / "chapter14"
WAVE_DIR = ROOT / "waveforms"
REPORT_DIR = ROOT / "reports"

ADC_FULL_SCALE = 4095
ADC_REFERENCE_V = 3.3

CHANNELS = {
    "vin": ("vin_true_v", "vin_mapped_v", 0.0080, "V"),
    "vout": ("vout_true_v", "vout_mapped_v", 0.0041, "V"),
    "iout": ("iout_true_a", "iout_mapped_a", 0.0022, "A"),
    "temperature": ("temperature_true_c", "temperature_mapped_c", 0.083, "degC"),
}


@dataclass(frozen=True)
class FrontEnd:
    name: str
    vin_ratio: float
    vout_ratio: float
    current_offset_v: float
    current_gain_v_per_a: float
    temperature_offset_v: float
    temperature_slope_v_per_c: float


NOMINAL = FrontEnd("nominal", 9.2, 4.9, 0.100, 0.400, 0.500, 0.0100)
TOLERANCE_ACTUAL = FrontEnd("tolerance_actual", 9.292, 4.8608, 0.112, 0.406, 0.505, 0.0099)


def firmware_config(profile: str) -> dict[str, int]:
    if profile == "calibrated":
        return {
            "adc_full_scale_code": ADC_FULL_SCALE,
            "adc_reference_uv": 3_300_000,
            "vin_divider_num": 9292,
            "vin_divider_den": 1000,
            "vout_divider_num": 48608,
            "vout_divider_den": 10000,
            "current_offset_uv": 112_000,
            "current_gain_uv_per_a": 406_000,
            "temperature_offset_uv": 505_000,
            "temperature_slope_uv_per_c": 9_900,
        }
    return {
        "adc_full_scale_code": ADC_FULL_SCALE,
        "adc_reference_uv": 3_300_000,
        "vin_divider_num": 92,
        "vin_divider_den": 10,
        "vout_divider_num": 49,
        "vout_divider_den": 10,
        "current_offset_uv": 100_000,
        "current_gain_uv_per_a": 400_000,
        "temperature_offset_uv": 500_000,
        "temperature_slope_uv_per_c": 10_000,
    }


def adc_code(adc_voltage: float) -> int:
    clipped = min(max(adc_voltage, 0.0), ADC_REFERENCE_V)
    return int(math.floor(clipped / ADC_REFERENCE_V * ADC_FULL_SCALE + 0.5))


def encode(front_end: FrontEnd, vin_v: float, vout_v: float, iout_a: float, temperature_c: float) -> dict[str, int]:
    return {
        "vin_code": adc_code(vin_v / front_end.vin_ratio),
        "vout_code": adc_code(vout_v / front_end.vout_ratio),
        "iout_code": adc_code(front_end.current_offset_v + iout_a * front_end.current_gain_v_per_a),
        "temperature_code": adc_code(front_end.temperature_offset_v + temperature_c * front_end.temperature_slope_v_per_c),
    }


def build_input_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    scenarios = [
        ("nominal_sweep", NOMINAL, "nominal"),
        ("tolerance_uncalibrated", TOLERANCE_ACTUAL, "nominal"),
        ("tolerance_calibrated", TOLERANCE_ACTUAL, "calibrated"),
    ]
    for case_id, actual_front_end, config_profile in scenarios:
        cfg = firmware_config(config_profile)
        for index in range(201):
            fraction = index / 200.0
            truth = {
                "vin_true_v": 10.0 + 20.0 * fraction,
                "vout_true_v": 16.0 * fraction,
                "iout_true_a": 7.5 * fraction,
                "temperature_true_c": -20.0 + 140.0 * fraction,
            }
            rows.append(
                {
                    "case": case_id,
                    "index": index,
                    **truth,
                    **encode(actual_front_end, truth["vin_true_v"], truth["vout_true_v"], truth["iout_true_a"], truth["temperature_true_c"]),
                    **cfg,
                    "enable": 1,
                    "clear_fault": 0,
                }
            )

    cfg = firmware_config("nominal")
    operating_truth = {
        "vin_true_v": 24.0,
        "vout_true_v": 12.0,
        "iout_true_a": 5.0,
        "temperature_true_c": 45.0,
    }
    rows.append(
        {
            "case": "nominal_operating_point",
            "index": 0,
            **operating_truth,
            **encode(NOMINAL, operating_truth["vin_true_v"], operating_truth["vout_true_v"], operating_truth["iout_true_a"], operating_truth["temperature_true_c"]),
            **cfg,
            "enable": 1,
            "clear_fault": 0,
        }
    )

    for index, code in enumerate((0, ADC_FULL_SCALE, 5000)):
        rows.append(
            {
                "case": "boundary_codes",
                "index": index,
                "vin_true_v": 0.0,
                "vout_true_v": 0.0,
                "iout_true_a": 0.0,
                "temperature_true_c": 0.0,
                "vin_code": code,
                "vout_code": code,
                "iout_code": code,
                "temperature_code": code,
                **cfg,
                "enable": 1,
                "clear_fault": 0,
            }
        )
    return rows


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def build_compile_command(compiler: str, hint: str, sources: list[Path], output: Path) -> list[str]:
    family = compiler_family(compiler, hint)
    include = ROOT / "src"
    if family == "zig":
        return [compiler, "cc", "-std=c99", "-Wall", "-Wextra", "-Werror", "-I", str(include), *map(str, sources), "-o", str(output)]
    if family == "msvc":
        return [compiler, "/nologo", "/W4", "/WX", f"/I{include}", *map(str, sources), f"/Fe:{output}"]
    return [compiler, "-std=c99", "-Wall", "-Wextra", "-Werror", "-I", str(include), *map(str, sources), "-o", str(output)]


def read_output(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with path.open("r", newline="", encoding="utf-8") as file:
        for raw in csv.DictReader(file):
            row: dict[str, object] = {
                "case": raw["case"],
                "index": int(raw["index"]),
            }
            for name in ("vin_true_v", "vout_true_v", "iout_true_a", "temperature_true_c", "vin_mapped_v", "vout_mapped_v", "iout_mapped_a", "temperature_mapped_c"):
                row[name] = float(raw[name])
            for name in ("vin_code", "vout_code", "iout_code", "temperature_code", "vin_q20", "vout_q20", "iout_q20", "temperature_q20"):
                row[name] = int(raw[name])
            for name in ("input_code_clamped", "physical_value_clamped", "arithmetic_overflow"):
                row[name] = raw[name] == "1"
            rows.append(row)
    return rows


def metric(case_id: str, name: str, value: float, tolerance: float, status: str, note: str) -> dict[str, object]:
    return {"case": case_id, "metric": name, "value": value, "tolerance": tolerance, "status": status, "note": note}


def build_metrics(rows: list[dict[str, object]], unit_output: str) -> list[dict[str, object]]:
    by_case = {case_id: [row for row in rows if row["case"] == case_id] for case_id in ("nominal_sweep", "nominal_operating_point", "tolerance_uncalibrated", "tolerance_calibrated", "boundary_codes")}
    metrics: list[dict[str, object]] = []
    errors: dict[tuple[str, str], float] = {}

    for case_id in ("nominal_sweep", "nominal_operating_point", "tolerance_uncalibrated", "tolerance_calibrated"):
        for channel, (truth_field, mapped_field, tolerance, unit) in CHANNELS.items():
            max_error = max(abs(float(row[mapped_field]) - float(row[truth_field])) for row in by_case[case_id])
            errors[(case_id, channel)] = max_error
            if case_id == "tolerance_uncalibrated":
                metrics.append(metric(case_id, f"max_abs_{channel}_error", max_error, 0.0, "INFO", f"元件偏差未校准时的最大 {unit} 误差"))
            else:
                metrics.append(metric(case_id, f"max_abs_{channel}_error", max_error, tolerance, "PASS" if max_error <= tolerance else "FAIL", f"最大 {unit} 映射误差不超过约一个通道 ADC LSB"))

    for channel in CHANNELS:
        uncalibrated = errors[("tolerance_uncalibrated", channel)]
        calibrated = errors[("tolerance_calibrated", channel)]
        ratio = calibrated / uncalibrated if uncalibrated > 0.0 else 0.0
        metrics.append(metric("calibration_improvement", f"{channel}_error_ratio", ratio, 0.1, "PASS" if ratio <= 0.1 else "FAIL", "校准后最大误差应低于未校准误差的 10%"))

    boundary = by_case["boundary_codes"]
    metrics.append(metric("boundary_codes", "over_code_clamp", float(sum(bool(row["input_code_clamped"]) for row in boundary if int(row["vin_code"]) > ADC_FULL_SCALE)), 1.0, "PASS" if any(bool(row["input_code_clamped"]) for row in boundary if int(row["vin_code"]) > ADC_FULL_SCALE) else "FAIL", "超过 12-bit 满量程的输入必须被钳位并置标志"))
    physical_clamp_present = any(bool(row["physical_value_clamped"]) for row in boundary)
    metrics.append(metric("boundary_codes", "physical_clamp_present", 1.0 if physical_clamp_present else 0.0, 1.0, "PASS" if physical_clamp_present else "FAIL", "电流和温度超出物理范围时必须钳位"))
    overflow_count = sum(bool(row["arithmetic_overflow"]) for row in rows)
    metrics.append(metric("all", "arithmetic_overflow_count", float(overflow_count), 0.0, "PASS" if overflow_count == 0 else "FAIL", "ADC 映射整数运算不得溢出"))

    for line in unit_output.splitlines():
        parts = line.strip().split(",", 1)
        if len(parts) == 2 and parts[0] in ("PASS", "FAIL"):
            passed = parts[0] == "PASS"
            metrics.append(metric("adc_unit_tests", parts[1], 1.0 if passed else 0.0, 1.0, "PASS" if passed else "FAIL", "ADC 映射 C 单元测试"))
    return metrics


def write_metrics(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["case", "metric", "value", "tolerance", "status", "note"])
        writer.writeheader()
        writer.writerows(rows)


def write_front_end_table(path: Path) -> None:
    rows = []
    for front_end in (NOMINAL, TOLERANCE_ACTUAL):
        row = asdict(front_end)
        row["vin_lsb_v"] = ADC_REFERENCE_V / ADC_FULL_SCALE * front_end.vin_ratio
        row["vout_lsb_v"] = ADC_REFERENCE_V / ADC_FULL_SCALE * front_end.vout_ratio
        row["iout_lsb_a"] = ADC_REFERENCE_V / ADC_FULL_SCALE / front_end.current_gain_v_per_a
        row["temperature_lsb_c"] = ADC_REFERENCE_V / ADC_FULL_SCALE / front_end.temperature_slope_v_per_c
        rows.append(row)
    write_rows(path, rows)


def plot_transfer(path: Path, rows: list[dict[str, object]]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    nominal = [row for row in rows if row["case"] == "nominal_sweep"]
    specs = [
        ("vin", "vin_code", "vin_true_v", "vin_mapped_v", "输入电压", "V", 18.0, "UVLO 18V"),
        ("vout", "vout_code", "vout_true_v", "vout_mapped_v", "输出电压", "V", 13.2, "OVP 13.2V"),
        ("iout", "iout_code", "iout_true_a", "iout_mapped_a", "输出电流", "A", 6.5, "OCP 6.5A"),
        ("temperature", "temperature_code", "temperature_true_c", "temperature_mapped_c", "温度", "°C", 100.0, "OTP 100°C"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.2))
    for ax, (_, code_field, truth_field, mapped_field, title, unit, threshold, threshold_label) in zip(axes.flat, specs):
        ax.plot([int(row[code_field]) for row in nominal], [float(row[truth_field]) for row in nominal], color="#94a3b8", linewidth=2.4, label="理想工程值")
        ax.plot([int(row[code_field]) for row in nominal], [float(row[mapped_field]) for row in nominal], color="#0f766e", linewidth=1.2, linestyle="--", label="C 映射结果")
        ax.axhline(threshold, color="#be123c", linewidth=1.0, linestyle=":", label=threshold_label)
        ax.set_title(f"{title}：ADC code → Q20 {unit}", loc="left")
        ax.set_xlabel("12-bit ADC code")
        ax.set_ylabel(unit)
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle("第 14 章：四通道 ADC 码值到 Q20 工程量的真实 C 映射", fontsize=15)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.96))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_calibration_error(path: Path, rows: list[dict[str, object]]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    cases = {
        "nominal_sweep": ("标称前端", "#64748b", ":"),
        "tolerance_uncalibrated": ("元件偏差未校准", "#be123c", "-"),
        "tolerance_calibrated": ("写入校准系数", "#0f766e", "--"),
    }
    specs = [
        ("vin_true_v", "vin_mapped_v", "输入电压误差", "V"),
        ("vout_true_v", "vout_mapped_v", "输出电压误差", "V"),
        ("iout_true_a", "iout_mapped_a", "输出电流误差", "A"),
        ("temperature_true_c", "temperature_mapped_c", "温度误差", "°C"),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(12.5, 8.2))
    for ax, (truth_field, mapped_field, title, unit) in zip(axes.flat, specs):
        for case_id, (label, color, linestyle) in cases.items():
            case_rows = [row for row in rows if row["case"] == case_id]
            ax.plot([float(row[truth_field]) for row in case_rows], [float(row[mapped_field]) - float(row[truth_field]) for row in case_rows], label=label, color=color, linestyle=linestyle, linewidth=1.5)
        ax.axhline(0.0, color="#111827", linewidth=0.8)
        ax.set_title(title, loc="left")
        ax.set_xlabel(f"真实值 / {unit}")
        ax.set_ylabel(f"映射值 - 真实值 / {unit}")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=8)
    fig.suptitle("第 14 章：元件偏差与校准系数对 ADC 映射误差的影响", fontsize=15)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.96))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_report(path: Path, metrics: list[dict[str, object]], compiler_display: str, row_count: int, runner_output: str, unit_output: str) -> None:
    pass_count = sum(row["status"] == "PASS" for row in metrics)
    fail_count = sum(row["status"] == "FAIL" for row in metrics)
    info_count = sum(row["status"] == "INFO" for row in metrics)
    lines = [
        "# 第 14 章报告：ADC 码值到 Q20 工程量映射",
        "",
        "本报告由 `scripts/run_adc_mapping_tests.py` 生成，映射结果来自真实编译执行的 `src/digital_power_adc_map.c`。元件偏差场景是可重复的合成前端参数，不是实物测量数据。",
        "",
        "## 执行摘要",
        "",
        f"- 编译器：`{compiler_display}`",
        f"- C 映射数据行：{row_count}",
        f"- 指标：PASS {pass_count} / FAIL {fail_count} / INFO {info_count}",
        "",
        "C 回放输出：",
        "",
        "```text",
        runner_output,
        "```",
        "",
        "C 单元测试输出：",
        "",
        "```text",
        unit_output,
        "```",
        "",
        "## 指标",
        "",
        "| 场景 | 指标 | 实际值 | 限制 | 状态 | 说明 |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for row in metrics:
        lines.append(f"| `{row['case']}` | `{row['metric']}` | {float(row['value']):.6g} | {float(row['tolerance']):.6g} | {row['status']} | {row['note']} |")
    lines.extend([
        "",
        "## 结果边界",
        "",
        "本报告证明映射公式、Q20 输出、码值钳位、物理范围钳位和校准系数在电脑端 C 测试中成立。未校准元件偏差来自脚本定义的合成参数；真实硬件仍需要测量参考电压、分压比、放大器增益和零点后写入校准值。",
        "",
    ])
    text = "\n".join(lines).replace("\r\n", "\n").replace("\r", "\n")
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(text.replace("\n", "\r\n"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Chapter 14 ADC-to-Q20 mapping checks.")
    parser.add_argument("--prepare-only", action="store_true", help="Only generate the ADC replay input and front-end table.")
    args = parser.parse_args(argv)

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    WAVE_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    input_rows = build_input_rows()
    input_path = BUILD_DIR / "14-adc-mapping-input.csv"
    output_path = BUILD_DIR / "14-adc-mapping-output.csv"
    runner_exe = BUILD_DIR / ("digital_power_adc_map_replay.exe" if os.name == "nt" else "digital_power_adc_map_replay")
    unit_exe = BUILD_DIR / ("digital_power_adc_map_tests.exe" if os.name == "nt" else "digital_power_adc_map_tests")
    write_rows(input_path, input_rows)
    write_front_end_table(WAVE_DIR / "14-adc-front-end-config.csv")

    if args.prepare_only:
        print(f"prepared,rows={len(input_rows)},input={input_path}")
        return 0

    compiler, hint = find_compiler()
    if compiler is None:
        print("summary,BLOCKED,未找到 C 编译器")
        return 2
    version = compiler_version(compiler, hint)
    compiler_display = f"{hint} {version}" if version else hint

    mapper_source = ROOT / "src" / "digital_power_adc_map.c"
    runner_source = ROOT / "tests" / "replay_digital_power_adc_map.c"
    unit_source = ROOT / "tests" / "test_digital_power_adc_map.c"
    for command, label in (
        (build_compile_command(compiler, hint, [mapper_source, unit_source], unit_exe), "unit_build"),
        (build_compile_command(compiler, hint, [mapper_source, runner_source], runner_exe), "runner_build"),
    ):
        code, output = run_command(command, BUILD_DIR)
        if code != 0:
            print(output)
            print(f"summary,FAIL,{label}_exit_code={code}")
            return 1

    unit_code, unit_output = run_command([str(unit_exe)], BUILD_DIR)
    if unit_code != 0:
        print(unit_output)
        print(f"summary,FAIL,unit_test_exit_code={unit_code}")
        return 1
    runner_code, runner_output = run_command([str(runner_exe), str(input_path), str(output_path)], BUILD_DIR)
    if runner_code != 0:
        print(runner_output)
        print(f"summary,FAIL,runner_exit_code={runner_code}")
        return 1

    rows = read_output(output_path)
    metrics = build_metrics(rows, unit_output)
    write_metrics(WAVE_DIR / "14-adc-mapping-summary.csv", metrics)
    write_rows(WAVE_DIR / "14-adc-mapping-samples.csv", rows)
    plot_transfer(WAVE_DIR / "14-adc-code-to-q20.png", rows)
    plot_calibration_error(WAVE_DIR / "14-adc-calibration-error.png", rows)
    write_report(REPORT_DIR / "14-adc-mapping-report.md", metrics, compiler_display, len(rows), runner_output, unit_output)

    pass_count = sum(row["status"] == "PASS" for row in metrics)
    fail_count = sum(row["status"] == "FAIL" for row in metrics)
    info_count = sum(row["status"] == "INFO" for row in metrics)
    max_uncal = max(float(row["value"]) for row in metrics if row["case"] == "tolerance_uncalibrated")
    max_cal_ratio = max(float(row["value"]) for row in metrics if row["case"] == "calibration_improvement")
    print("已生成第 14 章 ADC 到 Q20 映射数据、图表和报告。")
    print(f"summary,pass={pass_count},fail={fail_count},info={info_count},rows={len(rows)}")
    print(f"toolchain,{hint},{compiler_display}")
    print(f"calibration,max_uncalibrated_error={max_uncal:.6g},max_calibrated_ratio={max_cal_ratio:.6g}")
    return 1 if fail_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
