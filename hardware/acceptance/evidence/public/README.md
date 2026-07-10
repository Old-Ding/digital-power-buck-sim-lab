# 公开硬件证据

通过验收后，把经过筛选且不含个人或设备敏感信息的证据放在本目录，并在 `measurements.local.csv` 中使用仓库相对路径引用。

建议格式：

- 板级 HAL 构建与烧录日志：TXT
- 调试器连接或启动遥测记录：TXT/PNG
- 示波器截图：PNG
- 台架全景和接线照片：JPG/PNG
- 长时间温升数据：CSV
- 仪器导出波形：CSV

文件名以测试编号开头，例如 `FW-01-flash-log.txt`、`PWM-02-deadtime.png`、`LOAD-01-transient.csv`。提交前移除日志中的本机绝对路径、用户名和设备序列号。
