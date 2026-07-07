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

博客改为教学系列，采用“教学 + 项目实战 + 问题复盘”的结构。第一组文章：

```text
1. 为什么从 Buck 开始做 MATLAB + PLECS 仿真
2. 搭建开环 Buck，验证固定占空比下的输出
3. Buck 功率级参数初步估算
4. 加入离散 PI 电压环
5. 占空比限幅和抗积分饱和
6. 软启动设计
7. UVLO / OVP / OCP 保护逻辑
8. 电源状态机设计
9. 负载突变测试和波形分析
10. 从仿真控制器整理到 C 风格代码
```

单篇文章固定结构：

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

## 发布节奏

```text
先 GitHub commit
再补 docs
再写 blog
最后 CSDN 发布
```

这样可以保证教程不是空讲概念，每一篇都能对应到仓库里的模型、代码、波形或文档。

## 图片处理

文章中的拓扑图、控制框图和状态机图优先自绘，统一放在：

```text
assets/figures/
```

SVG 作为源图保存，PNG 用于 Markdown 引用。发布 CSDN 时，需要把 PNG 图片上传到 CSDN 编辑器，再替换文章里的本地相对路径。
