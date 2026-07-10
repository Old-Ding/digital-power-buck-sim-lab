from __future__ import annotations

import csv
import hashlib
import re
import shutil
import subprocess
from pathlib import Path

import matplotlib.pyplot as plt
from capstone import Cs, CS_ARCH_ARM, CS_MODE_MCLASS, CS_MODE_THUMB
from elftools.elf.elffile import ELFFile


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "firmware" / "cortex-m4f"
BUILD_DIR = ROOT / "artifacts" / "target-build" / "chapter18"
WAVE_DIR = ROOT / "waveforms"
REPORT_DIR = ROOT / "reports"

FLASH_ORIGIN = 0x08000000
FLASH_SIZE = 512 * 1024
RAM_ORIGIN = 0x20000000
RAM_SIZE = 128 * 1024
STACK_RESERVE = 4 * 1024

SOURCES = [
    ROOT / "src" / "digital_power_adc_map.c",
    ROOT / "src" / "digital_power_control_fixed.c",
    ROOT / "src" / "digital_power_pwm_map.c",
    ROOT / "src" / "digital_power_control_isr.c",
    ROOT / "src" / "digital_power_firmware.c",
    ROOT / "target" / "cortex-m4f" / "startup_cortex_m4f.c",
    ROOT / "target" / "cortex-m4f" / "firmware_entry.c",
]

REQUIRED_SYMBOLS = [
    "Reset_Handler",
    "main",
    "Control_IRQHandler",
    "DpFirmware_ControlIsr",
]


def run_command(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    return completed.returncode, output


def find_zig() -> str | None:
    resolved = shutil.which("zig")
    if resolved:
        return resolved
    package_root = Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Packages"
    matches = sorted(package_root.glob("zig.zig_*/*/zig.exe"), reverse=True)
    return str(matches[0]) if matches else None


def build_command(zig: str, elf_path: Path, keep_debug: bool) -> list[str]:
    command = [
        zig,
        "cc",
        "-target",
        "thumb-freestanding-eabihf",
        "-mcpu=cortex_m4",
        "-mthumb",
        "-mfloat-abi=hard",
        "-mfpu=fpv4-sp-d16",
        "-ffreestanding",
        "-fno-builtin",
        "-fdata-sections",
        "-ffunction-sections",
        "-std=c99",
        "-Os",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-I",
        str(ROOT / "src"),
        *map(str, SOURCES),
        f"-Wl,-T,{ROOT / 'target' / 'cortex-m4f' / 'linker.ld'}",
        "-Wl,--gc-sections",
        "-Wl,--entry=Reset_Handler",
        "-o",
        str(elf_path),
    ]
    if keep_debug:
        command.insert(command.index("-Wall"), "-g")
    return command


def write_rows(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_elf(path: Path) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]], bytes, int]:
    with path.open("rb") as file:
        elf = ELFFile(file)
        header = {
            "elf_class": elf.elfclass,
            "little_endian": elf.little_endian,
            "machine": elf.header["e_machine"],
            "entry": int(elf.header["e_entry"]),
        }
        sections: list[dict[str, object]] = []
        for section in elf.iter_sections():
            flags = int(section["sh_flags"])
            address = int(section["sh_addr"])
            size = int(section["sh_size"])
            if flags & 0x2:
                if FLASH_ORIGIN <= address < FLASH_ORIGIN + FLASH_SIZE:
                    region = "FLASH"
                elif RAM_ORIGIN <= address < RAM_ORIGIN + RAM_SIZE:
                    region = "RAM"
                else:
                    region = "OTHER"
                sections.append({
                    "section": section.name,
                    "address": f"0x{address:08X}",
                    "size_bytes": size,
                    "region": region,
                    "type": section["sh_type"],
                    "flags": f"0x{flags:X}",
                })

        symbols: list[dict[str, object]] = []
        symbol_table = elf.get_section_by_name(".symtab")
        if symbol_table is not None:
            for symbol in symbol_table.iter_symbols():
                symbols.append({
                    "symbol": symbol.name,
                    "address": int(symbol["st_value"]),
                    "size_bytes": int(symbol["st_size"]),
                    "type": symbol["st_info"]["type"],
                    "binding": symbol["st_info"]["bind"],
                    "section_index": symbol["st_shndx"],
                })
        text_section = elf.get_section_by_name(".text")
        if text_section is None:
            raise RuntimeError("ELF has no .text section")
        text_bytes = text_section.data()
        text_address = int(text_section["sh_addr"])
    return header, sections, symbols, text_bytes, text_address


def disassemble(text_bytes: bytes, text_address: int, symbols: list[dict[str, object]], path: Path) -> list[dict[str, object]]:
    decoder = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_MCLASS)
    decoder.detail = False
    function_labels: dict[int, list[str]] = {}
    for symbol in symbols:
        if symbol["type"] == "STT_FUNC" and symbol["symbol"]:
            address = int(symbol["address"]) & ~1
            function_labels.setdefault(address, []).append(str(symbol["symbol"]))

    instructions: list[dict[str, object]] = []
    lines = ["; Cortex-M4F Thumb disassembly generated from digital_power_cortex_m4f.elf", ""]
    for instruction in decoder.disasm(text_bytes, text_address):
        if instruction.address in function_labels:
            for label in function_labels[instruction.address]:
                lines.extend(["", f"{label}:"])
        byte_text = " ".join(f"{value:02x}" for value in instruction.bytes)
        lines.append(f"{instruction.address:08x}:  {byte_text:<12}  {instruction.mnemonic:<9} {instruction.op_str}".rstrip())
        instructions.append({
            "address": instruction.address,
            "mnemonic": instruction.mnemonic,
            "op_str": instruction.op_str,
        })
    text = "\n".join(lines).replace("\r\n", "\n").replace("\r", "\n")
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(text.replace("\n", "\r\n") + "\r\n")
    return instructions


def write_map(path: Path, header: dict[str, object], sections: list[dict[str, object]], symbols: list[dict[str, object]], command: list[str]) -> None:
    public_command = ["zig", *(argument.replace(str(ROOT), ".") for argument in command[1:])]
    lines = [
        "Cortex-M4F firmware map generated from ELF",
        "",
        f"Machine: {header['machine']}",
        f"Class: ELF{header['elf_class']}",
        f"Endian: {'little' if header['little_endian'] else 'big'}",
        f"Entry: 0x{int(header['entry']):08X}",
        "",
        "Build command:",
        " ".join(public_command),
        "",
        "Allocated sections:",
        "name,address,size_bytes,region,type,flags",
    ]
    for section in sections:
        lines.append(f"{section['section']},{section['address']},{section['size_bytes']},{section['region']},{section['type']},{section['flags']}")
    lines.extend(["", "Symbols:", "address,size_bytes,type,binding,name"])
    for symbol in sorted(symbols, key=lambda item: (int(item["address"]), str(item["symbol"]))):
        if symbol["symbol"]:
            lines.append(f"0x{int(symbol['address']):08X},{symbol['size_bytes']},{symbol['type']},{symbol['binding']},{symbol['symbol']}")
    text = "\n".join(lines).replace("\r\n", "\n").replace("\r", "\n")
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(text.replace("\n", "\r\n") + "\r\n")


def metric(case_id: str, name: str, value: float, limit: float, status: str, note: str) -> dict[str, object]:
    return {"case": case_id, "metric": name, "value": value, "limit": limit, "status": status, "note": note}


def build_metrics(
    header: dict[str, object],
    sections: list[dict[str, object]],
    symbols: list[dict[str, object]],
    instructions: list[dict[str, object]],
    elf_path: Path,
    bin_path: Path,
    text_matches_audit: bool,
) -> list[dict[str, object]]:
    symbol_by_name = {str(symbol["symbol"]): symbol for symbol in symbols if symbol["symbol"]}
    undefined = [symbol for symbol in symbols if symbol["section_index"] == "SHN_UNDEF" and symbol["symbol"]]
    required_present = sum(name in symbol_by_name for name in REQUIRED_SYMBOLS)
    reset_address = int(symbol_by_name.get("Reset_Handler", {}).get("address", 0))
    vector = next((section for section in sections if section["section"] == ".isr_vector"), None)
    flash_used = bin_path.stat().st_size
    data_bss = sum(int(section["size_bytes"]) for section in sections if section["section"] in (".data", ".bss"))
    ram_reserved = data_bss + STACK_RESERVE
    float_symbols = [symbol for symbol in symbols if re.match(r"__aeabi_[fd]", str(symbol["symbol"]))]
    float_prefixes = ("vadd", "vsub", "vmul", "vdiv", "vsqrt", "vcvt", "vldr", "vstr", "vpush", "vpop", "vcmp")
    float_instructions = [instruction for instruction in instructions if str(instruction["mnemonic"]).startswith(float_prefixes)]
    division_helpers = [symbol for symbol in symbols if symbol["symbol"] in ("__aeabi_ldivmod", "__aeabi_uldivmod")]
    vector_ok = vector is not None and vector["address"] == f"0x{FLASH_ORIGIN:08X}" and int(vector["size_bytes"]) >= 68
    entry_ok = (int(header["entry"]) & ~1) == (reset_address & ~1) and reset_address != 0

    return [
        metric("toolchain", "zig_target_build", 1.0, 1.0, "PASS", "Zig 真实生成 thumb-freestanding-eabihf ELF"),
        metric("elf", "arm_elf32_little_endian", 1.0 if header["machine"] == "EM_ARM" and header["elf_class"] == 32 and header["little_endian"] else 0.0, 1.0, "PASS" if header["machine"] == "EM_ARM" and header["elf_class"] == 32 and header["little_endian"] else "FAIL", "目标必须是 32 位小端 ARM ELF"),
        metric("elf", "entry_matches_reset_handler", 1.0 if entry_ok else 0.0, 1.0, "PASS" if entry_ok else "FAIL", "ELF 入口必须指向 Reset_Handler"),
        metric("elf", "vector_table_at_flash_origin", 1.0 if vector_ok else 0.0, 1.0, "PASS" if vector_ok else "FAIL", "向量表必须位于 0x08000000 且包含控制 IRQ 槽"),
        metric("elf", "release_text_matches_audit", 1.0 if text_matches_audit else 0.0, 1.0, "PASS" if text_matches_audit else "FAIL", "发布 ELF 与带符号审计 ELF 的 .text 必须逐字节相同"),
        metric("symbols", "required_symbol_count", float(required_present), float(len(REQUIRED_SYMBOLS)), "PASS" if required_present == len(REQUIRED_SYMBOLS) else "FAIL", "Reset/main/Control IRQ/固件 ISR 编排符号必须存在"),
        metric("symbols", "undefined_symbol_count", float(len(undefined)), 0.0, "PASS" if not undefined else "FAIL", "最终 ELF 不得保留未解析符号"),
        metric("memory", "flash_image_bytes", float(flash_used), float(FLASH_SIZE), "PASS" if 0 < flash_used <= FLASH_SIZE else "FAIL", "BIN 覆盖的 Flash 映像大小"),
        metric("memory", "ram_static_plus_stack_bytes", float(ram_reserved), float(RAM_SIZE), "PASS" if ram_reserved <= RAM_SIZE else "FAIL", "data+bss 加 4KB 栈保留"),
        metric("instructions", "soft_float_symbol_count", float(len(float_symbols)), 0.0, "PASS" if not float_symbols else "FAIL", "定点固件不应链接浮点运行库助手"),
        metric("instructions", "floating_instruction_count", float(len(float_instructions)), 0.0, "PASS" if not float_instructions else "FAIL", "控制映像不应出现 VFP 浮点指令"),
        metric("instructions", "int64_division_helper_count", float(len(division_helpers)), 0.0, "INFO", "64 位整数除法助手需要在目标板测量最坏执行时间"),
        metric("artifacts", "elf_nonzero_bytes", float(elf_path.stat().st_size), 1.0, "PASS" if elf_path.stat().st_size > 0 else "FAIL", "ELF 文件必须非空"),
        metric("artifacts", "bin_nonzero_bytes", float(bin_path.stat().st_size), 1.0, "PASS" if bin_path.stat().st_size > 0 else "FAIL", "BIN 文件必须非空"),
    ]


def plot_memory(path: Path, sections: list[dict[str, object]], bin_size: int) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    data_bss = sum(int(section["size_bytes"]) for section in sections if section["section"] in (".data", ".bss"))
    used = [bin_size, data_bss + STACK_RESERVE]
    capacities = [FLASH_SIZE, RAM_SIZE]
    labels = ["FLASH 映像", "RAM 静态+4KB栈"]
    colors = ["#0f766e", "#d97706"]
    fig, axes = plt.subplots(1, 2, figsize=(12.0, 5.2))
    axes[0].barh(labels, capacities, color="#e2e8f0", label="容量")
    axes[0].barh(labels, used, color=colors, label="已用/保留")
    for index, value in enumerate(used):
        axes[0].text(value + max(capacities) * 0.01, index, f"{value} B", va="center", fontsize=9)
    axes[0].set_xlabel("bytes")
    axes[0].set_title("目标内存占用", loc="left")
    axes[0].legend()
    axes[0].grid(True, axis="x", alpha=0.25)

    section_rows = [row for row in sections if int(row["size_bytes"]) > 0 and row["region"] in ("FLASH", "RAM")]
    section_rows.sort(key=lambda row: int(row["size_bytes"]), reverse=True)
    names = [str(row["section"]) for row in section_rows]
    sizes = [int(row["size_bytes"]) for row in section_rows]
    section_colors = ["#2563eb" if row["region"] == "FLASH" else "#be123c" for row in section_rows]
    axes[1].bar(names, sizes, color=section_colors)
    axes[1].set_ylabel("bytes")
    axes[1].set_title("已分配段大小", loc="left")
    axes[1].tick_params(axis="x", rotation=25)
    axes[1].grid(True, axis="y", alpha=0.25)
    fig.suptitle("第 18 章：Cortex-M4F 固件映像内存检查", fontsize=15)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def plot_symbols(path: Path, symbols: list[dict[str, object]]) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False
    functions = [symbol for symbol in symbols if symbol["type"] == "STT_FUNC" and int(symbol["size_bytes"]) > 0 and symbol["symbol"]]
    functions.sort(key=lambda symbol: int(symbol["size_bytes"]), reverse=True)
    functions = functions[:12]
    functions.reverse()
    fig, ax = plt.subplots(figsize=(11.5, 6.4))
    ax.barh([str(symbol["symbol"]) for symbol in functions], [int(symbol["size_bytes"]) for symbol in functions], color="#2563eb")
    for index, symbol in enumerate(functions):
        ax.text(int(symbol["size_bytes"]) + 4, index, f"{symbol['size_bytes']} B", va="center", fontsize=8)
    ax.set_xlabel("Thumb 函数大小 / bytes")
    ax.set_title("函数大小来自 ELF 符号表", loc="left")
    ax.grid(True, axis="x", alpha=0.25)
    fig.suptitle("第 18 章：目标固件最大函数", fontsize=15)
    fig.tight_layout(rect=(0.0, 0.0, 1.0, 0.94))
    fig.savefig(path, dpi=180)
    plt.close(fig)


def write_report(
    path: Path,
    metrics: list[dict[str, object]],
    zig_version: str,
    header: dict[str, object],
    elf_path: Path,
    bin_path: Path,
) -> None:
    passes = sum(row["status"] == "PASS" for row in metrics)
    fails = sum(row["status"] == "FAIL" for row in metrics)
    infos = sum(row["status"] == "INFO" for row in metrics)
    lines = [
        "# 第 18 章报告：Cortex-M4F 交叉构建与固件映像",
        "",
        "本报告由 `scripts/build_cortex_m4f_firmware.py` 生成。ELF/BIN、段表、符号和 Thumb 反汇编均来自本机真实 Zig 交叉构建。",
        "",
        "## 摘要",
        "",
        f"- Zig：`{zig_version}`",
        "- 目标：`thumb-freestanding-eabihf / cortex_m4 / hard-float ABI`",
        f"- ELF 入口：`0x{int(header['entry']):08X}`",
        f"- ELF 大小：{elf_path.stat().st_size} bytes",
        f"- BIN 大小：{bin_path.stat().st_size} bytes",
        f"- 指标：PASS {passes} / FAIL {fails} / INFO {infos}",
        f"- ELF SHA-256：`{sha256(elf_path)}`",
        f"- BIN SHA-256：`{sha256(bin_path)}`",
        "- 符号与反汇编来自同参数带调试审计 ELF，脚本已确认 `.text` 与发布 ELF 完全一致",
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
        "该映像证明平台无关固件可以为 Cortex-M4F 裸机目标完成编译、链接和指令生成。`target/cortex-m4f/firmware_entry.c` 使用可编译寄存器模型，未配置 STM32G4 的 RCC、ADC、TIM、DMA 或 NVIC；ELF 可审计但不能直接作为目标板功能固件烧录。",
        "",
    ])
    text = "\n".join(lines).replace("\r\n", "\n").replace("\r", "\n")
    with path.open("w", encoding="utf-8", newline="") as file:
        file.write(text.replace("\n", "\r\n"))


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    WAVE_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)

    zig = find_zig()
    if zig is None:
        print("summary,BLOCKED,未找到 Zig")
        return 2
    version_code, zig_version = run_command([zig, "version"])
    if version_code != 0:
        print(zig_version)
        return 2

    elf_path = OUTPUT_DIR / "digital_power_cortex_m4f.elf"
    bin_path = OUTPUT_DIR / "digital_power_cortex_m4f.bin"
    map_path = OUTPUT_DIR / "digital_power_cortex_m4f.map"
    list_path = OUTPUT_DIR / "digital_power_cortex_m4f.lst"
    audit_elf_path = BUILD_DIR / "digital_power_cortex_m4f.audit.elf"
    command = build_command(zig, elf_path, keep_debug=False)
    audit_command = build_command(zig, audit_elf_path, keep_debug=True)
    for label, build in (("release", command), ("audit", audit_command)):
        build_code, build_output = run_command(build)
        if build_code != 0:
            print(build_output)
            print(f"summary,FAIL,{label}_target_build_exit_code={build_code}")
            return 1
    copy_code, copy_output = run_command([zig, "objcopy", "-O", "binary", str(elf_path), str(bin_path)])
    if copy_code != 0:
        print(copy_output)
        print(f"summary,FAIL,objcopy_exit_code={copy_code}")
        return 1

    header, sections, _, release_text, release_text_address = inspect_elf(elf_path)
    audit_header, _, symbols, audit_text, audit_text_address = inspect_elf(audit_elf_path)
    text_matches_audit = (
        release_text == audit_text
        and release_text_address == audit_text_address
        and int(header["entry"]) == int(audit_header["entry"])
    )
    instructions = disassemble(audit_text, audit_text_address, symbols, list_path)
    write_map(map_path, header, sections, symbols, command)
    metrics = build_metrics(header, sections, symbols, instructions, elf_path, bin_path, text_matches_audit)
    public_symbols = [
        {
            "symbol": symbol["symbol"],
            "address": f"0x{int(symbol['address']):08X}",
            "size_bytes": symbol["size_bytes"],
            "type": symbol["type"],
            "binding": symbol["binding"],
            "section_index": symbol["section_index"],
        }
        for symbol in symbols
        if symbol["symbol"]
    ]
    write_rows(WAVE_DIR / "18-firmware-sections.csv", sections)
    write_rows(WAVE_DIR / "18-firmware-symbols.csv", public_symbols)
    write_rows(WAVE_DIR / "18-target-build-summary.csv", metrics)
    plot_memory(WAVE_DIR / "18-firmware-memory-usage.png", sections, bin_path.stat().st_size)
    plot_symbols(WAVE_DIR / "18-firmware-symbol-sizes.png", symbols)
    write_report(REPORT_DIR / "18-target-build-report.md", metrics, zig_version, header, elf_path, bin_path)

    passes = sum(row["status"] == "PASS" for row in metrics)
    fails = sum(row["status"] == "FAIL" for row in metrics)
    infos = sum(row["status"] == "INFO" for row in metrics)
    print("已生成第 18 章 Cortex-M4F ELF、BIN、map、反汇编和映像报告。")
    print(f"summary,pass={passes},fail={fails},info={infos},sections={len(sections)},symbols={len(public_symbols)},instructions={len(instructions)}")
    print(f"toolchain,zig,{zig_version},target=thumb-freestanding-eabihf,cpu=cortex_m4")
    print(f"image,elf_bytes={elf_path.stat().st_size},bin_bytes={bin_path.stat().st_size},entry=0x{int(header['entry']):08X}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
