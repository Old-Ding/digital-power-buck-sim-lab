from __future__ import annotations

import csv
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "waveforms" / "19-repository-quality.csv"
CHAPTERS = range(11, 21)

SCRIPT_BY_CHAPTER = {
    11: "run_host_build_tests.py",
    12: "run_c_python_parity.py",
    13: "run_fixed_point_parity.py",
    14: "run_adc_mapping_tests.py",
    15: "run_pwm_mapping_tests.py",
    16: "run_isr_timing_tests.py",
    17: "run_firmware_layering_tests.py",
    18: "build_cortex_m4f_firmware.py",
    19: "run_full_regression.py",
    20: "run_hardware_acceptance.py",
}


def run_command(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    return completed.returncode, output


def public_text_files() -> list[Path]:
    files = [
        ROOT / "README.md",
        ROOT / "blog" / "README.md",
        ROOT / "RELEASE_READINESS.md",
        *sorted((ROOT / "blog").glob("[0-9][0-9]-*.md")),
        *sorted((ROOT / "docs").glob("[0-9][0-9]-*.md")),
        *sorted((ROOT / "reports").glob("[0-9][0-9]-*.md")),
        *sorted((ROOT / "reports").glob("[0-9][0-9]-*.csv")),
        *sorted((ROOT / "waveforms").glob("[0-9][0-9]-*.csv")),
        *sorted((ROOT / "hardware" / "acceptance").glob("*.md")),
        *sorted((ROOT / "hardware" / "acceptance").glob("*.csv")),
        *sorted((ROOT / "hardware" / "acceptance" / "evidence" / "public").glob("*.md")),
        *sorted((ROOT / "firmware").rglob("*.map")),
        *sorted((ROOT / "firmware").rglob("*.lst")),
    ]
    return [path for path in files if path.is_file()]


def result(name: str, passed: bool, detail: str) -> dict[str, str]:
    return {"check": name, "status": "PASS" if passed else "FAIL", "detail": detail}


def check_draft_markers(files: list[Path]) -> dict[str, str]:
    pattern = re.compile(r"TODO|待补|占位|欢迎使用Markdown编辑器")
    hits: list[str] = []
    for path in files:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                hits.append(f"{path.relative_to(ROOT)}:{line_number}")
    return result("public_text_has_no_draft_markers", not hits, ", ".join(hits[:8]) if hits else "公开编号文本与数据扫描通过")


def check_machine_paths(files: list[Path]) -> dict[str, str]:
    pattern = re.compile(r"[A-Za-z]:[\\/](?:Users|codex|1codex|ZCJ)[\\/]")
    hits: list[str] = []
    for path in files:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                hits.append(f"{path.relative_to(ROOT)}:{line_number}")
    return result("public_text_has_no_machine_paths", not hits, ", ".join(hits[:8]) if hits else "未发现本机绝对路径")


def check_markdown_images() -> dict[str, str]:
    pattern = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
    checked = 0
    missing: list[str] = []
    for path in sorted((ROOT / "blog").glob("[0-9][0-9]-*.md")):
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            target_text = match.group(1).strip()
            if target_text.startswith(("http://", "https://")):
                continue
            checked += 1
            target = (path.parent / target_text).resolve()
            if not target.exists():
                missing.append(f"{path.relative_to(ROOT)} -> {target_text}")
    return result("blog_image_links_resolve", not missing, ", ".join(missing[:8]) if missing else "全部博客本地图片引用可解析")


def check_chapter_packages() -> dict[str, str]:
    missing: list[str] = []
    for chapter in CHAPTERS:
        prefix = f"{chapter:02d}-"
        if not list((ROOT / "blog").glob(f"{prefix}*.md")):
            missing.append(f"blog/{prefix}*.md")
        if not list((ROOT / "docs").glob(f"{prefix}*.md")):
            missing.append(f"docs/{prefix}*.md")
        if not list((ROOT / "reports").glob(f"{prefix}*.md")):
            missing.append(f"reports/{prefix}*.md")
        if not (ROOT / "scripts" / SCRIPT_BY_CHAPTER[chapter]).exists():
            missing.append(f"scripts/{SCRIPT_BY_CHAPTER[chapter]}")
        evidence_files = list((ROOT / "waveforms").glob(f"{prefix}*.csv")) + list((ROOT / "reports").glob(f"{prefix}*.csv"))
        if not evidence_files:
            missing.append(f"{prefix} CSV")
        if not list((ROOT / "waveforms").glob(f"{prefix}*.png")):
            missing.append(f"waveforms/{prefix}*.png")
    return result("chapters_11_20_have_complete_packages", not missing, ", ".join(missing[:12]) if missing else "第11～20章均包含教程、复现、脚本、CSV、PNG 和报告")


def check_tracked_hygiene() -> dict[str, str]:
    code, output = run_command(["git", "ls-files"])
    if code != 0:
        return result("tracked_files_exclude_local_outputs", False, output)
    forbidden = [
        line
        for line in output.splitlines()
        if line.startswith(("artifacts/", "blog/csdn/", "hardware/acceptance/evidence/local/"))
        or line in ("hardware/acceptance/inventory.local.csv", "hardware/acceptance/measurements.local.csv")
        or "__pycache__" in line
    ]
    return result("tracked_files_exclude_local_outputs", not forbidden, ", ".join(forbidden[:8]) if forbidden else "本地验收记录、artifacts、CSDN 本地包和 Python cache 均未跟踪")


def check_python_syntax() -> dict[str, str]:
    scripts = sorted((ROOT / "scripts").glob("*.py"))
    code, output = run_command([sys.executable, "-m", "py_compile", *map(str, scripts)])
    return result("all_python_scripts_compile", code == 0, output if output else f"编译 {len(scripts)} 个 Python 脚本")


def check_target_artifacts() -> dict[str, str]:
    required = [
        ROOT / "firmware" / "cortex-m4f" / "digital_power_cortex_m4f.elf",
        ROOT / "firmware" / "cortex-m4f" / "digital_power_cortex_m4f.bin",
        ROOT / "firmware" / "cortex-m4f" / "digital_power_cortex_m4f.map",
        ROOT / "firmware" / "cortex-m4f" / "digital_power_cortex_m4f.lst",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists() or path.stat().st_size == 0]
    return result("target_artifacts_exist", not missing, ", ".join(missing) if missing else "ELF、BIN、map、反汇编均存在且非空")


def check_workflow() -> dict[str, str]:
    path = ROOT / ".github" / "workflows" / "firmware-regression.yml"
    requirements = ROOT / "requirements-ci.txt"
    if not path.exists():
        return result("github_workflow_calls_local_entry", False, "缺少 firmware-regression.yml")
    text = path.read_text(encoding="utf-8")
    passed = (
        "python scripts\\run_full_regression.py" in text
        and "windows-latest" in text
        and "requirements-ci.txt" in text
        and requirements.exists()
    )
    return result("github_workflow_calls_local_entry", passed, "CI 调用统一入口并使用依赖清单" if passed else "工作流入口或依赖清单不完整")


def check_diff_whitespace() -> dict[str, str]:
    code, output = run_command(["git", "diff", "--check"])
    return result("git_diff_check", code == 0, "无空白错误" if code == 0 else output)


def main() -> int:
    OUTPUT_PATH.parent.mkdir(exist_ok=True)
    files = public_text_files()
    rows = [
        check_draft_markers(files),
        check_machine_paths(files),
        check_markdown_images(),
        check_chapter_packages(),
        check_tracked_hygiene(),
        check_python_syntax(),
        check_target_artifacts(),
        check_workflow(),
        check_diff_whitespace(),
    ]
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["check", "status", "detail"])
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(f"{row['status']},{row['check']},{row['detail']}")
    passes = sum(row["status"] == "PASS" for row in rows)
    fails = sum(row["status"] == "FAIL" for row in rows)
    print(f"summary,pass={passes},fail={fails},checks={len(rows)}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
