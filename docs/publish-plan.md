# 发布计划

## GitHub

建议仓库名：

```text
digital-power-buck-sim-lab
```

建议公开策略：

```text
前期可以 private，模型和文章结构稳定后改 public。
如果目标是作品集，也可以直接 public，但 README 中不要写未完成结果。
```

每个阶段至少一个 commit：

```text
chore: scaffold digital power buck simulation lab
feat: add open-loop buck power stage model
feat: add discrete pi voltage loop
feat: add soft-start reference ramp
feat: add protection state machine
docs: add load transient test report
docs: add csdn article for open-loop buck
```

## CSDN

博客只写问题型复盘，不写流水账。第一组文章：

```text
1. 24V 到 12V/5A 数字 Buck 仿真项目设计
2. 为什么数字电源要先做开环 Buck 仿真
3. 离散 PI 电压环如何控制 Buck 输出
4. 占空比限幅和抗积分饱和为什么必须做
5. 软启动为什么不能直接给 12V 目标值
6. 电源软件状态机如何设计
7. 负载突变时输出下陷怎么分析
8. 从 PLECS/Simulink 控制器迁移到 C 代码
```

## 发布节奏

```text
先 GitHub commit
再补 docs
再写 blog
最后 CSDN 发布
```

这样可以保证博客里的每个结论都有仓库内容支撑。
