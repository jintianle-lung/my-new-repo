#!/usr/bin/env python3
"""Validate the liran-plan adaptive workflow routing contract."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import sys
from typing import Any, Literal
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
CURRENT_VERSION = "4.52"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MULTI_AGENT_OPENING = (
    "你自行判断本任务是否需要多智能体协作；如需开启，只允许一个主智能体统筹，"
    "任一时刻最多同时运行五个子代理，子代理完成后必须及时回收，"
    "回收后可按需启用新的子代理，禁止子代理继续派生代理。"
)

CHECK_FILES = [
    ".gitignore",
    "AGENTS.md",
    "SKILL.md",
    "README.md",
    "docs/技能设计文档.md",
    "docs/用户原话.md",
    "docs/pitfalls/general.md",
    "references/四档自适应流程.md",
    "references/提示词向导.md",
    "references/功能1-原话留存.md",
    "references/功能2-需求讨论与分层文档.md",
    "references/功能3-高保真原型.md",
    "references/功能4-开发追踪与顺序.md",
    "references/功能5-任务微观化与提示词.md",
    "references/功能6-真机实测与回写.md",
    "references/模式-新项目引导.md",
    "references/模式-老项目初始化.md",
    "references/使用教程-常用提示词清单.md",
    "references/liran-plan-使用教程.html",
    "references/plan-docs-使用教程.html",
    "templates/03-索引.md",
    "templates/04-开发追踪.md",
    "templates/08-测试用例.md",
    "templates/09-真机实测.md",
    "templates/10-UI壳接入清单.md",
    "templates/UI壳单项接入清单.md",
    "templates/需求整理工作文档.md",
    "templates/正式PRD.md",
    "templates/任务归档.md",
    "templates/任务正式归档目标提示词.md",
    "templates/Stitch-实例级细节复修提示词.md",
    "templates/通用完整执行提示词规范.md",
]

FILE_REQUIRED_PHRASES = {
    ".gitignore": [
        ".playwright-mcp/",
    ],
    "docs/用户原话.md": [
        "多目标阶段节奏与纯文本选项",
        "深度流程还是必须两次 goal",
        "选项框需要正常文本输出",
    ],
    "SKILL.md": [
        "四档自适应流程",
        "修改前评分",
        "修改后评分",
        "正常 Markdown 加粗文本",
        "一个 Codex 单选框",
        "待用户验收",
        "未命中安全门禁时，采用用户指定档位",
        "以下完整结构只由完整流程默认创建",
        "任何档位都不得伪造",
        "客观不涉及 UI",
        "完整流程的验收责任和页面样式必须在同一个选择问题",
        "完整流程的最后验收目标按已确认的验收责任分支",
        "需求讨论每轮更新需求整理文档",
        "只有完整流程默认多轮整理",
        "`request_user_input` 可用时必须实际调用",
        "收到选择结果后的同一轮",
        "一个独立的 Markdown 代码块",
        "references/四档自适应流程.md",
        "3000–10000",
        "3000–10000",
        "通用完整执行提示词规范",
        "--prompt-kind long",
        "--prompt-kind stitch-instance-repair",
        "实例级复修提示词也必须保持 3000–10000 个字符",
        "任一时刻最多同时运行五个子代理",
        "回收后可按需启用新的子代理",
        "--archive-stage handoff",
        "运行时硬门禁",
        "## 流程合同",
        "## 档位执行门禁",
        "编码解锁门禁",
        "真实提示词校验",
        "4.4 PRD 生命周期与单任务归档合同",
        "深度非 UI：固定 2 次",
        "完整 UI：固定 4 次",
        "--goal-transition-file",
        "--goal-reclaim-file",
        "选项一：",
        "不得用 Markdown 格式",
        "需求整理文档",
        "归档受阻",
        "本次任务已完成并归档",
        "不能靠漏传参数绕过",
        "本轮新增、变更、确认、待确认项和真实路径",
        "liran_docs/requirements/<任务ID>-<任务名称>-需求整理.md",
        "需求状态：已确认",
        "候选想法：待评估",
        "CHG 编号",
        "PRD 只记录产品/功能需求事实",
        "唯一闭环顺序",
        "正式 PRD 待确认",
        "正式 PRD 需要修改",
        "待用户检查",
        "待归档确认",
        "用户明确回复“归档”后才启动独立正式归档",
        "正式 PRD 必须完整承接需求整理文档中的已确认需求",
    ],
    "AGENTS.md": [
        "Adaptive Workflow Precedence",
        "四档流程控制目标任务的研发过程，不取消本仓库自身的发布门禁",
        "用户在四档确认框中选择 Codex 真机测试",
    ],
    "references/提示词向导.md": [
        "具体任务直接分档",
        "六类场景和四档流程分离",
        "需求整理得对不对？改完后怎么测试？",
        "需求没问题，改完后让 Codex 自己真机测试",
        "需求没问题，但让 Codex 重新判断是否需要深度流程",
        "3000–10000",
        "3000–10000",
        "通用完整执行提示词规范",
        "--prompt-kind stitch-instance-repair",
        "任一时刻最多同时五个子代理",
        "真实提示词交付前门禁",
        "canonical builder",
        "4.9 需求整理文档与正式 PRD",
        "只有最后目标负责最终验收交接",
        "选项一：",
        "只回复本轮新增、变更、待确认点和真实路径",
        "正式 PRD 待确认",
    ],
    "references/四档自适应流程.md": [
        "没有命中安全门禁时，采用用户指定档位",
        "完整流程候选",
        "事实证据与禁止幻觉",
        "升级到完整流程",
        "**最终流程：",
        "修改前评分：",
        "修改后评分：",
        "流程变化：",
        "修改内容：",
        "内部测试：",
        "真机测试：",
        "页面样式检查：",
        "文档回写：",
        "最终状态：",
        "3000–10000",
        "3000–10000",
        "十一项标准结构",
        "运行时阶段门禁",
        "编码前门禁",
        "4.9 需求整理文档、正式 PRD 与归档门禁",
        "深度非 UI 固定 2 次",
        "完整 UI 固定 4 次",
        "归档中 → 已归档 → 已完成",
    ],
    "references/功能2-需求讨论与分层文档.md": [
        "轻量流程",
        "标准流程",
        "深度流程",
        "完整流程",
        "完整分层文档纪律只在完整流程",
        "页面样式检查按用户选择执行",
        "4.4 文档先行规则",
        "绝不乱放",
    ],
    "references/功能3-高保真原型.md": [
        "不检查页面样式是否符合方案",
        "Stitch 一比一还原",
        "Stitch 路线不调用 Product Design Design QA",
        "可以进入实例级细节复修",
        "初次承接受阻",
        "复修通过后才允许生成业务接线 /goal",
        "其他 Product Design 路线仍保留 Design QA",
        "深度流程中的 UI 壳与 Stitch",
        "完整流程核心分工",
        "开发目标衔接",
        "页面样式检查按用户选择执行",
        "Product Design Design QA 与 Stitch 复修分流",
        "通用完整执行提示词规范",
        "3000–10000",
        "3000–10000",
        "4.4 UI 过程资料生命周期",
    ],
    "references/功能4-开发追踪与顺序.md": [
        "待用户验收",
        "用户验收通过",
        "4.4 活动追踪与归档边界",
        "4.6 多目标阶段追踪",
        "当前第 N/M 次",
        "外部 AI 或 Stitch 的等待与恢复属于同一次 UI 目标",
        "归档受阻",
    ],
    "references/功能5-任务微观化与提示词.md": [
        "轻量 /goal",
        "标准 /goal",
        "深度 /goal",
        "完整流程非 UI",
        "更新受影响的 `liran_docs`",
        "不得要求用户复制第二条提示词",
        "以下章节只适用于完整流程",
        "通用完整执行提示词规范",
        "3000–10000",
        "3000–10000",
        "4.4 最终目标交接与独立归档",
    "archive_stage=\"non-final\"",
        "--goal-reclaim-file",
    ],
    "references/功能6-真机实测与回写.md": [
        "Codex 自己真机测试",
        "我自己测试",
        "待用户验收",
        "页面样式是否符合方案",
        "Codex 真机分支必须经过 `真机测试通过 → 待用户检查 → 待归档确认 → 归档中 → 已归档`",
        "用户自己测试分支必须经过 `用户验收通过 → 待用户检查 → 待归档确认 → 归档中 → 已归档`",
        "最后目标按已确认的验收责任分支",
        "`@Chrome` 无法完成时自动切换 `@电脑`",
        "通用完整执行提示词规范",
        "3000–10000",
        "3000–10000",
        "4.4 验收后的归档确认",
        "本次任务已完成并归档",
    ],
    "templates/04-开发追踪.md": [
        "待用户验收",
        "用户验收通过",
        "基础目标数",
        "当前目标",
        "UI 路线",
        "外部等待",
        "当前没有活动开发任务",
        "归档受阻",
        "修改前评分",
        "五维评分",
        "评分证据",
        "流程等级",
        "安全门禁",
    ],
    "templates/03-索引.md": [
        "当前任务入口",
        "archive/README.md",
    ],
    "templates/08-测试用例.md": [
        "精简稳定回归基线",
        "当前没有活动测试任务",
        "任务 ID",
    ],
    "templates/09-真机实测.md": [
        "验收责任",
        "Codex 真机测试",
        "用户自己测试",
        "当前目标：<第 N/M 次；必须是最后一次>",
        "UI 路线",
        "只能在本轮最后一次目标执行和收口",
        "用户验收通过 → 待用户检查 → 待归档确认",
        "任务 ID",
        "归档中 → 已归档 → 已完成",
        "当前没有待实测、失败或待复测任务",
    ],
    "templates/10-UI壳接入清单.md": [
        "流程档位",
        "当前目标：<第 N/M 次 UI 目标>",
        "UI 路线：<codex / product-design / external-ai / stitch / embedded-model>",
        "等待外部 AI 或 Stitch 返回时",
        "页面样式检查",
        "验收责任",
        "|---|---|---|---|---|---|---|---|---|---|",
        "复修通过后进入当前档位 /goal",
        "任务 ID",
        "单任务归档",
    ],
    "templates/UI壳单项接入清单.md": [
        "流程档位",
        "页面样式检查",
        "验收责任",
        "后续开发目标接真实 API",
        "后续开发目标再替换为真实 API 数据",
        "任务 ID",
        "PRD 需求文档",
    ],
    "templates/需求整理工作文档.md": [
        "需求整理",
        "任务 ID",
        "目前讨论内容",
        "已确认的内容",
        "还没有确认的内容",
        "当前形成的流程",
        "当前验收想法",
        "项目调查补充",
        "本轮结论",
        "下一轮继续讨论",
        "不是正式 PRD",
        "不强制正式章节",
    ],
    "templates/正式PRD.md": [
        "# <任务名称> · PRD",
        "文档状态：正式 PRD",
        "需求状态：已确认",
        "## 22. 当前状态与下一步",
        "只保存最终确认的产品需求",
    ],
    "templates/任务归档.md": [
        "安全归档校验",
        "归档受阻",
        "其他活动任务未受影响",
        "归档前活动任务 ID",
        "本次任务已完成并归档",
    ],
    "templates/Stitch-实例级细节复修提示词.md": [
        "页面结构与布局",
        "字体与文本排版",
        "颜色和视觉样式",
        "图片和视觉资源",
        "层级与组合关系",
        "状态表现",
        "响应式与不同视口",
        "控件规格是完整视觉保真的一个维度",
        "不适用：当前 Stitch 原始产物中不存在该元素。",
        "实例级复修提示词也必须保持 3000–10000 个字符",
    ],
    "templates/通用完整执行提示词规范.md": [
        "普通目标提示词不设 3000 字最低门槛",
        "专项提示词继续执行自身的长度",
        "任务性质",
        "当前场景",
        "目标和完成结果",
        "读取要求",
        "修改范围",
        "执行步骤",
        "业务与安全边界",
        "UI 专项要求",
        "验证要求",
        "完成后输出",
        "收口条件",
        "代码块后不得再追加执行要求",
        "任一时刻最多同时运行五个子代理",
        "子代理完成后必须及时回收",
        "回收后可按需启用新的子代理",
        "任务文档与归档合同",
        "--archive-stage handoff",
    ],
    "README.md": [
        f"版本：`{CURRENT_VERSION}`",
        f"{CURRENT_VERSION} 这次修了什么",
        "四档自适应流程",
        "0–35",
        "36–69",
        "70–89",
        "90–100",
        "简单多模块改造按标准流程",
        "复杂多模块改造按深度流程",
        "模块数量不能单独触发深度",
        "完整流程必须同时命中项目级硬门槛",
        "页面样式检查按用户选择执行",
        "3.7 提示词质量补强",
        "3000–10000",
        "并发上限而非累计上限",
        "需求整理文档先行",
        "单任务自动归档",
    ],
        "docs/技能设计文档.md": [
        f"liran-plan {CURRENT_VERSION}",
        "修改前评分",
        "流程已升级",
        "待用户验收",
        "页面样式检查按用户选择执行",
        "3000–10000",
        "通用完整执行提示词规范",
        "任一时刻最多同时五个子代理",
        "任务文档与归档生命周期",
        "归档受阻",
    ],
    "docs/pitfalls/general.md": [
        "修改行数小不代表影响小",
        "未知不能打零分",
        "手动验收不能标完成",
        "加粗状态不能放代码块",
        "用户选择不能被后续无条件门禁覆盖",
        "共用模板不能残留完整流程阶段名",
        "只检查正向关键词会产生假绿",
        "完整流程纪律没有按档位限定",
        "顶层原则和兜底入口也必须标明档位作用域",
        "确认框、自动交付和代码块必须是可执行合同",
        "短口令不等于完整执行提示词",
        "3000–10000",
        "先归档后清理",
        "归档受阻",
        "用一条长目标包住所有阶段会让责任和归档失控",
        "--goal-transition-file",
    ],
}

FORBIDDEN_FILE_PATTERNS = {
    "references/功能3-高保真原型.md": [
        r"(?m)^核心分工：$",
        r"(?m)^## 第一次 /goal 衔接$",
        r"即使不再生成独立 HTML，Design QA 仍然保留",
        r"不进入第一次 `/goal` 接业务",
        r"(?m)^- \*\*下游\*\*：第一次 `/goal`",
        r"哪些壳需要第一次 `/goal` 接线",
        r"Codex 第一次 `/goal` 要接入的任务清单",
        r"(?m)^- 第一次 `/goal` 再把这些静态数据",
        r"已确认的真机或用户验收责任、Design QA 和问题回写",
        r"完整流程第二次 /goal 负责：真机测试、问题回写、复测收口",
    ],
    "references/功能5-任务微观化与提示词.md": [
        r"(?m)^## 两种交付方式$",
        r"(?m)^### 方式 B —— 第一次 `/goal`",
        r"需要真实操作验证的任务，继续衔接功能六，并用第二次 `/goal`",
    ],
    "references/功能6-真机实测与回写.md": [
        r"(?m)^- 没有 `真机测试通过`，不允许进入 `已完成`。$",
        r"(?m)^- 真机实测默认由 Codex 全程执行",
        r"完整流程的真机阶段对应第二次 `/goal`",
    ],
    "templates/09-真机实测.md": [
        r"没有 `真机测试通过`，不允许进入 `已完成`",
    ],
    "templates/10-UI壳接入清单.md": [
        r"UI 壳接收检查通过后，第一次 `/goal` 才能",
        r"第一次 /goal 接线范围",
        r"进入第一次 /goal / 修 UI 壳 / 回写问题",
    ],
    "templates/UI壳单项接入清单.md": [
        r"(?m)^## Codex 第一次 /goal 接线任务$",
        r"临时入口处理：第一次 `/goal` 时",
        r"\| 第一次 `/goal` 接",
        r"；第一次 `/goal` 再替换为真实 API 数据",
    ],
    "references/liran-plan-使用教程.html": [
        r"需求确认后，用一条提示词同时把新增功能写进",
        r"再继续拆任务或开第一次 `/goal`",
        r"接收检查不通过时不能进入第一次 /goal",
        r"第二次 `/goal` 才做真机验收",
        r"第二次 `/goal` 真机闭环",
        r"详细的需求整理总结让我确认；确认无误后",
        r"用一个 Codex 单选框[^<\n]*我确认后只生成",
    ],
    "references/plan-docs-使用教程.html": [
        r"需求确认后，用一条提示词同时把新增功能写进",
        r"再继续拆任务或开第一次 `/goal`",
        r"接收检查不通过时不能进入第一次 /goal",
        r"第二次 `/goal` 才做真机验收",
        r"第二次 `/goal` 真机闭环",
        r"详细的需求整理总结让我确认；确认无误后",
        r"用一个 Codex 单选框[^<\n]*我确认后只生成",
    ],
    "references/使用教程-常用提示词清单.md": [
        r"详细的需求整理总结让你确认；你确认无误后",
        r"详细的需求整理总结让我确认；确认无误后",
        r"用一个 Codex 单选框[^\n]*我确认后只生成",
    ],
    "references/提示词向导.md": [
        r"详细的需求整理总结让你确认；你确认无误后",
        r"(?m)^\*\*需求整理得对不对？",
        r"(?m)^\d+\.\s+\$liran-plan",
        r"第一次目标模式：内部开发与内部验证",
    ],
    "references/四档自适应流程.md": [
        r"问题：`需求整理得对不对？改完后怎么测试？`",
        r"复修通过后才能继续同一深度目标的业务实现",
    ],
    "references/模式-新项目引导.md": [
        r"没有内部验证与真机实测通过，不要把模块标记为 `已完成`",
        r"第一次 `/goal` 达到内部完成状态后，创建 `liran_docs/09-真机实测\.md`，进入真实操作验证与问题回写闭环",
        r"详细总结给用户确认；确认无误后",
    ],
    "references/模式-老项目初始化.md": [
        r"开第一次 `/goal` 内部闭环，再走真机实测与回写（功能六）",
        r"详细总结给用户集中确认；确认无误后",
    ],
    "SKILL.md": [
        r"`已完成`：真机测试通过，且问题回写",
        r"H3\. \*\*真机实测不问用户继续\*\*：真机阶段由 Codex 全程托管",
        r"真机没跑通前，不标完成。",
        r"G1\. \*\*细到独立成文\*\*：哪怕只有几十个字（如一个按钮的逻辑），也单独成文档",
        r"G2\. \*\*改结构先改索引\*\*：任何模块增删改，先更新 `liran_docs/03-索引\.md`",
        r"G3\. \*\*文档与任务拆分同步产出\*\*：用户确认需求整理总结后，同一条提示词里同时生成/更新文档体系并一次性拆完全部微观任务",
        r"12\. 如果本轮涉及 UI，提示词里要明确要求：先确认文本视觉方案，必要时确认视觉图/原型图；造壳前由 Codex 生成 `liran_docs/10-UI壳接入清单\.md`",
        r"没有 UI 壳接入清单，不允许开第一次 `/goal`",
        r"D2\. 第二次 `/goal` 只做真实目标环境验收",
        r"\*\*第二次 `/goal`：真机验收闭环\*\*",
    ],
    "references/功能2-需求讨论与分层文档.md": [
        r"(?m)^- \*\*细到独立成文\*\*：细到每个功能模块、子模块、甚至",
    ],
    "templates/任务正式归档目标提示词.md": [
        "只有用户明确回复“归档”后才允许",
        "归档失败时保留活动区原文",
        "不计入普通目标数量",
    ],
}

REQUIRED_PHRASES = [
    "轻量流程",
    "标准流程",
    "深度流程",
    "完整流程",
    "项目现状",
    "修改规模",
    "依赖影响",
    "风险回滚",
    "验证复杂度",
    "当前流程：",
    "开始方式：",
    "选择原因：",
    "流程已升级：",
    "升级原因：",
    "修改后评分：",
    "待用户验收",
    "用户验收通过",
    "一个 Codex 单选框",
    "不得要求用户复制第二条提示词",
    "任务 ID",
    "归档受阻",
    "已归档",
    "goal_status=reclaim_pending",
    "goal_status=reclaimed",
    "用户检查不再占用普通目标执行状态",
    "archive 不计入普通 N/M",
    "归档失败时原普通目标保持 reclaimed",
    "重复回收必须幂等",
]

PRESSURE_SCENARIOS = [
    "S01-独立小Bug进入轻量流程",
    "S02-单模块多文件进入标准流程",
    "S03-一行共享逻辑进入深度流程",
    "S04-新项目进入完整流程",
    "S05-未知依赖不能打零分",
    "S06-低档位命中门禁自动升级",
    "S07-修改后发现调用方自动升级",
    "S08-用户自测进入待用户验收",
    "S09-UI小修不创建完整UI壳",
    "S10-单页面调整进入标准流程",
    "S11-新页面复杂状态进入深度流程",
    "S12-真机测试但不检查页面样式",
    "S13-Stitch不得跳过细节复修",
    "S14-关键状态使用正常加粗文本",
    "S15-选择框不用推荐且使用Codex和我",
    "S16-深度文档目标解锁开发目标",
    "S17-完整流程纪律不得覆盖轻量标准",
    "S18-深度页面允许用户自己测试",
    "S19-深度Stitch使用独立UI目标",
    "S20-完整非UI任务不依赖UI壳",
    "S21-事实证据不得靠幻觉补齐",
    "S22-升级到完整流程必须切回确认",
    "S23-局部样式与整页调整边界明确",
    "S24-完整流程最后目标按验收责任分支",
    "S25-深度UI只执行已触发QA",
    "S26-完整流程总结一次确认验收责任",
    "S27-顶层核心原则不得强制完整整理",
    "S28-其他入口不得强制多轮整理",
    "S29-原生选择框可用时必须实际调用",
    "S30-选择后同轮自动交付提示词",
    "S31-提示词使用单一完整代码块",
    "S32-深度两阶段职责不混用",
    "S33-Chrome无法操作时自动切换电脑",
    "S34-全权托管跳过确认与用户交接",
    "S35-明确用户自测覆盖托管默认",
    "S36-真实提示词交付前必须运行时校验",
    "S37-深度编码前必须审计真实产物与diff",
    "S38-上下文恢复不得无证据改变档位",
    "S39-立即生成提示词选项必须来自canonical builder",
    "S40-具体修改首轮创建任务文档",
    "S41-路径不明禁止乱放",
    "S42-活动文档只保留当前任务",
    "S43-归档失败保留活动内容",
    "S44-所有中间目标禁止归档",
    "S45-最后目标先交接再归档",
    "S46-取消暂停替代不得完成",
    "S47-统一任务ID隔离多活动任务",
    "S48-历史归档默认不扫描",
    "S49-建档后聊天默认增量回执",
    "S50-四档固定目标矩阵",
    "S51-UI目标只插入一次且可显式跳过",
    "S52-每个目标保留N/M与阶段合同",
    "S53-外部AI等待不新增目标",
    "S54-归档必须等待用户确认",
    "S55-选择框和文字回退均为纯文本",
    "S56-最后一次轻量目标不自动归档",
    "S57-最后一次标准目标不自动归档",
    "S58-深度非UI第二次目标不自动归档",
    "S59-深度UI第三次目标不自动归档",
    "S60-完整非UI第三次目标不自动归档",
    "S61-完整UI第四次目标不自动归档",
    "S62-最后目标结束后进入待用户检查",
    "S63-用户发现问题时禁止归档",
    "S64-用户提出新增需求时禁止归档",
    "S65-用户明确回复归档后才生成归档提示词",
    "S66-归档模板缺少用户确认时失败",
    "S67-归档失败保留活动区原文",
    "S68-归档成功后才允许已完成",
    "S69-普通完成通知和归档成功通知不能混用",
    "S70-历史项目补归档模板仍能独立运行",
    "S71-旧final或full-first兼容值不能绕过新确认",
    "S72-归档模板不计入普通四档目标数量",
    "S73-归档只能按任务ID清理",
    "S74-其他活动任务不能受到归档影响",
    "S75-需求整理中的已确认细节必须完整进入正式PRD",
    "S76-正式PRD不能只保留高层摘要",
    "S77-接口字段参数和阈值不能在转换时丢失",
    "S78-页面和UI细节不能在转换时丢失",
    "S79-状态异常和边界规则不能在转换时丢失",
    "S80-验收标准不能被压缩成一句功能正常",
    "S81-用户原话继续只保存在用户原话文件",
    "S82-项目事实继续保存在项目事实文档",
    "S83-项目索引继续由03-索引维护",
    "S84-开发测试真机UI和归档过程不能进入PRD",
    "S85-每条已确认需求必须有正式PRD去向",
    "S86-正式PRD必须建立REQ和AC关联文档追踪",
    "S87-待确认需求不能被伪装成正式需求",
    "S88-正式PRD转换审计发现遗漏时必须阻止确认",
    "S89-需求整理文档和正式PRD真实示例差异能够被检测",
    "S90-详细PRD转换和内容归位必须同时成立",
    "S91-最后普通目标完成后先reclaim_pending再reclaimed",
    "S92-回收失败不能伪造reclaimed",
    "S93-普通目标完成不等于项目已完成",
    "S94-用户检查不占用普通目标执行状态",
    "S95-用户发现问题不能重新打开原目标",
    "S96-archive目标不计入普通N/M",
    "S97-归档失败保持普通目标reclaimed",
    "S98-重复回收必须幂等",
    "S99-历史合同不能无证据迁移为reclaimed",
    "S100-archive目标自身完成后也要回收",
]

FULL_FLOW_CONFIRMATION_FILES = (
    "SKILL.md",
    "README.md",
    "docs/技能设计文档.md",
    "references/提示词向导.md",
    "references/模式-新项目引导.md",
    "references/模式-老项目初始化.md",
    "references/使用教程-常用提示词清单.md",
    "references/liran-plan-使用教程.html",
    "references/plan-docs-使用教程.html",
)

STATUS_MARKERS = (
    "**当前流程：",
    "**开始方式：",
    "**选择原因：",
    "**修改后评分：",
    "**流程已升级：",
    "**升级原因：",
    "**最终流程：",
)

Tier = Literal["轻量流程", "标准流程", "深度流程", "完整流程"]
ScoreBand = Literal["轻量流程", "标准流程", "深度流程", "完整流程候选"]
RuntimePromptTier = Literal["light", "standard", "deep", "full-docs"]
ArchiveStage = Literal["non-final", "handoff", "archive", "final", "full-first"]
GoalStage = Literal[
    "single", "documentation", "ui", "development",
    "development-and-acceptance", "acceptance",
]
TaskScope = Literal[
    "老项目单文件局部修改",
    "老项目单模块小功能",
    "老项目单模块完整改造",
    "老项目简单多模块改造",
    "老项目复杂多模块改造",
    "跨模块功能",
    "新UI壳或高保真还原",
    "新项目或项目级改造",
]

BASE_GOAL_SEQUENCES: dict[RuntimePromptTier, tuple[GoalStage, ...]] = {
    "light": ("single",),
    "standard": ("single",),
    "deep": ("documentation", "development-and-acceptance"),
    "full-docs": ("documentation", "development", "acceptance"),
}
GOAL_STAGES = tuple(dict.fromkeys(
    stage for sequence in BASE_GOAL_SEQUENCES.values() for stage in sequence
)) + ("ui",)
UI_ROUTE_CODES = (
    "not-applicable", "pending", "codex", "product-design", "external-ai", "stitch", "embedded-model",
)


def goal_sequence(
    tier: RuntimePromptTier,
    *,
    ui_goal_enabled: bool = False,
) -> tuple[GoalStage, ...]:
    """Return the only valid ordered goal stages for one routed task."""
    try:
        sequence = BASE_GOAL_SEQUENCES[tier]
    except KeyError as exc:
        raise ValueError(f"unknown runtime tier: {tier}") from exc
    if ui_goal_enabled and tier in {"deep", "full-docs"}:
        return (sequence[0], "ui", *sequence[1:])
    return sequence


def should_enable_ui_goal(
    tier: RuntimePromptTier,
    *,
    has_ui: bool,
    user_skips_ui: bool = False,
) -> bool:
    """Insert one UI goal only for deep/full UI work without an explicit skip."""
    return tier in {"deep", "full-docs"} and has_ui and not user_skips_ui

TASK_DOCUMENT_TRIGGER_WORDS = (
    "帮我修", "修复", "修改", "新增", "添加", "增加", "优化", "删除", "移除",
    "重构", "续作", "继续", "整理", "迁移", "部署", "发布",
)
TASK_DOCUMENT_READ_ONLY_WORDS = ("解释", "状态查询", "查询当前状态", "只读", "知识问答")
TASK_DOCUMENT_WRITE_FORBIDDEN_WORDS = (
    "不要修改任何文件", "不要写入任何文件", "不要写任何文件",
    "禁止写入任何文件", "仅给方案", "只给方案",
)
PLACEHOLDER_PATTERN = re.compile(r"<[^>]+>|(?i:\bTODO\b|\bTBD\b)|待填写|待补充")
TASK_DOCUMENT_REQUIRED_FIELDS = (
    "任务 ID", "任务名称", "任务类型", "创建日期", "更新日期", "流程档位", "当前状态",
    "首次用户原话", "已核实项目事实", "当前问题或现状", "期望结果", "已确认需求",
    "影响范围", "禁止修改范围", "验收标准", "待确认项", "决策记录", "下一步",
)

PRD_REQUIRED_SECTIONS = (
    "产品/功能概述",
    "背景与问题",
    "用户与使用场景",
    "产品目标",
    "非目标与明确不做",
    "当前项目事实",
    "用户流程",
    "功能需求",
    "数据、状态与业务规则",
    "页面与 UI 需求",
    "异常、边界与安全规则",
    "兼容性与限制",
    "影响范围",
    "验收标准",
    "需求追踪矩阵",
    "关联文档索引",
    "待确认项",
    "决策记录",
    "需求变更记录",
    "PRD 版本说明",
    "变更影响矩阵",
    "当前状态与下一步",
)
PRD_AUXILIARY_SECTIONS = ("0. 文档控制",)
PRD_REQUIREMENT_FIELDS = (
    "触发条件",
    "前置条件",
    "用户操作",
    "系统行为",
    "数据变化",
    "状态变化",
    "正常结果",
    "异常处理",
    "禁止行为",
    "对应 AC",
)
PRD_ACCEPTANCE_FIELDS = (
    "对应需求",
    "验收步骤",
    "预期结果",
    "失败条件",
)
PRD_FORBIDDEN_PROCESS_PATTERNS = (
    r"(?m)^\s*##\s+流程合同\s*$",
    r"(?m)^\s*##\s+档位执行门禁\s*$",
    r"(?m)^\s*##\s+(?:首次用户原话|已核实项目事实|Goal 完整提示词|微观任务(?:正文)?|开发流水|测试执行记录|真机执行记录|UI 接收过程|归档操作日志)\s*$",
    r"(?m)^\s*(?:目标阶段|当前目标|流程档位|目标提示词数量)\s*[：:]",
    r"(?m)^\s*(?:微观任务正文|开发流水|测试执行记录|真机执行记录|UI 接收过程|命令输出|审计日志|归档操作日志)\s*[：:]",
    r"(?m)^\s*(?:首次用户原话|已核实项目事实)\s*[：:]",
)
LIFECYCLE_SEQUENCE = (
    "需求整理文档",
    "正常聊天整理",
    "用户确认整理完成",
    "正式 PRD",
    "PRD 确认",
    "可选 UI 壳",
    "内部开发",
    "真机实测",
    "问题回写",
    "修复复测",
    "安全归档",
)
OPTION_STAGE_REQUIRED_PHRASES = (
    "需求整理好了吗？整理好了的话，请回复‘需求整理好了’",
    "正式 PRD 没问题吗？没问题的话，请回复‘PRD 没问题’",
    "正式 PRD 需要修改",
    "每个需要用户选择的节点都必须提供可操作选项",
    "request_user_input",
    "选项一：",
    "选项二：正式 PRD 需要修改",
    "选项一：$liran-plan Codex 真机测试",
    "选项二：$liran-plan 我自己测试",
    "两步原生选择",
    "五条 UI 路线",
    "Codex 真机测试",
    "我自己测试",
    "UI 路线",
)
ARCHIVE_SAFE_STEPS = (
    "长期事实已更新",
    "归档已创建",
    "归档内容已校验",
    "归档索引已更新",
    "活动区已按任务 ID 清理",
    "其他活动任务未受影响",
    "当前索引有效",
    "活动区无已完成残留",
)
ARCHIVE_STATES = (
    "未开始", "归档中", "已归档", "归档受阻", "已取消", "暂停归档", "被新任务替代"
)
GOAL_STATUSES = ("active", "reclaim_pending", "reclaimed")
ARCHIVE_GOAL_STAGES = ("archive", "final", "full-first")
ARCHIVE_ACCEPTANCE_OWNERS = ("Codex 真机测试", "用户自己测试", "我自己测试")
ARCHIVE_STATE_TRANSITIONS = {
    "待归档确认": ("归档中",),
    "归档中": ("已归档", "归档受阻"),
    "已归档": ("已完成",),
}
ARCHIVE_PROMPT_REQUIRED_PHRASES = (
    "用户已经明确回复“归档”",
    "归档确认原始消息：",
    "任务 ID：",
    "任务名称：",
    "正式 PRD：",
    "需求整理文档：",
    "归档目录：",
    "当前归档状态：",
    "归档确认时间：",
    "归档触发来源：",
    "最后一次普通目标已完成",
    "无待确认项",
    "无待实测",
    "无待用户验收",
    "无失败",
    "无受阻",
    "无未修复问题",
    "先更新长期事实",
    "创建单任务归档",
    "校验归档内容和证据路径",
    "更新归档索引",
    "按任务 ID 清理活动区",
    "其他活动任务未受影响",
    "当前索引有效",
    "活动区无本任务残留",
    "只有归档成功后才能标记已归档和已完成",
)
HANDOFF_PROMPT_REQUIRED_PHRASES = (
    "当前目标完成开发、测试、验收、问题回写和必要修复",
    "当前目标完成并已回收",
    "goal_status=reclaimed",
    "项目状态：待用户检查",
    "资料归档状态：待归档确认",
    "用户检查期间不再执行当前目标",
    "当前目标暂不执行正式归档",
    "不清理活动文档",
    "进入待用户检查和待归档确认",
    "用户发现问题",
    "新增需求或优化",
    "回到需求整理或需求变更流程",
    "只有用户明确回复“归档”后才调用正式归档模板",
    "归档失败不得重新打开普通目标",
)
HANDOFF_PROMPT_FORBIDDEN_PHRASES = (
    "自动创建归档",
    "自动更新归档索引",
    "自动清理活动区",
    "自动标记已归档",
    "自动标记已完成",
    "本次任务已完成并归档",
    "没有问题，自动归档",
)


def should_create_task_document(
    task: str,
    *,
    read_only: bool = False,
    writes_forbidden: bool = False,
) -> bool:
    """Return whether requirement gathering must start from a task Markdown file."""
    if read_only or writes_forbidden:
        return False
    normalized = re.sub(r"\s+", "", task).lower()
    if any(word in normalized for word in TASK_DOCUMENT_WRITE_FORBIDDEN_WORDS):
        return False
    if not any(word in normalized for word in TASK_DOCUMENT_TRIGGER_WORDS):
        return False
    if not any(word in normalized for word in TASK_DOCUMENT_READ_ONLY_WORDS):
        return True
    return bool(
        re.search(
            r"(?:再|然后|并|同时|接着).*(?:帮我修|修复|修改|新增|添加|增加|优化|删除|移除|重构|续作|继续|整理|迁移|部署|发布)",
            normalized,
        )
    )


def resolve_lifecycle_directory(
    *,
    user_path: str | Path | None = None,
    agents_path: str | Path | None = None,
    index_path: str | Path | None = None,
    existing_path: str | Path | None = None,
) -> Path | None:
    """Resolve a declared lifecycle directory without inventing a fallback."""
    for candidate in (user_path, agents_path, index_path, existing_path):
        if candidate is not None and str(candidate).strip():
            return Path(candidate)
    return None


def task_document_failures(text: str) -> list[str]:
    """Validate the minimum reusable Markdown requirement-document schema."""
    failures: list[str] = []
    values: dict[str, str] = {}
    for index, field_name in enumerate(TASK_DOCUMENT_REQUIRED_FIELDS):
        match = re.search(
            rf"(?m)^\s*(?:[-*]\s*)?{re.escape(field_name)}\s*[：:]\s*(.+?)\s*$",
            text,
        )
        value = match.group(1).strip() if match is not None else ""
        if not value and index >= 7:
            section = re.search(
                rf"(?ms)^##\s+{re.escape(field_name)}\s*$\n(.*?)(?=^##\s+|\Z)",
                text,
            )
            value = section.group(1).strip() if section is not None else ""
        values[field_name] = value
        if not value:
            failures.append(f"任务需求工作文档缺少有效字段：{field_name}")
        elif PLACEHOLDER_PATTERN.search(value):
            failures.append(f"任务需求工作文档字段含未替换占位：{field_name}")
    if values.get("任务 ID") in {"待定", "待确认", "无"} or PLACEHOLDER_PATTERN.search(
        values.get("任务 ID", "")
    ):
        failures.append("任务需求工作文档必须使用稳定任务 ID。")
    return failures


def requirements_gathering_document_failures(text: str) -> list[str]:
    """Validate the lightweight chat-style requirement-gathering document."""
    failures: list[str] = []
    if "需求整理" not in text or "不是正式 PRD" not in text:
        failures.append("需求整理文档必须明确声明其文档类型。")
    task_id = document_task_id(text)
    if not task_id or PLACEHOLDER_PATTERN.search(task_id):
        failures.append("需求整理文档必须使用稳定任务 ID。")
    if re.search(r"(?m)^\s*(?:当前状态|需求状态)\s*[：:]\s*(?:正式 PRD|已确认|已归档)", text):
        failures.append("需求整理文档不能提前标记正式 PRD 已确认或已归档。")
    if re.search(r"(?m)^##\s+(?:流程合同|档位执行门禁|Goal|开发流水|测试执行记录|真机执行记录|UI 接收过程|归档操作日志)\s*$", text):
        failures.append("需求整理文档不得混入执行阶段流水或 Goal 合同。")
    if not any(section in text for section in ("用户想解决的问题", "目前讨论内容", "已确认的内容", "还没有确认的内容")):
        failures.append("需求整理文档至少需要问题、讨论、确认或待确认内容。")
    return failures


def document_task_id(text: str) -> str:
    """Return the exact Markdown task ID field, not an arbitrary substring hit."""
    match = re.search(r"(?m)^\s*(?:[-*]\s*)?任务 ID\s*[：:]\s*(\S+)\s*$", text)
    return match.group(1) if match is not None else ""


def prd_document_failures(
    text: str,
    *,
    expected_status: Literal["draft", "formal"] | None = None,
) -> list[str]:
    """Validate the PRD fact source without accepting execution-process content."""
    failures: list[str] = []
    def section_body(number: int, name: str) -> str:
        match = re.search(
            rf"(?ms)^##\s+{number}\.\s+{re.escape(name)}\s*$\n(.*?)(?=^##\s+\d+\.\s+|\Z)",
            text,
        )
        return match.group(1) if match else ""
    headings: list[tuple[str, int]] = []
    for index, section in enumerate(PRD_REQUIRED_SECTIONS, start=1):
        matches = list(
            re.finditer(
                rf"(?m)^##\s+{index}\.\s+{re.escape(section)}\s*$",
                text,
            )
        )
        if not matches:
            failures.append(f"PRD 缺少固定章节：{section}")
        elif len(matches) > 1:
            failures.append(f"PRD 固定章节重复：{section}")
        else:
            headings.append((section, matches[0].start()))
    allowed_level2 = {
        *PRD_AUXILIARY_SECTIONS,
        *(f"{index}. {section}" for index, section in enumerate(PRD_REQUIRED_SECTIONS, start=1)),
    }
    for heading in re.findall(r"(?m)^##\s+(.+?)\s*$", text):
        if heading.strip() not in allowed_level2:
            failures.append(f"PRD 出现固定结构之外的二级章节：{heading.strip()}")
    if len(headings) == len(PRD_REQUIRED_SECTIONS):
        actual = [section for section, _ in sorted(headings, key=lambda item: item[1])]
        if actual != list(PRD_REQUIRED_SECTIONS):
            failures.append("PRD 固定章节顺序错误。")

    title = text.splitlines()[0].strip() if text.splitlines() else ""
    if not title.endswith("· PRD"):
        failures.append("PRD 首行必须使用“<任务名称> · PRD”标题。")

    control = section_body(0, "文档控制")
    for field_name in ("任务 ID", "文档状态", "需求状态", "PRD 版本"):
        match = re.search(rf"(?m)^\s*{re.escape(field_name)}\s*[：:]\s*(\S.+?)\s*$", control)
        if match is None or PLACEHOLDER_PATTERN.search(match.group(1)):
            failures.append(f"PRD 文档控制缺少有效字段：{field_name}")
    status_match = re.search(r"(?m)^\s*文档状态\s*[：:]\s*(\S.+?)\s*$", control)
    requirement_status_match = re.search(r"(?m)^\s*需求状态\s*[：:]\s*(\S.+?)\s*$", control)
    if expected_status == "draft":
        if status_match is None or status_match.group(1).strip() != "PRD 草稿":
            failures.append("PRD 草稿的文档状态必须是“PRD 草稿”。")
        if requirement_status_match is None or requirement_status_match.group(1).strip() != "需求整理中":
            failures.append("PRD 草稿的需求状态必须是“需求整理中”。")
    elif expected_status == "formal":
        if status_match is None or status_match.group(1).strip() != "正式 PRD":
            failures.append("正式 PRD 的文档状态必须是“正式 PRD”。")
        if requirement_status_match is None or requirement_status_match.group(1).strip() != "已确认":
            failures.append("正式 PRD 的需求状态必须是“已确认”。")
        pending = section_body(17, "待确认项").strip()
        if not pending or pending not in {"无", "无。", "- 无", "- 无。"} or re.search(r"待确认|<[^>]+>", pending):
            failures.append("正式 PRD 转换前必须清空待确认项并写明“无”。")

    for pattern in PRD_FORBIDDEN_PROCESS_PATTERNS:
        match = re.search(pattern, text)
        if match is not None:
            failures.append(f"PRD 混入执行过程内容：{match.group(0).strip()}")

    requirement_ids = sorted(set(re.findall(r"(?m)^\s*(?:#{1,6}\s*)?(REQ-\d+)(?:\s+v\d+(?:\.\d+)?)?\b", text)))
    acceptance_ids = sorted(set(re.findall(r"(?m)^\s*(?:#{1,6}\s*)?(AC-\d+)\b", text)))
    if not requirement_ids:
        failures.append("PRD 至少需要一条 REQ-* 需求。")
    if not acceptance_ids:
        failures.append("PRD 至少需要一条 AC-* 验收标准。")

    for requirement_id in requirement_ids:
        block_match = re.search(
            rf"(?ms)^\s*(?:#{{1,6}}\s*)?{re.escape(requirement_id)}(?:\s+v\d+(?:\.\d+)?)?\b.*?(?=^\s*(?:#{{1,6}}\s*)?REQ-\d+(?:\s+v\d+(?:\.\d+)?)?\b|^\s*(?:#{{1,6}}\s*)?AC-\d+\b|\Z)",
            text,
        )
        block = block_match.group(0) if block_match else ""
        for field_name in PRD_REQUIREMENT_FIELDS:
            if not re.search(rf"(?m)^\s*{re.escape(field_name)}\s*[：:]\s*\S+", block):
                failures.append(f"{requirement_id} 缺少字段：{field_name}")
        mapped = re.findall(r"AC-\d+", re.search(r"(?m)^\s*对应 AC\s*[：:]\s*(.+)$", block).group(1) if re.search(r"(?m)^\s*对应 AC\s*[：:]\s*(.+)$", block) else "")
        if not mapped:
            failures.append(f"{requirement_id} 缺少有效的 AC-* 映射。")
        elif any(item not in acceptance_ids for item in mapped):
            failures.append(f"{requirement_id} 映射了不存在的 AC-*：{mapped[0]}")

    for acceptance_id in acceptance_ids:
        block_match = re.search(
            rf"(?ms)^\s*(?:#{{1,6}}\s*)?{re.escape(acceptance_id)}\b.*?(?=^\s*(?:#{{1,6}}\s*)?REQ-\d+(?:\s+v\d+(?:\.\d+)?)?\b|^\s*(?:#{{1,6}}\s*)?AC-\d+\b|\Z)",
            text,
        )
        block = block_match.group(0) if block_match else ""
        for field_name in PRD_ACCEPTANCE_FIELDS:
            if not re.search(rf"(?m)^\s*{re.escape(field_name)}\s*[：:]\s*\S+", block):
                failures.append(f"{acceptance_id} 缺少字段：{field_name}")
        mapped = re.findall(r"REQ-\d+", re.search(r"(?m)^\s*对应需求\s*[：:]\s*(.+)$", block).group(1) if re.search(r"(?m)^\s*对应需求\s*[：:]\s*(.+)$", block) else "")
        if not mapped:
            failures.append(f"{acceptance_id} 缺少有效的 REQ-* 映射。")
        elif any(item not in requirement_ids for item in mapped):
            failures.append(f"{acceptance_id} 映射了不存在的 REQ-*：{mapped[0]}")

    index_section = section_body(16, "关联文档索引")
    if not index_section or not all(field in index_section for field in ("文件类型", "文件路径", "文件作用", "当前状态", "关联需求")):
        failures.append("PRD 的关联文档索引必须只记录文件类型、路径、作用、状态和需求关联。")

    change_ids = sorted(set(re.findall(r"\bCHG-\d+\b", text)))
    if change_ids:
        change_section = section_body(19, "需求变更记录")
        impact_section = section_body(21, "变更影响矩阵")
        for field_name in ("变更编号", "用户原话", "原需求", "新需求", "影响", "等级", "状态"):
            if field_name not in change_section:
                failures.append(f"需求变更记录缺少字段：{field_name}")
        if "CHG-" not in impact_section or not all(
            field_name in impact_section
            for field_name in ("REQ", "AC", "页面/UI", "模块/微观任务", "04", "08", "09", "Goal")
        ):
            failures.append("存在 CHG 需求变更时必须提供完整变更影响矩阵。")
    return failures


def prd_conversion_failures(
    text: str,
    *,
    source_text: str | None = None,
    source_path: Path | None = None,
    score_text: str | None = None,
    score_path: Path | None = None,
    require_score: bool = False,
) -> list[str]:
    """Validate formal status and, when supplied, confirmed-source detail coverage."""
    failures = prd_document_failures(text, expected_status="formal")
    if source_path is not None:
        if not source_path.is_file():
            failures.append(f"需求整理来源文件不存在：{source_path}")
        else:
            source_text = source_path.read_text(encoding="utf-8", errors="replace")
    if source_text is None:
        return failures
    if score_path is not None:
        if not score_path.is_file():
            failures.append(f"正式 PRD 评分记录文件不存在：{score_path}")
        else:
            score_text = score_path.read_text(encoding="utf-8", errors="replace")
    if require_score and score_text is None:
        failures.append("正式 PRD 转换完成后必须提供评分记录和流程等级。")
    if score_text is not None:
        failures.extend(score_record_failures(score_text))
    confirmed = re.search(
        r"(?ms)^##\s+(?:已确认的内容|已确认需求|功能需求)(?:\s*.*)?$\n(.*?)(?=^##\s+|\Z)",
        source_text,
    )
    confirmed_text = confirmed.group(1) if confirmed else source_text
    detail_patterns = (
        (r"(?:接口路径|URL|路径)\s*[：:]\s*([^\n]+)", "接口路径"),
        (r"(?:请求方法|HTTP 方法)\s*[：:]\s*([^\n]+)", "请求方法"),
        (r"(?:字段名|字段)\s*[：:]\s*([^\n]+)", "字段名"),
        (r"(?:阈值|时间窗|超时)\s*[：:]\s*([^\n]+)", "阈值"),
        (r"(?:页面规则|布局|尺寸|间距|栅格)\s*[：:]\s*([^\n]+)", "页面规则"),
        (r"(?:异常处理|边界处理|空态|权限失败)\s*[：:]\s*([^\n]+)", "异常处理"),
    )
    for pattern, label in detail_patterns:
        values = [item.strip() for item in re.findall(pattern, confirmed_text)]
        for value in values:
            if value and value not in text:
                failures.append(f"正式 PRD 缺少来源需求细节：{label}={value}")
    source_ids = set(re.findall(r"\bREQ-[A-Za-z0-9-]+\b", confirmed_text))
    if source_ids:
        prd_ids = set(re.findall(r"\bREQ-[A-Za-z0-9-]+\b", text))
        missing_ids = sorted(source_ids - prd_ids)
        if missing_ids:
            failures.append("正式 PRD 缺少来源已确认需求编号：" + "、".join(missing_ids))
    if re.search(r"(?m)^##\s+(?:首次用户原话|已核实项目事实|开发流水|测试执行记录|真机执行记录|UI 接收过程)\s*$", text):
        failures.append("正式 PRD 不能复制用户原话、项目事实或执行流水章节。")
    return failures


def score_record_failures(text: str) -> list[str]:
    """Validate the post-formal-PRD five-dimension score and routed tier."""
    failures: list[str] = []
    required = (
        "任务 ID", "项目现状", "修改规模", "依赖与修改后影响",
        "风险与回滚", "验证复杂度", "总分", "流程等级", "评分证据",
        "范围上限", "安全门禁", "项目级完整条件",
    )
    for field in required:
        if field not in text:
            failures.append(f"评分记录缺少字段：{field}")
    dimensions = ("项目现状", "修改规模", "依赖与修改后影响", "风险与回滚", "验证复杂度")
    values: list[int] = []
    for dimension in dimensions:
        match = re.search(
            rf"(?m)^\s*{re.escape(dimension)}\s*[：:]\s*(\d{{1,2}})\b",
            text,
        )
        if match is None:
            failures.append(f"评分记录缺少 {dimension} 的 0–20 分数。")
            continue
        value = int(match.group(1))
        values.append(value)
        if not 0 <= value <= 20:
            failures.append(f"评分记录的 {dimension} 必须在 0–20 分范围内。")
    total_match = re.search(
        r"(?m)^\s*总分\s*[：:]\s*(\d{1,3})\s*(?:/\s*100)?",
        text,
    )
    if total_match is None:
        failures.append("评分记录缺少 0–100 总分。")
    else:
        total = int(total_match.group(1))
        if not 0 <= total <= 100:
            failures.append("评分记录总分必须在 0–100 范围内。")
        elif len(values) == 5 and total != sum(values):
            failures.append("评分记录总分必须等于五个维度分数之和。")
        band_match = re.search(r"(?m)^\s*(?:评分分段|评分区间)\s*[：:]\s*(.+)$", text)
        if band_match is not None and score_band(total) not in band_match.group(1):
            failures.append("评分记录的评分分段与总分不一致。")
    return failures


def lifecycle_sequence_failures(text: str) -> list[str]:
    """Ensure the canonical requirement-to-archive lifecycle is stated once and in order."""
    failures: list[str] = []
    canonical = " → ".join(LIFECYCLE_SEQUENCE)
    if canonical in text:
        return failures
    positions: list[int] = []
    for step in LIFECYCLE_SEQUENCE:
        position = text.find(step)
        if position < 0:
            failures.append(f"闭环流程缺少步骤：{step}")
        positions.append(position)
    present = [position for position in positions if position >= 0]
    if len(present) == len(LIFECYCLE_SEQUENCE) and present != sorted(present):
        failures.append("闭环流程步骤顺序错误，必须从需求整理依次走到安全归档。")
    return failures


def option_stage_failures(text: str) -> list[str]:
    """Ensure every required confirmation point declares a usable choice path."""
    return [
        f"选项门禁缺少节点或选项规则：{phrase}"
        for phrase in OPTION_STAGE_REQUIRED_PHRASES
        if phrase not in text
    ]


def archive_lifecycle_failures(
    payload: dict[str, Any],
    *,
    root: Path = ROOT,
) -> list[str]:
    """Validate a single-task archive snapshot before active content is cleaned."""
    failures: list[str] = []
    scan_archive_raw = payload.get("scan_archive", False)
    if not isinstance(scan_archive_raw, bool):
        failures.append("scan_archive 必须是布尔值。")
    if scan_archive_raw is True:
        reason = str(payload.get("archive_scan_reason", ""))
        if not any(word in reason for word in ("回归", "追溯", "版本", "用户要求")):
            failures.append("历史归档默认不参与新任务扫描；读取时必须记录回归、追溯、版本调查或用户要求。")

    lifecycle_keys = set(payload) - {"scan_archive", "archive_scan_reason"}
    if not lifecycle_keys:
        return failures

    task_id = str(payload.get("task_id", "")).strip()
    if not task_id:
        failures.append("归档合同缺少任务 ID。")
    artifact_ids = payload.get("artifact_task_ids", [])
    if (
        not isinstance(artifact_ids, list)
        or not artifact_ids
        or any(str(item).strip() != task_id for item in artifact_ids)
    ):
        failures.append("需求、追踪、测试、真机、UI 与归档必须使用同一个任务 ID。")

    goal_stage = str(payload.get("goal_stage", ""))
    archive_state = str(payload.get("archive_state", ""))
    final_state = str(payload.get("final_state", ""))
    source_state = str(payload.get("source_state", ""))
    acceptance_owner = str(payload.get("acceptance_owner", ""))
    source_goal_status = str(payload.get("source_goal_status", ""))
    if goal_stage not in ARCHIVE_GOAL_STAGES:
        failures.append("归档合同的目标阶段必须是 archive（正式归档）或兼容的 final/full-first。")
    if acceptance_owner not in ARCHIVE_ACCEPTANCE_OWNERS:
        failures.append("归档合同必须使用已确认的验收责任。")
    if archive_state not in ARCHIVE_STATES:
        failures.append("归档合同包含未知归档状态。")
    confirmation = payload.get("user_archive_confirmation")
    if confirmation is not True:
        failures.append("启动正式归档前必须有用户明确回复“归档”的确认。")
    confirmation_evidence = str(payload.get("archive_confirmation_evidence", "")).strip()
    if not confirmation_evidence:
        failures.append("归档合同必须记录用户归档确认的真实消息或证据路径。")
    steps = payload.get("steps", [])
    if not isinstance(steps, list):
        steps = []
        failures.append("归档步骤必须是有序数组。")
    cleanup_raw = payload.get("cleanup_performed", False)
    if not isinstance(cleanup_raw, bool):
        failures.append("cleanup_performed 必须是布尔值。")
    cleanup_performed = cleanup_raw is True
    for field_name in (
        "other_active_tasks_preserved", "current_index_valid", "completed_residue_absent"
    ):
        if field_name in payload and not isinstance(payload[field_name], bool):
            failures.append(f"{field_name} 必须是布尔值。")

    if goal_stage == "full-first" and (
        steps or cleanup_performed or archive_state not in {"", "未开始"}
    ):
        failures.append("完整流程第一次目标禁止归档；只能在第二次最终目标收口。")

    if goal_stage == "archive" and archive_state == "归档中" and source_state == "待归档确认":
        if not confirmation:
            failures.append("待归档确认进入归档中前必须先记录用户明确归档确认。")
    if goal_stage == "archive" and source_goal_status != "reclaimed":
        failures.append("独立 archive 目标启动前，原普通目标必须已经 reclaimed。")
    if payload.get("archive_goal_counted") is True:
        failures.append("archive 目标不得计入普通目标数量。")
    if "source_goal_index" in payload or "source_goal_count" in payload:
        source_index = payload.get("source_goal_index")
        source_count = payload.get("source_goal_count")
        if type(source_index) is not int or type(source_count) is not int or source_index != source_count:
            failures.append("独立 archive 目标只能对应已经完成的普通目标 M/M。")

    closed_without_completion = {"已取消", "暂停归档", "被新任务替代"}
    if archive_state in closed_without_completion and final_state == "已完成":
        failures.append(f"{archive_state} 只能保存关闭事实，不得标记为已完成。")

    if final_state == "已完成":
        expected_source = (
            "用户验收通过"
            if acceptance_owner in {"用户自己测试", "我自己测试"}
            else "真机测试通过"
        )
        if source_state != expected_source:
            failures.append(f"归档完成前必须有明确验收通过状态：{expected_source}。")
        if archive_state != "已归档":
            failures.append("只有归档状态为已归档时才能进入已完成。")
        if "archive_goal_status" in payload and payload.get("archive_goal_status") != "reclaimed":
            failures.append("正式归档成功后，archive 目标自身也必须 reclaimed。")

    unresolved = payload.get("unresolved_states", [])
    if unresolved and archive_state == "已归档":
        failures.append("存在未解决、待确认、待实测、待验收、失败或受阻状态时不得完成归档。")
    if unresolved and cleanup_performed:
        failures.append("存在未解决、待确认、待实测、待验收、失败或受阻状态时禁止清理活动区。")

    positions = [steps.index(step) for step in ARCHIVE_SAFE_STEPS if step in steps]
    if positions != sorted(positions):
        failures.append("归档步骤顺序错误：必须先更新长期事实和验证归档，再清理活动区。")
    prerequisites = ARCHIVE_SAFE_STEPS[:4]
    if cleanup_performed and (
        any(step not in steps for step in prerequisites)
        or "活动区已按任务 ID 清理" not in steps
    ):
        failures.append("清理活动区前必须先创建并验证归档、再更新归档索引。")
    if archive_state == "归档受阻" and cleanup_performed:
        failures.append("归档受阻时必须保留活动内容，禁止继续清理。")
    cleanup_step_present = "活动区已按任务 ID 清理" in steps
    if cleanup_step_present != cleanup_performed:
        failures.append("归档步骤与清理状态矛盾：活动区清理记录必须与实际清理结果一致。")
    if cleanup_performed:
        before_ids = payload.get("active_task_ids_before")
        after_ids = payload.get("active_task_ids_after")
        if not isinstance(before_ids, list) or not isinstance(after_ids, list):
            failures.append("清理活动区必须提供归档前后的活动任务 ID 列表。")
        else:
            expected_after = sorted(
                str(item) for item in before_ids if str(item) != task_id
            )
            if sorted(str(item) for item in after_ids) != expected_after:
                failures.append("归档前后的活动任务 ID 不一致；只能移除当前任务，其他活动任务必须保留。")

    if final_state == "已完成":
        missing_steps = [step for step in ARCHIVE_SAFE_STEPS if step not in steps]
        if missing_steps:
            failures.append("完成归档前缺少安全步骤：" + "、".join(missing_steps))
        if payload.get("other_active_tasks_preserved") is not True:
            failures.append("归档后必须证明其他活动任务未受影响。")
        if payload.get("current_index_valid") is not True:
            failures.append("归档后必须证明当前索引仍然有效。")
        if payload.get("completed_residue_absent") is not True:
            failures.append("归档后活动文件仍有本任务已完成残留。")
        if not cleanup_performed:
            failures.append("活动区尚未按任务 ID 清理，不能声明已完成。")

    if cleanup_performed or archive_state in closed_without_completion | {"已归档"} or final_state == "已完成":
        requirements_raw = payload.get("requirements_path")
        requirements_path = Path(str(requirements_raw or ""))
        if not requirements_path.is_absolute():
            requirements_path = root / requirements_path
        if not requirements_raw or not requirements_path.is_file():
            failures.append(f"需求工作文档路径不是有效文件，不能声明已归档：{requirements_path}")
        else:
            requirements_text = requirements_path.read_text(encoding="utf-8", errors="replace")
            if document_task_id(requirements_text) != task_id:
                failures.append("需求工作文档正文没有精确声明当前任务 ID。")
            document_failures = task_document_failures(requirements_text)
            if document_failures:
                failures.append("需求工作文档结构无效：" + document_failures[0])

        archive_raw = payload.get("archive_path")
        archive_path = Path(str(archive_raw or ""))
        if not archive_path.is_absolute():
            archive_path = root / archive_path
        archive_texts: list[str] = []
        if archive_path.is_file():
            archive_texts.append(archive_path.read_text(encoding="utf-8", errors="replace"))
        elif archive_path.is_dir():
            archive_texts.extend(
                path.read_text(encoding="utf-8", errors="replace")
                for path in archive_path.rglob("*.md")
                if path.is_file()
            )
        else:
            failures.append(f"归档路径不存在，不能声明已归档：{archive_path}")
        if archive_path.exists() and not any(
            document_task_id(text) == task_id
            and "任务归档" in text
            and re.search(r"(?m)^\s*(?:[-*]\s*)?归档状态\s*[：:]\s*\S+", text)
            for text in archive_texts
        ):
            failures.append("归档正文必须精确声明当前任务 ID、任务归档标识和归档状态。")
    return failures

PROMPT_MIN_CHARS = 0
PROMPT_MAX_CHARS = 10000
# Backward-compatible names retained for callers; every complete prompt uses the same range.
EXECUTABLE_PROMPT_MIN_CHARS = PROMPT_MIN_CHARS
EXECUTABLE_PROMPT_MAX_CHARS = PROMPT_MAX_CHARS
LONG_PROMPT_MIN_CHARS = 0
LONG_PROMPT_MAX_CHARS = PROMPT_MAX_CHARS
PROMPT_KINDS = (
    "workflow",
    "long",
    "archive",
    "stitch-instance-repair",
    "stitch-generation",
    "external-ai-ui",
    "product-design",
    "image-generation",
    "special-prompt",
)
EXECUTABLE_PROMPT_REQUIRED_SECTIONS = (
    "任务性质",
    "当前场景",
    "目标和完成结果",
    "读取要求",
    "修改范围",
    "执行步骤",
    "业务与安全边界",
    "UI 专项要求",
    "验证要求",
    "完成后输出",
    "收口条件",
)
EXECUTABLE_PROMPT_FORBIDDEN_SHORTCUTS = (
    "详见文档",
    "详见模板",
    "按之前规则执行",
    "其他要求不变",
)

RUNTIME_TIER_LABELS: dict[RuntimePromptTier, str] = {
    "light": "轻量流程",
    "standard": "标准流程",
    "deep": "深度流程",
    "full-docs": "完整流程",
}


@dataclass(frozen=True)
class FlowContract:
    """Serializable state carried by a generated goal across context compression."""

    tier: RuntimePromptTier
    pre_score: int
    goal_count: int
    acceptance_owner: str
    visual_qa: str
    phase: str
    base_goal_count: int = 0
    goal_index: int = 0
    goal_stage: str = ""
    ui_goal_enabled: bool = False
    ui_route: str = "not-applicable"
    awaiting_external_input: bool = False
    unlocked_gates: tuple[str, ...] = field(default_factory=tuple)
    upgrade_evidence: tuple[str, ...] = field(default_factory=tuple)
    task_type: str = "待确认"
    state: str = ""
    entry_evidence: tuple[str, ...] = field(default_factory=tuple)
    completed_gates: tuple[str, ...] = field(default_factory=tuple)
    pending_gates: tuple[str, ...] = field(default_factory=tuple)
    allowed_next_actions: tuple[str, ...] = field(default_factory=tuple)
    forbidden_actions: tuple[str, ...] = field(default_factory=tuple)
    summary_output: bool = False
    summary_confirmed: bool = False
    acceptance_confirmed: bool = False
    prompt_status: str = "未生成"
    artifact_audit: bool = False
    block_reason: str = ""
    task_id: str = ""
    requirements_path: str = ""
    archive_path: str = ""
    archive_state: str = "未开始"
    user_archive_confirmation: bool = False
    archive_confirmation_evidence: str = ""
    archive_confirmation_at: str = ""
    archive_trigger_source: str = ""
    goal_status: str = "active"
    goal_completion_evidence: tuple[str, ...] = field(default_factory=tuple)
    goal_reclaimed_at: str = ""
    task_state_after_goal: str = ""
    archive_state_after_goal: str = ""
    user_check_notification_sent: bool = False
    user_check_notification_evidence: str = ""

    def __post_init__(self) -> None:
        if self.tier not in RUNTIME_PROMPT_SEQUENCES:
            raise ValueError(f"unknown runtime tier: {self.tier}")
        if not 0 <= self.pre_score <= 100:
            raise ValueError("pre_score must be in the range 0..100")
        if self.goal_count < 1:
            raise ValueError("goal_count must be positive")
        if type(self.base_goal_count) is not int or self.base_goal_count < 0:
            raise ValueError("base_goal_count must be a non-negative integer")
        if type(self.goal_index) is not int or self.goal_index < 0:
            raise ValueError("goal_index must be a non-negative integer")
        if self.goal_stage and self.goal_stage not in GOAL_STAGES:
            raise ValueError(f"unknown goal stage: {self.goal_stage}")
        if self.ui_route not in UI_ROUTE_CODES:
            raise ValueError(f"unknown UI route: {self.ui_route}")
        for name in (
            "ui_goal_enabled", "awaiting_external_input", "summary_output",
            "summary_confirmed", "acceptance_confirmed", "artifact_audit",
            "user_archive_confirmation",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be a boolean")
        for name, value in (("acceptance_owner", self.acceptance_owner), ("visual_qa", self.visual_qa), ("phase", self.phase)):
            if not str(value).strip():
                raise ValueError(f"{name} must not be empty")
        if not self.state:
            object.__setattr__(self, "state", self.phase)
        if not str(self.state).strip() or not str(self.prompt_status).strip():
            raise ValueError("state and prompt_status must not be empty")
        if self.state == "受阻" and not str(self.block_reason).strip():
            raise ValueError("block_reason must not be empty when state is 受阻")
        if self.archive_state not in ARCHIVE_STATES:
            raise ValueError(f"unknown archive state: {self.archive_state}")
        if self.goal_status not in GOAL_STATUSES:
            raise ValueError(f"unknown goal status: {self.goal_status}")
        if type(self.user_check_notification_sent) is not bool:
            raise ValueError("user_check_notification_sent must be a boolean")

    def to_dict(self) -> dict[str, Any]:
        return {
            "tier": self.tier,
            "pre_score": self.pre_score,
            "goal_count": self.goal_count,
            "base_goal_count": self.base_goal_count,
            "goal_index": self.goal_index,
            "goal_stage": self.goal_stage,
            "ui_goal_enabled": self.ui_goal_enabled,
            "ui_route": self.ui_route,
            "awaiting_external_input": self.awaiting_external_input,
            "acceptance_owner": self.acceptance_owner,
            "visual_qa": self.visual_qa,
            "phase": self.phase,
            "unlocked_gates": list(self.unlocked_gates),
            "upgrade_evidence": list(self.upgrade_evidence),
            "task_type": self.task_type,
            "state": self.state,
            "entry_evidence": list(self.entry_evidence),
            "completed_gates": list(self.completed_gates),
            "pending_gates": list(self.pending_gates),
            "allowed_next_actions": list(self.allowed_next_actions),
            "forbidden_actions": list(self.forbidden_actions),
            "summary_output": self.summary_output,
            "summary_confirmed": self.summary_confirmed,
            "acceptance_confirmed": self.acceptance_confirmed,
            "prompt_status": self.prompt_status,
            "artifact_audit": self.artifact_audit,
            "block_reason": self.block_reason,
            "task_id": self.task_id,
            "requirements_path": self.requirements_path,
            "archive_path": self.archive_path,
            "archive_state": self.archive_state,
            "user_archive_confirmation": self.user_archive_confirmation,
            "archive_confirmation_evidence": self.archive_confirmation_evidence,
            "archive_confirmation_at": self.archive_confirmation_at,
            "archive_trigger_source": self.archive_trigger_source,
            "goal_status": self.goal_status,
            "goal_completion_evidence": list(self.goal_completion_evidence),
            "goal_reclaimed_at": self.goal_reclaimed_at,
            "task_state_after_goal": self.task_state_after_goal,
            "archive_state_after_goal": self.archive_state_after_goal,
            "user_check_notification_sent": self.user_check_notification_sent,
            "user_check_notification_evidence": self.user_check_notification_evidence,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FlowContract":
        state = str(data.get("state", data["phase"]))
        block_reason = str(data.get("block_reason", ""))
        if state == "受阻" and not block_reason.strip():
            block_reason = "历史合同迁移：阻塞原因待补充"
        for name in ("base_goal_count", "goal_index"):
            if name in data and type(data[name]) is not int:
                raise ValueError(f"{name} must be an integer")
        for name in (
            "ui_goal_enabled", "awaiting_external_input", "summary_output",
            "summary_confirmed", "acceptance_confirmed", "artifact_audit",
            "user_archive_confirmation", "user_check_notification_sent",
        ):
            if name in data and type(data[name]) is not bool:
                raise ValueError(f"{name} must be a boolean")
        goal_status = data.get("goal_status", "active")
        if "goal_status" not in data and state in {"待用户检查", "待归档确认"}:
            evidence = tuple(str(item) for item in data.get("goal_completion_evidence", []))
            if (
                evidence
                and str(data.get("task_state_after_goal", "")) == "待用户检查"
                and str(data.get("archive_state_after_goal", "")) == "待归档确认"
            ):
                goal_status = "reclaimed"
        return cls(
            tier=data["tier"],
            pre_score=int(data["pre_score"]),
            goal_count=int(data["goal_count"]),
            acceptance_owner=str(data["acceptance_owner"]),
            visual_qa=str(data["visual_qa"]),
            phase=str(data["phase"]),
            base_goal_count=data.get("base_goal_count", 0),
            goal_index=data.get("goal_index", 0),
            goal_stage=str(data.get("goal_stage", "")),
            ui_goal_enabled=data.get("ui_goal_enabled", False),
            ui_route=str(data.get("ui_route", "not-applicable")),
            awaiting_external_input=data.get("awaiting_external_input", False),
            unlocked_gates=tuple(str(item) for item in data.get("unlocked_gates", [])),
            upgrade_evidence=tuple(str(item) for item in data.get("upgrade_evidence", [])),
            task_type=str(data.get("task_type", "待确认")),
            state=state,
            entry_evidence=tuple(str(item) for item in data.get("entry_evidence", [])),
            completed_gates=tuple(str(item) for item in data.get("completed_gates", [])),
            pending_gates=tuple(str(item) for item in data.get("pending_gates", [])),
            allowed_next_actions=tuple(str(item) for item in data.get("allowed_next_actions", [])),
            forbidden_actions=tuple(str(item) for item in data.get("forbidden_actions", [])),
            summary_output=bool(data.get("summary_output", False)),
            summary_confirmed=bool(data.get("summary_confirmed", False)),
            acceptance_confirmed=bool(data.get("acceptance_confirmed", False)),
            prompt_status=str(data.get("prompt_status", "未生成")),
            artifact_audit=bool(data.get("artifact_audit", False)),
            block_reason=block_reason,
            task_id=str(data.get("task_id", "")),
            requirements_path=str(data.get("requirements_path", "")),
            archive_path=str(data.get("archive_path", "")),
            archive_state=str(data.get("archive_state", "未开始")),
            user_archive_confirmation=data.get("user_archive_confirmation", False),
            archive_confirmation_evidence=str(data.get("archive_confirmation_evidence", "")),
            archive_confirmation_at=str(data.get("archive_confirmation_at", "")),
            archive_trigger_source=str(data.get("archive_trigger_source", "")),
            goal_status=str(goal_status),
            goal_completion_evidence=tuple(str(item) for item in data.get("goal_completion_evidence", [])),
            goal_reclaimed_at=str(data.get("goal_reclaimed_at", "")),
            task_state_after_goal=str(data.get("task_state_after_goal", "")),
            archive_state_after_goal=str(data.get("archive_state_after_goal", "")),
            user_check_notification_sent=data.get("user_check_notification_sent", False),
            user_check_notification_evidence=str(data.get("user_check_notification_evidence", "")),
        )

    @classmethod
    def from_json(cls, value: str) -> "FlowContract":
        loaded = json.loads(value)
        if not isinstance(loaded, dict):
            raise ValueError("flow contract JSON must contain an object")
        return cls.from_dict(loaded)


def multi_goal_contract_failures(contract: FlowContract) -> list[str]:
    """Validate persisted goal count, position, stage, and external-wait state."""
    if not any((contract.base_goal_count, contract.goal_index, contract.goal_stage)):
        return []

    failures: list[str] = []
    sequence = goal_sequence(contract.tier, ui_goal_enabled=contract.ui_goal_enabled)
    expected_base = len(BASE_GOAL_SEQUENCES[contract.tier])
    if contract.ui_goal_enabled and contract.tier in {"light", "standard"}:
        failures.append("轻量和标准流程不使用独立 UI 目标。")
    if contract.ui_goal_enabled and contract.ui_route == "not-applicable":
        failures.append("启用 UI 目标时必须在合同中锁定 UI 路线。")
    if contract.ui_route == "pending" and contract.goal_stage != "documentation":
        failures.append("UI 路线 pending 只允许出现在路线选择前的 documentation 目标。")
    if not contract.ui_goal_enabled and contract.ui_route != "not-applicable":
        failures.append("未启用 UI 目标时 UI 路线必须为 not-applicable。")
    if contract.base_goal_count != expected_base:
        failures.append(f"基础目标数与档位不一致：应为 {expected_base}。")
    if contract.goal_count != len(sequence):
        failures.append(f"目标数与档位/UI 决策不一致：应为 {len(sequence)}。")
    if not 1 <= contract.goal_index <= len(sequence):
        failures.append("当前目标编号必须在有效目标数范围内。")
    elif contract.goal_stage != sequence[contract.goal_index - 1]:
        failures.append(
            f"当前目标阶段与编号不一致：应为 {sequence[contract.goal_index - 1]}。"
        )
    if contract.awaiting_external_input and contract.goal_stage != "ui":
        failures.append("只有 UI 目标可以进入等待外部输入。")
    if contract.awaiting_external_input and contract.ui_route not in {"external-ai", "stitch"}:
        failures.append("只有 external-ai 或 stitch UI 路线可以等待用户回传外部输入。")
    return failures


def goal_handoff_failures(
    contract: FlowContract,
    *,
    target_goal_index: int,
    event: str,
    evidence: list[str] | tuple[str, ...] = (),
) -> list[str]:
    """Reject skipped stages and preserve an externally waiting UI goal."""
    if not all((contract.base_goal_count, contract.goal_index, contract.goal_stage)):
        return ["目标交接合同缺少多阶段字段。"]
    failures = multi_goal_contract_failures(contract)
    if failures:
        return failures
    if contract.awaiting_external_input:
        negative_markers = (
            "继续等待", "仍在等待", "尚未", "未收到", "未确认", "无法确认",
            "不确定", "缺失", "未提供",
        )
        positive_markers = (
            "收到外部输入", "外部输入已回传", "外部产物已提供",
            "收到外部产物", "已提供 Project ID", "已提供 Screen ID",
        )
        if target_goal_index == contract.goal_index:
            if not any(marker in event for marker in negative_markers) and any(
                marker in event for marker in positive_markers
            ):
                return []
            return ["外部输入未确认收到，当前 UI 目标必须继续等待。"]
        return ["当前 UI 目标正在等待外部输入，禁止递增目标编号。"]
    sequence = goal_sequence(contract.tier, ui_goal_enabled=contract.ui_goal_enabled)
    if (
        target_goal_index == contract.goal_index + 1
        and target_goal_index <= len(sequence)
        and sequence[target_goal_index - 1] == "ui"
        and contract.ui_route == "pending"
    ):
        failures.append("进入 UI 目标前必须先选择并锁定 canonical UI 路线。")
    evidence_set = set(contract.completed_gates) | set(evidence)
    if contract.goal_stage == "documentation":
        required = TIER_PRECODE_REQUIRED_GATES[contract.tier]
        missing = [item for item in required if item not in evidence_set]
        if missing:
            failures.append("文档目标缺少完成证据：" + "、".join(missing))
        if not contract.artifact_audit:
            failures.append("文档目标交接前必须完成真实产物审计。")
    elif contract.goal_stage == "ui":
        required = ("文本视觉方案已确认", "UI 壳已完成", "UI 壳接收检查")
        missing = [item for item in required if item not in evidence_set]
        if missing:
            failures.append("UI 目标缺少完成证据：" + "、".join(missing))
        if contract.ui_route == "stitch":
            if "Stitch 复修通过" not in evidence_set:
                failures.append("Stitch UI 目标缺少强制复修通过证据。")
        elif contract.visual_qa == "检查页面样式是否符合方案":
            if "视觉 QA 通过" not in evidence_set:
                failures.append("UI 目标缺少视觉 QA 通过证据。")
        elif not any(item.startswith("视觉 QA 不适用：") for item in evidence_set):
            failures.append("UI 目标必须记录视觉 QA 不适用原因。")
    elif contract.goal_stage == "development":
        if contract.state != "内部测试通过" and "内部测试通过" not in evidence_set:
            failures.append("开发目标缺少内部测试通过完成证据。")
    if target_goal_index != contract.goal_index + 1:
        failures.append("目标交接只能进入紧邻的下一次，不得跳步。")
    if "已完成" not in event:
        failures.append("解锁下一目标前必须有当前目标已完成事件。")
    if contract.goal_index >= contract.goal_count:
        failures.append("当前已是最后目标，不得继续递增。")
    return failures


def goal_reclaim_failures(payload: dict[str, Any]) -> list[str]:
    """Validate the last ordinary goal's handoff/reclaim event.

    Reclaiming closes the ordinary goal only. It must not start the independent
    task-document archive lifecycle.
    """
    failures: list[str] = []
    contract_data = payload.get("contract")
    if not isinstance(contract_data, dict):
        return ["目标回收合同必须提供 contract 对象。"]
    try:
        contract = FlowContract.from_dict(contract_data)
    except (KeyError, TypeError, ValueError) as exc:
        return [f"目标回收合同中的流程合同无效：{exc}"]

    task_id = str(payload.get("task_id", "")).strip()
    if contract.task_id.strip() and task_id != contract.task_id.strip():
        failures.append("目标回收合同的任务 ID 与流程合同不一致。")
    if not task_id:
        failures.append("目标回收合同缺少任务 ID。")

    goal_index = payload.get("goal_index")
    goal_count = payload.get("goal_count")
    if type(goal_index) is not int or type(goal_count) is not int:
        failures.append("目标回收合同必须提供整数 goal_index 和 goal_count。")
    else:
        if goal_index != goal_count:
            failures.append("只有最后一个 M/M 普通目标允许回收。")
        if goal_index < 1 or goal_count < 1:
            failures.append("目标编号和目标总数必须为正整数。")
    if str(payload.get("goal_stage", "")) not in FINAL_GOAL_STAGES:
        failures.append("目标回收只能用于最后普通目标阶段。")

    status_before = str(payload.get("goal_status_before", ""))
    status_after = str(payload.get("goal_status_after", ""))
    if status_before not in GOAL_STATUSES:
        failures.append("goal_status_before 不是合法目标状态。")
    if status_after != "reclaimed":
        failures.append("目标回收后的 goal_status 必须是 reclaimed。")
    if status_before in {"active", "reclaim_pending"} and contract.goal_status != status_before:
        failures.append("goal_status_before 与流程合同中的目标状态不一致。")
    if status_before == "reclaimed" and contract.goal_status != "reclaimed":
        failures.append("重复回收时流程合同必须已经是 reclaimed。")

    expected_acceptance = (
        "用户验收通过"
        if contract.acceptance_owner in {"用户自己测试", "我自己测试"}
        else "真机测试通过"
    )
    if payload.get("acceptance_result") != expected_acceptance:
        failures.append(f"目标回收前必须有验收通过证据：{expected_acceptance}。")
    for field_name in (
        "issue_writeback_complete", "retest_complete", "post_score_complete",
        "user_check_notification_sent", "archive_started",
        "archive_cleanup_performed", "archive_index_updated",
    ):
        value = payload.get(field_name)
        if type(value) is not bool:
            failures.append(f"{field_name} 必须是布尔值。")
        elif field_name in {
            "issue_writeback_complete", "retest_complete", "post_score_complete",
            "user_check_notification_sent",
        } and value is not True:
            failures.append(f"{field_name} 完成后才能回收普通目标。")
        elif field_name in {
            "archive_started", "archive_cleanup_performed", "archive_index_updated",
        } and value is True:
            failures.append(f"普通目标回收时禁止执行 {field_name}。")

    evidence = payload.get("goal_completion_evidence", [])
    if not isinstance(evidence, (list, tuple)) or not evidence or not all(str(item).strip() for item in evidence):
        failures.append("目标回收合同必须保存真实完成证据。")
    if str(payload.get("task_state_after", "")) != "待用户检查":
        failures.append("普通目标回收后项目状态必须是待用户检查。")
    if str(payload.get("archive_state_after", "")) != "待归档确认":
        failures.append("普通目标回收后归档状态必须保持待归档确认。")
    if payload.get("user_check_notification_sent") is True and not str(
        payload.get("user_check_notification_evidence", "")
    ).strip():
        failures.append("进入待用户检查前必须保存通知证据。")

    return failures


FLOW_STATE_ORDER = (
    "未开始", "只读调查中", "修改前评分已完成", "需求整理中",
    "待详细总结确认", "待集中确认", "正式 PRD 待确认", "提示词生成中", "提示词待校验",
    "提示词已解锁", "文档准备中", "任务拆分中", "产物审计中",
    "编码已解锁", "开发目标已解锁", "开发中", "内部验证中", "内部测试通过",
    "持久化任务清单已完成", "受影响文档真实 diff 已完成",
    "验收准备中", "验收目标执行中", "待实测", "待用户验收", "待实测或待用户验收", "真机测试中",
    "真机测试通过", "回写中", "修改后复评中", "用户验收通过",
    "待用户检查", "待归档确认",
    "归档中", "已归档", "归档受阻", "已取消", "暂停归档", "被新任务替代",
    "已完成", "受阻",
)

GOAL_STAGE_FORBIDDEN_TARGET_STATES: dict[GoalStage, frozenset[str]] = {
    "documentation": frozenset({
        "编码已解锁", "开发目标已解锁", "开发中", "内部验证中", "内部测试通过",
        "待实测", "待用户验收", "待实测或待用户验收", "真机测试中",
        "真机测试通过", "用户验收通过", "回写中", "修改后复评中",
        "待用户检查", "待归档确认", "归档中", "已归档", "归档受阻", "已完成",
    }),
    "ui": frozenset({
        "开发目标已解锁", "验收目标执行中",
        "待实测", "待用户验收", "待实测或待用户验收", "真机测试中",
        "真机测试通过", "用户验收通过", "回写中", "修改后复评中",
        "待用户检查", "待归档确认", "归档中", "已归档", "归档受阻", "已完成",
    }),
    "development": frozenset({
        "验收目标执行中",
        "真机测试中", "真机测试通过", "用户验收通过",
        "回写中", "修改后复评中", "待用户检查", "待归档确认", "归档中", "已归档", "归档受阻", "已完成",
    }),
}

TIER_PRECODE_REQUIRED_GATE = {
    "light": "失败测试已确认 RED",
    "standard": "持久化模块任务清单",
    "deep": "全部微观任务写回",
    "full-docs": "文档与任务产物审计",
}

TIER_PRECODE_REQUIRED_GATES: dict[RuntimePromptTier, tuple[str, ...]] = {
    "light": ("依赖扫描完成", "失败测试已确认 RED"),
    "standard": ("持久化模块任务清单", "受影响文档真实 diff"),
    "deep": (
        "受影响文档真实 diff",
        "全部微观任务写回",
        "开发追踪已更新",
        "验收准备已完成",
    ),
    "full-docs": (
        "完整文档体系真实 diff",
        "全部微观任务写回",
        "文档与任务产物审计",
    ),
}

STATE_EVENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "待详细总结确认": ("需求整理好了", "总结好了"),
    "待集中确认": ("输出详细需求总结", "详细需求总结已输出", "PRD 没问题", "用户确认正式 PRD"),
    "正式 PRD 待确认": ("正式 PRD 已输出", "PRD 已转换", "PRD 索引已更新"),
    "提示词生成中": (
        "用户确认总结",
        "用户确认需求总结",
        "确认总结和验收责任",
        "PRD 没问题",
        "用户确认正式 PRD",
        "用户选择",
        "验收责任已确认",
        "集中选择已完成",
    ),
    "提示词待校验": ("提示词生成完成", "生成提示词"),
    "提示词已解锁": ("提示词校验通过", "提示词已解锁"),
    "编码已解锁": ("编码解锁",),
    "开发目标已解锁": ("开发目标解锁",),
    "验收目标执行中": ("开始验收目标", "验收目标执行中"),
    "内部测试通过": ("内部测试通过", "内部验证完成"),
    "验收准备中": ("验收准备",),
    "待实测": ("待实测", "真机清单已准备"),
    "待用户验收": ("待用户验收", "用户验收入口已准备"),
    "回写中": ("回写", "验收结果已记录"),
    "修改后复评中": ("修改后复评", "修改后评分"),
    "真机测试通过": ("真机测试通过",),
    "用户验收通过": ("用户验收通过",),
    "待用户检查": ("待用户检查", "等待用户检查", "当前目标完成开发"),
    "待归档确认": ("待归档确认", "等待用户回复归档", "用户检查"),
    "归档中": ("开始归档", "用户明确回复归档", "归档中"),
    "已归档": ("归档校验通过", "已归档"),
    "已完成": ("完成", "验收通过"),
}


def flow_transition_failures(
    contract: FlowContract,
    *,
    target_state: str,
    event: str,
    evidence: list[str] | tuple[str, ...] = (),
) -> list[str]:
    """Validate one explicit state transition and reject skipped confirmation gates."""
    failures: list[str] = []
    evidence_set = set(contract.completed_gates) | set(contract.unlocked_gates) | set(evidence)
    if target_state not in FLOW_STATE_ORDER:
        return [f"未知流程状态：{target_state}"]
    forbidden_states = GOAL_STAGE_FORBIDDEN_TARGET_STATES.get(contract.goal_stage, frozenset())
    if target_state in forbidden_states:
        failures.append(
            f"目标阶段 {contract.goal_stage} 禁止进入状态：{target_state}。"
        )
    if contract.state == target_state and target_state != "受阻":
        failures.append(f"状态转换必须推进到下一状态，不能重复提交当前状态：{target_state}")

    if target_state in STATE_EVENT_KEYWORDS and not any(
        keyword in event for keyword in STATE_EVENT_KEYWORDS[target_state]
    ):
        failures.append(
            f"状态转换事件与目标状态不匹配：进入 {target_state} 必须包含事件关键词之一："
            + "、".join(STATE_EVENT_KEYWORDS[target_state])
        )

    completion_event = "需求整理好了" in event or "总结好了" in event
    if completion_event and target_state != "待详细总结确认":
        failures.append("需求整理好了后必须先输出详细需求总结，不能直接进入提示词阶段。")
    if target_state == "待集中确认" and not any(
        marker in event
        for marker in (
            "输出详细需求总结",
            "详细需求总结已输出",
            "PRD 没问题",
            "用户确认正式 PRD",
        )
    ):
        failures.append("进入待集中确认前必须先真实输出详细总结或收到正式 PRD 确认。")
    if target_state == "正式 PRD 待确认":
        if not all(marker in event or marker in evidence_set for marker in ("PRD 草稿已转换", "PRD 索引已更新", "正式 PRD 已输出")):
            failures.append("进入正式 PRD 待确认前必须完成草稿转换、PRD 索引并输出正式 PRD。")
        if "PRD 没问题" in event:
            failures.append("正式 PRD 输出和用户确认不能在同一条消息中伪造。")
    if contract.state == "正式 PRD 待确认" and target_state in {"提示词生成中", "提示词待校验", "提示词已解锁"}:
        if "PRD 没问题" not in event and "PRD 没问题" not in evidence_set:
            failures.append("正式 PRD 未收到用户“PRD 没问题”确认，禁止进入提示词阶段。")
    if target_state in {"提示词生成中", "提示词待校验", "提示词已解锁"}:
        if "需求整理好了" in event or "总结好了" in event:
            failures.append("同一条用户消息不能同时伪造总结输出和总结确认。")
        if not contract.summary_output:
            failures.append("提示词解锁前必须有“总结已输出”证据。")
        if not contract.summary_confirmed:
            failures.append("提示词解锁前必须有用户确认总结证据。")
        if not contract.acceptance_confirmed or contract.acceptance_owner == "待确认":
            failures.append("提示词解锁前必须确认验收责任。")

    if target_state in {"编码已解锁", "开发中"}:
        required_gates = TIER_PRECODE_REQUIRED_GATES[contract.tier]
        missing_gates = [gate for gate in required_gates if gate not in evidence_set]
        for gate in missing_gates:
            failures.append(f"编码解锁前缺少档位必需门禁：{gate}")
        if contract.prompt_status not in {"校验通过", "已解锁"} and "提示词校验通过" not in evidence_set:
            failures.append("编码解锁前必须有提示词校验通过证据。")

    if "同一条用户消息" in event and target_state in {"提示词生成中", "提示词已解锁", "编码已解锁"}:
        failures.append("同一条用户消息不能跨越详细总结输出和用户确认两个状态。")

    if target_state == "待用户检查":
        if contract.state not in {"修改后复评中", "真机测试通过", "用户验收通过"}:
            failures.append("最后一次普通目标必须先完成修改后复评，才能进入待用户检查。")
        if (
            contract.goal_status != "reclaimed"
            and any((contract.goal_completion_evidence, contract.task_state_after_goal, contract.archive_state_after_goal))
        ):
            failures.append("普通目标进入待用户检查前必须已经 reclaimed，不能继续占用原目标执行状态。")
        if not any(marker in event for marker in ("开发", "测试", "验收", "问题回写", "必要修复")):
            failures.append("进入待用户检查前必须记录开发、测试、验收、问题回写和必要修复完成证据。")
        return failures
    if target_state == "待归档确认":
        if contract.state != "待用户检查":
            failures.append("待归档确认只能从待用户检查进入。")
        if (
            contract.goal_status != "reclaimed"
            and any((contract.goal_completion_evidence, contract.task_state_after_goal, contract.archive_state_after_goal))
        ):
            failures.append("待归档确认不能把仍 active 的普通目标当作已完成交接。")
        if "归档" not in event and "用户检查" not in event:
            failures.append("进入待归档确认前必须记录用户检查通知和归档确认等待。")
        return failures

    if contract.state in ARCHIVE_STATE_TRANSITIONS:
        allowed_archive_states = ARCHIVE_STATE_TRANSITIONS[contract.state]
        if target_state not in allowed_archive_states:
            failures.append(
                f"归档状态转换不合法：{contract.state} → {target_state}；"
                f"允许：{'、'.join(allowed_archive_states)}。"
            )
        if contract.state == "已归档" and target_state == "已完成":
            if contract.archive_state != "已归档":
                failures.append("进入已完成前，归档状态必须是已归档。")
            for label, value in (
                ("任务 ID", contract.task_id),
                ("需求工作文档路径", contract.requirements_path),
                ("归档路径", contract.archive_path),
            ):
                if not value.strip():
                    failures.append(f"进入已完成前必须保留{label}。")
        if contract.state == "待归档确认" and target_state == "归档中":
            if not contract.user_archive_confirmation:
                failures.append("进入归档中前必须有用户明确回复“归档”的确认。")
            if not contract.archive_confirmation_evidence.strip():
                failures.append("进入归档中前必须保留用户归档确认的真实证据。")
        return failures
    tier_states = TIER_STATE_SEQUENCES.get(contract.tier, FLOW_STATE_ORDER)
    if contract.state not in tier_states and contract.state != "受阻":
        failures.append(f"当前状态不属于 {contract.tier} 的合法状态序列：{contract.state}")
        return failures
    if contract.state == "受阻":
        if target_state == "受阻":
            return failures
        if not evidence:
            failures.append("受阻恢复必须提供新的验证或外部状态证据。")
        return failures
    if target_state in {"真机测试通过", "用户验收通过"}:
        if not contract.acceptance_confirmed or contract.acceptance_owner not in ARCHIVE_ACCEPTANCE_OWNERS:
            failures.append("验收通过前必须保留已确认的验收责任。")
        expected_state = (
            "用户验收通过"
            if contract.acceptance_owner in {"用户自己测试", "我自己测试"}
            else "真机测试通过"
        )
        if target_state != expected_state:
            failures.append(f"验收责任与目标状态不一致：应进入 {expected_state}。")
        if contract.state != "修改后复评中":
            failures.append(
                f"验收通过状态不能跳步：{contract.state} → {target_state}；"
                "必须先完成当前档位的实现、验收回写和修改后复评。"
            )
        return failures
    if target_state not in tier_states and target_state != "受阻":
        failures.append(f"目标状态不属于 {contract.tier} 的合法状态序列：{target_state}")
        return failures
    if contract.state in tier_states and target_state in tier_states:
        if contract.state == "待用户检查" and target_state == "归档中":
            if contract.user_archive_confirmation and contract.archive_confirmation_evidence.strip():
                return failures
        current_index = tier_states.index(contract.state)
        target_index = tier_states.index(target_state)
        if target_state not in {contract.state, "受阻"} and target_index > current_index + 1:
            failures.append(f"状态转换不能跳步：{contract.state} → {target_state}；允许的下一状态只能是 {tier_states[current_index + 1]}。")
    return failures


def flow_contract_failures(
    contract: FlowContract,
    *,
    resumed_tier: RuntimePromptTier | None = None,
    post_score: int | None = None,
    upgrade_evidence: list[str] | tuple[str, ...] = (),
    acceptance_owner: str | None = None,
    goal_count: int | None = None,
) -> list[str]:
    """Reject context-resume drift without new score and evidence."""
    failures = multi_goal_contract_failures(contract)
    if resumed_tier is not None and resumed_tier != contract.tier:
        if resumed_tier == "full-docs" and contract.tier != "full-docs":
            if post_score is None or post_score <= 69 or not upgrade_evidence:
                failures.append("没有修改后评分和调用方证据时不得把流程恢复为完整流程。")
        else:
            failures.append("上下文恢复后的流程档位必须与流程合同一致。")
    if resumed_tier is not None and post_score is None and resumed_tier != contract.tier:
        failures.append("档位变化必须提供修改后评分证据。")
    if acceptance_owner is not None and acceptance_owner != contract.acceptance_owner:
        failures.append("上下文恢复不得改变已确认的验收责任。")
    if goal_count is not None and goal_count != contract.goal_count:
        if post_score is None or not upgrade_evidence:
            failures.append("上下文恢复不得改变目标提示词数量，除非提供新的修改后评分和范围证据。")
    if post_score is not None and not 0 <= post_score <= 100:
        failures.append("修改后评分必须在 0–100 范围内。")
    if contract.state == "已完成" and contract.archive_state != "已归档":
        failures.append("流程只有在归档状态为已归档后才能恢复为已完成。")
    if contract.archive_state != "未开始" or contract.state in {"归档中", "已归档", "归档受阻", "已完成"}:
        if not contract.task_id.strip():
            failures.append("归档状态恢复必须保留任务 ID。")
        if not contract.requirements_path.strip():
            failures.append("归档状态恢复必须保留需求工作文档路径。")
        if not contract.archive_path.strip():
            failures.append("归档状态恢复必须保留归档路径。")
        if not contract.user_archive_confirmation:
            failures.append("归档状态恢复必须保留用户明确回复“归档”的确认。")
        if not contract.archive_confirmation_evidence.strip():
            failures.append("归档状态恢复必须保留用户归档确认的真实证据。")
    return failures

WORKFLOW_CONTRACT_REQUIRED_PHRASES = (
    "## 流程合同",
    "流程档位：",
    "修改前评分：",
    "基础目标数量：",
    "目标提示词数量：",
    "当前目标：",
    "目标阶段：",
    "UI 目标：",
    "UI 路线：",
    "等待外部输入：",
    "验收责任：",
    "页面样式检查：",
    "当前阶段：",
    "编码解锁条件：",
    "允许升级条件：",
    "上下文压缩后必须恢复本流程合同，不得重新猜测档位。",
    "没有修改后评分证据不得改变档位。",
    "当前状态：",
    "已完成门禁：",
    "待完成门禁：",
    "允许下一动作：",
    "禁止动作：",
    "需求总结已输出：",
    "需求总结已确认：",
    "验收责任已确认：",
    "提示词状态：",
    "真实产物审计：",
    "进入证据：",
    "阻塞原因：",
    "状态转换规则：",
    "需求整理好了只能进入待详细总结确认",
    "PRD 草稿已转换",
    "PRD 索引已更新",
    "正式 PRD 已输出",
    "PRD 确认状态：",
    "目标状态：",
    "目标回收状态：",
    "目标完成证据：",
    "用户检查通知证据：",
    "归档目标不计入普通 N/M",
    "回收失败保持 reclaim_pending",
)

RUNTIME_PROMPT_SEQUENCES: dict[RuntimePromptTier, tuple[str, ...]] = {
    "light": (
        "依赖扫描完成",
        "失败测试已确认 RED",
        "编码解锁",
        "内部验证",
        "按已确认验收责任",
        "修改后评分",
    ),
    "standard": (
        "持久化模块任务清单",
        "受影响文档真实 diff",
        "编码解锁",
        "TDD 实现",
        "内部验证回写",
        "按已确认验收责任",
        "验收结果再次回写",
        "修改后评分",
    ),
    "deep": (
        "受影响文档真实 diff",
        "全部微观任务写回",
        "开发追踪已更新",
        "验收准备已完成",
        "编码解锁",
        "TDD 实现",
        "内部验证回写",
        "真机测试或待用户验收",
        "验收结果再次回写",
        "修改后评分",
    ),
    "full-docs": (
        "完整文档体系真实 diff",
        "全部微观任务写回",
        "文档与任务产物审计",
        "下一目标解锁",
    ),
}

GOAL_STAGE_PROMPT_SEQUENCES: dict[tuple[RuntimePromptTier, GoalStage], tuple[str, ...]] = {
    ("light", "single"): RUNTIME_PROMPT_SEQUENCES["light"],
    ("standard", "single"): RUNTIME_PROMPT_SEQUENCES["standard"],
    ("deep", "documentation"): (
        "受影响文档真实 diff", "全部微观任务写回", "开发追踪已更新",
        "验收准备已完成", "下一目标解锁",
    ),
    ("full-docs", "documentation"): (
        "完整文档体系真实 diff", "全部微观任务写回", "文档与任务产物审计",
        "下一目标解锁",
    ),
    ("deep", "ui"): (
        "文本视觉方案已确认", "UI 壳已完成", "UI 壳接收检查",
        "视觉 QA 或 Stitch 复修", "下一目标解锁",
    ),
    ("full-docs", "ui"): (
        "文本视觉方案已确认", "UI 壳已完成", "UI 壳接收检查",
        "视觉 QA 或 Stitch 复修", "下一目标解锁",
    ),
    ("full-docs", "development"): (
        "前置产物审计", "编码解锁", "TDD 实现", "内部验证回写",
        "内部测试通过", "下一目标解锁",
    ),
    ("deep", "development-and-acceptance"): (
        "前置产物审计", "编码解锁", "TDD 实现", "内部验证回写",
        "真机测试或待用户验收", "验收结果再次回写", "修改后评分",
    ),
    ("full-docs", "acceptance"): (
        "验收准备已完成", "真机测试或待用户验收", "验收结果再次回写",
        "修改后评分",
    ),
}
FINAL_GOAL_STAGES = {"single", "development-and-acceptance", "acceptance"}

TIER_STATE_SEQUENCES: dict[RuntimePromptTier, tuple[str, ...]] = {
    "light": (
        "未开始", "只读调查中", "修改前评分已完成", "需求整理中",
        "待详细总结确认", "正式 PRD 待确认", "待集中确认", "提示词生成中", "提示词待校验", "提示词已解锁",
        "编码已解锁", "开发中", "内部测试通过", "验收准备中",
        "待实测或待用户验收", "回写中", "修改后复评中", "真机测试通过", "用户验收通过", "待用户检查", "待归档确认", "归档中", "已归档", "已完成",
    ),
    "standard": (
        "未开始", "只读调查中", "修改前评分已完成", "需求整理中",
        "待详细总结确认", "正式 PRD 待确认", "待集中确认", "提示词生成中", "提示词待校验", "提示词已解锁",
        "持久化任务清单已完成", "受影响文档真实 diff 已完成", "编码已解锁",
        "开发中", "内部测试通过", "验收准备中", "待实测或待用户验收",
        "回写中", "修改后复评中", "真机测试通过", "用户验收通过", "待用户检查", "待归档确认", "归档中", "已归档", "已完成",
    ),
    "deep": (
        "未开始", "只读调查中", "修改前评分已完成", "需求整理中",
        "待详细总结确认", "正式 PRD 待确认", "待集中确认", "提示词生成中", "提示词待校验",
        "提示词已解锁", "文档准备中", "任务拆分中", "开发追踪已更新",
        "验收准备中", "编码已解锁", "开发中", "内部测试通过",
        "待实测或待用户验收", "回写中", "修改后复评中", "真机测试通过", "用户验收通过", "待用户检查", "待归档确认", "归档中", "已归档", "已完成",
    ),
    "full-docs": (
        "未开始", "只读调查中", "修改前评分已完成", "需求整理中",
        "待详细总结确认", "正式 PRD 待确认", "待集中确认", "提示词生成中", "提示词待校验",
        "提示词已解锁", "文档准备中", "任务拆分中", "产物审计中",
        "开发目标已解锁", "开发中", "内部测试通过", "验收准备中",
        "验收目标执行中", "回写中", "修改后复评中", "真机测试通过", "用户验收通过", "待用户检查", "待归档确认", "归档中", "已归档", "已完成",
    ),
}

TIER_ORDER: dict[Tier, int] = {
    "轻量流程": 0,
    "标准流程": 1,
    "深度流程": 2,
    "完整流程": 3,
}


def executable_prompt_failures(
    prompt: str,
    *,
    applicable: bool = True,
    minimum_chars: int = EXECUTABLE_PROMPT_MIN_CHARS,
    maximum_chars: int = EXECUTABLE_PROMPT_MAX_CHARS,
) -> list[str]:
    """Validate a complete copyable execution prompt, not ordinary chat text."""
    if not applicable:
        return []

    failures: list[str] = []
    char_count = len(prompt)
    if char_count < minimum_chars:
        failures.append(f"完整执行提示词少于 {minimum_chars} 个字符：{char_count}")
    if char_count > maximum_chars:
        failures.append(f"完整执行提示词超过 {maximum_chars} 个字符：{char_count}")

    first_line = prompt.splitlines()[0].strip() if prompt.splitlines() else ""
    if MULTI_AGENT_OPENING not in prompt:
        failures.append("完整执行提示词缺少统一多智能体开头。")
    elif first_line != MULTI_AGENT_OPENING:
        failures.append("统一多智能体开头必须是完整执行提示词的第一行。")

    heading_matches: dict[str, list[re.Match[str]]] = {}
    for section in EXECUTABLE_PROMPT_REQUIRED_SECTIONS:
        pattern = re.compile(
            rf"(?m)^\s*#{{1,6}}\s*(?:(?:[一二三四五六七八九十百]+|\d+)[、.)]\s*)?{re.escape(section)}\s*$"
        )
        matches = list(pattern.finditer(prompt))
        heading_matches[section] = matches
        if not matches:
            failures.append(f"完整执行提示词缺少实际 Markdown 标题：{section}")
        elif len(matches) > 1:
            failures.append(f"完整执行提示词标准章节必须唯一：{section}")

    section_positions = [
        (section, matches[0].start())
        for section, matches in heading_matches.items()
        if matches
    ]
    if section_positions:
        actual_order = [section for section, _ in sorted(section_positions, key=lambda item: item[1])]
        if len(actual_order) == len(EXECUTABLE_PROMPT_REQUIRED_SECTIONS) and actual_order != list(EXECUTABLE_PROMPT_REQUIRED_SECTIONS):
            failures.append("完整执行提示词标准章节顺序错误，必须按十一项规范顺序排列。")
    for index, (section, position) in enumerate(sorted(section_positions, key=lambda item: item[1])):
        heading_end = heading_matches[section][0].end()
        detail_end = (
            sorted(section_positions, key=lambda item: item[1])[index + 1][1]
            if index + 1 < len(section_positions)
            else len(prompt)
        )
        detail = prompt[heading_end:detail_end].strip()
        if len(detail) < 20:
            failures.append(f"完整执行提示词章节只有标题或细节不足：{section}")

    for shortcut in EXECUTABLE_PROMPT_FORBIDDEN_SHORTCUTS:
        if shortcut in prompt:
            failures.append(f"完整执行提示词禁止用摘要替代必要正文：{shortcut}")

    line_counts: dict[str, int] = {}
    for line in prompt.splitlines():
        normalized = line.strip()
        if len(normalized) < 6:
            continue
        line_counts[normalized] = line_counts.get(normalized, 0) + 1
    repeated = [line for line, count in line_counts.items() if count >= 4]
    if repeated:
        failures.append(f"完整执行提示词存在重复凑字：{repeated[0]}")

    if OPTION_SKILL_PREFIX in prompt or OPTION_DETAIL_SUFFIX in prompt:
        failures.append("固定选项前缀和细节后缀只能出现在用户选择项，不得进入正式提示词正文。")

    return failures


def workflow_prompt_failures(
    prompt: str,
    *,
    tier: RuntimePromptTier,
    archive_stage: ArchiveStage | None = None,
    minimum_chars: int = EXECUTABLE_PROMPT_MIN_CHARS,
    maximum_chars: int = EXECUTABLE_PROMPT_MAX_CHARS,
) -> list[str]:
    """Validate one generated prompt against its runtime workflow contract."""
    # 普通 Goal 采用文件指针型短合同；专项提示词走独立校验分支。
    short_markers = ("普通目标提示词", "目标提示词类型：普通", "文件指针型")
    # 普通 Goal 默认走短版；仅当正文明确带有旧式流程合同标题时保留完整合同兼容校验。
    is_short_prompt = any(marker in prompt for marker in short_markers) or "## 流程合同" not in prompt
    if is_short_prompt:
        required_groups = {
            "任务 ID": ("任务 ID：", "任务ID："),
            "流程档位": ("流程档位：", "当前流程：", "流程等级："),
            "修改前评分": ("修改前评分：", "当前评分：", "评分："),
            "五维评分": ("五维评分：", "评分明细：", "评分维度："),
            "评分证据": ("评分证据：", "评分依据："),
            "阶段": ("当前阶段：", "目标阶段："),
            "目标 N/M": ("当前目标：", "目标 N/M：", "目标数量："),
            "读取文件": ("必须读取：", "读取文件：", "必须读取的真实文件："),
            "允许修改": ("允许修改：", "允许修改范围："),
            "禁止修改": ("禁止修改：", "禁止修改范围："),
            "验证": ("验证要求：", "验证："),
            "状态回写": ("状态回写：", "回写位置："),
            "完成条件": ("完成条件：",),
            "下一阶段": ("下一阶段解锁条件：", "下一阶段："),
        }
        failures = [
            f"普通目标提示词缺少：{label}"
            for label, aliases in required_groups.items()
            if not any(alias in prompt for alias in aliases)
        ]
        if len(prompt) > maximum_chars:
            failures.append(f"普通目标提示词超过 {maximum_chars} 个字符：{len(prompt)}")
        flow_line = next(
            (
                line.strip()
                for line in prompt.splitlines()
                if any(alias in line for alias in ("流程档位：", "当前流程：", "流程等级："))
            ),
            "",
        )
        flow_value = re.sub(r"^.*?(?:流程档位|当前流程|流程等级)\s*[：:]\s*", "", flow_line)
        if flow_value not in {
            "轻量流程", "标准流程", "深度流程", "完整流程", "完整流程候选",
            "light", "standard", "deep", "full-docs",
        }:
            failures.append("普通目标提示词的流程档位必须是合法四档值。")
        score_line = next(
            (
                line.strip()
                for line in prompt.splitlines()
                if any(alias in line for alias in ("修改前评分：", "当前评分：", "评分："))
            ),
            "",
        )
        score_match = re.search(r"(?:修改前评分|当前评分|评分)\s*[：:]\s*(\d{1,3})\s*(?:/\s*100)?", score_line)
        if score_match is None or not 0 <= int(score_match.group(1)) <= 100:
            failures.append("普通目标提示词的修改前评分必须是 0–100 范围内的数字。")
        stage_match = re.search(r"(?m)^\s*(?:当前目标|目标 N/M)：\s*第\s*(\d+)\s*/\s*(\d+)\s*次", prompt)
        inferred_stage: ArchiveStage = "non-final"
        if stage_match is not None and stage_match.group(1) == stage_match.group(2):
            inferred_stage = "handoff"
        normalized_stage = archive_stage
        if normalized_stage == "final":
            normalized_stage = "handoff"
        elif normalized_stage == "full-first":
            normalized_stage = "non-final"
        if normalized_stage == "archive":
            failures.append("正式归档必须使用独立 archive 提示词，不能作为普通目标阶段。")
        elif normalized_stage is not None and normalized_stage != inferred_stage:
            failures.append("归档阶段参数与当前目标编号不一致。")
        else:
            normalized_stage = normalized_stage or inferred_stage
        if normalized_stage == "handoff":
            for phrase in HANDOFF_PROMPT_REQUIRED_PHRASES:
                if phrase not in prompt:
                    failures.append(f"最后一次普通目标交接缺少：{phrase}")
        if normalized_stage in {"handoff", "non-final"}:
            for phrase in HANDOFF_PROMPT_FORBIDDEN_PHRASES:
                if phrase in prompt:
                    failures.append(f"普通目标禁止自动归档或最终归档话术：{phrase}")
        return failures
    failures = executable_prompt_failures(
        prompt,
        minimum_chars=minimum_chars,
        maximum_chars=maximum_chars,
    )

    if tier not in RUNTIME_PROMPT_SEQUENCES:
        return failures + [f"未知运行时流程档位：{tier}"]

    for phrase in WORKFLOW_CONTRACT_REQUIRED_PHRASES:
        if phrase not in prompt:
            failures.append(f"运行时提示词的流程合同缺少：{phrase}")

    contract_lines = {
        label: next(
            (line.strip() for line in prompt.splitlines() if line.strip().startswith(label)),
            "",
        )
        for label in (
            "流程档位：",
            "修改前评分：",
            "基础目标数量：",
            "目标提示词数量：",
            "当前目标：",
            "目标阶段：",
            "UI 目标：",
            "UI 路线：",
            "等待外部输入：",
            "验收责任：",
            "页面样式检查：",
            "当前阶段：",
            "编码解锁条件：",
            "允许升级条件：",
            "当前状态：",
            "已完成门禁：",
            "待完成门禁：",
            "允许下一动作：",
            "禁止动作：",
            "需求总结已输出：",
            "需求总结已确认：",
            "验收责任已确认：",
            "提示词状态：",
            "真实产物审计：",
            "进入证据：",
            "阻塞原因：",
        )
    }
    score_line = contract_lines["修改前评分："]
    score_match = re.search(r"修改前评分：\s*(\d{1,3})\s*(?:/\s*100)?", score_line)
    if score_match is None or not 0 <= int(score_match.group(1)) <= 100:
        failures.append("流程合同的修改前评分必须是 0–100 范围内的具体数字。")
    goal_count_line = contract_lines["目标提示词数量："]
    goal_count_match = re.search(r"目标提示词数量：\s*(\d+)", goal_count_line)
    if goal_count_match is None or int(goal_count_match.group(1)) < 1:
        failures.append("流程合同必须给出正整数目标提示词数量。")
    base_count_match = re.search(
        r"基础目标数量：\s*(\d+)", contract_lines["基础目标数量："]
    )
    current_goal_match = re.search(
        r"当前目标：\s*第\s*(\d+)\s*/\s*(\d+)\s*次",
        contract_lines["当前目标："],
    )
    goal_stage_value = contract_lines["目标阶段："][len("目标阶段："):].strip()
    ui_goal_value = contract_lines["UI 目标："][len("UI 目标："):].strip()
    ui_route_value = contract_lines["UI 路线："][len("UI 路线："):].strip()
    waiting_value = contract_lines["等待外部输入："][len("等待外部输入："):].strip()
    ui_goal_enabled = ui_goal_value == "启用"
    if ui_goal_value not in {"启用", "跳过", "不适用"}:
        failures.append("流程合同的 UI 目标必须是启用、跳过或不适用。")
    if ui_goal_enabled and tier in {"light", "standard"}:
        failures.append("轻量和标准流程不使用独立 UI 目标。")
    if ui_route_value not in UI_ROUTE_CODES:
        failures.append("流程合同的 UI 路线不合法。")
    elif ui_goal_enabled == (ui_route_value == "not-applicable"):
        failures.append("UI 目标决策与 UI 路线不一致。")
    if ui_route_value == "pending" and goal_stage_value != "documentation":
        failures.append("UI 路线 pending 只允许出现在 documentation 目标。")
    if waiting_value == "是" and ui_route_value not in {"external-ai", "stitch"}:
        failures.append("只有 external-ai 或 stitch UI 路线可以等待外部输入。")
    if waiting_value not in {"是", "否"}:
        failures.append("流程合同的等待外部输入必须是是或否。")
    if waiting_value == "是" and goal_stage_value != "ui":
        failures.append("只有 UI 目标可以等待外部输入。")
    try:
        expected_goals = goal_sequence(tier, ui_goal_enabled=ui_goal_enabled)
    except ValueError:
        expected_goals = ()
    expected_base_count = len(BASE_GOAL_SEQUENCES[tier])
    if base_count_match is None or int(base_count_match.group(1)) != expected_base_count:
        failures.append(f"流程合同的基础目标数量必须为 {expected_base_count}。")
    parsed_goal_count = int(goal_count_match.group(1)) if goal_count_match is not None else 0
    if parsed_goal_count != len(expected_goals):
        failures.append(f"流程合同的目标总数必须为 {len(expected_goals)}。")
    if current_goal_match is None:
        failures.append("流程合同必须写明当前是第 N/M 次目标。")
        goal_index = 0
    else:
        goal_index = int(current_goal_match.group(1))
        declared_total = int(current_goal_match.group(2))
        if declared_total != parsed_goal_count:
            failures.append("当前目标行的总数与目标提示词数量不一致。")
        if not 1 <= goal_index <= len(expected_goals):
            failures.append("当前目标编号超出合法范围。")
        elif goal_stage_value != expected_goals[goal_index - 1]:
            failures.append(
                f"当前目标阶段与编号不一致：应为 {expected_goals[goal_index - 1]}。"
            )
    for label, line in contract_lines.items():
        if label not in {"流程档位：", "修改前评分：", "基础目标数量：", "目标提示词数量："} and (not line or not line[len(label):].strip()):
            failures.append(f"流程合同字段不得为空：{label}")

    state_line = contract_lines["当前状态："]
    state_value = state_line[len("当前状态："):].strip() if state_line else ""
    if state_value and state_value not in FLOW_STATE_ORDER:
        failures.append(f"流程合同当前状态不是合法状态：{state_value}")
    if state_value and state_value not in TIER_STATE_SEQUENCES[tier] and state_value != "受阻":
        failures.append(f"流程合同当前状态不属于所选档位 {tier} 的独立状态序列：{state_value}")
    for label in ("需求总结已输出：", "需求总结已确认：", "验收责任已确认：", "真实产物审计："):
        value = contract_lines[label][len(label):].strip() if contract_lines[label] else ""
        if value and not re.match(r"^(是|否|已|未|待|通过|不适用)", value):
            failures.append(f"流程合同字段必须使用明确状态值：{label}")
    for label in ("需求总结已输出：", "需求总结已确认：", "验收责任已确认："):
        value = contract_lines[label][len(label):].strip() if contract_lines[label] else ""
        if value and not re.match(r"^(是|已|通过)", value):
            failures.append(f"提示词解锁前必须完成：{label}")
    audit_value = contract_lines["真实产物审计："][len("真实产物审计："):].strip()
    if audit_value and not re.match(r"^(是|已|通过)", audit_value):
        failures.append("提示词解锁前必须完成：真实产物审计：")
    prompt_status = contract_lines["提示词状态："]
    prompt_status_value = prompt_status[len("提示词状态："):].strip() if prompt_status else ""
    if prompt_status_value and prompt_status_value not in {"未生成", "生成中", "待校验", "校验通过", "已解锁", "不适用"}:
        failures.append(f"流程合同提示词状态不合法：{prompt_status_value}")
    if re.search(r"流程档位：\s*续作优化", prompt):
        failures.append("正式流程名称必须使用轻量流程、标准流程、深度流程或完整流程，不能使用“续作优化”。")
    if contract_lines["进入证据："] and not contract_lines["进入证据："][len("进入证据："):].strip():
        failures.append("流程合同的进入证据不得为空。")
    block_reason = contract_lines["阻塞原因："]
    block_reason_value = block_reason[len("阻塞原因："):].strip() if block_reason else ""
    if not block_reason_value:
        failures.append("流程合同的阻塞原因不得为空；无阻塞时应明确写“不适用”。")
    if state_value == "受阻" and block_reason_value in {"不适用", "无", "无阻塞"}:
        failures.append("当前状态为受阻时必须填写具体阻塞原因。")

    tier_label = RUNTIME_TIER_LABELS[tier]
    if f"流程档位：{tier}" not in prompt and f"流程档位：{tier_label}" not in prompt:
        failures.append(f"运行时提示词没有锁定所选档位：{tier}")

    gate_marker = "## 档位执行门禁"
    stage_key = (tier, goal_stage_value)
    sequence = GOAL_STAGE_PROMPT_SEQUENCES.get(stage_key, ())
    if not sequence:
        failures.append(f"运行时提示词的目标阶段不合法：{tier}/{goal_stage_value}")
    if gate_marker not in prompt:
        failures.append("运行时提示词缺少 `## 档位执行门禁`。")
        for phrase in sequence:
            failures.append(f"{tier} 运行时门禁缺少阶段：{phrase}")
        return failures

    gate_text = prompt.split(gate_marker, 1)[1]
    next_heading = re.search(r"(?m)^##\s+", gate_text)
    if next_heading is not None:
        gate_text = gate_text[: next_heading.start()]
    positions = [gate_text.find(phrase) for phrase in sequence]
    for phrase, position in zip(sequence, positions):
        if position < 0:
            failures.append(f"{tier} 运行时门禁缺少阶段：{phrase}")
    if all(position >= 0 for position in positions) and positions != sorted(positions):
        failures.append(
            f"{tier} 运行时门禁顺序错误：必须依次执行 " + " → ".join(sequence)
        )
    if all(position >= 0 for position in positions):
        unlock_position = gate_text.find("编码解锁")
        if unlock_position >= 0:
            for forbidden in ("修改源码", "实现源码", "编辑 src", "编辑 frontend", "编辑 electron"):
                if forbidden in gate_text[:unlock_position]:
                    failures.append(
                        f"{tier} 编码解锁前禁止出现实现编辑动作：{forbidden}"
                    )
                    break

    local_negation = re.compile(
        r"(?:禁止|不要|不得|不能|不可|不做|不执行|不允许|不接|无需|不)"
        r"(?:在(?:本阶段|当前目标))?"
        r"(?:直接|同时|立即|一并|执行|进行|进入|标记(?:为)?|输出|宣布|声称)?\s*$"
    )
    future_stage_owner = re.compile(
        r"(?:留给|交给|由)?(?:后续|下一).{0,16}目标(?:再|负责)?\s*$"
    )

    def locally_exempt(
        line: str,
        start: int,
        end: int | None = None,
        *,
        allow_future_owner: bool = False,
    ) -> bool:
        prefix = line[:start].rstrip()
        if local_negation.search(prefix):
            return True
        if not allow_future_owner:
            return False
        window = line[start : min(len(line), (end or start) + 24)]
        return bool(future_stage_owner.search(prefix)) or bool(
            re.search(r"(?:留给|交给|由)(?:后续|下一).{0,16}目标", window)
        )

    real_acceptance_pattern = r"(?:执行|进行|开始).{0,8}(?:真机测试|真机验收|用户验收|最终验收)"
    forbidden_action_patterns: dict[str, tuple[str, ...]] = {
        "documentation": (
            r"(?:修改|编辑|编写|实现).{0,8}(?:源码|业务代码|功能代码|前端代码)",
            real_acceptance_pattern,
        ),
        "ui": (
            r"(?:接入|接通|调用|实现|替换).{0,16}(?:真实 API|真实接口|真实数据|权限|表单提交|业务逻辑|数据流)",
            r"(?:真实 API|真实接口|真实数据|权限|表单提交|业务逻辑|数据流).{0,8}(?:接入|接通|调用|实现)",
            real_acceptance_pattern,
        ),
        "development": (real_acceptance_pattern,),
    }
    for line in prompt.splitlines():
        for pattern in forbidden_action_patterns.get(goal_stage_value, ()):
            match = re.search(pattern, line)
            if match is not None and not locally_exempt(
                line, match.start(), match.end(), allow_future_owner=True
            ):
                failures.append(
                    f"目标阶段 {goal_stage_value} 的肯定动作越过当前阶段：{match.group(0)}"
                )
                break
        else:
            continue
        break

    inferred_archive_stage: ArchiveStage = (
        "handoff" if goal_stage_value in FINAL_GOAL_STAGES else "non-final"
    )
    normalized_archive_stage = archive_stage
    if normalized_archive_stage == "final":
        normalized_archive_stage = "handoff"
    elif normalized_archive_stage == "full-first":
        normalized_archive_stage = "non-final"
    if normalized_archive_stage == "archive":
        failures.append("正式归档必须使用独立 archive 提示词，不能作为普通目标阶段。")
    elif normalized_archive_stage is not None and normalized_archive_stage != inferred_archive_stage:
        failures.append("归档阶段参数与当前目标阶段不一致。")
    archive_stage = normalized_archive_stage or inferred_archive_stage
    if archive_stage == "handoff":
        for phrase in HANDOFF_PROMPT_REQUIRED_PHRASES:
            if phrase not in prompt:
                failures.append(f"最后一次普通目标交接缺少：{phrase}")
        for phrase in HANDOFF_PROMPT_FORBIDDEN_PHRASES:
            if phrase in prompt:
                failures.append(f"普通目标禁止自动归档或最终归档话术：{phrase}")
    elif archive_stage == "non-final":
        declaration_pattern = re.compile(
            r"本次任务(?:已|已经|全部|整体|最终)?完成(?:并|[。！!]|$)"
            r"|(?:全部|所有)(?:任务)?(?:均|都)?已?完成"
            r"|(?:当前状态|归档状态)[:：]\s*(?:归档中|已归档|已完成)"
            r"|(?:进入|标记(?:为)?|更新为)\s*(?:归档中|已归档|已完成)"
            r"|(?:执行|完成)最终归档"
        )
        for line in prompt.splitlines():
            for declaration in declaration_pattern.finditer(line):
                if not locally_exempt(line, declaration.start()):
                    failures.append(
                        f"中间目标禁止归档或使用最终完成话术：{declaration.group(0)}"
                    )
                    break
            else:
                continue
            break
    return failures


def prompt_failures_for_kind(
    prompt: str,
    *,
    kind: str,
    tier: RuntimePromptTier | None = None,
    archive_stage: ArchiveStage | None = None,
) -> list[str]:
    """Dispatch generated-prompt validation without weakening workflow defaults."""
    if kind not in PROMPT_KINDS:
        return [f"未知提示词类型：{kind}"]
    if kind == "archive":
        return formal_archive_prompt_failures(prompt)
    if kind == "stitch-instance-repair":
        from scripts import check_codex_ui_flow_docs as ui_check

        return ui_check.stitch_instance_repair_prompt_failures(prompt)
    if kind in {
        "stitch-generation",
        "external-ai-ui",
        "product-design",
        "image-generation",
        "special-prompt",
    }:
        return special_prompt_failures(prompt, kind=kind)
    if tier is None:
        return ["普通提示词必须同时提供 --prompt-tier。"]
    if kind == "long":
        return workflow_prompt_failures(
            prompt,
            tier=tier,
            archive_stage=archive_stage,
            minimum_chars=LONG_PROMPT_MIN_CHARS,
            maximum_chars=LONG_PROMPT_MAX_CHARS,
        )
    return workflow_prompt_failures(
        prompt,
        tier=tier,
        archive_stage=archive_stage,
    )


def formal_archive_prompt_failures(prompt: str) -> list[str]:
    """Validate the independent archive prompt after explicit user confirmation."""
    failures: list[str] = []
    if not prompt.strip():
        return ["正式归档提示词不能为空。"]
    lines = prompt.splitlines()
    if not lines or lines[0].strip() != MULTI_AGENT_OPENING:
        failures.append("正式归档提示词第一行必须是统一多智能体开头。")
    for phrase in ARCHIVE_PROMPT_REQUIRED_PHRASES:
        if phrase not in prompt:
            failures.append(f"正式归档提示词缺少：{phrase}")
    for label in ("任务 ID：", "正式 PRD：", "需求整理文档：", "归档目录："):
        match = re.search(rf"(?m)^\s*{re.escape(label)}\s*(\S.+?)\s*$", prompt)
        if match is None or PLACEHOLDER_PATTERN.search(match.group(1)):
            failures.append(f"正式归档提示词字段无效：{label}")
    if "普通目标提示词" in prompt and "不计入普通目标数量" not in prompt:
        failures.append("正式归档提示词必须声明其独立于普通目标数量。")
    if "归档失败" not in prompt or "保留活动区原文" not in prompt:
        failures.append("正式归档提示词必须规定失败时保留活动区原文。")
    return failures


def special_prompt_failures(prompt: str, *, kind: str) -> list[str]:
    """Route specialist prompts away from the ordinary Goal contract.

    Specialist templates own their detailed structure and length rules. This
    shared gate only checks that a real prompt was supplied and that the
    ordinary selection wrapper was not accidentally pasted into the prompt.
    """
    if kind not in PROMPT_KINDS or kind in {"workflow", "long", "stitch-instance-repair"}:
        return [f"不是专项提示词类型：{kind}"]
    failures: list[str] = []
    if not prompt.strip():
        failures.append(f"{kind} 专项提示词不能为空。")
    if OPTION_SKILL_PREFIX in prompt or OPTION_DETAIL_SUFFIX in prompt:
        failures.append(f"{kind} 专项提示词不得包含用户选择项包装。")
    if "## 流程合同" in prompt or "## 档位执行门禁" in prompt:
        failures.append(f"{kind} 专项提示词不得套用普通 Goal 流程合同。")
    if kind == "stitch-generation":
        from scripts import check_codex_ui_flow_docs as ui_check

        failures.extend(ui_check.stitch_generation_prompt_failures(prompt))
    return failures


def prompt_delivery_failures(
    delivery: str,
    *,
    prompt_kind: str = "workflow",
) -> list[str]:
    """Validate the user-visible wrapper around one copyable prompt."""
    failures: list[str] = []
    if prompt_kind not in PROMPT_KINDS:
        return [f"未知提示词类型：{prompt_kind}"]
    fence_matches = list(re.finditer(r"(?m)^```[^\n]*$", delivery))
    if len(fence_matches) != 2:
        failures.append("完整执行提示词必须放在一个独立 Markdown 代码块中。")
        return failures

    opening, closing = fence_matches
    before = delivery[: opening.start()].strip()
    after = delivery[closing.end() :].strip()
    body = delivery[opening.end() : closing.start()].strip("\n")

    if len([line for line in before.splitlines() if line.strip()]) > 1:
        failures.append("代码块外只允许一句简短用途或原因说明。")
    if after:
        failures.append("代码块后不得继续补充执行要求。")
    if prompt_kind == "stitch-instance-repair":
        from scripts import check_codex_ui_flow_docs as ui_check

        failures.extend(ui_check.stitch_instance_repair_prompt_failures(body))
    elif prompt_kind in {
        "stitch-generation",
        "external-ai-ui",
        "product-design",
        "image-generation",
        "special-prompt",
    }:
        failures.extend(special_prompt_failures(body, kind=prompt_kind))
    else:
        failures.extend(executable_prompt_failures(body))
    return failures

OPTION_SKILL_PREFIX = "$liran-plan "
OPTION_DETAIL_SUFFIX = "（额外要求：生成提示词里面的目标需求需要详细，不漏一点细节。）"


def build_prompt_option(option_text: str) -> str:
    """Build the only allowed user-visible prompt-generating option form."""
    clean = option_text.strip()
    if clean.startswith(OPTION_SKILL_PREFIX):
        clean = clean[len(OPTION_SKILL_PREFIX):].lstrip()
    if clean.endswith(OPTION_DETAIL_SUFFIX):
        clean = clean[: -len(OPTION_DETAIL_SUFFIX)].rstrip()
    if not clean:
        raise ValueError("prompt-generating option text must not be empty")
    return f"{OPTION_SKILL_PREFIX}{clean}{OPTION_DETAIL_SUFFIX}"

PAGE_OPTIONS = [
    build_prompt_option("需求没问题，改完后让 Codex 自己真机测试，也检查页面样式是否符合方案"),
    build_prompt_option("需求没问题，改完后让 Codex 自己真机测试，不检查页面样式是否符合方案"),
    build_prompt_option("需求没问题，改完后我自己测试"),
]

NON_PAGE_OPTIONS = [
    build_prompt_option("需求没问题，改完后让 Codex 自己真机测试"),
    build_prompt_option("需求没问题，改完后我自己测试"),
    "需求没问题，但让 Codex 重新判断应该走哪个流程",
]

DEEP_PAGE_OPTIONS = [
    build_prompt_option("需求没问题，直接生成完整提示词，改完后让 Codex 自己真机测试，也检查页面样式是否符合方案"),
    build_prompt_option("需求没问题，直接生成完整提示词，改完后让 Codex 自己真机测试，不检查页面样式是否符合方案"),
    build_prompt_option("需求没问题，直接生成完整提示词，完成后我自己测试"),
]

DEEP_NON_PAGE_OPTIONS = [
    build_prompt_option("需求没问题，直接生成完整提示词，完成后让 Codex 自己真机测试"),
    build_prompt_option("需求没问题，直接生成完整提示词，完成后我自己测试"),
    "需求没问题，但让 Codex 重新判断是否需要深度流程",
]

FULL_FLOW_OPTIONS = [
    build_prompt_option("Codex 真机测试"),
    build_prompt_option("我自己测试"),
]

UI_ROUTE_OPTIONS = [
    build_prompt_option("Codex 直接生成前端 UI 壳"),
    build_prompt_option("@product-design"),
    build_prompt_option("@product-design + 外部 AI 生成前端 UI"),
    build_prompt_option("@product-design + $Stitch / Stitch MCP"),
    build_prompt_option("@product-design + Codex 内嵌 Gemini 或其他生成的好看的模型生成前端 UI"),
]
UI_ROUTE_MORE_OPTION = "继续选择外部 AI、Stitch 或内嵌模型路线"
UI_ROUTE_PRIMARY_OPTIONS = [*UI_ROUTE_OPTIONS[:2], UI_ROUTE_MORE_OPTION]
UI_ROUTE_ADVANCED_OPTIONS = UI_ROUTE_OPTIONS[2:]

PROMPT_GENERATING_OPTIONS = tuple(
    PAGE_OPTIONS[:3]
    + NON_PAGE_OPTIONS[:2]
    + DEEP_PAGE_OPTIONS[:3]
    + DEEP_NON_PAGE_OPTIONS[:2]
    + FULL_FLOW_OPTIONS
    + UI_ROUTE_OPTIONS
)

CONFIRMATION_OPTION_SETS = {
    "page": tuple(PAGE_OPTIONS),
    "non-page": tuple(NON_PAGE_OPTIONS),
    "deep-page": tuple(DEEP_PAGE_OPTIONS),
    "deep-non-page": tuple(DEEP_NON_PAGE_OPTIONS),
    "full-flow": tuple(FULL_FLOW_OPTIONS),
    "ui-route": tuple(UI_ROUTE_OPTIONS),
    "ui-route-primary": tuple(UI_ROUTE_PRIMARY_OPTIONS),
    "ui-route-advanced": tuple(UI_ROUTE_ADVANCED_OPTIONS),
}

CONFIRMATION_MARKDOWN_PATTERNS = (
    r"`", r"\*\*", r"__", r"\[[^\]]+\]\([^\)]+\)",
    r"(?m)^\s*(?:#{1,6}\s|[-*+]\s|\d+[.)]\s)",
)


def canonical_confirmation_options(kind: str) -> tuple[str, ...]:
    """Return the immutable option set shared by native and text confirmations."""
    try:
        return CONFIRMATION_OPTION_SETS[kind]
    except KeyError as exc:
        raise ValueError(f"unknown confirmation option set: {kind}") from exc


def option_wrapper_failures(options: list[str], *, expected_count: int) -> list[str]:
    failures: list[str] = []
    if len(options) != expected_count:
        failures.append(f"prompt-generating option count must be {expected_count}, got {len(options)}")
    for option in options:
        if not option.startswith(OPTION_SKILL_PREFIX):
            failures.append(f"option missing exact skill prefix: {option}")
        if option.count(OPTION_SKILL_PREFIX) != 1:
            failures.append(f"option must contain the skill prefix exactly once: {option}")
        if not option.endswith(OPTION_DETAIL_SUFFIX):
            failures.append(f"option missing exact terminal detail suffix: {option}")
        elif option in PROMPT_GENERATING_OPTIONS:
            continue
        else:
            failures.append(f"prompt-generating option is not from the canonical builder: {option}")
    return failures


def confirmation_delivery_failures(
    question: str,
    options: list[str],
    *,
    descriptions: list[str] | None = None,
    confirmation_kind: str = "acceptance",
    option_actions: list[str] | None = None,
    prompt_generating: bool,
) -> list[str]:
    """Validate one native-selector or text-fallback confirmation payload."""
    failures: list[str] = []
    descriptions = descriptions or []
    option_actions = option_actions or [
        "generate-prompt"
        if prompt_generating and (
            option in PROMPT_GENERATING_OPTIONS or option.startswith(OPTION_SKILL_PREFIX)
        )
        else "continue"
        for option in options
    ]
    if descriptions and len(descriptions) != len(options):
        failures.append("选项说明数量必须与选项数量一致。")
    if descriptions and any(not description.strip() for description in descriptions):
        failures.append("选项说明不得为空。")
    if len(option_actions) != len(options) or any(
        action not in {"generate-prompt", "continue"} for action in option_actions
    ):
        failures.append("每个选项必须有 generate-prompt 或 continue 动作。")
        return failures
    if prompt_generating != any(action == "generate-prompt" for action in option_actions):
        failures.append("prompt_generating 必须与各选项动作一致。")
    normalized_question = re.sub(r"\s+", "", question)
    for value in (question, *options, *descriptions):
        if any(re.search(pattern, value) for pattern in CONFIRMATION_MARKDOWN_PATTERNS):
            failures.append("用户可见选项框必须使用普通文本，不得包含 Markdown 格式。")
            break

    if prompt_generating:
        if not 2 <= len(options) <= 3:
            failures.append("原生选择框必须提供 2–3 个选项。")
        if confirmation_kind.startswith("ui-route"):
            expected_options = CONFIRMATION_OPTION_SETS.get(confirmation_kind)
            if expected_options is None or tuple(options) != expected_options:
                failures.append("UI 路线原生选择必须使用对应阶段的 canonical 选项。")
            if "UI" not in question or "路线" not in question:
                failures.append("UI 路线选择问题必须明确询问 UI 路线。")
            expected_actions = (
                ("generate-prompt", "generate-prompt", "continue")
                if confirmation_kind == "ui-route-primary"
                else ("generate-prompt",) * len(options)
            )
            if tuple(option_actions) != expected_actions:
                failures.append("UI 路线选择的生成/继续动作与阶段不一致。")
        else:
            if "需求" not in normalized_question or not (
                "测试" in normalized_question or "验收" in normalized_question
            ):
                failures.append("确认问题必须同时确认需求是否正确和测试/验收责任。")
            acceptance_sets = {
                kind: values
                for kind, values in CONFIRMATION_OPTION_SETS.items()
                if kind in {"page", "non-page", "deep-page", "deep-non-page", "full-flow"}
            }
            if confirmation_kind == "acceptance":
                matches_canonical = tuple(options) in acceptance_sets.values()
            else:
                matches_canonical = tuple(options) == acceptance_sets.get(confirmation_kind)
            if not matches_canonical:
                failures.append("验收确认必须完整匹配一套 canonical 需求/测试选项。")
            expected_actions = tuple(
                "generate-prompt" if option in PROMPT_GENERATING_OPTIONS else "continue"
                for option in options
            )
            if tuple(option_actions) != expected_actions:
                failures.append("验收选项的生成/继续动作与 canonical 合同不一致。")
        generating_options = [
            option for option, action in zip(options, option_actions)
            if action == "generate-prompt"
        ]
        failures.extend(option_wrapper_failures(generating_options, expected_count=len(generating_options)))
        unknown = [option for option in generating_options if option not in PROMPT_GENERATING_OPTIONS]
        if unknown:
            failures.append("会立即生成提示词的选项必须来自统一 canonical builder：" + unknown[0])
        if len(set(options)) != len(options):
            failures.append("prompt-generating options must be unique within one confirmation payload")
        if any("推荐" in option for option in options):
            failures.append("用户可见确认选项不得包含推荐。")
    if any(
        action == "continue" and (
            OPTION_SKILL_PREFIX in option or OPTION_DETAIL_SUFFIX in option
        )
        for option, action in zip(options, option_actions)
    ):
        failures.append("不会立即生成提示词的选项不得携带选项专用包装。")

    return failures


def text_confirmation_fallback_failures(text: str, options: list[str]) -> list[str]:
    """Validate a plain-text fallback when the native selector is unavailable."""
    failures: list[str] = []
    if any(re.search(pattern, text) for pattern in CONFIRMATION_MARKDOWN_PATTERNS):
        failures.append("文字回退选项必须使用普通文本，不得包含 Markdown 格式。")
    numerals = "一二三四五六七八九"
    for index, option in enumerate(options):
        expected = f"选项{numerals[index]}：{option}"
        if expected not in text:
            failures.append(f"文字回退缺少普通文本选项：选项{numerals[index]}。")
    return failures


def runtime_artifact_failures(
    tier: RuntimePromptTier,
    artifact_paths: list[str | Path],
    *,
    changed_paths: list[str | Path] = (),
    root: Path = ROOT,
) -> list[str]:
    """Audit concrete workflow artifacts before an implementation gate is unlocked."""
    if tier not in RUNTIME_PROMPT_SEQUENCES:
        return [f"未知运行时流程档位：{tier}"]
    failures: list[str] = []
    if tier in {"standard", "deep", "full-docs"} and not artifact_paths:
        failures.append(f"{tier} 必须提供真实文件产物路径，不能只在聊天中声称已完成。")
    normalized_changed: set[str] = set()
    for raw_changed in changed_paths:
        changed = Path(raw_changed)
        if not changed.is_absolute():
            changed = root / changed
        normalized_changed.add(str(changed.resolve()))
    if tier in {"standard", "deep", "full-docs"} and not normalized_changed:
        failures.append(f"{tier} 必须提供真实 diff 文件清单，不能只声称产物已更新。")
    for raw_path in artifact_paths:
        path = Path(raw_path)
        if not path.is_absolute():
            path = root / path
        if not path.exists():
            failures.append(f"运行时产物不存在：{path}")
            continue
        if not path.is_file():
            failures.append(f"运行时产物不是文件：{path}")
            continue
        content = path.read_text(encoding="utf-8", errors="replace").strip()
        if len(content) < 40:
            failures.append(f"运行时产物内容为空或仍是占位：{path}")
        if re.search(r"待填写|TODO|placeholder|待补充|占位符", content, re.I):
            failures.append(f"运行时产物仍含未完成占位内容：{path}")
        if tier in {"standard", "deep", "full-docs"} and normalized_changed and str(path.resolve()) not in normalized_changed:
            failures.append(f"运行时产物没有出现在本轮真实 diff：{path}")
    return failures

TASK_SCOPE_CAPS: dict[TaskScope, Tier] = {
    "老项目单文件局部修改": "轻量流程",
    "老项目单模块小功能": "标准流程",
    "老项目单模块完整改造": "标准流程",
    "老项目简单多模块改造": "标准流程",
    "老项目复杂多模块改造": "深度流程",
}


def scope_cap_for_task(task_scope: TaskScope) -> Tier | None:
    """Return the maximum default tier for a bounded task scope."""
    if task_scope in TASK_SCOPE_CAPS:
        return TASK_SCOPE_CAPS[task_scope]
    return None


def requires_full_reconfirmation(previous: Tier, routed: Tier) -> bool:
    """A deep-to-full route change must return to full-flow confirmation."""
    return previous != "完整流程" and routed == "完整流程"


def normalize_unknown(value: int | None, *, critical: bool = False) -> int | None:
    if value is None:
        return None
    return value


def score_band(total: int) -> ScoreBand:
    if not 0 <= total <= 100:
        raise ValueError("total must be in the range 0..100")
    if total <= 35:
        return "轻量流程"
    if total <= 69:
        return "标准流程"
    if total <= 89:
        return "深度流程"
    return "完整流程候选"


def route_tier(
    scores: tuple[int, int, int, int, int],
    *,
    deep_gate: bool = False,
    full_gate: bool = False,
    critical_unknown: bool = False,
    scope_cap: Tier | None = None,
    task_scope: TaskScope | None = None,
    user_requested: Tier | None = None,
) -> Tier:
    if len(scores) != 5 or any(score not in range(0, 21) for score in scores):
        raise ValueError("scores must contain five values in the range 0..20")
    if user_requested is not None and user_requested not in TIER_ORDER:
        raise ValueError(f"unknown user-requested tier: {user_requested}")
    if scope_cap is not None and scope_cap not in TIER_ORDER:
        raise ValueError(f"unknown scope cap: {scope_cap}")
    if task_scope is not None and task_scope not in TASK_SCOPE_CAPS and task_scope not in {
        "跨模块功能",
        "新UI壳或高保真还原",
        "新项目或项目级改造",
    }:
        raise ValueError(f"unknown task scope: {task_scope}")
    if scope_cap is None and task_scope is not None:
        scope_cap = scope_cap_for_task(task_scope)
    complex_scope = task_scope == "老项目复杂多模块改造"
    if complex_scope:
        deep_gate = True

    total = sum(scores)
    project_scope = task_scope == "新项目或项目级改造"
    if full_gate or project_scope:
        routed: Tier = "完整流程"
    elif deep_gate or critical_unknown:
        routed = "深度流程"
    else:
        band = score_band(total)
        if band == "轻量流程":
            routed = "轻量流程"
        elif band == "标准流程":
            routed = "标准流程"
        else:
            routed = "深度流程"

    if (
        scope_cap is not None
        and not deep_gate
        and not critical_unknown
        and not full_gate
        and not project_scope
        and TIER_ORDER[routed] > TIER_ORDER[scope_cap]
    ):
        routed = scope_cap

    if user_requested is None:
        return routed
    if user_requested == "完整流程":
        return "完整流程"
    if full_gate or project_scope:
        return "完整流程"
    if (
        (deep_gate or critical_unknown)
        and TIER_ORDER[user_requested] < TIER_ORDER["深度流程"]
    ):
        return "深度流程"
    if (
        scope_cap is not None
        and not deep_gate
        and not critical_unknown
        and TIER_ORDER[user_requested] > TIER_ORDER[scope_cap]
    ):
        return scope_cap
    return user_requested


def markdown_subsection(text: str, heading: str) -> str:
    marker = f"### {heading}"
    start = text.find(marker)
    if start < 0:
        return ""
    body_start = start + len(marker)
    match = re.search(r"(?m)^###? ", text[body_start:])
    if match is None:
        return text[body_start:]
    return text[body_start : body_start + match.start()]


def parse_markdown_table_row(line: str) -> list[str]:
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [cell.strip() for cell in inner.split("|")]


def score_table_failures(text: str) -> list[str]:
    failures: list[str] = []
    expected_dimensions = [
        "项目现状",
        "修改规模",
        "依赖影响",
        "风险回滚",
        "验证复杂度",
    ]
    expected_header = ["维度", "0–4 分", "5–8 分", "9–14 分", "15–20 分"]
    lines = text.splitlines()
    table_start = -1

    for index, line in enumerate(lines):
        if parse_markdown_table_row(line) == expected_header:
            table_start = index
            break

    if table_start < 0 or table_start + 1 >= len(lines):
        return ["修改前评分表缺少精确表头：维度 / 0–4 分 / 5–8 分 / 9–14 分 / 15–20 分。"]

    separator = parse_markdown_table_row(lines[table_start + 1])
    if len(separator) != len(expected_header) or not all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in separator
    ):
        failures.append("修改前评分表分隔行格式不合法。")

    rows: list[list[str]] = []
    for line in lines[table_start + 2 :]:
        if not line.strip().startswith("|"):
            break
        rows.append(parse_markdown_table_row(line))

    row_by_dimension = {row[0]: row for row in rows if row}
    for dimension in expected_dimensions:
        row = row_by_dimension.get(dimension)
        if row is None:
            failures.append(f"修改前评分表缺少维度：{dimension}。")
            continue
        if len(row) != 5 or any(not cell for cell in row[1:]):
            failures.append(f"修改前评分表维度 `{dimension}` 必须有完整的 0–20 分定义。")

    return failures


def markdown_link_failures(
    rel: str,
    text: str,
    *,
    root: Path = ROOT,
) -> list[str]:
    failures: list[str] = []
    source = root / rel

    for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", text):
        raw_target = match.group(1).strip().strip("<>")
        target = raw_target
        if (
            not target
            or target.startswith("#")
            or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", target)
            or target.startswith("mailto:")
        ):
            continue

        path_part = unquote(target.split("#", 1)[0])
        if not path_part:
            continue
        candidate = Path(path_part)
        if not candidate.is_absolute():
            candidate = source.parent / candidate
        if not candidate.exists():
            line_no = text.count("\n", 0, match.start()) + 1
            failures.append(
                f"{rel}:{line_no}: local Markdown link target does not exist: {target}"
            )

    return failures


def html_anchor_failures(rel: str, text: str) -> list[str]:
    failures: list[str] = []
    anchors = set(re.findall(r'\b(?:id|name)=["\']([^"\']+)["\']', text))

    for match in re.finditer(r'href=["\']#([^"\']+)["\']', text):
        anchor = match.group(1)
        if anchor and anchor not in anchors:
            line_no = text.count("\n", 0, match.start()) + 1
            failures.append(f"{rel}:{line_no}: HTML anchor does not exist: #{anchor}")

    return failures


def version_failures(loaded: dict[str, str]) -> list[str]:
    required_markers = {
        "README.md": [f"版本：`{CURRENT_VERSION}`", f"## {CURRENT_VERSION} "],
        "docs/技能设计文档.md": [f"liran-plan {CURRENT_VERSION}"],
        "SKILL.md": [CURRENT_VERSION],
        "references/使用教程-常用提示词清单.md": [
            f"{CURRENT_VERSION} 核心"
        ],
        "references/liran-plan-使用教程.html": [
            f"{CURRENT_VERSION} 四档自适应"
        ],
        "references/plan-docs-使用教程.html": [
            f"{CURRENT_VERSION} 四档自适应"
        ],
    }
    failures: list[str] = []

    for rel, markers in required_markers.items():
        text = loaded.get(rel, "")
        for marker in markers:
            if marker not in text:
                failures.append(f"{rel}: current version marker missing: {marker}")

    return failures


def global_installation_failures(
    codex_home: Path,
    *,
    root: Path = ROOT,
) -> list[str]:
    failures: list[str] = []
    expected_root = root.resolve()

    for name in ("liran-plan", "plan-docs"):
        link = codex_home / "skills" / name
        if not link.is_symlink():
            failures.append(f"global skill link is missing or not a symlink: {link}")
            continue
        if link.resolve() != expected_root:
            failures.append(
                f"global skill link points to {link.resolve()}, expected {expected_root}"
            )

    prompt = codex_home / "prompts" / "liran-plan.md"
    if not prompt.is_file():
        failures.append(f"global slash prompt is missing: {prompt}")
    else:
        prompt_text = prompt.read_text(encoding="utf-8")
        if CURRENT_VERSION not in prompt_text:
            failures.append(
                f"global slash prompt must contain current version {CURRENT_VERSION}: {prompt}"
            )
        for phrase in (
            "0–35",
            "36–69",
            "70–89",
            "90–100",
            "轻量流程",
            "标准流程",
            "深度流程",
            "完整流程",
            "一个 Codex 单选框",
            "`request_user_input` 可用时必须实际调用",
            "用户选择后，必须在同一轮",
            "一个独立 Markdown 代码块",
            "目标矩阵固定",
            "等待外部输入",
            "--goal-transition-file",
            "选项一：",
            "老项目单文件局部修改最高轻量",
            "新项目和项目级改造才进入完整",
            "UI 五路线选择项",
            "原生选择框每题最多 3 项",
            "继续选择外部 AI、Stitch 或内嵌模型路线",
            "OpenCodex 本地路由",
            "当前会话内",
            "不维护固定模型白名单",
            "不新增强制模型选择框",
            "具体项目修改任务",
            "PRD 草稿",
            "PRD 需求文档",
            "唯一闭环顺序",
            "需求整理好了吗？整理好了的话，请回复‘需求整理好了’",
            "正式 PRD 没问题吗？没问题的话，请回复‘PRD 没问题’；需要修改请说明修改点。",
            "固定 22 章结构",
            "正式 PRD 待确认",
            "用户指定 → AGENTS.md → 03-索引.md",
            "正式 PRD 转换完成后必须完成五维评分",
            "修改前总分",
            "评分证据",
            "归档受阻",
            "中间目标禁止归档",
            "本次任务已完成并归档",
        ):
            if phrase not in prompt_text:
                failures.append(f"global slash prompt missing phrase `{phrase}`: {prompt}")
        failures.extend(
            full_flow_confirmation_failures(
                str(prompt),
                prompt_text,
            )
        )
        prompt_options = (
            PAGE_OPTIONS[:3]
            + NON_PAGE_OPTIONS[:2]
            + DEEP_PAGE_OPTIONS[:3]
            + DEEP_NON_PAGE_OPTIONS[:2]
            + FULL_FLOW_OPTIONS
            + UI_ROUTE_OPTIONS
        )
        if not all(option in prompt_text for option in prompt_options):
            failures.append(f"global slash prompt does not contain all 17 prompt options: {prompt}")
        if re.search(r"(?<![/\d])\d{1,2}/10(?![/\d])", prompt_text):
            failures.append(f"global slash prompt still contains a 0-10 score example: {prompt}")

    return failures


def full_flow_confirmation_failures(rel: str, text: str) -> list[str]:
    """Validate formal-PRD confirmation and the consolidated acceptance choices."""
    visible_text = re.sub(r"(?ms)^```[^\n]*\n.*?^```\s*$", "", text)
    visible_text = re.sub(r"(?is)<pre[^>]*>.*?</pre>", "", visible_text)
    boundary_normalized = re.sub(
        r"</(?:pre|p|div|li|section)>",
        "\n\n",
        visible_text,
        flags=re.IGNORECASE,
    )
    normalized = re.sub(r"\s+", " ", boundary_normalized).replace("`", "")
    has_legacy_summary = bool(re.search(r"详细(?:的需求整理)?总结", normalized))
    has_formal_prd_confirmation = "正式 PRD" in normalized and "PRD 没问题" in normalized
    if not has_legacy_summary and not has_formal_prd_confirmation:
        return [f"{rel}: S26 full-flow PRD/summary confirmation is missing"]
    required = (
        "同一个",
        FULL_FLOW_OPTIONS[0],
        FULL_FLOW_OPTIONS[1],
    )
    missing = [phrase for phrase in required if phrase not in normalized]
    if missing:
        return [f"{rel}: S26 full-flow summary confirmation is missing: {', '.join(missing)}"]
    return []


def pressure_failures(loaded: dict[str, str]) -> list[str]:
    failures: list[str] = []

    failures.extend(
        f"lifecycle sequence: {failure}"
        for failure in lifecycle_sequence_failures(loaded.get("SKILL.md", ""))
    )
    failures.extend(
        f"option gate: {failure}"
        for failure in option_stage_failures(loaded.get("SKILL.md", ""))
    )

    for rel in (
        "SKILL.md",
        "README.md",
        "docs/技能设计文档.md",
        "references/四档自适应流程.md",
        "references/提示词向导.md",
        "references/功能3-高保真原型.md",
        "references/功能5-任务微观化与提示词.md",
        "references/功能6-真机实测与回写.md",
        "references/使用教程-常用提示词清单.md",
        "references/liran-plan-使用教程.html",
        "references/plan-docs-使用教程.html",
    ):
        if re.search(r"(?<![/\d])\d{1,2}/10(?![/\d])", loaded.get(rel, "")):
            failures.append(f"score contract: active document still uses a 0-10 score example: {rel}")

    skill_contract = loaded.get("SKILL.md", "")
    for phrase in (
        "同时新增三个或以上独立功能模块",
        "大规模数据或技术栈迁移",
        "多个大型模块同时改造",
        "用户明确要求完整流程",
    ):
        if phrase not in skill_contract:
            failures.append(f"full-flow gate: SKILL.md is missing project-level condition: {phrase}")

    routing_cases = [
        ("S01", (2, 2, 3, 2, 3), {}, "轻量流程"),
        ("S02", (7, 8, 8, 7, 7), {}, "标准流程"),
        ("S03", (6, 7, 8, 7, 8), {"deep_gate": True}, "深度流程"),
        ("S04", (14, 14, 14, 14, 14), {"full_gate": True}, "完整流程"),
        (
            "S06",
            (4, 4, 4, 14, 4),
            {"deep_gate": True, "user_requested": "轻量流程"},
            "深度流程",
        ),
        ("S10", (7, 8, 8, 7, 7), {}, "标准流程"),
        ("S11", (7, 8, 7, 6, 8), {"deep_gate": True}, "深度流程"),
    ]
    for scenario, scores, kwargs, expected in routing_cases:
        actual = route_tier(scores, **kwargs)
        if actual != expected:
            failures.append(
                f"{scenario}: expected {expected}, got {actual} for scores {scores}"
            )

    expected_bands: dict[int, ScoreBand] = {
        0: "轻量流程",
        35: "轻量流程",
        36: "标准流程",
        69: "标准流程",
        70: "深度流程",
        89: "深度流程",
        90: "完整流程候选",
        100: "完整流程候选",
    }
    for total, expected in expected_bands.items():
        actual = score_band(total)
        if actual != expected:
            failures.append(
                f"score band: total {total} expected {expected}, got {actual}"
            )
    if route_tier((18, 18, 18, 18, 18)) != "深度流程":
        failures.append(
            "full candidate without project-level semantics must use deep execution"
        )
    if (
        route_tier((4, 5, 5, 4, 5), user_requested="轻量流程")
        != "轻量流程"
    ):
        failures.append("user override: lower tier must be accepted without a hard gate")
    if (
        route_tier(
            (2, 2, 2, 2, 2),
            scope_cap="标准流程",
            user_requested="完整流程",
        )
        != "完整流程"
    ):
        failures.append("user override: explicit full workflow must bypass a small-task cap")

    scoped_routes = {
        "老项目单文件局部修改": "轻量流程",
        "老项目单模块小功能": "标准流程",
        "老项目单模块完整改造": "标准流程",
        "老项目简单多模块改造": "标准流程",
        "老项目复杂多模块改造": "深度流程",
    }
    for task_scope, expected_cap in scoped_routes.items():
        if scope_cap_for_task(task_scope) != expected_cap:
            failures.append(f"scope cap: {task_scope} must cap at {expected_cap}")
    if scope_cap_for_task("跨模块功能") is not None:
        failures.append("scope cap: legacy cross-module alias must remain uncapped")
    if scope_cap_for_task("新项目或项目级改造") is not None:
        failures.append("scope cap: project-level work must use the full-flow gate")
    if not requires_full_reconfirmation("深度流程", "完整流程"):
        failures.append("S22: deep-to-full upgrade must require full-flow reconfirmation")
    if requires_full_reconfirmation("标准流程", "深度流程"):
        failures.append("S22: standard-to-deep upgrade must not require full-flow reconfirmation")

    if normalize_unknown(None) is not None or normalize_unknown(None, critical=True) is not None:
        failures.append("S05: unknown evidence must remain unscored until investigated")
    if route_tier((0, 0, 12, 0, 0), critical_unknown=True) != "深度流程":
        failures.append("S05: critical unknown must enforce a deep minimum route")
    if route_tier((18, 18, 18, 18, 18)) != "深度流程":
        failures.append("S30: score 90 without a project gate must use deep execution")
    if route_tier((4, 4, 4, 4, 4), full_gate=True) != "完整流程":
        failures.append("S31: a confirmed project-level full gate must allow full execution below 90")
    try:
        route_tier((0, 0, 0, 0, 0), user_requested="快速流程")
    except ValueError:
        pass
    else:
        failures.append("user override: unknown tier labels must be rejected")

    pre_route = route_tier((7, 8, 8, 7, 7))
    post_route = route_tier((12, 14, 15, 12, 18))
    if (pre_route, post_route) != ("标准流程", "深度流程"):
        failures.append(
            f"S07: expected 标准流程 -> 深度流程, got {pre_route} -> {post_route}"
        )

    tracking = loaded.get("templates/04-开发追踪.md", "")
    if "内部测试通过 → 待用户验收 → 用户验收通过 → 待用户检查 → 待归档确认 → 归档中 → 已归档 → 已完成" not in tracking:
        failures.append("S08: manual acceptance state transition is incomplete")

    lifecycle_contracts = {
        "SKILL.md": (
            "具体项目修改任务",
            "需求整理文档",
            "本轮新增、变更、确认、待确认项和真实路径",
            "归档受阻",
            "本次任务已完成并归档",
        ),
        "references/四档自适应流程.md": (
            "4.9 需求整理文档、正式 PRD 与归档门禁",
            "所有中间目标禁止归档",
            "其他活动任务未受影响",
        ),
        "references/提示词向导.md": (
            "4.9 需求整理文档与正式 PRD",
            "只回复本轮新增、变更、待确认点和真实路径",
            "历史",
            "按任务 ID 清理活动区",
        ),
    }
    for rel, phrases in lifecycle_contracts.items():
        text = loaded.get(rel, "")
        for phrase in phrases:
            if phrase not in text:
                failures.append(f"S40-S49: {rel} missing lifecycle contract: {phrase}")

    ui_doc = loaded.get("references/功能3-高保真原型.md", "")
    if "轻量流程" not in ui_doc or "不创建完整 UI 壳" not in ui_doc:
        failures.append("S09: light UI work must not create a full UI shell")
    if "单页面或单组件调整" not in ui_doc or "不走完整五路线" not in ui_doc:
        failures.append("S10: standard single-page work must avoid the full UI route")
    if "新页面、复杂状态、跨页面交互、UI 与业务联动" not in ui_doc:
        failures.append("S11: deep UI triggers are incomplete")
    if "不检查页面样式是否符合方案" not in ui_doc:
        failures.append("S12: real-device testing without visual comparison is missing")
    for phrase in (
        "Stitch 路线不调用 Product Design Design QA",
        "可以进入实例级细节复修",
        "初次承接受阻",
        "复修通过后才允许生成业务接线 /goal",
        "其他 Product Design 路线仍保留 Design QA",
    ):
        if phrase not in ui_doc:
            failures.append(f"S13: Stitch repair gate missing: {phrase}")

    adaptive_doc = loaded.get("references/四档自适应流程.md", "")
    if "Stitch 复修在所有档位和全权托管中都不得跳过" not in adaptive_doc:
        failures.append("S13: unattended mode must not bypass Stitch repair")

    option_sections = {
        "涉及页面的轻量和标准流程": PAGE_OPTIONS,
        "不涉及页面的轻量和标准流程": NON_PAGE_OPTIONS,
        "涉及页面的深度流程": DEEP_PAGE_OPTIONS,
        "不涉及页面的深度流程": DEEP_NON_PAGE_OPTIONS,
    }
    for rel in ("references/四档自适应流程.md", "references/提示词向导.md"):
        guide = loaded.get(rel, "")
        for heading, options in option_sections.items():
            section = markdown_subsection(guide, heading)
            if not section:
                failures.append(f"S15: confirmation section missing from {rel}: {heading}")
                continue
            for option in options:
                if option not in section and option not in section.replace("`", ""):
                    failures.append(
                        f"S15: exact confirmation option missing from {rel} [{heading}]: {option}"
                    )
    if any("推荐" in option for option in PAGE_OPTIONS + NON_PAGE_OPTIONS):
        failures.append("S15: confirmation options must not contain 推荐")
    actionable_options = (
        PAGE_OPTIONS[:3]
        + NON_PAGE_OPTIONS[:2]
        + DEEP_PAGE_OPTIONS[:3]
        + DEEP_NON_PAGE_OPTIONS[:2]
        + FULL_FLOW_OPTIONS
        + UI_ROUTE_OPTIONS
    )
    wrapper_failures = option_wrapper_failures(actionable_options, expected_count=17)
    failures.extend(f"S36: {failure}" for failure in wrapper_failures)
    reroute_options = NON_PAGE_OPTIONS[2:] + DEEP_NON_PAGE_OPTIONS[2:]
    if any(
        OPTION_SKILL_PREFIX in option or OPTION_DETAIL_SUFFIX in option
        for option in reroute_options
    ):
        failures.append("S36: reroute options must not carry option-only wrappers")
    for rel, text in loaded.items():
        if rel.startswith("templates/") and (
            OPTION_SKILL_PREFIX in text or OPTION_DETAIL_SUFFIX in text
        ):
            failures.append(f"S36: formal prompt template must not contain option-only wrappers: {rel}")

    full_option_files = (
        "SKILL.md",
        "README.md",
        "docs/技能设计文档.md",
        "references/提示词向导.md",
        "references/使用教程-常用提示词清单.md",
        "references/模式-新项目引导.md",
        "references/模式-老项目初始化.md",
        "references/liran-plan-使用教程.html",
        "references/plan-docs-使用教程.html",
    )
    for rel in full_option_files:
        text = loaded.get(rel, "").replace("`", "")
        if not all(option in text for option in FULL_FLOW_OPTIONS):
            failures.append(f"S36: full-flow acceptance options are not synchronized in {rel}")

    ui_option_files = (
        "SKILL.md",
        "README.md",
        "references/提示词向导.md",
        "references/功能3-高保真原型.md",
        "references/使用教程-常用提示词清单.md",
        "references/liran-plan-使用教程.html",
        "references/plan-docs-使用教程.html",
    )
    for rel in ui_option_files:
        text = loaded.get(rel, "").replace("`", "")
        if not all(option in text for option in UI_ROUTE_OPTIONS):
            failures.append(f"S36: UI route options are not synchronized in {rel}")
        if "@product-design + 外部 AI 生成前端 UI" not in text or "@product-design + Codex 内嵌 Gemini 或其他生成的好看的模型生成前端 UI" not in text:
            failures.append(f"S36: external AI and Codex embedded-model UI routes must both be explicit in {rel}")
        if "OpenCodex 本地路由" not in text or "当前会话内" not in text:
            failures.append(f"S36: Codex embedded-model route semantics are missing in {rel}")
        if "不维护固定模型白名单" not in text or "不新增强制模型选择框" not in text:
            failures.append(f"S36: embedded-model route must avoid a fixed allowlist and forced selector in {rel}")

    ui_route_doc = loaded.get("references/提示词向导.md", "")
    for option in UI_ROUTE_OPTIONS:
        if option not in ui_route_doc and option not in ui_route_doc.replace("`", ""):
            failures.append(f"S36: UI route prompt option missing detail suffix: {option}")

    feature_five = loaded.get("references/功能5-任务微观化与提示词.md", "")
    for phrase in (
        "深度非 UI：2 次",
        "深度 UI：3 次",
        "文档目标",
        "开发与验收目标",
    ):
        if phrase not in feature_five:
            failures.append(f"S16/S32: deep staged goal contract missing: {phrase}")

    skill = loaded.get("SKILL.md", "")
    if "以下完整结构只由完整流程默认创建" not in skill:
        failures.append(
            "S17: full documentation rules must be explicitly scoped away from light and standard workflows"
        )
    if "完整流程默认保留 UI 目标" not in skill or "客观不涉及 UI" not in skill:
        failures.append(
            "S20/S51: full workflow must define the UI default and non-UI skip branch"
        )

    deep_page_manual = DEEP_PAGE_OPTIONS[2]
    for rel in ("references/功能3-高保真原型.md", "references/功能6-真机实测与回写.md"):
        if deep_page_manual not in loaded.get(rel, ""):
            failures.append(
                f"S18: deep page manual-testing option missing from {rel}: {deep_page_manual}"
            )

    if (
        "深度流程中的 UI 壳与 Stitch" not in ui_doc
        or "独立 UI 目标" not in ui_doc
    ):
        failures.append(
            "S19: deep Stitch/high-fidelity work must use an independent UI goal"
        )

    adaptive = loaded.get("references/四档自适应流程.md", "")
    if (
        "事实证据与禁止幻觉" not in adaptive
        or "不得伪造已经读取" not in adaptive
        or "不得伪造测试通过" not in adaptive
        or "不得伪造真机操作" not in adaptive
    ):
        failures.append(
            "S21: adaptive workflow must forbid fabricated read, test, and real-device evidence"
        )
    if "升级到完整流程" not in adaptive or "切回完整流程需求确认" not in adaptive:
        failures.append(
            "S22: an in-flight upgrade to full workflow must define a safe confirmation handoff"
        )
    if "局部样式修复" not in ui_doc or "整页或整组件调整" not in ui_doc:
        failures.append(
            "S23: light local styling and standard page/component work need an explicit boundary"
        )
    if "完整流程的最后验收目标按已确认的验收责任分支" not in skill:
        failures.append(
            "S24: full-flow final goal must preserve Codex and user acceptance branches"
        )
    feature_six = loaded.get("references/功能6-真机实测与回写.md", "")
    if "最后目标按已确认的验收责任分支" not in feature_six:
        failures.append(
            "S24: feature six must preserve both final-goal acceptance owners"
        )
    if "已触发的 Design QA" not in ui_doc:
        failures.append(
            "S25: deep UI execution must not run Design QA when the QA branch was not triggered"
        )

    core_match = re.search(
        r"核心原则：(?P<body>.*?)底层原则：",
        skill,
        flags=re.DOTALL,
    )
    if core_match is not None:
        for line in core_match.group("body").splitlines():
            if (
                re.search(r"每轮.*完整.*需求", line)
                and not re.search(r"完整流程.*需求整理.*每轮", line)
            ):
                failures.append(
                    "S27: top-level core principle must scope full requirement summaries to the full workflow"
                )
                break

    other_entry = re.search(r"(?m)^6\. \*\*其他\*\*：(?P<body>.*)$", skill)
    if other_entry is not None:
        other_body = other_entry.group("body")
        if (
            re.search(r"多轮(?:需求)?整理", other_body)
            and not (
                re.search(r"按四档.*整理深度", other_body)
                and re.search(r"只有完整流程.*多轮整理", other_body)
            )
        ):
            failures.append(
                "S28: the other entry must route by score instead of forcing multi-round clarification"
            )

    confirmation_contract_files = (
        "SKILL.md",
        "references/提示词向导.md",
        "references/四档自适应流程.md",
    )
    for rel in confirmation_contract_files:
        text = loaded.get(rel)
        if text is None:
            continue
        if not all(
            phrase in text
            for phrase in (
                "`request_user_input`",
                "可用时必须实际调用",
                "选项一：",
                "纯文本",
            )
        ):
            failures.append(
                f"{rel}: S29 native Codex selector must be called when available"
            )
        if not all(
            phrase in text
            for phrase in (
                "收到选择结果后的同一轮",
                "不得等待用户再说",
            )
        ):
            failures.append(
                f"{rel}: S30 confirmed selection must auto-deliver the prompt in the same turn"
            )

    prompt_block_contract_files = (
        "SKILL.md",
        "references/提示词向导.md",
        "references/功能5-任务微观化与提示词.md",
    )
    for rel in prompt_block_contract_files:
        text = loaded.get(rel)
        if text is None:
            continue
        if not all(
            phrase in text
            for phrase in (
                "一个独立的 Markdown 代码块",
                "代码块内部不得嵌套三反引号",
            )
        ):
            failures.append(
                f"{rel}: S31 copyable prompt must use one complete fenced block"
            )

    expected_goal_sequences = {
        ("light", False): ("single",),
        ("standard", False): ("single",),
        ("deep", False): ("documentation", "development-and-acceptance"),
        ("deep", True): ("documentation", "ui", "development-and-acceptance"),
        ("full-docs", False): ("documentation", "development", "acceptance"),
        ("full-docs", True): ("documentation", "ui", "development", "acceptance"),
    }
    for (tier, ui_enabled), expected in expected_goal_sequences.items():
        if goal_sequence(tier, ui_goal_enabled=ui_enabled) != expected:
            failures.append(f"S50/S51: invalid goal sequence for {tier}, UI={ui_enabled}")
    if not should_enable_ui_goal("deep", has_ui=True):
        failures.append("S51: deep UI goal should be enabled")
    if should_enable_ui_goal("deep", has_ui=True, user_skips_ui=True):
        failures.append("S51: explicit UI skip must remove the deep UI goal")
    if should_enable_ui_goal("full-docs", has_ui=False):
        failures.append("S51: objective non-UI full work must not add a UI goal")

    for rel in ("SKILL.md", "references/四档自适应流程.md", "references/提示词向导.md"):
        text = loaded.get(rel, "")
        for phrase in ("第 N/M 次", "目标阶段", "等待外部输入"):
            if phrase not in text:
                failures.append(f"S52/S53: {rel} missing goal handoff contract: {phrase}")
        if "只有最后目标负责最终验收交接" not in text or "中间目标禁止归档" not in text:
            failures.append(f"S54: {rel} missing final-only archive contract")
        if "选项一：" not in text or "纯文本" not in text:
            failures.append(f"S55: {rel} missing plain-text confirmation fallback")

    unattended_contract = (
        "优先使用 `@Chrome`",
        "`@Chrome` 无法完成时自动切换 `@电脑`",
        "不得要求用户代为操作",
    )
    for rel in (
        "SKILL.md",
        "references/功能5-任务微观化与提示词.md",
        "references/功能6-真机实测与回写.md",
    ):
        text = loaded.get(rel)
        if text is not None and not all(phrase in text for phrase in unattended_contract):
            failures.append(
                f"{rel}: S33 goal must fall back from Chrome to Computer and must not hand executable work to the user"
            )

    delegation_contract = (
        "全权托管模式",
        "不再显示验收选择框",
        "只记录为 `受阻`",
    )
    for rel in (
        "SKILL.md",
        "references/提示词向导.md",
        "references/功能6-真机实测与回写.md",
    ):
        text = loaded.get(rel)
        if text is not None and not all(phrase in text for phrase in delegation_contract):
            failures.append(
                f"{rel}: S34 explicit full delegation must skip acceptance confirmation and never hand work back to the user"
            )

    self_test_override = "明确选择“我自己测试”时，以用户自测为准"
    for rel in (
        "SKILL.md",
        "references/提示词向导.md",
        "references/功能6-真机实测与回写.md",
    ):
        text = loaded.get(rel)
        if text is not None and self_test_override not in text:
            failures.append(
                f"{rel}: S35 explicit user self-test choice must override unattended defaults"
            )

    for rel in FULL_FLOW_CONFIRMATION_FILES:
        text = loaded.get(rel)
        if text is not None:
            failures.extend(full_flow_confirmation_failures(rel, text))

    runtime_contract_files = (
        "SKILL.md",
        "references/四档自适应流程.md",
        "references/提示词向导.md",
        "references/功能5-任务微观化与提示词.md",
        "references/功能6-真机实测与回写.md",
    )
    for rel in runtime_contract_files:
        text = loaded.get(rel)
        if text is None:
            continue
        if "流程合同" not in text or "档位执行门禁" not in text:
            failures.append(f"S36/S37: runtime contract headings missing from {rel}")
        if "真实 diff" not in text or "禁止编辑" not in text:
            failures.append(f"S37: real artifact diff and source edit lock missing from {rel}")
    skill_runtime = loaded.get("SKILL.md", "")
    if skill_runtime and ("workflow_prompt_failures()" not in skill_runtime or "--prompt-file" not in skill_runtime):
        failures.append("S36: real generated prompts must be checked through the runtime validator")
    if skill_runtime and ("FlowContract" not in skill_runtime or "没有修改后评分" not in skill_runtime or "真实 diff" not in skill_runtime):
        failures.append("S38: context recovery must persist FlowContract and evidence requirements")
    if skill_runtime and "canonical builder" not in skill_runtime:
        failures.append("S39: prompt-generating options must use one canonical builder")

    return failures


def fenced_status_failures(rel: str, text: str) -> list[str]:
    failures: list[str] = []
    fence_char: str | None = None
    for lineno, line in enumerate(text.splitlines(), start=1):
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker_char = match.group(1)[0]
            if fence_char is None:
                fence_char = marker_char
            elif fence_char == marker_char:
                fence_char = None
            continue
        if fence_char is not None and any(marker in line for marker in STATUS_MARKERS):
            failures.append(
                f"{rel}:{lineno}: workflow status marker must not be inside a fenced block"
            )
    return failures


def legacy_wording_failures(rel: str, text: str) -> list[str]:
    failures: list[str] = []
    for pattern in FORBIDDEN_FILE_PATTERNS.get(rel, []):
        match = re.search(pattern, text)
        if match:
            lineno = text.count("\n", 0, match.start()) + 1
            failures.append(
                f"{rel}:{lineno}: conflicting legacy wording matched: {pattern}"
            )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-global",
        action="store_true",
        help="also validate ~/.codex skill links and slash prompt",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        help="validate one real generated execution prompt before delivery",
    )
    parser.add_argument(
        "--prompt-tier",
        choices=tuple(RUNTIME_PROMPT_SEQUENCES),
        help="runtime tier used with --prompt-file",
    )
    parser.add_argument(
        "--prompt-kind",
        choices=PROMPT_KINDS,
        default="workflow",
        help="prompt validation route; specialist prompt kinds bypass the ordinary Goal contract",
    )
    parser.add_argument(
        "--archive-stage",
        choices=("non-final", "handoff", "archive", "final", "full-first"),
        help="override the archive stage inferred from --prompt-tier",
    )
    parser.add_argument(
        "--confirmation-file",
        type=Path,
        help="validate a JSON confirmation payload with question/options/prompt_generating",
    )
    parser.add_argument(
        "--artifact-file",
        action="append",
        default=[],
        help="concrete artifact path to audit before unlocking implementation (repeatable)",
    )
    parser.add_argument(
        "--changed-file",
        action="append",
        default=[],
        help="artifact path present in the real diff (repeatable)",
    )
    parser.add_argument(
        "--contract-file",
        type=Path,
        help="validate a serialized FlowContract during context recovery",
    )
    parser.add_argument(
        "--state-transition-file",
        type=Path,
        help="validate one serialized state transition with contract, target_state, event and evidence",
    )
    parser.add_argument(
        "--goal-transition-file",
        type=Path,
        help="validate one multi-goal handoff with contract, target_goal_index and event",
    )
    parser.add_argument(
        "--goal-reclaim-file",
        type=Path,
        help="validate one last ordinary-goal reclaim contract",
    )
    parser.add_argument(
        "--archive-contract-file",
        type=Path,
        help="validate one task-document archive lifecycle JSON snapshot",
    )
    parser.add_argument(
        "--prd-file",
        type=Path,
        help="validate one PRD draft or formal PRD document",
    )
    parser.add_argument(
        "--prd-status",
        choices=("draft", "formal"),
        help="expected PRD lifecycle status used with --prd-file",
    )
    parser.add_argument(
        "--prd-source-file",
        type=Path,
        help="optional chat-style requirement document used for formal PRD detail coverage audit",
    )
    parser.add_argument(
        "--score-file",
        type=Path,
        help="post-formal-PRD five-dimension score record used to unlock target generation",
    )
    parser.add_argument(
        "--requirements-file",
        type=Path,
        help="validate one chat-style requirement-gathering document",
    )
    parser.add_argument("--resume-tier", choices=tuple(RUNTIME_PROMPT_SEQUENCES))
    parser.add_argument("--post-score", type=int)
    parser.add_argument("--goal-count", type=int)
    parser.add_argument("--upgrade-evidence", action="append", default=[])
    parser.add_argument("--acceptance-owner")
    args = parser.parse_args(argv)

    failures: list[str] = []
    combined_parts: list[str] = []
    loaded: dict[str, str] = {}

    for rel in CHECK_FILES:
        path = ROOT / rel
        if not path.exists():
            failures.append(f"missing file: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        loaded[rel] = text
        combined_parts.append(text)
        failures.extend(fenced_status_failures(rel, text))
        if path.suffix == ".md":
            failures.extend(markdown_link_failures(rel, text))
        elif path.suffix == ".html":
            if not text.strip():
                failures.append(f"{rel}: HTML file is empty")
            failures.extend(html_anchor_failures(rel, text))

        for lineno, line in enumerate(text.splitlines(), start=1):
            if re.search(r"需求没问题.*推荐", line):
                failures.append(
                    f"{rel}:{lineno}: user-facing confirmation option must not contain 推荐"
                )

    checked_rel_paths = set(CHECK_FILES)
    for path in ROOT.rglob("*.md"):
        rel = path.relative_to(ROOT).as_posix()
        if rel in checked_rel_paths or ".git" in path.parts:
            continue
        failures.extend(markdown_link_failures(rel, path.read_text(encoding="utf-8")))

    for path in ROOT.rglob("*.html"):
        rel = path.relative_to(ROOT).as_posix()
        if rel in checked_rel_paths or ".git" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            failures.append(f"{rel}: HTML file is empty")
        failures.extend(html_anchor_failures(rel, text))

    for rel, phrases in FILE_REQUIRED_PHRASES.items():
        text = loaded.get(rel)
        if text is None:
            continue
        for phrase in phrases:
            if phrase not in text:
                failures.append(f"{rel}: required phrase missing: {phrase}")

    for rel in FORBIDDEN_FILE_PATTERNS:
        text = loaded.get(rel)
        if text is None:
            continue
        failures.extend(legacy_wording_failures(rel, text))

    combined = "\n".join(combined_parts)
    for phrase in REQUIRED_PHRASES:
        if phrase not in combined:
            failures.append(f"required phrase missing across adaptive-flow docs: {phrase}")

    scenario_text = loaded.get("references/四档自适应流程.md", "")
    for scenario in PRESSURE_SCENARIOS:
        if scenario not in scenario_text:
            failures.append(f"adaptive pressure scenario missing: {scenario}")
    failures.extend(pressure_failures(loaded))
    failures.extend(
        score_table_failures(loaded.get("references/四档自适应流程.md", ""))
    )
    failures.extend(version_failures(loaded))

    left_html = loaded.get("references/liran-plan-使用教程.html")
    right_html = loaded.get("references/plan-docs-使用教程.html")
    if left_html is not None and right_html is not None and left_html != right_html:
        failures.append("the two HTML tutorials must remain byte-for-byte identical")

    if args.check_global:
        failures.extend(global_installation_failures(Path.home() / ".codex"))

    if args.prompt_file is not None:
        if args.prompt_kind in {"workflow", "long"} and args.prompt_tier is None:
            failures.append("--prompt-file 必须同时提供 --prompt-tier。")
        elif not args.prompt_file.is_file():
            failures.append(f"真实提示词文件不存在：{args.prompt_file}")
        else:
            failures.extend(
                prompt_failures_for_kind(
                    args.prompt_file.read_text(encoding="utf-8"),
                    kind=args.prompt_kind,
                    tier=args.prompt_tier,
                    archive_stage=args.archive_stage,
                )
            )

    if args.requirements_file is not None:
        if not args.requirements_file.is_file():
            failures.append(f"需求整理文档不存在：{args.requirements_file}")
        else:
            if "需求整理" not in args.requirements_file.stem:
                failures.append("需求整理文档文件名必须包含“需求整理”，以免与正式 PRD 混淆。")
            failures.extend(
                requirements_gathering_document_failures(
                    args.requirements_file.read_text(encoding="utf-8")
                )
            )

    if args.prd_file is not None:
        if not args.prd_file.is_file():
            failures.append(f"PRD 文件不存在：{args.prd_file}")
        else:
            prd_text = args.prd_file.read_text(encoding="utf-8")
            if args.prd_source_file is not None or args.prd_status == "formal":
                failures.extend(
                    prd_conversion_failures(
                        prd_text,
                        source_path=args.prd_source_file,
                        score_path=args.score_file,
                        require_score=args.prd_source_file is not None,
                    )
                )
            else:
                failures.extend(
                    prd_document_failures(prd_text, expected_status=args.prd_status)
                )

    if args.confirmation_file is not None:
        if not args.confirmation_file.is_file():
            failures.append(f"确认载荷文件不存在：{args.confirmation_file}")
        else:
            try:
                payload = json.loads(args.confirmation_file.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("JSON 顶层必须是对象")
                question = payload.get("question")
                options = payload.get("options")
                descriptions = payload.get("descriptions")
                confirmation_kind = payload.get("confirmation_kind", "acceptance")
                option_actions = payload.get("option_actions")
                prompt_generating = payload.get("prompt_generating")
                fallback_text = payload.get("fallback_text")
                if not isinstance(question, str) or not isinstance(options, list) or not all(isinstance(item, str) for item in options) or not isinstance(descriptions, list) or not all(isinstance(item, str) and item.strip() for item in descriptions) or len(descriptions) != len(options) or confirmation_kind not in {"acceptance", "page", "non-page", "deep-page", "deep-non-page", "full-flow", "ui-route-primary", "ui-route-advanced"} or (option_actions is not None and (not isinstance(option_actions, list) or not all(isinstance(item, str) for item in option_actions))) or not isinstance(prompt_generating, bool):
                    raise ValueError("需要 question 字符串、options/descriptions 等长非空字符串数组、合法 confirmation_kind 和 prompt_generating 布尔值")
                failures.extend(
                    confirmation_delivery_failures(
                        question,
                        options,
                        descriptions=descriptions,
                        confirmation_kind=confirmation_kind,
                        option_actions=option_actions,
                        prompt_generating=prompt_generating,
                    )
                )
                if fallback_text is not None:
                    if not isinstance(fallback_text, str):
                        raise ValueError("fallback_text 必须是字符串")
                    failures.extend(text_confirmation_fallback_failures(fallback_text, options))
            except (json.JSONDecodeError, ValueError) as exc:
                failures.append(f"确认载荷 JSON 无效：{exc}")

    if args.artifact_file:
        if args.prompt_tier is None:
            failures.append("--artifact-file 必须同时提供 --prompt-tier。")
        else:
            failures.extend(
                runtime_artifact_failures(
                    args.prompt_tier,
                    args.artifact_file,
                    changed_paths=args.changed_file,
                )
            )

    if args.contract_file is not None:
        if not args.contract_file.is_file():
            failures.append(f"流程合同文件不存在：{args.contract_file}")
        else:
            try:
                contract = FlowContract.from_json(args.contract_file.read_text(encoding="utf-8"))
                failures.extend(
                    flow_contract_failures(
                        contract,
                        resumed_tier=args.resume_tier,
                        post_score=args.post_score,
                        upgrade_evidence=args.upgrade_evidence,
                        acceptance_owner=args.acceptance_owner,
                        goal_count=args.goal_count,
                    )
                )
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                failures.append(f"流程合同 JSON 无效：{exc}")

    if args.archive_contract_file is not None:
        path = args.archive_contract_file
        if not path.is_file():
            failures.append(f"归档合同文件不存在：{path}")
        else:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("JSON 顶层必须是对象")
                failures.extend(archive_lifecycle_failures(payload))
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                failures.append(f"归档合同 JSON 无效：{exc}")

    if args.state_transition_file is not None:
        path = args.state_transition_file
        if not path.is_file():
            failures.append(f"状态转换文件不存在：{path}")
        else:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("JSON 顶层必须是对象")
                contract_data = payload.get("contract")
                contract_path = payload.get("contract_file")
                if contract_data is None and contract_path:
                    contract_data = json.loads(Path(contract_path).read_text(encoding="utf-8"))
                if not isinstance(contract_data, dict):
                    raise ValueError("必须提供 contract 对象或 contract_file")
                contract = FlowContract.from_dict(contract_data)
                target_state = payload.get("target_state")
                event = payload.get("event")
                evidence = payload.get("evidence", [])
                if not isinstance(target_state, str) or not isinstance(event, str) or not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
                    raise ValueError("需要 target_state 字符串、event 字符串和 evidence 字符串数组")
                failures.extend(flow_transition_failures(contract, target_state=target_state, event=event, evidence=evidence))
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                failures.append(f"状态转换 JSON 无效：{exc}")

    if args.goal_transition_file is not None:
        path = args.goal_transition_file
        if not path.is_file():
            failures.append(f"目标交接文件不存在：{path}")
        else:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict) or not isinstance(payload.get("contract"), dict):
                    raise ValueError("必须提供 contract 对象")
                target_goal_index = payload.get("target_goal_index")
                event = payload.get("event")
                evidence = payload.get("evidence", [])
                if type(target_goal_index) is not int or not isinstance(event, str) or not isinstance(evidence, list) or not all(isinstance(item, str) for item in evidence):
                    raise ValueError("需要 target_goal_index 整数、event 字符串和 evidence 字符串数组")
                failures.extend(
                    goal_handoff_failures(
                        FlowContract.from_dict(payload["contract"]),
                        target_goal_index=target_goal_index,
                        event=event,
                        evidence=evidence,
                    )
                )
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                failures.append(f"目标交接 JSON 无效：{exc}")

    if args.goal_reclaim_file is not None:
        path = args.goal_reclaim_file
        if not path.is_file():
            failures.append(f"目标回收文件不存在：{path}")
        else:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict):
                    raise ValueError("JSON 顶层必须是对象")
                failures.extend(goal_reclaim_failures(payload))
            except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
                failures.append(f"目标回收 JSON 无效：{exc}")

    if failures:
        print("Adaptive workflow docs check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Adaptive workflow docs check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
