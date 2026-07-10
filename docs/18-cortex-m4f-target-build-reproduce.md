# 第 18 章复现说明：Cortex-M4F 交叉构建与映像检查

## 目标

使用 Zig 真实生成 Cortex-M4F 裸机 ELF/BIN，检查复位入口、向量表、段布局、关键符号、内存容量、浮点依赖和 64 位除法助手，并导出 map、反汇编、CSV、PNG 和报告。

## 环境

- Python 3
- matplotlib
- pyelftools 0.33 或兼容版本
- Capstone 5.x
- Zig 0.16.0 或兼容版本

安装 Python 依赖：

```powershell
python -m pip install pyelftools capstone
```

## 最短命令

```powershell
python scripts\build_cortex_m4f_firmware.py
```

预期摘要：

```text
summary,pass=13,fail=0,info=1,sections=5,symbols=107,instructions=1695
toolchain,zig,0.16.0,target=thumb-freestanding-eabihf,cpu=cortex_m4
image,elf_bytes=131652,bin_bytes=5112,entry=0x08000F85
```

## 构建流程

脚本执行两次同参数交叉构建：

| 构建 | 输出 | 用途 |
| --- | --- | --- |
| 发布构建 | `firmware/cortex-m4f/digital_power_cortex_m4f.elf` | 公开、提取 BIN、检查段和入口 |
| 审计构建 | `artifacts/target-build/chapter18/digital_power_cortex_m4f.audit.elf` | 保留符号和调试信息，生成 map/反汇编 |

两者只相差 `-g`，脚本要求 `.text` 字节和入口地址完全一致。

## 关键目标参数

```text
-target thumb-freestanding-eabihf
-mcpu=cortex_m4
-mthumb
-mfloat-abi=hard
-mfpu=fpv4-sp-d16
-ffreestanding
-fno-builtin
-Os
```

链接脚本：`target/cortex-m4f/linker.ld`。

## 当前段布局

| 段 | 地址 | 大小 |
| --- | --- | ---: |
| `.isr_vector` | `0x08000000` | 68 B |
| `.text` | `0x08000044` | 4800 B |
| `.ARM.exidx` | `0x08001304` | 208 B |
| `.data` | `0x20000000` | 36 B |
| `.bss` | `0x20000024` | 244 B |

内存检查：

| 项目 | 当前值 | 容量 |
| --- | ---: | ---: |
| Flash BIN | 5112 B | 524288 B |
| `.data + .bss + 4KB stack` | 4376 B | 131072 B |

## 当前指令与符号检查

| 检查 | 当前结果 |
| --- | ---: |
| 必需符号 | 4/4 |
| 未解析符号 | 0 |
| 浮点运行库助手 | 0 |
| VFP 浮点指令 | 0 |
| 64 位整数除法助手 | 2，INFO |
| Thumb 反汇编指令 | 1695 |

两个除法助手为 `__aeabi_ldivmod` 和 `__aeabi_uldivmod`，需要目标板周期计数，不作为构建失败。

## 生成文件

| 文件 | 内容 |
| --- | --- |
| `firmware/cortex-m4f/digital_power_cortex_m4f.elf` | 发布 ELF |
| `firmware/cortex-m4f/digital_power_cortex_m4f.bin` | Flash 二进制 |
| `firmware/cortex-m4f/digital_power_cortex_m4f.map` | 段和符号映射 |
| `firmware/cortex-m4f/digital_power_cortex_m4f.lst` | Thumb 反汇编 |
| `waveforms/18-firmware-sections.csv` | 分配段数据 |
| `waveforms/18-firmware-symbols.csv` | 审计符号表 |
| `waveforms/18-target-build-summary.csv` | PASS/FAIL/INFO 指标 |
| `waveforms/18-firmware-memory-usage.png` | Flash/RAM 与段大小 |
| `waveforms/18-firmware-symbol-sizes.png` | 最大函数大小 |
| `reports/18-target-build-report.md` | 哈希和完整报告 |

## 常见失败

### string.h 或 memset 找不到

裸机 freestanding 目标没有默认 libc。检查生产源是否隐含依赖主机标准库；小型必要操作应使用明确的目标运行库或项目内实现。

### `__aeabi_ldivmod` 未解析

不要使用 `-nostdlib` 直接切断 Zig compiler-rt。当前构建保留编译器运行库，但不链接主机 libc。

### ELF 警告找不到 `_start`

确认传入 `-Wl,--entry=Reset_Handler`，并在链接脚本中保留 `ENTRY(Reset_Handler)`。

### 发布 ELF 和审计 ELF 的 `.text` 不一致

检查两次构建是否除了 `-g` 之外还有优化、宏、目标 CPU 或源码差异。不要继续使用不匹配的反汇编证据。

### 向量表不在 `0x08000000`

检查 `.isr_vector` 是否使用 `KEEP()`，链接脚本 FLASH 起始地址是否正确，以及启动文件是否带 section 属性。

### BIN 明显大于已分配代码

检查 ELF 各可加载段的物理地址是否出现大空洞。BIN 会填充段之间的地址间隔。

### 发现 VFP 指令或浮点助手

定位符号和反汇编调用者，确认是否意外把浮点日志、常量或算法带入控制映像。仅设置 hard-float ABI 不应自动产生浮点计算。

### 64 位除法影响 3.5 us 预算

先在目标板用 DWT 周期计数器测量各阶段，再决定是否改为预计算倒数、常量除法或调整标度。没有实测前不要为消除符号重写算法。
