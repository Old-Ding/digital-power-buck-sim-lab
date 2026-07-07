# 测试矩阵

## 必测工况

| 用例 | 工况 | 关键观察量 |
| --- | --- | --- |
| startup_no_load | 空载启动 | Vout、duty、integrator |
| startup_full_load | 满载启动 | Vout、IL/Iout、duty |
| load_step_20_to_100 | 20% 到 100% 负载突变 | 下陷幅度、恢复时间 |
| load_step_100_to_20 | 100% 到 20% 负载突变 | 过冲幅度、恢复时间 |
| input_step_low | Vin 降到 18V | duty 是否触顶 |
| input_uvlo | Vin 低于 UVLO | 是否关断并锁存 |
| ocp_fault | 输出过流 | 是否触发 OCP |
| ovp_fault | 输出过压 | 是否触发 OVP |

## 记录模板

```text
测试目的:
输入条件:
期望结果:
关键波形:
异常现象:
根因分析:
最小修改:
验证结果:
对应 commit:
```
