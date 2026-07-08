# CSDN 教学系列目录

系列名称暂定：

```text
MATLAB + PLECS 数字电源仿真入门
```

## 系列定位

这个系列按“教学 + 项目实战 + 问题复盘”组织，不再写成单纯项目说明。

每篇文章尽量满足三个要求：

```text
1. 能让读者知道这一篇要解决什么问题
2. 能解释为什么这样设计
3. 能对应到 GitHub 里的模型、代码或文档
```

## 文章规划

| 序号 | 文件 | 主题 |
| --- | --- | --- |
| 01 | 01-project-overview.md | 为什么从 Buck 开始做 MATLAB + PLECS 仿真 |
| 02 | 02-open-loop-buck.md | 搭建开环 Buck，验证固定占空比下的输出 |
| 03 | 03-buck-parameter-design.md | 电感、电容和开关频率初步选择 |
| 04 | 04-discrete-pi-control.md | 加入离散 PI 电压环 |
| 05 | 05-duty-limit-anti-windup.md | 占空比限幅和抗积分饱和 |
| 06 | 06-soft-start.md | 软启动设计 |
| 07 | 07-protection-state-machine.md | 保护逻辑和状态机 |
| 08 | 08-load-transient.md | 负载突变测试和波形分析 |
| 09 | 09-adc-noise-duty-jitter.md | ADC 噪声和 duty 抖动 |
| 10 | 10-controller-to-c.md | 从仿真控制器整理到 C 风格代码 |

## 单篇结构

```text
前言
目录
这一篇解决什么问题
前置知识
模型或代码怎么搭
关键变量怎么看
结果怎么判断
常见问题
小结
下一篇预告
```

## 图片规范

教程文章优先使用仿真软件和测试结果的真实截图，自绘图只用于解释抽象关系。

图片按来源分目录保存：

```text
assets/figures/       自绘概念图，例如控制链路、状态机、教学示意图
assets/screenshots/   PLECS、MATLAB/Simulink 等软件界面截图
waveforms/            仿真波形、测试结果图
```

原则：

```text
能用 PLECS/MATLAB 真实截图说明的，不用自绘图替代
能用仿真波形证明的，不只写文字结论
自绘图只承担概念解释职责，不伪装成仿真结果
```

SVG 作为自绘源图保存，PNG 用于 Markdown 引用和 CSDN 上传。发布到 CSDN 时，需要把对应 PNG 图片上传到 CSDN 编辑器，再替换为 CSDN 图片链接。

第一篇当前使用的图片：

| 图片 | 用途 |
| --- | --- |
| buck-topology.png | Buck 功率级拓扑 |
| digital-control-loop.png | 数字闭环控制链路 |
| power-state-machine.png | 电源软件状态机 |

从第 2 篇开始，文章主体图片应优先来自 PLECS 模型截图和仿真波形截图。
