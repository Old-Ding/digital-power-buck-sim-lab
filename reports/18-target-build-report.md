# 第 18 章报告：Cortex-M4F 交叉构建与固件映像

本报告由 `scripts/build_cortex_m4f_firmware.py` 生成。ELF/BIN、段表、符号和 Thumb 反汇编均来自本机真实 Zig 交叉构建。

## 摘要

- Zig：`0.16.0`
- 目标：`thumb-freestanding-eabihf / cortex_m4 / hard-float ABI`
- ELF 入口：`0x08000F85`
- ELF 大小：131652 bytes
- BIN 大小：5112 bytes
- 指标：PASS 13 / FAIL 0 / INFO 1
- ELF SHA-256：`40a9257c4f46093f5209d5cabf16e46210364fa7f1e9bdd5b887a5607608e530`
- BIN SHA-256：`fb4944639f645579acbdacc81d164c454414ddcf86cdf563e843498a1aa5ce7a`
- 符号与反汇编来自同参数带调试审计 ELF，脚本已确认 `.text` 与发布 ELF 完全一致

## 指标

| 场景 | 指标 | 实际值 | 限制/参考 | 状态 | 说明 |
| --- | --- | ---: | ---: | --- | --- |
| `toolchain` | `zig_target_build` | 1 | 1 | PASS | Zig 真实生成 thumb-freestanding-eabihf ELF |
| `elf` | `arm_elf32_little_endian` | 1 | 1 | PASS | 目标必须是 32 位小端 ARM ELF |
| `elf` | `entry_matches_reset_handler` | 1 | 1 | PASS | ELF 入口必须指向 Reset_Handler |
| `elf` | `vector_table_at_flash_origin` | 1 | 1 | PASS | 向量表必须位于 0x08000000 且包含控制 IRQ 槽 |
| `elf` | `release_text_matches_audit` | 1 | 1 | PASS | 发布 ELF 与带符号审计 ELF 的 .text 必须逐字节相同 |
| `symbols` | `required_symbol_count` | 4 | 4 | PASS | Reset/main/Control IRQ/固件 ISR 编排符号必须存在 |
| `symbols` | `undefined_symbol_count` | 0 | 0 | PASS | 最终 ELF 不得保留未解析符号 |
| `memory` | `flash_image_bytes` | 5112 | 524288 | PASS | BIN 覆盖的 Flash 映像大小 |
| `memory` | `ram_static_plus_stack_bytes` | 4376 | 131072 | PASS | data+bss 加 4KB 栈保留 |
| `instructions` | `soft_float_symbol_count` | 0 | 0 | PASS | 定点固件不应链接浮点运行库助手 |
| `instructions` | `floating_instruction_count` | 0 | 0 | PASS | 控制映像不应出现 VFP 浮点指令 |
| `instructions` | `int64_division_helper_count` | 2 | 0 | INFO | 64 位整数除法助手需要在目标板测量最坏执行时间 |
| `artifacts` | `elf_nonzero_bytes` | 131652 | 1 | PASS | ELF 文件必须非空 |
| `artifacts` | `bin_nonzero_bytes` | 5112 | 1 | PASS | BIN 文件必须非空 |

## 证据边界

该映像证明平台无关固件可以为 Cortex-M4F 裸机目标完成编译、链接和指令生成。`target/cortex-m4f/firmware_entry.c` 使用可编译寄存器模型，未配置 STM32G4 的 RCC、ADC、TIM、DMA 或 NVIC；ELF 可审计但不能直接作为目标板功能固件烧录。
