from __future__ import annotations

import csv
import json
import os
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
ACCEPTANCE_DIR = ROOT / "hardware" / "acceptance"
WAVE_DIR = ROOT / "waveforms"
REPORT_DIR = ROOT / "reports"

PLAN_PATH = ACCEPTANCE_DIR / "test-plan.csv"
INVENTORY_TEMPLATE = ACCEPTANCE_DIR / "inventory-template.csv"
INVENTORY_LOCAL = ACCEPTANCE_DIR / "inventory.local.csv"
MEASUREMENTS_LOCAL = ACCEPTANCE_DIR / "measurements.local.csv"

DEVICE_LABELS = {
    "development_board": "Cortex-M4F开发板",
    "power_stage_24v_12v_5a": "24V/12V/5A功率级",
    "current_limited_supply_0_30v_5a": "限流台式电源",
    "electronic_load_0_30v_10a": "电子负载",
    "oscilloscope_100mhz": "示波器",
    "differential_probe_50v": "差分探头",
    "multimeter": "万用表",
    "debug_probe": "调试接口/探针",
    "thermal_camera_or_thermocouple": "测温设备",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def is_true(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "y")


def detect_windows_hardware() -> dict[str, object]:
    if os.name != "nt":
        return {"probe_count": 0, "board_count": 0, "serial_count": 0, "jlink_software": False, "detail": "非Windows环境未执行PnP检测"}
    script = r"""
$devices = Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue
$probe = @($devices | Where-Object { $_.FriendlyName -match 'ST-LINK|J-Link|SEGGER|XDS' -or $_.InstanceId -match 'VID_0483|VID_1366' })
$board = @($devices | Where-Object { $_.FriendlyName -match 'STM32|NUCLEO|C2000|DPOW' })
$serial = @(Get-CimInstance Win32_SerialPort -ErrorAction SilentlyContinue)
$jlink = Test-Path "$env:ProgramFiles\SEGGER"
@{probe_count=$probe.Count; board_count=$board.Count; serial_count=$serial.Count; jlink_software=$jlink} | ConvertTo-Json -Compress
"""
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        return {"probe_count": 0, "board_count": 0, "serial_count": 0, "jlink_software": False, "detail": "PnP检测命令失败"}
    try:
        data = json.loads(completed.stdout.strip().lstrip("\ufeff"))
    except json.JSONDecodeError:
        return {"probe_count": 0, "board_count": 0, "serial_count": 0, "jlink_software": False, "detail": "PnP检测输出无法解析"}
    data["detail"] = "Windows PnP/CIM 实时检测"
    return data


def build_inventory(detection: dict[str, object]) -> list[dict[str, object]]:
    source_path = INVENTORY_LOCAL if INVENTORY_LOCAL.exists() else INVENTORY_TEMPLATE
    manual_rows = read_csv(source_path)
    rows: list[dict[str, object]] = []
    for row in manual_rows:
        item = row["item"]
        label = row.get("label", "").strip() or DEVICE_LABELS.get(item, item)
        model = row["model"].strip()
        declared_available = is_true(row["available"]) and bool(model)
        available = declared_available
        source = "inventory.local.csv" if INVENTORY_LOCAL.exists() else "template"
        detail = model if model else "未登记型号"
        if item == "debug_probe":
            detected = int(detection.get("probe_count", 0)) > 0
            available = declared_available and detected
            detail = f"{detail}；PnP探针数量 {int(detection.get('probe_count', 0))}"
        if item == "development_board":
            detail = f"{detail}；PnP开发板数量 {int(detection.get('board_count', 0))}（仅供参考）"
        rows.append({
            "item": item,
            "label": label,
            "required": row["required"],
            "available": "yes" if available else "no",
            "source": source,
            "detail": detail,
        })
    rows.extend([
        {
            "item": "detected_serial_ports",
            "label": "检测到的串口",
            "required": "no",
            "available": "yes" if int(detection.get("serial_count", 0)) > 0 else "no",
            "source": "Windows CIM",
            "detail": f"数量 {int(detection.get('serial_count', 0))}",
        },
        {
            "item": "jlink_software",
            "label": "J-Link软件",
            "required": "no",
            "available": "yes" if bool(detection.get("jlink_software", False)) else "no",
            "source": "installed software",
            "detail": "软件存在不代表调试器已连接",
        },
    ])
    return rows


def read_measurements() -> dict[str, dict[str, str]]:
    if not MEASUREMENTS_LOCAL.exists():
        return {}
    return {row["test_id"]: row for row in read_csv(MEASUREMENTS_LOCAL)}


def software_fail_count() -> tuple[int | None, str]:
    path = WAVE_DIR / "19-full-regression.csv"
    if not path.exists():
        return None, "缺少第19章全回归CSV"
    rows = read_csv(path)
    failures = sum(row.get("status") != "PASS" for row in rows)
    return failures, "waveforms/19-full-regression.csv"


def parse_bound(value: str) -> float | None:
    value = value.strip()
    return float(value) if value else None


def relative_evidence_exists(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    path = Path(value)
    if path.is_absolute():
        return False
    resolved = (ROOT / path).resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError:
        return False
    return resolved.exists() and resolved.is_file()


def build_results(plan: list[dict[str, str]], inventory: list[dict[str, object]]) -> list[dict[str, object]]:
    measurements = read_measurements()
    inventory_by_item = {str(row["item"]): row for row in inventory}
    results: list[dict[str, object]] = []
    for test in plan:
        test_id = test["test_id"]
        minimum = parse_bound(test["min_value"])
        maximum = parse_bound(test["max_value"])
        measured_value: float | None = None
        evidence_file = ""
        reason = ""
        required_items = [item.strip() for item in test.get("required_items", "").split(";") if item.strip()]
        unknown_items = [item for item in required_items if item not in inventory_by_item]
        missing_items = [item for item in required_items if item in inventory_by_item and inventory_by_item[item]["available"] != "yes"]
        if test_id == "SW-01":
            failures, evidence_file = software_fail_count()
            if failures is None:
                status = "BLOCKED"
                reason = evidence_file
            else:
                measured_value = float(failures)
                status = "PASS" if failures == 0 else "FAIL"
                reason = "第19章顶层步骤失败数"
        elif unknown_items:
            status = "FAIL"
            reason = f"test plan引用未知设备：{', '.join(unknown_items)}"
        elif missing_items:
            status = "BLOCKED"
            labels = [str(inventory_by_item[item]["label"]) for item in missing_items]
            reason = f"本项缺少设备：{'、'.join(labels)}"
        elif test_id not in measurements or not measurements[test_id]["measured_value"].strip():
            status = "BLOCKED"
            reason = "缺少本地测量值"
        else:
            measurement = measurements[test_id]
            evidence_file = measurement["evidence_file"].strip()
            try:
                measured_value = float(measurement["measured_value"])
            except ValueError:
                status = "FAIL"
                reason = "测量值不是数字"
            else:
                in_range = (minimum is None or measured_value >= minimum) and (maximum is None or measured_value <= maximum)
                evidence_ok = not is_true(test["evidence_required"]) or relative_evidence_exists(evidence_file)
                status = "PASS" if in_range and evidence_ok else "FAIL"
                if not in_range:
                    reason = "测量值超出验收范围"
                elif not evidence_ok:
                    reason = "公开证据文件不存在或不是仓库相对路径"
                else:
                    reason = "数值与证据均满足"
        results.append({
            "test_id": test_id,
            "stage": test["stage"],
            "scenario": test["scenario"],
            "measurement": test["measurement"],
            "unit": test["unit"],
            "min_value": test["min_value"],
            "max_value": test["max_value"],
            "measured_value": "" if measured_value is None else measured_value,
            "status": status,
            "evidence_file": evidence_file,
            "reason": reason,
        })
    return results


def plot_status(path: Path, inventory: list[dict[str, object]], results: list[dict[str, object]]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    colors = {"PASS": "#0f766e", "BLOCKED": "#d97706", "FAIL": "#be123c"}
    fig, axes = plt.subplots(1, 2, figsize=(14.0, 8.0), gridspec_kw={"width_ratios": [0.9, 1.6]})

    required = [row for row in inventory if row["required"] == "yes"]
    axes[0].barh(
        [str(row["label"]) for row in required],
        [1 for _ in required],
        color="#e2e8f0",
    )
    axes[0].barh(
        [str(row["label"]) for row in required],
        [1 if row["available"] == "yes" else 0 for row in required],
        color="#0f766e",
    )
    for index, row in enumerate(required):
        ready = row["available"] == "yes"
        axes[0].text(0.5, index, "READY" if ready else "MISSING", ha="center", va="center", color="white" if ready else "#475569", fontsize=8, fontweight="bold")
    axes[0].set_xlim(0.0, 1.0)
    axes[0].set_xticks([0, 1], ["缺少", "可用"])
    axes[0].set_title("完整发布所需设备", loc="left")
    axes[0].grid(True, axis="x", alpha=0.25)

    labels = [f"{row['test_id']} {row['measurement']}" for row in results]
    values = [1 for _ in results]
    axes[1].barh(labels, values, color=[colors[str(row["status"])] for row in results])
    for index, row in enumerate(results):
        axes[1].text(0.5, index, str(row["status"]), ha="center", va="center", color="white" if row["status"] != "BLOCKED" else "#172033", fontsize=8, fontweight="bold")
    axes[1].set_xlim(0.0, 1.0)
    axes[1].set_xticks([])
    axes[1].set_title("验收项状态", loc="left")
    axes[1].invert_yaxis()

    counts = {status: sum(row["status"] == status for row in results) for status in colors}
    fig.suptitle(f"第 20 章：低压硬件验收状态  PASS {counts['PASS']} / BLOCKED {counts['BLOCKED']} / FAIL {counts['FAIL']}", fontsize=15)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.95))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_report(path: Path, inventory: list[dict[str, object]], results: list[dict[str, object]], detection: dict[str, object]) -> None:
    passes = sum(row["status"] == "PASS" for row in results)
    blocked = sum(row["status"] == "BLOCKED" for row in results)
    fails = sum(row["status"] == "FAIL" for row in results)
    v1_status = "PASS" if blocked == 0 and fails == 0 else "FAIL" if fails else "BLOCKED"
    lines = [
        "# 第 20 章报告：低压硬件最终验收",
        "",
        "本报告由 `scripts/run_hardware_acceptance.py` 生成。软件回归自动读取第19章结果；硬件项目由设备清单、数值范围和公开证据文件共同判定。",
        "",
        "## 摘要",
        "",
        f"- 验收项：PASS {passes} / BLOCKED {blocked} / FAIL {fails}",
        f"- v1.0 门禁：`{v1_status}`",
        f"- 调试探针设备数：{int(detection.get('probe_count', 0))}",
        f"- 开发板设备数：{int(detection.get('board_count', 0))}",
        f"- 串口数：{int(detection.get('serial_count', 0))}",
        f"- J-Link 软件：{'已安装' if bool(detection.get('jlink_software', False)) else '未检测到'}",
        "",
        "## 必需设备",
        "",
        "| 设备 | ID | 必需 | 可用 | 来源 | 说明 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in inventory:
        lines.append(f"| {row['label']} | `{row['item']}` | {row['required']} | {row['available']} | {row['source']} | {row['detail']} |")
    lines.extend([
        "",
        "## 验收项",
        "",
        "| ID | 场景 | 测量 | 范围 | 实测 | 状态 | 原因 |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ])
    for row in results:
        minimum = row["min_value"] or "-∞"
        maximum = row["max_value"] or "+∞"
        value = row["measured_value"] if row["measured_value"] != "" else "-"
        lines.append(f"| `{row['test_id']}` | {row['scenario']} | {row['measurement']} / {row['unit']} | {minimum}～{maximum} | {value} | {row['status']} | {row['reason']} |")
    lines.extend([
        "",
        "## 发布边界",
        "",
        "当前软件全回归可以作为 Cortex-M4F 软件基线证据。没有开发板、功率级、台式电源、电子负载、示波器、差分探头、万用表、测温设备和真实测量文件时，硬件验收保持 BLOCKED；v1.0 标签不得创建。",
        "",
    ])
    text = "\n".join(lines).replace("\r\n", "\n").replace("\r", "\n")
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(text.replace("\n", "\r\n"))


def main() -> int:
    WAVE_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    plan = read_csv(PLAN_PATH)
    detection = detect_windows_hardware()
    inventory = build_inventory(detection)
    results = build_results(plan, inventory)
    write_rows(WAVE_DIR / "20-hardware-inventory.csv", inventory)
    write_rows(WAVE_DIR / "20-acceptance-summary.csv", results)
    plot_status(WAVE_DIR / "20-acceptance-status.png", inventory, results)
    write_report(REPORT_DIR / "20-hardware-acceptance-report.md", inventory, results, detection)
    passes = sum(row["status"] == "PASS" for row in results)
    blocked = sum(row["status"] == "BLOCKED" for row in results)
    fails = sum(row["status"] == "FAIL" for row in results)
    v1_status = "PASS" if blocked == 0 and fails == 0 else "FAIL" if fails else "BLOCKED"
    print("已生成第 20 章低压硬件验收清单、状态图和报告。")
    print(f"summary,pass={passes},blocked={blocked},fail={fails},tests={len(results)},v1={v1_status}")
    print(f"hardware,probe={int(detection.get('probe_count', 0))},board={int(detection.get('board_count', 0))},serial={int(detection.get('serial_count', 0))}")
    return 1 if fails else 2 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
