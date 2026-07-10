from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle


ROOT = Path(__file__).resolve().parents[1]
BUILD_DIR = ROOT / "artifacts" / "host-build" / "chapter11"
REPORT_DIR = ROOT / "reports"
WAVE_DIR = ROOT / "waveforms"


@dataclass
class StepResult:
    gate: str
    status: str
    detail: str


def find_msvc_cl() -> str | None:
    bases = [
        Path("C:/Program Files/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC"),
        Path("C:/Program Files/Microsoft Visual Studio/2022/Community/VC/Tools/MSVC"),
        Path("C:/Program Files/Microsoft Visual Studio/2022/Professional/VC/Tools/MSVC"),
        Path("C:/Program Files/Microsoft Visual Studio/2022/Enterprise/VC/Tools/MSVC"),
    ]
    for base in bases:
        if not base.exists():
            continue
        matches = sorted(base.glob("*/bin/Hostx64/x64/cl.exe"), reverse=True)
        if matches:
            return str(matches[0])
    return None


def find_winget_zig() -> str | None:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return None

    package_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
    if not package_root.exists():
        return None

    matches = sorted(package_root.glob("zig.zig_*/*/zig.exe"), reverse=True)
    if matches:
        return str(matches[0])
    return None


def find_compiler() -> tuple[str | None, str]:
    env_cc = os.environ.get("CC")
    if env_cc:
        resolved = shutil.which(env_cc) or (env_cc if Path(env_cc).exists() else None)
        if resolved:
            return resolved, "CC"

    for name in ("zig", "gcc", "clang", "cc", "cl"):
        resolved = shutil.which(name)
        if resolved:
            return resolved, name

    zig = find_winget_zig()
    if zig:
        return zig, "zig"

    msvc = find_msvc_cl()
    if msvc:
        return msvc, "cl"

    return None, "none"


def run_command(command: list[str], cwd: Path) -> tuple[int, str]:
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True)
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part)
    return completed.returncode, output.strip()


def compiler_family(compiler: str, hint: str) -> str:
    name = Path(compiler).name.lower()
    if hint == "zig" or name == "zig.exe":
        return "zig"
    if hint == "cl" or name == "cl.exe":
        return "msvc"
    if "clang" in name:
        return "clang"
    return "gcc"


def compiler_version(compiler: str, hint: str) -> str | None:
    family = compiler_family(compiler, hint)
    if family == "zig":
        code, output = run_command([compiler, "version"], ROOT)
    elif family in ("gcc", "clang"):
        code, output = run_command([compiler, "--version"], ROOT)
    else:
        return None

    if code != 0 or not output:
        return None
    return output.splitlines()[0].strip()


def build_command(compiler: str, hint: str, exe_path: Path) -> list[str]:
    source = ROOT / "src" / "digital_power_control.c"
    test = ROOT / "tests" / "test_digital_power_control_host.c"
    include = ROOT / "src"
    family = compiler_family(compiler, hint)

    if family == "zig":
        return [
            compiler,
            "cc",
            "-std=c99",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(include),
            str(source),
            str(test),
            "-o",
            str(exe_path),
        ]

    if family == "msvc":
        return [
            compiler,
            "/nologo",
            "/W4",
            "/WX",
            f"/I{include}",
            str(source),
            str(test),
            f"/Fe:{exe_path}",
        ]

    return [
        compiler,
        "-std=c99",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-I",
        str(include),
        str(source),
        str(test),
        "-o",
        str(exe_path),
    ]


def write_summary(path: Path, rows: list[StepResult]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["gate", "status", "detail"])
        writer.writeheader()
        for row in rows:
            writer.writerow({"gate": row.gate, "status": row.status, "detail": row.detail})


def plot_gate(path: Path, rows: list[StepResult]) -> None:
    status_color = {"PASS": "#2e8b57", "BLOCKED": "#d9480f", "SKIPPED": "#868e96", "FAIL": "#c92a2a"}
    gate_labels = {
        "toolchain": "检测编译器",
        "build": "C 代码编译",
        "unit_tests": "基础测试",
        "report": "结果报告",
    }

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(9.2, 3.4))
    ax.set_xlim(-0.55, len(rows) - 0.45)
    ax.set_ylim(0.0, 1.0)
    ax.axis("off")

    for idx in range(len(rows) - 1):
        ax.annotate(
            "",
            xy=(idx + 0.62, 0.54),
            xytext=(idx + 0.40, 0.54),
            arrowprops={"arrowstyle": "-|>", "color": "#94a3b8", "lw": 1.4},
        )

    for idx, row in enumerate(rows):
        color = status_color.get(row.status, "#868e96")
        ax.add_patch(
            Rectangle(
                (idx - 0.36, 0.34),
                0.72,
                0.40,
                facecolor="#f8fafc",
                edgecolor="#cbd5e1",
                linewidth=1.2,
            )
        )
        ax.add_patch(Rectangle((idx - 0.36, 0.34), 0.72, 0.05, facecolor=color, edgecolor="none"))
        ax.text(idx, 0.61, gate_labels.get(row.gate, row.gate), ha="center", va="center", color="#172033", fontsize=12)
        ax.text(idx, 0.47, row.status, ha="center", va="center", color=color, fontsize=12, fontweight="bold")

    counts = {status: sum(row.status == status for row in rows) for status in status_color}
    ax.text(
        (len(rows) - 1) / 2,
        0.88,
        "第 11 章：C 控制器电脑端检查结果",
        ha="center",
        va="center",
        color="#111827",
        fontsize=16,
        fontweight="bold",
    )
    ax.text(
        (len(rows) - 1) / 2,
        0.14,
        f"结果汇总：通过 {counts['PASS']} / 失败 {counts['FAIL']} / 阻塞 {counts['BLOCKED']} / 跳过 {counts['SKIPPED']}",
        ha="center",
        va="center",
        color="#475569",
        fontsize=10.5,
    )
    fig.tight_layout(pad=1.0)
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_report(
    path: Path,
    rows: list[StepResult],
    compiler: str | None,
    compiler_display: str | None,
    compile_cmd: list[str] | None,
    build_output: str,
    test_output: str,
) -> None:
    lines = [
        "# 第 11 章报告：电脑端编译和单元测试检查",
        "",
        "本报告由 `scripts/run_host_build_tests.py` 生成，用来判断第 10 章的 C 风格控制器是否已经具备电脑端编译和单元测试证据。",
        "",
        "## 检查结果",
        "",
        "| Gate | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for row in rows:
        lines.append(f"| `{row.gate}` | {row.status} | {row.detail} |")

    lines.extend(["", "## 工具链", ""])
    if compiler:
        lines.append(f"- 检测到的编译器：`{compiler_display or 'unknown'}`")
        lines.append(f"- 编译器路径：`{compiler}`")
    else:
        lines.append("- 检测到的编译器：`未找到`")

    if compile_cmd:
        lines.extend(["", "## 编译命令", "", "```powershell", " ".join(compile_cmd), "```"])

    if build_output:
        lines.extend(["", "## 编译输出", "", "```text", build_output, "```"])

    if test_output:
        lines.extend(["", "## 测试输出", "", "```text", test_output, "```"])

    lines.extend(
        [
            "",
            "## 边界",
            "",
            "读这份报告时，先看 `toolchain`、`build`、`unit_tests` 三个检查项。它们对应的是电脑端证据；不要把这个结果误读成定点化安全、MCU 寄存器适配、ISR 时序、HIL 或硬件闭环已经完成。",
        ]
    )
    report_text = "\n".join(lines).replace("\r\n", "\n").replace("\r", "\n")
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(report_text.replace("\n", "\r\n") + "\r\n")


def main() -> int:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    WAVE_DIR.mkdir(exist_ok=True)

    rows: list[StepResult] = []
    compiler, hint = find_compiler()
    compile_cmd: list[str] | None = None
    build_output = ""
    test_output = ""
    compiler_display: str | None = None

    if compiler is None:
        rows.append(StepResult("toolchain", "BLOCKED", "PATH 和常见安装目录中没有找到 zig、gcc、clang、cc 或 cl"))
        rows.append(StepResult("build", "SKIPPED", "缺少 C 编译器，未执行编译"))
        rows.append(StepResult("unit_tests", "SKIPPED", "缺少可执行文件，未运行电脑端单元测试"))
    else:
        version = compiler_version(compiler, hint)
        compiler_display = f"{hint} {version}" if version else hint
        rows.append(StepResult("toolchain", "PASS", f"检测到 {compiler_display}: {compiler}"))
        exe_path = BUILD_DIR / ("digital_power_control_host_tests.exe" if os.name == "nt" else "digital_power_control_host_tests")
        compile_cmd = build_command(compiler, hint, exe_path)
        code, build_output = run_command(compile_cmd, BUILD_DIR)
        if code != 0:
            rows.append(StepResult("build", "FAIL", f"编译失败，退出码 {code}"))
            rows.append(StepResult("unit_tests", "SKIPPED", "编译失败，未运行测试"))
        else:
            rows.append(StepResult("build", "PASS", f"生成 {exe_path}"))
            test_code, test_output = run_command([str(exe_path)], BUILD_DIR)
            if test_code == 0 and "SUMMARY,PASS" in test_output:
                rows.append(StepResult("unit_tests", "PASS", "电脑端单元测试通过"))
            else:
                rows.append(StepResult("unit_tests", "FAIL", f"测试失败，退出码 {test_code}"))

    rows.append(StepResult("report", "PASS", "已生成 CSV、PNG 和 Markdown 报告"))

    write_summary(REPORT_DIR / "11-host-build-summary.csv", rows)
    plot_gate(WAVE_DIR / "11-host-build-gate.png", rows)
    write_report(
        REPORT_DIR / "11-host-build-test-report.md",
        rows,
        compiler,
        compiler_display,
        compile_cmd,
        build_output,
        test_output,
    )

    pass_count = sum(1 for row in rows if row.status == "PASS")
    blocked_count = sum(1 for row in rows if row.status == "BLOCKED")
    fail_count = sum(1 for row in rows if row.status == "FAIL")
    skipped_count = sum(1 for row in rows if row.status == "SKIPPED")

    print("已生成第 11 章电脑端编译测试检查报告。")
    print(f"summary,pass={pass_count},blocked={blocked_count},skipped={skipped_count},fail={fail_count}")
    if compiler:
        print(f"toolchain,{hint},{compiler_display or hint}")
    else:
        print("toolchain,none,未找到 C 编译器")

    return 1 if fail_count else 0


if __name__ == "__main__":
    sys.exit(main())
