#!/usr/bin/env python3
"""Validate Codex UI flow docs against the latest real frontend UI-shell flow."""

from __future__ import annotations

import argparse
from pathlib import Path
import hashlib
import re
import sys


ROOT = Path(__file__).resolve().parents[1]

MULTI_AGENT_OPENING = "你自行判断本任务是否需要多智能体协作；如需开启，只允许一个主智能体统筹，任一时刻最多同时运行五个子代理，子代理完成后必须及时回收，回收后可按需启用新的子代理，禁止子代理继续派生代理。"

CHECK_FILES = [
    "SKILL.md",
    "README.md",
    "docs/技能设计文档.md",
    "references/功能3-高保真原型.md",
    "references/四档自适应流程.md",
    "references/功能6-真机实测与回写.md",
    "references/提示词向导.md",
    "references/模式-新项目引导.md",
    "references/模式-老项目初始化.md",
    "references/使用教程-常用提示词清单.md",
    "references/liran-plan-使用教程.html",
    "references/plan-docs-使用教程.html",
    "templates/10-UI壳接入清单.md",
    "templates/UI壳单项接入清单.md",
    "templates/Stitch-实例级细节复修提示词.md",
    "templates/Stitch-页面设计开发提示词.md",
    "docs/pitfalls/general.md",
]

STITCH_REPAIR_TEMPLATE = "templates/Stitch-实例级细节复修提示词.md"
STITCH_GENERATION_TEMPLATE = "templates/Stitch-页面设计开发提示词.md"
STITCH_REPAIR_ORIGINAL_BODY_SHA256 = "a717324baef13957d9ca07b45a6dfd8e30fcafaa255361127f73d757473c4f81"
STITCH_REPAIR_EXPANSION_MARKER = "\n十、完整视觉维度复修"
PROMPT_MIN_CHARS = 3000
PROMPT_MAX_CHARS = 10000
STITCH_GENERATION_PLACEHOLDER_RE = re.compile(r"\{[^{}\n]{1,80}\}")
STITCH_GENERATION_TITLE_RE = re.compile(r"^# .+\s—\sStitch 多页面设计提示词\s*$")
STITCH_GENERATION_REQUIRED_SECTIONS = [
    "额外设计约束：",
    "（0）视觉风格整体要清爽明亮",
    "（1）信息密度：",
    "（2）文字克制：",
    "（3）色彩纪律：",
    "（4）层级与留白：",
    "（5）一致性：",
    "（6）必须删除：",
    "（7）组件克制：",
    "（8）空白保护：",
    "## Stitch 任务边界",
    "## 一、项目上下文",
    "## 二、PC 端与移动端页面清单（必须分端逐一完成）",
    "## 三、统一设计系统（所有屏幕必须复用，但具体值由设计器自主确定）",
    "## 四、每个屏幕的详细设计要求",
    "## 五、端与页面类型补充要求",
    "## 六、Stitch 执行顺序",
    "## 七、交付给 Codex 的信息",
    "项目总页面数 = PC 端独立页面数 + 移动端独立页面数",
    "页面数量不设置固定上限或下限。",
    "不得遗漏，也不得自行增加",
    "可以分批生成",
    "最终必须覆盖完整页面清单",
    "Stitch 不负责预留接口",
    "Stitch Project Title",
    "Stitch Screen Name",
]
STITCH_GENERATION_FORBIDDEN_PHRASES = (
    "## 流程合同",
    "## 档位执行门禁",
    "第一步：自行分析",
    "第二步：产出以下内容",
    "# 高保真原型 · 通用提示词结构",
    "## 执行目标与不可提前收口协议",
    "NOT_STARTED",
    "INTERRUPTED",
)

STITCH_REPAIR_REQUIRED_SECTIONS = [
    MULTI_AGENT_OPENING,
    "请直接开始执行下面步骤。",
    "一、先自动定位文件",
    "二、视觉事实来源优先级",
    "三、修改前先做控件规格盘点",
    "四、一比一还原硬规则",
    "五、必须保真的实例级属性",
    "六、允许修改范围",
    "七、明确禁止",
    "八、验证要求",
    "九、完成后输出",
    "收口条件：",
    "十、完整视觉维度复修",
    "十一、项目微调与完整性门禁",
]

STITCH_REPAIR_VISUAL_DIMENSIONS = {
    "页面结构与布局": "布局",
    "尺寸与间距": "尺寸与间距",
    "字体与文本排版": "字体",
    "颜色和视觉样式": "颜色",
    "控件规格": "控件规格",
    "图片和视觉资源": "资源",
    "层级与组合关系": "层级",
    "状态表现": "状态",
    "响应式与不同视口": "响应式",
}

STITCH_REPAIR_RUNTIME_RULES = [
    "任一时刻最多同时运行五个子代理",
    "子代理完成后必须及时回收",
    "回收后可按需启用新的子代理",
    "控件规格是完整视觉保真的一个维度",
    "不能遮蔽页面结构",
    "微调只允许填充或替换项目事实",
    "不适用：当前 Stitch 原始产物中不存在该元素。",
    "不得删除对应规则、列表项或章节",
        "3000–10000",
    "一个独立 Markdown 代码块",
]

STITCH_INSTANCE_FORBIDDEN_CONTRACT_PHRASES = (
    "## 流程合同",
    "## 档位执行门禁",
    "流程档位：",
    "目标提示词数量：",
    "当前目标：第",
    "目标阶段：",
    "UI 路线：",
    "--archive-stage",
    "归档中",
)

STITCH_INSTANCE_ALLOWED_FACT_PREFIXES = (
    "项目名称：",
    "项目路径：",
    "Stitch Project Title：",
    "Stitch Project ID：",
    "Stitch Screen Name：",
    "Stitch Screen ID：",
    "Stitch Screen 映射：",
    "下载路径：",
    "HTML 样式来源文件：",
    "源码路径：",
    "真实入口：",
    "视口：",
    "主题：",
    "启动命令：",
    "构建命令：",
    "测试命令：",
    "验证命令：",
    "允许编辑文件：",
    "项目专属限制：",
)

STITCH_PAGE_COUNT_CONTRACT_FILES = (
    "SKILL.md",
    "references/功能3-高保真原型.md",
    "references/提示词向导.md",
    "references/使用教程-常用提示词清单.md",
    "templates/Stitch-页面设计开发提示词.md",
)

STITCH_PAGE_COUNT_REQUIRED_PHRASES = (
    "完整页面清单",
    "页面数量不设置固定上限或下限。",
    "不得遗漏，也不得自行增加",
    "可以分批生成",
    "最终必须覆盖完整页面清单",
    "项目总页面数 = PC 端独立页面数 + 移动端独立页面数",
)

STITCH_PAGE_COUNT_TOKEN = (
    r"(?:\d+\s*(?:[–—-]\s*\d+)?|"
    r"[一二三四五六七八九十百]+(?:至|到)[一二三四五六七八九十百]+)"
)

STITCH_FIXED_PAGE_COUNT_PATTERNS = (
    rf"首版.{{0,36}}{STITCH_PAGE_COUNT_TOKEN}\s*页",
    rf"(?:Stitch|页面|核心页面).{{0,36}}(?:控制在|限制为|最多|不超过|只生成).{{0,20}}{STITCH_PAGE_COUNT_TOKEN}\s*页",
)

DEPRECATED_PHRASES = [
    "geminimcp",
    "$gemini-pro",
    "$gemini-ui",
    "复杂界面用",
    "简单 UI 用",
    "UI 原型默认路线",
    "UI 原型可选 Gemini",
    "开始原型 html 设计",
    "原型 html 设计提示词",
    "原型确认后",
    "需求/交互修订",
    "单独生图分支",
    "生图分支",
    "第 8 阶段",
    "先生成视觉方案图再定文字方案",
    "直接生图",
    "Gemini MCP CLI",
    "@product-design + Gemini MCP CLI",
    "Codex UI 原型 html / Codex 直接优化",
    "生成原型 HTML",
    "调整已有原型 HTML",
    "从零生成原型 HTML",
    "原型 html 作为基线",
    "请让我选择三条 UI 路线：",
    "三路线造真实前端 UI 壳",
    "# 高保真原型 · 通用提示词结构",
    "第一步：自行分析",
    "第二步：产出以下内容",
    "claude-version",
    "Claude 版",
    "Claude Code",
    "双版本",
    "两个平行版本",
    "选哪个版本",
    "差异表",
    "codex-version/",
    "<code>$liran-plan",
]

FILE_REQUIRED_PHRASES = {
    "SKILL.md": [
        "页面结构与布局",
        "字体与文本排版",
        "图片和视觉资源",
        "3000–10000",
        "实例级复修提示词也必须保持 3000–10000 个字符",
        "不适用：当前 Stitch 原始产物中不存在该元素。",
    ],
    "references/功能3-高保真原型.md": [
        "控件规格只是其中一个维度",
        "不得删除任何固定词语",
        "3000–10000",
        "实例级复修提示词也必须保持 3000–10000 个字符",
    ],
    "references/提示词向导.md": [
        "控件规格不得遮蔽其他视觉维度",
        "项目微调只能填充或替换项目事实",
        "3000–10000",
        "实例级复修提示词也必须保持 3000–10000 个字符",
    ],
    "references/模式-新项目引导.md": [
        "90% 以上高还原",
        "布局主要结构",
        "字体字号",
        "所有可见前端元素",
        "按钮",
        "输入框",
        "输出框/结果区",
        "批量差异盘点",
        "实例级尺寸保真规则",
        "控件规格盘点",
        "表格",
    ],
    "references/模式-老项目初始化.md": [
        "90% 以上高还原",
        "布局主要结构",
        "字体字号",
        "所有可见前端元素",
        "按钮",
        "输入框",
        "输出框/结果区",
        "批量差异盘点",
        "实例级尺寸保真规则",
        "控件规格盘点",
        "表格",
    ],
    "templates/10-UI壳接入清单.md": [
        "实例级尺寸保真规则",
        "控件规格盘点",
        "第一事实来源是 Stitch 下载下来的 HTML",
        "Button / Input / Icon / Table",
        "页面数量不设置固定上限或下限",
        "最终必须覆盖完整页面清单",
    ],
    "templates/UI壳单项接入清单.md": [
        "事实来源优先级",
        "控件规格盘点",
        "表格 / 表头 / 单元格 / 筛选栏 / 操作列按钮",
        "尺寸保真检查",
        "完整视觉维度盘点",
        "固定正文与完整性门禁",
        "实例级复修提示词也必须保持 3000–10000 个字符",
    ],
}

REQUIRED_PHRASES = [
    "真实前端 UI 壳",
    "五条 UI 路线",
    "Codex 直接生成前端 UI 壳",
    "@product-design",
    "@product-design + 外部 AI 生成前端 UI",
    "@product-design + $Stitch / Stitch MCP",
    "@product-design + Codex 内嵌 Gemini 或其他生成的好看的模型生成前端 UI",
    "第五条路线",
    "不复制提示词到外部软件",
    "不维护固定模型白名单",
    "不新增强制模型选择框",
    "外部 AI 路线",
    "非 Stitch Design QA",
    "OpenCodex 本地路由",
    "当前会话内",
    "先确认文本视觉方案",
    "必要时确认视觉图",
    "文本视觉方案 + 视觉图 / 原型图",
    "视觉方案确认好了吗",
    "Stitch 专用提示词",
    "Stitch 多页面设计提示词",
    "额外设计约束",
    "templates/Stitch-页面设计开发提示词.md",
    "Stitch MCP",
    "Project ID",
    "Screen ID",
    "Stitch Project ID",
    "Stitch Screen ID",
    "Stitch Project Title",
    "Stitch Screen Name",
    "Stitch Screen 映射",
    "HTML 样式来源文件",
    "静态数据来源",
    "根据 Stitch MCP 下载下来的文件里的 HTML 样式一比一还原",
    "实例级尺寸保真规则",
    "实例级视觉规格保真",
    "控件规格盘点",
    "第一事实来源：Stitch 下载下来的 HTML",
    "第二事实来源：Stitch 下载下来的代码 / 样式 / MD 规范",
    "第三事实来源：Stitch 下载下来的截图",
    "事实来源优先级",
    "禁止自由发挥",
    "禁止只模仿大概风格",
    "禁止重新设计",
    "Stitch 已经生成好了样式",
    "Stitch HTML",
    "静态数据",
    "不提前对 Stitch 做额外限制",
    "不规定 Stitch 必须怎么写依赖",
    "Stitch 不负责预留接口",
    "视觉未对齐前",
    "禁止为了工程整洁",
    "老项目默认样式",
    "公共组件默认值",
    "局部作用域",
    "实例级覆盖",
    "官方 MCP",
    "$liran-image2",
    "禁止使用 $imagegen",
    "liran_docs/10-UI壳接入清单.md",
    "liran_docs/ui-shells/",
    "合法占位文件",
    "允许编辑文件清单",
    "外部 AI 输入包",
    "TODO(ui-shell)",
    "TODO(codex-connect)",
    "TODO(codex-state)",
    "TODO(codex-permission)",
    "TODO(codex-validate)",
    "TODO(codex-route)",
    "外部 AI 开工前就绪门禁",
    "Stitch 路线开工前就绪门禁",
    "只在 Codex 指定文件里",
    "不得自行新增、删除、移动、重命名文件",
    "样式默认只能在当前 UI 壳范围内生效",
    "默认禁止",
    "UI 壳接收检查",
    "接收检查不通过",
    "后续 development 目标",
    "真实 API 调用",
    "状态管理",
    "替换 mock 数据",
    "多屏",
    "页面 / 弹窗 / 抽屉 / 状态页 / 组件",
    "已有项目",
    "视觉图确认前不要把文本视觉草案写死进文档",
    "用户明确选择生图工具",
    "Design QA",
    "内置浏览器",
    "@Chrome",
    "@电脑",
    "QA 不通过",
    "90%",
    "QA 不能挤牙膏",
    "批量差异盘点",
    "整体布局",
    "比例",
    "页面密度",
    "容器尺寸",
    "位置",
    "对齐",
    "卡片",
    "弹窗",
    "面板",
    "dock",
    "工具栏",
    "字号",
    "字重",
    "行高",
    "颜色",
    "透明度",
    "边框",
    "圆角",
    "阴影",
    "P0",
    "P1",
    "P2",
    "P3",
    "P0 + P1",
    "没有 actionable P0/P1/P2",
    "design-qa.md",
    "同一张对比图",
    "局部放大对比",
    "五大保真面",
    "不能只改一个",
    "chrome://extensions",
    "刷新扩展",
    "popup",
    "side panel",
    "options page",
    "布局主要结构",
    "真实图片",
    "原型图",
    "字体字号",
    "细微差距",
    "所有可见前端元素",
    "按钮",
    "输入框",
    "输出框/结果区",
    "表单",
    "表格",
    "表头",
    "单元格",
    "筛选栏",
    "操作列按钮",
    "列表",
    "标签",
    "徽标",
    "导航",
    "菜单",
    "标签页",
    "面包屑",
    "图标",
    "图片",
    "头像",
    "Toast/提示",
    "分页",
    "进度条",
    "加载态",
    "空态",
    "错误态",
    "桌面端",
    "移动端",
    "状态变化",
    "响应式断点",
    "内容变多 / 变少",
    "响应式表现",
    "弹窗",
    "hover / focus / active / disabled / selected",
    "expanded / collapsed",
    "modal open / close",
    "panel switch",
    "screen switch",
    "尺寸保真检查",
    "实例级控件规格检查",
    "Button / Input / Icon / Table",
    "例外只能是实现路径例外",
]

IMAGEGEN_ALLOWED_CONTEXT = [
    "禁止使用 $imagegen",
    "禁止使用 `$imagegen`",
    "不要使用 `$imagegen`",
    "不要使用 $imagegen",
]


def line_allowed_for_imagegen(line: str) -> bool:
    return any(allowed in line for allowed in IMAGEGEN_ALLOWED_CONTEXT)


def contract_failures(loaded: dict[str, str]) -> list[str]:
    failures: list[str] = []
    ui_doc = loaded.get("references/功能3-高保真原型.md", "")
    early_contract = ui_doc.split("完整流程核心分工", 1)[0]
    deep_manual_option = "需求没问题，直接生成完整提示词，完成后我自己测试"
    obsolete_deep_option = "需求没问题，但让 Codex 重新判断是否需要深度流程"

    for phrase in (
        "局部样式修复",
        "整页或整组件调整",
        "新页面、复杂状态、跨页面交互、UI 与业务联动",
    ):
        if phrase not in early_contract:
            failures.append(f"功能三的四档 UI 分流缺少边界：{phrase}")

    if deep_manual_option not in early_contract:
        failures.append("功能三的深度页面选项缺少“完成后我自己测试”。")
    if obsolete_deep_option in early_contract:
        failures.append("功能三的深度页面仍保留旧的重新判断选项。")

    for rel in STITCH_PAGE_COUNT_CONTRACT_FILES:
        text = loaded.get(rel, "")
        for phrase in STITCH_PAGE_COUNT_REQUIRED_PHRASES:
            if phrase not in text:
                failures.append(f"{rel}: Stitch 完整页面清单规则缺少：{phrase}")
        for pattern in STITCH_FIXED_PAGE_COUNT_PATTERNS:
            match = re.search(pattern, text)
            if match:
                failures.append(
                    f"{rel}: Stitch 提示词仍保留固定页数限制：{match.group(0)}"
                )

    feature_six = loaded.get("references/功能6-真机实测与回写.md", "")
    if deep_manual_option not in feature_six:
        failures.append("功能六的深度页面验收分支缺少用户自己测试。")

    left_rel = "references/liran-plan-使用教程.html"
    right_rel = "references/plan-docs-使用教程.html"
    left_html = loaded.get(left_rel, "")
    right_html = loaded.get(right_rel, "")
    if left_html != right_html:
        failures.append("两份 HTML 教程内容不一致。")

    template = loaded.get(STITCH_REPAIR_TEMPLATE, "")
    for section in STITCH_REPAIR_REQUIRED_SECTIONS:
        if section not in template:
            failures.append(f"Stitch 强制复修提示词缺少固定正文：{section}")
    if template:
        template_length = len(template)
        if template_length < PROMPT_MIN_CHARS or template_length > PROMPT_MAX_CHARS:
            failures.append(
                f"Stitch 实例级复修固定模板必须保持 3000–10000 个字符：{template_length}"
            )
        if STITCH_REPAIR_EXPANSION_MARKER not in template:
            failures.append("Stitch 强制复修提示词缺少增量补强标记。")
        else:
            original_body = template.split(STITCH_REPAIR_EXPANSION_MARKER, 1)[0]
            digest = hashlib.sha256(original_body.encode("utf-8")).hexdigest()
            if digest != STITCH_REPAIR_ORIGINAL_BODY_SHA256:
                failures.append("Stitch 强制复修提示词的原固定正文已被删除或改写。")

        if re.search(r"2000\s*[–—-]\s*(?:5000|8000)", template):
            failures.append(
                "Stitch 实例级复修提示词不得残留旧版字数限制。"
            )

        for phrase, label in STITCH_REPAIR_VISUAL_DIMENSIONS.items():
            if phrase not in template:
                failures.append(f"Stitch 强制复修提示词缺少{label}视觉维度：{phrase}")
        for phrase in STITCH_REPAIR_RUNTIME_RULES:
            if phrase not in template:
                label = (
                    "控件规格不能遮蔽其他视觉维度"
                    if phrase.startswith("控件规格") or "遮蔽" in phrase
                    else phrase
                )
                failures.append(f"Stitch 强制复修提示词缺少运行时门禁：{label}")

    stitch_contract_files = (
        "SKILL.md",
        "references/功能3-高保真原型.md",
        "references/四档自适应流程.md",
        "references/提示词向导.md",
    )
    for rel in stitch_contract_files:
        text = loaded.get(rel, "")
        for phrase in (
            "可以进入实例级细节复修",
            "初次承接受阻",
            "复修通过后",
        ):
            if phrase not in text:
                failures.append(f"{rel}: Stitch 三段式门禁缺少：{phrase}")

    combined_stitch_contract = "\n".join(
        loaded.get(rel, "") for rel in stitch_contract_files
    )
    for forbidden in (
        "Stitch 和明确高保真任务必须 Design QA",
        "Stitch 一比一还原或用户明确要求高保真还原时，不提供跳过页面样式检查的选项",
        "使用 Stitch，或用户明确要求高保真还原",
    ):
        if forbidden in combined_stitch_contract:
            failures.append(f"Stitch 路线仍残留 Product Design Design QA 门禁：{forbidden}")

    if "Product Design 路线仍保留 Design QA" not in combined_stitch_contract:
        failures.append("缺少其他 Product Design 路线仍保留 Design QA 的明确反向保护。")

    conditional_gate = "Design QA 已触发时，QA 不通过不能收口"
    for rel in (left_rel, right_rel):
        text = loaded.get(rel, "")
        if conditional_gate not in text:
            failures.append(f"{rel}: Design QA 教程缺少按触发条件生效的收口门禁。")
        remaining = text.replace(conditional_gate, "")
        if "QA 不通过不能收口" in remaining:
            failures.append(f"{rel}: 存在无条件 Design QA 收口门禁。")

    generation = loaded.get(STITCH_GENERATION_TEMPLATE, "")
    failures.extend(
        stitch_generation_prompt_failures(generation, allow_placeholders=True)
    )

    return failures


def extra_constraints_follow_title(text: str) -> bool:
    lines = text.splitlines()
    index = 0
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines) or STITCH_GENERATION_TITLE_RE.match(lines[index].strip()) is None:
        return False
    index += 1
    while index < len(lines) and not lines[index].strip():
        index += 1
    return index < len(lines) and lines[index].strip() == "额外设计约束："


def stitch_generation_prompt_failures(
    prompt: str,
    *,
    allow_placeholders: bool = False,
) -> list[str]:
    """Validate a Stitch page-generation prompt or its template."""
    if not prompt.strip():
        return ["Stitch 页面生成提示词不能为空。"]
    failures: list[str] = []
    if not extra_constraints_follow_title(prompt):
        failures.append("Stitch 页面生成提示词必须在一级标题后紧接额外设计约束原文。")
    for section in STITCH_GENERATION_REQUIRED_SECTIONS:
        if section not in prompt:
            failures.append(f"Stitch 页面生成提示词缺少固定结构：{section}")
    for phrase in STITCH_GENERATION_FORBIDDEN_PHRASES:
        if phrase in prompt:
            failures.append(f"Stitch 页面生成提示词不得包含：{phrase}")
    if not allow_placeholders:
        leftover = STITCH_GENERATION_PLACEHOLDER_RE.search(prompt)
        if leftover:
            failures.append(f"Stitch 页面生成提示词仍有未填占位符：{leftover.group(0)}")
    return failures


def stitch_instance_repair_prompt_failures(prompt: str) -> list[str]:
    """Validate a directly delivered Stitch instance-repair prompt.

    The fixed template is the immutable prefix. Project facts may be appended
    as labelled lines; workflow-contract fields and length limits are never
    part of this prompt type.
    """
    failures: list[str] = []
    template_path = ROOT / STITCH_REPAIR_TEMPLATE
    if not template_path.is_file():
        return [f"Stitch 实例级复修模板不存在：{STITCH_REPAIR_TEMPLATE}"]
    template = template_path.read_text(encoding="utf-8")
    template_prefix = template.rstrip("\n")
    if not prompt.startswith(template_prefix):
        failures.append("Stitch 实例级复修提示词必须以固定模板正文原样开头。")
    for section in STITCH_REPAIR_REQUIRED_SECTIONS:
        if section not in prompt:
            failures.append(f"Stitch 实例级复修提示词缺少固定正文：{section}")
    for phrase in STITCH_INSTANCE_FORBIDDEN_CONTRACT_PHRASES:
        if phrase in prompt:
            failures.append(
                f"Stitch 实例级复修提示词不得包含普通流程字段：{phrase}"
            )
    char_count = len(prompt)
    if char_count < PROMPT_MIN_CHARS:
        failures.append(f"Stitch 实例级复修提示词少于 {PROMPT_MIN_CHARS} 个字符：{char_count}")
    if char_count > PROMPT_MAX_CHARS:
        failures.append(f"Stitch 实例级复修提示词超过 {PROMPT_MAX_CHARS} 个字符：{char_count}")
    if re.search(r"2000\s*[–—-]\s*5000|2000\s*[–—-]\s*8000|不设置字数上限", prompt):
        failures.append("Stitch 实例级复修提示词必须使用统一 3000–10000 字符规则。")

    if prompt.startswith(template_prefix):
        facts = prompt[len(template_prefix):].lstrip("\n")
        for lineno, line in enumerate(facts.splitlines(), start=1):
            normalized = line.strip()
            if not normalized or normalized in {"项目事实：", "项目资料："}:
                continue
            if not any(normalized.startswith(prefix) for prefix in STITCH_INSTANCE_ALLOWED_FACT_PREFIXES):
                failures.append(
                    f"Stitch 实例级复修提示词包含未授权项目资料或额外正文（追加区第 {lineno} 行）。"
                )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prompt-file",
        type=Path,
        help="validate one directly delivered Stitch instance-repair prompt",
    )
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
        for phrase in DEPRECATED_PHRASES:
            if phrase in text:
                failures.append(f"{rel}: deprecated phrase still present: {phrase}")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if ("imagegen" in line or "$imagegen" in line) and not line_allowed_for_imagegen(line):
                failures.append(f"{rel}:{lineno}: imagegen mention is not clearly forbidden")

    for rel, phrases in FILE_REQUIRED_PHRASES.items():
        path = ROOT / rel
        if not path.exists():
            failures.append(f"missing file: {rel}")
            continue
        text = path.read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in text:
                failures.append(f"{rel}: required phrase missing: {phrase}")

    combined = "\n".join(combined_parts)
    for phrase in REQUIRED_PHRASES:
        if phrase not in combined:
            failures.append(f"required phrase missing across Codex docs: {phrase}")

    failures.extend(contract_failures(loaded))

    if args.prompt_file is not None:
        if not args.prompt_file.is_file():
            failures.append(f"提示词文件不存在：{args.prompt_file}")
        else:
            failures.extend(
                stitch_instance_repair_prompt_failures(
                    args.prompt_file.read_text(encoding="utf-8")
                )
            )

    if failures:
        print("Codex UI flow docs check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Codex UI flow docs check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
