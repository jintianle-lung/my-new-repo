# 识字小乐园

面向读写训练的浏览器小游戏集合，目前包含 7 个小游戏。入口是 [index.html](index.html)，可下载或克隆仓库后用浏览器打开。

## 在 Codex 中使用规划技能

本仓库内置 **liran-plan 4.52**，来源为 [zarq/liran-plan-docs](https://gitee.com/zarq/liran-plan-docs)，固定提交 `4ee5b9e531b761a222e0f54529e39f952801e83b`。

用 Codex 打开本仓库后，从 [AGENTS.md](AGENTS.md) 读取工作规则；技能位于 [.agents/skills/liran-plan/SKILL.md](.agents/skills/liran-plan/SKILL.md)。支持仓库技能发现的环境可以使用 `$liran-plan`；如果技能未被列出或存在多个同名版本，直接要求 Codex 先读取上述仓库内路径，再按其流程整理当前需求。

技能包含引用资料、模板、校验脚本和配套测试，任务文档写在 `liran_docs/`。上游设计说明及原话作为技能校验资料保存在技能目录内，与游戏自身需求分开。

## 核对技能文件

从仓库根目录执行（需要 Python 3.10 或以上）：

```sh
cd .agents/skills/liran-plan
python scripts/check_adaptive_flow_docs.py
python scripts/check_codex_ui_flow_docs.py
python -m unittest discover -s tests
```

这些检查验证技能文档与校验器，不表示全部小游戏已经通过浏览器测试。上游的全局安装测试需要系统允许创建符号链接；Windows 缺少该权限时，这一测试会报 WinError 1314，需与其他测试结果分开记录。

## 来源与许可

第三方技能沿用其 [MIT 许可证](.agents/skills/liran-plan/LICENSE)。作者电脑的 6 处技能链接已改为相对路径；原始及接入后的逐文件 SHA-256、来源版本、提交和本地适配清单见 [UPSTREAM.json](.agents/skills/liran-plan/UPSTREAM.json)。游戏代码的许可范围不由第三方技能的 MIT 许可证扩展。
