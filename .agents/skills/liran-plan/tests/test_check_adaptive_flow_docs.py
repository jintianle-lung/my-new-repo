import re
import tempfile
import unittest
from contextlib import redirect_stdout
import io
import json
from pathlib import Path

from scripts import check_adaptive_flow_docs as adaptive


def load_current_docs() -> dict[str, str]:
    return {
        rel: (adaptive.ROOT / rel).read_text(encoding="utf-8")
        for rel in adaptive.CHECK_FILES
    }


class AdaptiveFlowValidatorTests(unittest.TestCase):
    def _valid_executable_prompt(self, *, filler: str = "") -> str:
        sections = [
            ("## 一、任务性质", "本次修复当前模块的已确认问题，不扩大到无关功能。"),
            ("## 二、当前场景", "这是老项目标准流程，前置需求与验收责任已确认。"),
            ("## 三、目标和完成结果", "完成局部修复、相关测试和文档回写，不声明未验证的结果。"),
            ("## 四、读取要求", "先读取 AGENTS.md、相关 liran_docs、源码、配置、测试和长期避坑记录。"),
            ("## 五、修改范围", "只修改已确认模块和直接测试，新文件、依赖和公共接口必须有证据。"),
            ("## 六、执行步骤", "依次调查、写失败测试、实现、局部验证、回写文档、检查最终 diff。"),
            ("## 七、业务与安全边界", "不改权限、认证、支付、数据库和删除逻辑，不编造外部事实。"),
            ("## 八、UI 专项要求", "不适用：当前任务不涉及 UI，因此不执行视觉承接。"),
            ("## 九、验证要求", "运行语法检查、相关单测、lint、typecheck 或构建，并检查 git diff。"),
            ("## 十、完成后输出", "列出读取文件、修改文件、逐文件变更、验证结果、风险与遗留事项。"),
            ("## 十一、收口条件", "只有范围内修改、相关测试、文档回写和 diff 审计都有证据时才收口。"),
        ]
        body = "\n\n".join(f"{title}\n{detail}" for title, detail in sections)
        return (
            adaptive.MULTI_AGENT_OPENING
            + "\n\n"
            + body
            + "\n"
            + (filler or "请在不扩大范围的前提下完成调查、修改、验证和回写。" * 100)
        )

    def _valid_workflow_prompt(self, tier: str) -> str:
        defaults = {
            "light": ("single", 1, 1),
            "standard": ("single", 1, 1),
            "deep": ("development-and-acceptance", 2, 2),
            "full-docs": ("documentation", 1, 3),
        }
        stage, index, count = defaults[tier]
        return self._valid_staged_workflow_prompt(
            tier, stage, index=index, count=count
        )

    def _valid_task_document(self, task_id: str = "TASK-1") -> str:
        return "\n".join(
            f"{field}：{task_id if field == '任务 ID' else '有效内容'}"
            for field in adaptive.TASK_DOCUMENT_REQUIRED_FIELDS
        )

    def _valid_staged_workflow_prompt(
        self,
        tier: str,
        stage: str,
        *,
        index: int,
        count: int,
        ui_goal_enabled: bool = False,
    ) -> str:
        sequences = {
            "single": (
                "依赖扫描完成", "失败测试已确认 RED", "编码解锁", "内部验证",
                "按已确认验收责任", "修改后评分",
            ),
            "documentation": (
                "受影响文档真实 diff", "全部微观任务写回", "开发追踪已更新",
                "验收准备已完成", "下一目标解锁",
            ),
            "ui": (
                "文本视觉方案已确认", "UI 壳已完成", "UI 壳接收检查",
                "视觉 QA 或 Stitch 复修", "下一目标解锁",
            ),
            "development": (
                "前置产物审计", "编码解锁", "TDD 实现", "内部验证回写",
                "内部测试通过", "下一目标解锁",
            ),
            "development-and-acceptance": (
                "前置产物审计", "编码解锁", "TDD 实现", "内部验证回写",
                "真机测试或待用户验收", "验收结果再次回写", "修改后评分",
            ),
            "acceptance": (
                "验收准备已完成", "真机测试或待用户验收", "验收结果再次回写",
                "修改后评分",
            ),
        }
        if tier == "standard" and stage == "single":
            sequences["single"] = (
                "持久化模块任务清单", "受影响文档真实 diff", "编码解锁",
                "TDD 实现", "内部验证回写", "按已确认验收责任",
                "验收结果再次回写", "修改后评分",
            )
        if tier == "full-docs" and stage == "documentation":
            sequences["documentation"] = (
                "完整文档体系真实 diff", "全部微观任务写回",
                "文档与任务产物审计", "下一目标解锁",
            )
        base_count = {"light": 1, "standard": 1, "deep": 2, "full-docs": 3}[tier]
        contract = "\n".join(
            [
                "## 流程合同",
                f"流程档位：{tier}",
                "修改前评分：60/100，并附真实证据。",
                f"基础目标数量：{base_count}",
                f"目标提示词数量：{count}",
                f"当前目标：第 {index}/{count} 次",
                f"目标阶段：{stage}",
                f"UI 目标：{'启用' if ui_goal_enabled else '跳过'}",
                f"UI 路线：{'pending' if ui_goal_enabled and stage == 'documentation' else 'product-design' if ui_goal_enabled else 'not-applicable'}",
                "等待外部输入：否",
                "验收责任：Codex 真机测试",
                "页面样式检查：不涉及页面",
                "当前阶段：提示词已解锁",
                "当前状态：提示词已解锁",
                "已完成门禁：已完成的前置检查。",
                "待完成门禁：当前目标阶段。",
                "允许下一动作：按顺序执行本阶段。",
                "禁止动作：跨入后续目标。",
                "需求总结已输出：是，已保存为可核对证据。",
                "需求总结已确认：是，用户已明确确认。",
                "验收责任已确认：是，已记录验收责任。",
                "提示词状态：校验通过",
                "真实产物审计：已完成，文件存在且有真实 diff。",
                "进入证据：已完成前置状态的文件和命令证据。",
                "阻塞原因：不适用。",
                "状态转换规则：只能按当前档位的合法下一状态推进。",
                "需求整理好了只能进入待详细总结确认，不能直接生成提示词。",
                "PRD 草稿已转换，正式 PRD 已输出，PRD 索引已更新。",
                "PRD 确认状态：PRD 没问题，已收到用户确认。",
                "目标状态：当前普通目标执行状态与项目任务状态分离。",
                "目标回收状态：active → reclaim_pending → reclaimed。",
                "目标完成证据：真实验收、问题回写、复测和修改后评分均已留证。",
                "用户检查通知证据：已发送固定用户检查通知。",
                "归档目标不计入普通 N/M。",
                "回收失败保持 reclaim_pending。",
                "编码解锁条件：前置产物全部通过真实文件审计。",
                "允许升级条件：只有修改后评分和新证据命中门禁时允许升级。",
                "上下文压缩后必须恢复本流程合同，不得重新猜测档位。",
                "没有修改后评分证据不得改变档位。",
            ]
        )
        gates = "\n".join(
            f"{number}. {phrase}：记录可核对的文件、命令和结果。"
            for number, phrase in enumerate(sequences[stage], start=1)
        )
        prompt = self._valid_executable_prompt()
        opening, remainder = prompt.split("\n\n", 1)
        prompt = f"{opening}\n\n{contract}\n\n## 档位执行门禁\n{gates}\n\n{remainder}"
        if stage in {"single", "development-and-acceptance", "acceptance"} and index == count:
            prompt += """

当前目标完成开发、测试、验收、问题回写和必要修复。
当前目标完成并已回收，goal_status=reclaimed。
项目状态：待用户检查。
资料归档状态：待归档确认。
用户检查期间不再执行当前目标。
当前目标暂不执行正式归档，不清理活动文档。
当前目标结束后进入待用户检查和待归档确认。
如果用户发现问题，回到问题回写、修复、测试和验收；如果用户提出新增需求或优化，回到需求整理或需求变更流程。
只有用户明确回复“归档”后才调用正式归档模板。
归档失败不得重新打开普通目标。
"""
        return prompt

    def test_executable_prompt_requires_multi_agent_opening_as_first_line(self):
        prompt = self._valid_executable_prompt()
        self.assertEqual([], adaptive.executable_prompt_failures(prompt))

        missing = prompt.replace(adaptive.MULTI_AGENT_OPENING + "\n\n", "", 1)
        failures = adaptive.executable_prompt_failures(missing)
        self.assertTrue(any("多智能体开头" in failure for failure in failures))

        moved = "请直接开始执行。\n" + prompt
        failures = adaptive.executable_prompt_failures(moved)
        self.assertTrue(any("第一行" in failure for failure in failures))

    def test_current_version_is_4_52(self):
        self.assertEqual("4.52", adaptive.CURRENT_VERSION)

    def test_prompt_kind_stitch_instance_repair_skips_workflow_contract(self):
        from scripts import check_codex_ui_flow_docs as ui_check

        template = (ui_check.ROOT / ui_check.STITCH_REPAIR_TEMPLATE).read_text(encoding="utf-8")
        prompt = template + "\n" + "\n".join(
            f"项目专属限制：事实 {index}" for index in range(100)
        )
        self.assertEqual(
            [],
            adaptive.prompt_failures_for_kind(
                prompt,
                kind="stitch-instance-repair",
            ),
        )

    def test_special_prompt_kinds_bypass_ordinary_goal_contract(self):
        from scripts import check_codex_ui_flow_docs as ui_check

        filled = ui_check.STITCH_GENERATION_PLACEHOLDER_RE.sub(
            "已填",
            (ui_check.ROOT / ui_check.STITCH_GENERATION_TEMPLATE).read_text(
                encoding="utf-8"
            ),
        )
        for kind in (
            "stitch-generation",
            "external-ai-ui",
            "product-design",
            "image-generation",
            "special-prompt",
        ):
            with self.subTest(kind=kind):
                prompt = (
                    filled
                    if kind == "stitch-generation"
                    else f"{kind} 专项提示词\n读取要求：按专项模板执行。"
                )
                self.assertEqual(
                    [],
                    adaptive.prompt_failures_for_kind(
                        prompt,
                        kind=kind,
                    ),
                )

    def test_special_prompt_kinds_reject_workflow_contract_and_wrappers(self):
        prompt = "## 流程合同\n$liran-plan 需求没问题，改完后执行。"
        for kind in (
            "stitch-generation",
            "external-ai-ui",
            "product-design",
            "image-generation",
            "special-prompt",
        ):
            with self.subTest(kind=kind):
                failures = adaptive.prompt_failures_for_kind(prompt, kind=kind)
                self.assertTrue(failures)

    def test_special_prompt_kinds_do_not_require_tier_in_cli(self):
        import tempfile
        from scripts import check_codex_ui_flow_docs as ui_check

        filled = ui_check.STITCH_GENERATION_PLACEHOLDER_RE.sub(
            "已填",
            (ui_check.ROOT / ui_check.STITCH_GENERATION_TEMPLATE).read_text(
                encoding="utf-8"
            ),
        )
        for kind in ("stitch-generation", "external-ai-ui", "product-design", "image-generation", "special-prompt"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp_dir:
                path = Path(tmp_dir) / f"{kind}.txt"
                body = (
                    filled
                    if kind == "stitch-generation"
                    else f"{kind} 专项提示词\n读取要求：按专项模板执行。"
                )
                path.write_text(body, encoding="utf-8")
                output = io.StringIO()
                with redirect_stdout(output):
                    status = adaptive.main(["--prompt-file", str(path), "--prompt-kind", kind])
                self.assertEqual(0, status, output.getvalue())

    def test_prompt_kind_long_is_legacy_alias_for_short_goal_contract(self):
        short_prompt = (
            "普通目标提示词\n"
            "任务 ID：TASK-1\n"
            "流程档位：标准流程\n"
            "修改前评分：42/100\n"
            "五维评分：项目现状 8；修改规模 9；依赖与修改后影响 8；风险与回滚 7；验证复杂度 10\n"
            "评分证据：已检查代码、调用方、测试和 Git diff。\n"
            "目标阶段：development\n"
            "当前目标：第 1/1 次\n"
            "必须读取：liran_docs/requirements/TASK-1-PRD.md、源码、测试\n"
            "允许修改：已确认模块及其直接测试\n"
            "禁止修改：无关模块、密钥和生产数据\n"
            "验证要求：运行相关测试并检查真实 diff\n"
            "状态回写：04-开发追踪.md、08-测试用例.md\n"
            "完成条件：实现、验证和回写均有证据\n"
            "下一阶段解锁条件：当前目标完成并通过校验"
            "\n当前目标完成开发、测试、验收、问题回写和必要修复。"
            "\n当前目标完成并已回收，goal_status=reclaimed。"
            "\n项目状态：待用户检查。"
            "\n资料归档状态：待归档确认。"
            "\n用户检查期间不再执行当前目标。"
            "\n当前目标暂不执行正式归档，不清理活动文档。"
            "\n当前目标结束后进入待用户检查和待归档确认。"
            "\n用户发现问题时回到问题回写、修复、测试和验收；有新增需求或优化时回到需求整理或需求变更流程。"
            "\n只有用户明确回复“归档”后才调用正式归档模板。"
            "\n归档失败不得重新打开普通目标。"
        )
        self.assertEqual(
            [],
            adaptive.prompt_failures_for_kind(short_prompt, kind="long", tier="standard"),
        )

        oversized_prompt = self._valid_workflow_prompt("standard") + "\n验证细节。" * 2000
        oversized_failures = adaptive.prompt_failures_for_kind(
            oversized_prompt,
            kind="long",
            tier="standard",
        )
        self.assertTrue(any("10000" in failure for failure in oversized_failures))

    def test_score_record_requires_five_dimensions_and_consistent_total(self):
        incomplete = "任务 ID：TASK-1\n总分：60/100\n流程等级：标准流程"
        failures = adaptive.score_record_failures(incomplete)
        self.assertTrue(any("五个维度" in failure or "项目现状" in failure for failure in failures))

        complete = "\n".join(
            [
                "任务 ID：TASK-1",
                "项目现状：8",
                "修改规模：10",
                "依赖与修改后影响：12",
                "风险与回滚：6",
                "验证复杂度：9",
                "总分：45/100",
                "评分分段：标准流程",
                "流程等级：标准流程",
                "评分证据：已检查调用方、模块、测试和 Git diff。",
                "范围上限：标准流程",
                "安全门禁：无",
                "项目级完整条件：不满足",
            ]
        )
        self.assertEqual([], adaptive.score_record_failures(complete))

    def test_prd_source_audit_requires_score_file_when_requested(self):
        source = "## 已确认的内容\n接口路径：/api/status"
        formal = self._valid_prd_document(status="正式 PRD", requirement_status="已确认", version="1.0")
        failures = adaptive.prd_conversion_failures(
            formal, source_text=source, require_score=True
        )
        self.assertTrue(any("评分记录" in failure for failure in failures))

    def test_prd_source_audit_accepts_a_valid_score_record(self):
        source = "## 已确认的内容\n"
        formal = self._valid_prd_document(status="正式 PRD", requirement_status="已确认", version="1.0")
        score = "\n".join(
            [
                "任务 ID：TASK-1",
                "项目现状：8",
                "修改规模：10",
                "依赖与修改后影响：12",
                "风险与回滚：6",
                "验证复杂度：9",
                "总分：45/100",
                "评分分段：标准流程",
                "流程等级：标准流程",
                "评分证据：真实调查记录。",
                "范围上限：标准流程",
                "安全门禁：无",
                "项目级完整条件：不满足",
            ]
        )
        self.assertEqual(
            [],
            adaptive.prd_conversion_failures(
                formal,
                source_text=source,
                score_text=score,
                require_score=True,
            ),
        )

    def test_prd_draft_and_formal_schema_are_valid(self):
        draft = self._valid_prd_document(status="PRD 草稿", requirement_status="需求整理中", version="草稿")
        self.assertEqual([], adaptive.prd_document_failures(draft, expected_status="draft"))
        formal = self._valid_prd_document(status="正式 PRD", requirement_status="已确认", version="1.0")
        self.assertEqual([], adaptive.prd_document_failures(formal, expected_status="formal"))
        self.assertEqual([], adaptive.prd_conversion_failures(formal))

    def test_prd_accepts_heading_style_req_and_ac_ids(self):
        document = self._valid_prd_document().replace("REQ-001\n触发条件", "### REQ-001 [v1.0]\n触发条件", 1)
        document = document.replace("AC-001\n对应需求", "### AC-001\n对应需求", 1)
        self.assertEqual([], adaptive.prd_document_failures(document))

    def test_prd_rejects_process_content_and_missing_requirement_mapping(self):
        document = self._valid_prd_document()
        missing_mapping = document.replace("对应 AC：AC-001", "对应 AC：", 1)
        failures = adaptive.prd_document_failures(missing_mapping)
        self.assertTrue(any("REQ-001" in failure and "AC" in failure for failure in failures))
        contaminated = document + "\n## 流程合同\n目标阶段：development\n开发流水：已完成\n"
        failures = adaptive.prd_document_failures(contaminated)
        self.assertTrue(any("过程" in failure or "流程合同" in failure for failure in failures))

        for process_heading in ("## Goal 完整提示词", "## 微观任务正文", "## 测试执行记录", "## 真机执行记录"):
            with self.subTest(process_heading=process_heading):
                failures = adaptive.prd_document_failures(document + f"\n{process_heading}\n执行内容\n")
                self.assertTrue(any("过程" in failure for failure in failures))

    def test_formal_prd_keeps_user_words_and_project_facts_outside_prd(self):
        document = self._valid_prd_document()
        field_contaminated = document + "\n首次用户原话：用户原话应保存在原话文档。\n已核实项目事实：事实应回写项目文档。\n"
        field_failures = adaptive.prd_document_failures(field_contaminated, expected_status="formal")
        self.assertTrue(any("首次用户原话" in failure or "已核实项目事实" in failure for failure in field_failures))
        contaminated = document + "\n## 首次用户原话\n用户原话应保存在原话文档。\n## 已核实项目事实\n事实应回写项目文档。\n"
        failures = adaptive.prd_document_failures(contaminated, expected_status="formal")
        self.assertTrue(any("固定结构之外" in failure or "过程" in failure for failure in failures))

    def test_requirements_gathering_document_is_chat_style_and_not_prd(self):
        template = (adaptive.ROOT / "templates/需求整理工作文档.md").read_text(encoding="utf-8")
        self.assertEqual([], adaptive.requirements_gathering_document_failures(
            template.replace("<稳定且唯一的任务 ID>", "TASK-1")
            .replace("<任务类型>", "功能修复")
            .replace("<YYYY-MM-DD>", "2026-09-13")
        ))

    def test_prd_rejects_unexpected_level_two_section(self):
        document = self._valid_prd_document() + "\n## 临时施工日志\n不应进入 PRD。\n"
        failures = adaptive.prd_document_failures(document)
        self.assertTrue(any("固定结构之外" in failure for failure in failures))

    def test_prd_change_requires_impact_matrix(self):
        document = self._valid_prd_document() + "\nCHG-001：用户确认增加一个状态。\n"
        failures = adaptive.prd_document_failures(document)
        self.assertTrue(any("变更影响矩阵" in failure for failure in failures))

    def test_formal_prd_cannot_keep_pending_confirmation_items(self):
        document = self._valid_prd_document()
        document = document.replace("## 17. 待确认项\n\n无。", "## 17. 待确认项\n\n仍待确认：页面权限", 1)
        failures = adaptive.prd_conversion_failures(document)
        self.assertTrue(any("待确认项" in failure for failure in failures))

    def test_skill_exposes_one_ordered_prd_to_archive_lifecycle(self):
        skill = (adaptive.ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual([], adaptive.lifecycle_sequence_failures(skill))

    def test_lifecycle_validator_rejects_skipped_or_reordered_steps(self):
        skill = (adaptive.ROOT / "SKILL.md").read_text(encoding="utf-8")
        broken = skill.replace("需求整理文档 → 正常聊天整理", "正式 PRD → 正常聊天整理", 1)
        failures = adaptive.lifecycle_sequence_failures(broken)
        self.assertTrue(any("顺序" in failure or "步骤" in failure for failure in failures))

    def test_option_gate_requires_choices_at_each_confirmation_node(self):
        skill = (adaptive.ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual([], adaptive.option_stage_failures(skill))
        broken = skill.replace("正式 PRD 没问题", "正式 PRD 已确认", 1)
        failures = adaptive.option_stage_failures(broken)
        self.assertTrue(any("选项" in failure for failure in failures))

    def test_prd_conversion_transition_requires_output_index_and_user_confirmation(self):
        contract = adaptive.FlowContract(
            tier="standard", pre_score=35, goal_count=1, acceptance_owner="待确认",
            visual_qa="待确认", phase="待集中确认", state="待集中确认",
            summary_output=True, summary_confirmed=True, block_reason="不适用",
        )
        failures = adaptive.flow_transition_failures(
            contract,
            target_state="正式 PRD 待确认",
            event="正式 PRD 已输出",
            evidence=["PRD 草稿已转换", "PRD 索引已更新", "正式 PRD 已输出"],
        )
        self.assertEqual([], failures)
        confirmed_contract = adaptive.FlowContract(
            tier="standard", pre_score=35, goal_count=1, acceptance_owner="待确认",
            visual_qa="待确认", phase="正式 PRD 待确认", state="正式 PRD 待确认",
            summary_output=True, summary_confirmed=True, block_reason="不适用",
        )
        failures = adaptive.flow_transition_failures(
            confirmed_contract,
            target_state="提示词生成中",
            event="PRD 没问题，用户确认后生成提示词",
            evidence=["PRD 没问题"],
        )
        self.assertTrue(any("验收责任" in failure for failure in failures))

    def test_formal_prd_confirmation_unlocks_consolidated_choice_state(self):
        contract = adaptive.FlowContract(
            tier="standard", pre_score=35, goal_count=1, acceptance_owner="待确认",
            visual_qa="待确认", phase="正式 PRD 待确认", state="正式 PRD 待确认",
            summary_output=True, summary_confirmed=True, block_reason="不适用",
        )
        failures = adaptive.flow_transition_failures(
            contract,
            target_state="待集中确认",
            event="PRD 没问题，进入验收责任和页面样式选择",
            evidence=["PRD 没问题"],
        )
        self.assertEqual([], failures)

    def test_cli_validates_prd_file_and_status(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "TASK-1-PRD.md"
            path.write_text(self._valid_prd_document(status="正式 PRD", requirement_status="已确认", version="1.0"), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                status = adaptive.main(["--prd-file", str(path), "--prd-status", "formal"])
            self.assertEqual(0, status, output.getvalue())

    def _valid_prd_document(self, *, status="正式 PRD", requirement_status="已确认", version="1.0"):
        sections = [
            "产品/功能概述", "背景与问题", "用户与使用场景", "产品目标",
            "非目标与明确不做", "当前项目事实", "用户流程", "功能需求",
            "数据、状态与业务规则", "页面与 UI 需求", "异常、边界与安全规则",
            "兼容性与限制", "影响范围", "验收标准", "需求追踪矩阵",
            "关联文档索引", "待确认项", "决策记录", "需求变更记录",
            "PRD 版本说明", "变更影响矩阵", "当前状态与下一步",
        ]
        body = "# 示例功能 · PRD\n\n"
        body += f"## 0. 文档控制\n\n任务 ID：TASK-1\n文档状态：{status}\n需求状态：{requirement_status}\nPRD 版本：{version}\n\n"
        for index, section in enumerate(sections, start=1):
            body += f"## {index}. {section}\n\n"
            if section == "功能需求":
                body += "REQ-001\n触发条件：用户打开功能。\n前置条件：用户已登录。\n用户操作：点击按钮。\n系统行为：系统执行动作。\n数据变化：记录一次操作。\n状态变化：状态由待处理变为完成。\n正常结果：显示成功。\n异常处理：失败时显示错误并允许重试。\n禁止行为：不得越权写入数据。\n对应 AC：AC-001\n\n"
            elif section == "验收标准":
                body += "AC-001\n对应需求：REQ-001\n验收步骤：执行主流程并观察结果。\n预期结果：显示成功且数据正确。\n失败条件：结果错误、崩溃或无证据。\n\n"
            elif section == "关联文档索引":
                body += "文件类型：模块文档；文件路径：待本阶段生成；文件作用：记录实现细节；当前状态：待创建；关联需求：REQ-001。\n\n"
            elif section == "待确认项":
                body += "无。\n\n"
            else:
                body += "已根据当前事实完成记录，未混入执行过程正文。\n\n"
        return body

    def test_cli_prompt_kind_stitch_instance_repair_does_not_require_tier(self):
        from scripts import check_codex_ui_flow_docs as ui_check

        template = (ui_check.ROOT / ui_check.STITCH_REPAIR_TEMPLATE).read_text(encoding="utf-8")
        prompt = template + "\n项目路径：/tmp/example\n"
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "instance-repair.md"
            path.write_text(prompt, encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                status = adaptive.main(
                    [
                        "--prompt-file",
                        str(path),
                        "--prompt-kind",
                        "stitch-instance-repair",
                    ]
                )
            self.assertEqual(0, status, output.getvalue())

    def test_goal_sequences_use_fixed_base_counts_and_one_optional_ui_stage(self):
        self.assertEqual(("single",), adaptive.goal_sequence("light"))
        self.assertEqual(("single",), adaptive.goal_sequence("standard"))
        self.assertEqual(
            ("documentation", "development-and-acceptance"),
            adaptive.goal_sequence("deep"),
        )
        self.assertEqual(
            ("documentation", "ui", "development-and-acceptance"),
            adaptive.goal_sequence("deep", ui_goal_enabled=True),
        )
        self.assertEqual(
            ("documentation", "development", "acceptance"),
            adaptive.goal_sequence("full-docs"),
        )
        self.assertEqual(
            ("documentation", "ui", "development", "acceptance"),
            adaptive.goal_sequence("full-docs", ui_goal_enabled=True),
        )

    def test_ui_goal_decision_honors_scope_and_explicit_skip(self):
        for tier in ("deep", "full-docs"):
            self.assertTrue(adaptive.should_enable_ui_goal(tier, has_ui=True))
            self.assertFalse(
                adaptive.should_enable_ui_goal(tier, has_ui=True, user_skips_ui=True)
            )
            self.assertFalse(adaptive.should_enable_ui_goal(tier, has_ui=False))
        self.assertFalse(adaptive.should_enable_ui_goal("standard", has_ui=True))

    def test_flow_contract_round_trips_multi_goal_stage_fields(self):
        contract = adaptive.FlowContract(
            tier="deep",
            pre_score=62,
            base_goal_count=2,
            goal_count=3,
            goal_index=2,
            goal_stage="ui",
            ui_goal_enabled=True,
            ui_route="external-ai",
            awaiting_external_input=True,
            acceptance_owner="Codex 真机测试",
            visual_qa="检查页面样式是否符合方案",
            phase="UI 目标执行中",
        )
        self.assertEqual(contract, adaptive.FlowContract.from_json(contract.to_json()))
        self.assertEqual([], adaptive.flow_contract_failures(contract))

    def test_flow_contract_rejects_goal_count_stage_and_waiting_drift(self):
        wrong_count = adaptive.FlowContract(
            tier="deep", pre_score=62, base_goal_count=2, goal_count=2,
            goal_index=2, goal_stage="ui", ui_goal_enabled=True, ui_route="product-design",
            acceptance_owner="Codex 真机测试", visual_qa="检查页面样式是否符合方案",
            phase="UI 目标执行中",
        )
        self.assertTrue(any("目标数" in item for item in adaptive.flow_contract_failures(wrong_count)))
        missing_route = adaptive.FlowContract(
            tier="deep", pre_score=62, base_goal_count=2, goal_count=3,
            goal_index=2, goal_stage="ui", ui_goal_enabled=True,
            acceptance_owner="Codex 真机测试", visual_qa="检查页面样式是否符合方案",
            phase="UI 目标执行中",
        )
        self.assertTrue(any("UI 路线" in item for item in adaptive.flow_contract_failures(missing_route)))
        waiting_codex = adaptive.FlowContract(
            tier="deep", pre_score=62, base_goal_count=2, goal_count=3,
            goal_index=2, goal_stage="ui", ui_goal_enabled=True, ui_route="codex",
            awaiting_external_input=True, acceptance_owner="Codex 真机测试",
            visual_qa="检查页面样式是否符合方案", phase="UI 目标执行中",
        )
        self.assertTrue(any("external-ai" in item for item in adaptive.flow_contract_failures(waiting_codex)))
        wrong_wait = adaptive.FlowContract(
            tier="full-docs", pre_score=80, base_goal_count=3, goal_count=3,
            goal_index=2, goal_stage="development", ui_goal_enabled=False,
            awaiting_external_input=True, acceptance_owner="Codex 真机测试",
            visual_qa="不涉及页面", phase="开发目标执行中",
        )
        self.assertTrue(any("外部输入" in item for item in adaptive.flow_contract_failures(wrong_wait)))

        light_ui = adaptive.FlowContract(
            tier="light", pre_score=10, base_goal_count=1, goal_count=1,
            goal_index=1, goal_stage="single", ui_goal_enabled=True, ui_route="product-design",
            acceptance_owner="Codex 真机测试", visual_qa="检查页面样式是否符合方案",
            phase="提示词已解锁",
        )
        self.assertTrue(
            any("不使用独立 UI 目标" in item for item in adaptive.flow_contract_failures(light_ui))
        )

    def test_goal_handoff_cannot_skip_or_advance_while_waiting(self):
        waiting = adaptive.FlowContract(
            tier="deep", pre_score=62, base_goal_count=2, goal_count=3,
            goal_index=2, goal_stage="ui", ui_goal_enabled=True, ui_route="external-ai",
            awaiting_external_input=True, acceptance_owner="Codex 真机测试",
            visual_qa="检查页面样式是否符合方案", phase="UI 目标执行中",
        )
        failures = adaptive.goal_handoff_failures(
            waiting, target_goal_index=3, event="UI 目标已完成"
        )
        self.assertTrue(any("等待外部输入" in item for item in failures))

        active = adaptive.FlowContract.from_dict(
            {
                **waiting.to_dict(),
                "awaiting_external_input": False,
                "completed_gates": [
                    "文本视觉方案已确认", "UI 壳已完成", "UI 壳接收检查",
                    "视觉 QA 通过",
                ],
            }
        )
        self.assertEqual(
            [],
            adaptive.goal_handoff_failures(
                active, target_goal_index=3, event="UI 目标已完成"
            ),
        )
        self.assertTrue(
            adaptive.goal_handoff_failures(
                active, target_goal_index=4, event="UI 目标已完成"
            )
        )

    def test_waiting_ui_goal_resumes_only_after_positive_external_input_evidence(self):
        waiting = adaptive.FlowContract(
            tier="deep", pre_score=62, base_goal_count=2, goal_count=3,
            goal_index=2, goal_stage="ui", ui_goal_enabled=True, ui_route="external-ai",
            awaiting_external_input=True, acceptance_owner="Codex 真机测试",
            visual_qa="检查页面样式是否符合方案", phase="UI 目标执行中",
        )
        self.assertEqual(
            [],
            adaptive.goal_handoff_failures(
                waiting, target_goal_index=2, event="已收到外部输入，结束等待并恢复 UI 目标"
            ),
        )
        for event in (
            "继续等待外部输入", "尚未收到外部输入", "外部输入缺失",
            "未确认收到外部输入", "无法确认收到外部输入", "不确定是否收到外部输入",
        ):
            failures = adaptive.goal_handoff_failures(
                waiting, target_goal_index=2, event=event
            )
            self.assertTrue(any("未确认收到" in item for item in failures), event)

    def test_goal_handoff_rejects_legacy_contract_without_stage_fields(self):
        contract = adaptive.FlowContract(
            tier="deep",
            pre_score=60,
            goal_count=1,
            acceptance_owner="Codex 真机测试",
            visual_qa="不涉及页面",
            phase="提示词已解锁",
        )
        failures = adaptive.goal_handoff_failures(
            contract,
            target_goal_index=1,
            event="当前目标已完成",
        )
        self.assertTrue(any("缺少多阶段字段" in item for item in failures))

    def test_goal_handoff_requires_stage_completion_evidence(self):
        contract = adaptive.FlowContract(
            tier="deep", pre_score=62, base_goal_count=2, goal_count=2,
            goal_index=1, goal_stage="documentation", ui_goal_enabled=False,
            acceptance_owner="Codex 真机测试", visual_qa="不涉及页面",
            phase="文档目标执行中", state="未开始", artifact_audit=False,
        )
        failures = adaptive.goal_handoff_failures(
            contract, target_goal_index=2, event="文档目标已完成"
        )
        self.assertTrue(any("完成证据" in item or "产物审计" in item for item in failures))

        pending_ui = adaptive.FlowContract(
            tier="deep", pre_score=62, base_goal_count=2, goal_count=3,
            goal_index=1, goal_stage="documentation", ui_goal_enabled=True,
            ui_route="pending", acceptance_owner="Codex 真机测试",
            visual_qa="检查页面样式是否符合方案", phase="文档目标已完成",
            completed_gates=adaptive.TIER_PRECODE_REQUIRED_GATES["deep"],
            artifact_audit=True,
        )
        failures = adaptive.goal_handoff_failures(
            pending_ui, target_goal_index=2, event="文档目标已完成"
        )
        self.assertTrue(any("canonical UI 路线" in item for item in failures))

    def test_full_non_ui_goal_chain_hands_off_with_stage_evidence(self):
        documentation = adaptive.FlowContract(
            tier="full-docs", pre_score=80, base_goal_count=3, goal_count=3,
            goal_index=1, goal_stage="documentation", ui_goal_enabled=False,
            acceptance_owner="Codex 真机测试", visual_qa="不涉及页面",
            phase="产物审计中", state="产物审计中",
            completed_gates=adaptive.TIER_PRECODE_REQUIRED_GATES["full-docs"],
            artifact_audit=True,
        )
        self.assertEqual(
            [],
            adaptive.goal_handoff_failures(
                documentation, target_goal_index=2, event="文档目标已完成"
            ),
        )

        development = adaptive.FlowContract(
            tier="full-docs", pre_score=80, base_goal_count=3, goal_count=3,
            goal_index=2, goal_stage="development", ui_goal_enabled=False,
            acceptance_owner="Codex 真机测试", visual_qa="不涉及页面",
            phase="开发目标已解锁", state="开发目标已解锁",
            completed_gates=adaptive.TIER_PRECODE_REQUIRED_GATES["full-docs"],
            summary_output=True, summary_confirmed=True, acceptance_confirmed=True,
            prompt_status="已解锁", artifact_audit=True,
        )
        self.assertEqual(
            [],
            adaptive.flow_transition_failures(
                development, target_state="开发中", event="开始开发",
                evidence=list(adaptive.TIER_PRECODE_REQUIRED_GATES["full-docs"]),
            ),
        )
        development_done = adaptive.FlowContract.from_dict(
            {
                **development.to_dict(),
                "state": "内部测试通过",
                "phase": "内部测试通过",
                "completed_gates": [*development.completed_gates, "内部测试通过"],
            }
        )
        self.assertEqual(
            [],
            adaptive.goal_handoff_failures(
                development_done, target_goal_index=3, event="开发目标已完成"
            ),
        )

        acceptance = adaptive.FlowContract.from_dict(
            {
                **development_done.to_dict(),
                "goal_index": 3,
                "goal_stage": "acceptance",
                "state": "验收目标执行中",
                "phase": "验收目标执行中",
            }
        )
        self.assertEqual(
            [],
            adaptive.flow_transition_failures(
                acceptance, target_state="回写中", event="验收结果已记录并回写"
            ),
        )

    def test_ui_handoff_uses_route_specific_visual_evidence(self):
        base = adaptive.FlowContract(
            tier="deep", pre_score=62, base_goal_count=2, goal_count=3,
            goal_index=2, goal_stage="ui", ui_goal_enabled=True, ui_route="product-design",
            acceptance_owner="Codex 真机测试",
            visual_qa="不检查页面样式是否符合方案", phase="UI 目标已完成",
            completed_gates=("文本视觉方案已确认", "UI 壳已完成", "UI 壳接收检查"),
        )
        failures = adaptive.goal_handoff_failures(
            base, target_goal_index=3, event="UI 目标已完成"
        )
        self.assertTrue(any("不适用原因" in item for item in failures))
        self.assertEqual(
            [],
            adaptive.goal_handoff_failures(
                base,
                target_goal_index=3,
                event="UI 目标已完成",
                evidence=["视觉 QA 不适用：用户选择不检查页面样式"],
            ),
        )

        stitch = adaptive.FlowContract.from_dict(
            {
                **base.to_dict(),
                "visual_qa": "检查页面样式是否符合方案",
                "ui_route": "stitch",
            }
        )
        failures = adaptive.goal_handoff_failures(
            stitch,
            target_goal_index=3,
            event="UI 目标已完成",
            evidence=["视觉 QA 通过"],
        )
        self.assertTrue(any("Stitch" in item and "复修" in item for item in failures))

    def test_stage_specific_workflow_prompts_accept_only_their_own_gates(self):
        cases = (
            ("light", "single", 1, 1, False),
            ("standard", "single", 1, 1, False),
            ("deep", "documentation", 1, 2, False),
            ("deep", "ui", 2, 3, True),
            ("deep", "development-and-acceptance", 2, 2, False),
            ("deep", "development-and-acceptance", 3, 3, True),
            ("full-docs", "documentation", 1, 3, False),
            ("full-docs", "documentation", 1, 4, True),
            ("full-docs", "ui", 2, 4, True),
            ("full-docs", "development", 2, 3, False),
            ("full-docs", "development", 3, 4, True),
            ("full-docs", "acceptance", 3, 3, False),
            ("full-docs", "acceptance", 4, 4, True),
        )
        for tier, stage, index, count, ui_enabled in cases:
            with self.subTest(tier=tier, stage=stage):
                prompt = self._valid_staged_workflow_prompt(
                    tier, stage, index=index, count=count,
                    ui_goal_enabled=ui_enabled,
                )
                self.assertEqual([], adaptive.workflow_prompt_failures(prompt, tier=tier))

    def test_intermediate_goal_prompt_rejects_archive_or_completion_language(self):
        prompt = self._valid_staged_workflow_prompt(
            "deep", "documentation", index=1, count=2
        ) + "\n本次任务已完成并归档。"
        failures = adaptive.workflow_prompt_failures(prompt, tier="deep")
        self.assertTrue(any("中间目标禁止" in item for item in failures))

        completed = self._valid_staged_workflow_prompt(
            "deep", "documentation", index=1, count=2
        ) + "\n本次任务全部完成。"
        failures = adaptive.workflow_prompt_failures(completed, tier="deep")
        self.assertTrue(any("中间目标禁止" in item for item in failures))

        prohibited = self._valid_staged_workflow_prompt(
            "deep", "documentation", index=1, count=2
        ) + "\n禁止动作：不得执行最终归档，不得标记已归档，不得宣布本次任务整体完成。\n不要输出本次任务全部完成。"
        self.assertEqual([], adaptive.workflow_prompt_failures(prohibited, tier="deep"))

    def test_stage_prompt_rejects_affirmative_cross_stage_actions(self):
        cases = (
            ("deep", "documentation", 1, 2, False, "直接修改源码并实现业务代码"),
            ("deep", "ui", 2, 3, True, "同时接入真实 API、权限与表单提交"),
            ("full-docs", "development", 2, 3, False, "直接执行真机验收"),
        )
        for tier, stage, index, count, ui_enabled, action in cases:
            prompt = self._valid_staged_workflow_prompt(
                tier, stage, index=index, count=count,
                ui_goal_enabled=ui_enabled,
            ) + f"\n{action}。"
            failures = adaptive.workflow_prompt_failures(prompt, tier=tier)
            self.assertTrue(any("越过当前阶段" in item for item in failures), action)

    def test_stage_prompt_allows_explicit_cross_stage_prohibitions(self):
        prompt = self._valid_staged_workflow_prompt(
            "deep", "ui", index=2, count=3, ui_goal_enabled=True
        ) + "\n禁止动作：不得接入真实 API、权限或表单提交。\n真实 API 由后续 development 目标接入，真实权限由后续 development 目标实现。"
        self.assertEqual([], adaptive.workflow_prompt_failures(prompt, tier="deep"))

    def test_stage_prompt_does_not_let_unrelated_negation_hide_positive_actions(self):
        cases = (
            ("deep", "ui", 2, 3, True, "不接 mock，直接接入真实 API"),
            ("deep", "ui", 2, 3, True, "不得遗漏真实 API 接入和表单提交"),
            ("full-docs", "development", 2, 3, False, "后续直接执行真机验收"),
            ("deep", "documentation", 1, 2, False, "下一目标说明完成后，当前目标直接修改源码"),
        )
        for tier, stage, index, count, ui_enabled, action in cases:
            prompt = self._valid_staged_workflow_prompt(
                tier, stage, index=index, count=count,
                ui_goal_enabled=ui_enabled,
            ) + f"\n{action}。"
            failures = adaptive.workflow_prompt_failures(prompt, tier=tier)
            self.assertTrue(any("越过当前阶段" in item for item in failures), action)

    def test_light_and_standard_prompts_cannot_enable_an_independent_ui_goal(self):
        for tier in ("light", "standard"):
            prompt = self._valid_staged_workflow_prompt(
                tier, "single", index=1, count=1
            ).replace("UI 目标：跳过", "UI 目标：启用", 1)
            failures = adaptive.workflow_prompt_failures(prompt, tier=tier)
            self.assertTrue(any("不使用独立 UI 目标" in item for item in failures))

    def test_confirmation_payload_rejects_markdown_question_and_option_wrappers(self):
        option = adaptive.PAGE_OPTIONS[0]
        failures = adaptive.confirmation_delivery_failures(
            "**需求整理得对不对？改完后怎么测试？**",
            [f"`{option}`"],
            prompt_generating=True,
        )
        self.assertTrue(any("Markdown" in item for item in failures))

    def test_confirmation_payload_rejects_markdown_descriptions(self):
        option = adaptive.PAGE_OPTIONS[0]
        failures = adaptive.confirmation_delivery_failures(
            "需求整理得对不对？改完后怎么测试？",
            [option],
            descriptions=["有 **Markdown** 的说明"],
            prompt_generating=True,
        )
        self.assertTrue(any("Markdown" in item for item in failures))

    def test_native_confirmation_requires_two_or_three_options(self):
        failures = adaptive.confirmation_delivery_failures(
            "需求整理得对不对？改完后怎么测试？",
            [adaptive.PAGE_OPTIONS[0]],
            descriptions=["由 Codex 测试并检查页面"],
            prompt_generating=True,
        )
        self.assertTrue(any("2–3" in item for item in failures))

    def test_text_confirmation_fallback_uses_plain_option_paragraphs(self):
        option = adaptive.PAGE_OPTIONS[0]
        self.assertEqual(
            [],
            adaptive.text_confirmation_fallback_failures(
                f"选项一：{option}", [option]
            ),
        )
        failures = adaptive.text_confirmation_fallback_failures(f"1. `{option}`", [option])
        self.assertTrue(any("Markdown" in item for item in failures))

    def test_cli_validates_goal_handoff_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "goal-handoff.json"
            contract = adaptive.FlowContract(
                tier="deep", pre_score=62, base_goal_count=2, goal_count=2,
                goal_index=1, goal_stage="documentation", ui_goal_enabled=False,
                acceptance_owner="Codex 真机测试", visual_qa="不涉及页面",
                phase="文档目标已完成",
                completed_gates=adaptive.TIER_PRECODE_REQUIRED_GATES["deep"],
                artifact_audit=True,
            )
            path.write_text(
                json.dumps(
                    {
                        "contract": contract.to_dict(),
                        "target_goal_index": 2,
                        "event": "文档目标已完成",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                status = adaptive.main(["--goal-transition-file", str(path)])
            self.assertEqual(0, status, output.getvalue())

    def test_cli_confirmation_fallback_rejects_markdown_rendering(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "confirmation.json"
            option = adaptive.PAGE_OPTIONS[0]
            path.write_text(
                json.dumps(
                    {
                        "question": "需求整理得对不对？改完后怎么测试？",
                        "options": [option],
                        "descriptions": ["由 Codex 执行验收"],
                        "prompt_generating": True,
                        "fallback_text": f"1. `{option}`",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                status = adaptive.main(["--confirmation-file", str(path)])
            self.assertEqual(1, status)
            self.assertIn("Markdown", output.getvalue())

    def test_cli_confirmation_rejects_markdown_descriptions(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "confirmation.json"
            option = adaptive.PAGE_OPTIONS[0]
            path.write_text(
                json.dumps(
                    {
                        "question": "需求整理得对不对？改完后怎么测试？",
                        "options": [option],
                        "descriptions": ["有 `Markdown` 的说明"],
                        "prompt_generating": True,
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                status = adaptive.main(["--confirmation-file", str(path)])
            self.assertEqual(1, status)
            self.assertIn("Markdown", output.getvalue())

    def test_flow_contract_json_rejects_string_multi_goal_booleans(self):
        payload = {
            "tier": "deep", "pre_score": 62, "base_goal_count": 2,
            "goal_count": 3, "goal_index": 2, "goal_stage": "ui",
            "ui_goal_enabled": "false", "awaiting_external_input": "false",
            "acceptance_owner": "Codex 真机测试",
            "visual_qa": "不涉及页面", "phase": "UI 目标执行中",
        }
        with self.assertRaisesRegex(ValueError, "boolean"):
            adaptive.FlowContract.from_dict(payload)

        for field in ("summary_output", "summary_confirmed", "acceptance_confirmed", "artifact_audit"):
            strict_payload = {
                **payload,
                "ui_goal_enabled": True,
                "awaiting_external_input": False,
                "ui_route": "product-design",
                field: "false",
            }
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                adaptive.FlowContract.from_dict(strict_payload)

    def test_executable_prompt_allows_short_ordinary_pointer_text(self):
        self.assertEqual(
            [],
            adaptive.workflow_prompt_failures(
                "普通目标提示词\n任务 ID：TASK-1\n流程档位：标准流程\n修改前评分：42/100\n目标阶段：development\n当前目标：第 1/1 次\n"
                "五维评分：项目现状 8；修改规模 9；依赖与修改后影响 8；风险与回滚 7；验证复杂度 10\n评分证据：已检查代码、调用方、测试和 Git diff。\n"
                "必须读取：liran_docs/requirements/TASK-1-PRD.md\n允许修改：已确认模块\n"
                "禁止修改：无关模块\n验证要求：运行测试\n状态回写：04-开发追踪.md\n"
                "完成条件：实现并验证\n下一阶段解锁条件：当前目标完成\n"
                "当前目标完成开发、测试、验收、问题回写和必要修复。\n"
                "当前目标完成并已回收，goal_status=reclaimed。\n"
                "项目状态：待用户检查。\n"
                "资料归档状态：待归档确认。\n"
                "用户检查期间不再执行当前目标。\n"
                "当前目标暂不执行正式归档，不清理活动文档。\n"
                "当前目标结束后进入待用户检查和待归档确认。\n"
                "用户发现问题时回到问题回写、修复、测试和验收；有新增需求或优化时回到需求整理或需求变更流程。\n"
                "只有用户明确回复“归档”后才调用正式归档模板。\n"
                "归档失败不得重新打开普通目标。",
                tier="standard",
            ),
        )

    def test_short_goal_requires_score_and_flow_tier(self):
        prompt = (
            "普通目标提示词\n任务 ID：TASK-1\n当前阶段：development\n当前目标：第 1/1 次\n"
            "必须读取：liran_docs/requirements/TASK-1-PRD.md\n允许修改：已确认模块\n"
            "禁止修改：无关模块\n验证要求：运行测试\n状态回写：04-开发追踪.md\n"
            "完成条件：实现并验证\n下一阶段解锁条件：当前目标完成\n"
            "当前目标完成开发、测试、验收、问题回写和必要修复。\n"
            "当前目标暂不执行正式归档，不清理活动文档。\n"
            "当前目标结束后进入待用户检查和待归档确认。\n"
            "如果用户发现问题，回到问题回写、修复、测试和验收；如果用户提出新增需求或优化，回到需求整理或需求变更流程。\n"
            "只有用户明确回复“归档”后才调用正式归档模板。"
        )
        failures = adaptive.workflow_prompt_failures(
            prompt, tier="standard", archive_stage="handoff"
        )
        self.assertTrue(any("流程档位" in item for item in failures))
        self.assertTrue(any("修改前评分" in item for item in failures))

    def test_short_goal_rejects_invalid_score_or_flow_tier_values(self):
        prompt = (
            "普通目标提示词\n任务 ID：TASK-1\n流程档位：未知流程\n修改前评分：101/100\n"
            "五维评分：项目现状 8；修改规模 9；依赖与修改后影响 8；风险与回滚 7；验证复杂度 10\n"
            "评分证据：已检查代码、调用方、测试和 Git diff。\n当前阶段：development\n"
            "当前目标：第 1/1 次\n必须读取：PRD.md\n允许修改：模块\n禁止修改：无关范围\n"
            "验证要求：运行测试\n状态回写：04-开发追踪.md\n完成条件：实现并验证\n"
            "下一阶段解锁条件：当前目标完成\n当前目标完成开发、测试、验收、问题回写和必要修复。\n"
            "当前目标暂不执行正式归档，不清理活动文档。\n当前目标结束后进入待用户检查和待归档确认。\n"
            "如果用户发现问题，回到问题回写、修复、测试和验收；如果用户提出新增需求或优化，回到需求整理或需求变更流程。\n"
            "只有用户明确回复“归档”后才调用正式归档模板。"
        )
        failures = adaptive.workflow_prompt_failures(prompt, tier="standard", archive_stage="handoff")
        self.assertTrue(any("合法四档值" in item for item in failures))
        self.assertTrue(any("0–100" in item for item in failures))

    def test_prd_conversion_requires_post_conversion_scoring_gate_in_docs(self):
        loaded = load_current_docs()
        for rel in (
            "SKILL.md",
            "references/提示词向导.md",
            "references/功能2-需求讨论与分层文档.md",
            "templates/正式PRD.md",
            "templates/通用完整执行提示词规范.md",
        ):
            self.assertIn("正式 PRD 转换完成后必须评分并确定流程等级", loaded[rel], rel)

    def test_executable_prompt_rejects_over_10000_characters(self):
        failures = adaptive.executable_prompt_failures(self._valid_executable_prompt(filler="执行细节。" * 2000))
        self.assertTrue(any("10000" in failure for failure in failures))

    def test_executable_prompt_requires_standard_sections(self):
        prompt = self._valid_executable_prompt().replace("九、验证要求", "九、其他要求", 1)
        failures = adaptive.executable_prompt_failures(prompt)
        self.assertTrue(any("验证要求" in failure for failure in failures))

    def test_executable_prompt_rejects_headings_without_details(self):
        headings = "\n".join(f"## {section}" for section in adaptive.EXECUTABLE_PROMPT_REQUIRED_SECTIONS)
        prompt = headings + "\n" + ("只有无关填充不能代替章节细节。" * 80)
        failures = adaptive.executable_prompt_failures(prompt)
        self.assertTrue(any("只有标题或细节不足" in failure for failure in failures))

    def test_executable_prompt_rejects_summary_shortcuts(self):
        prompt = self._valid_executable_prompt() + "\n其他要求不变，详见文档。"
        failures = adaptive.executable_prompt_failures(prompt)
        self.assertTrue(any("摘要替代" in failure for failure in failures))

    def test_executable_prompt_rejects_repeated_padding(self):
        prompt = self._valid_executable_prompt() + ("\n重复凑字内容。" * 8)
        failures = adaptive.executable_prompt_failures(prompt)
        self.assertTrue(any("重复凑字" in failure for failure in failures))

    def test_short_non_executable_message_is_exempt(self):
        self.assertEqual([], adaptive.executable_prompt_failures("请选择验收方式。", applicable=False))

    def test_runtime_deep_prompt_rejects_documentation_deferred_until_after_code(self):
        prompt = self._valid_staged_workflow_prompt(
            "deep", "documentation", index=1, count=2
        )
        prompt = prompt.replace(
            "受影响文档真实 diff：记录可核对的文件、命令和结果。",
            "先实现源码，最后再统一补受影响文档。",
            1,
        )
        failures = adaptive.workflow_prompt_failures(prompt, tier="deep")
        self.assertTrue(any("受影响文档真实 diff" in failure for failure in failures))

    def test_runtime_deep_prompt_accepts_full_precode_to_acceptance_sequence(self):
        prompt = self._valid_workflow_prompt("deep")
        self.assertEqual([], adaptive.workflow_prompt_failures(prompt, tier="deep"))

    def test_runtime_gate_does_not_use_later_prose_to_fake_precode_stage(self):
        prompt = self._valid_staged_workflow_prompt(
            "deep", "documentation", index=1, count=2
        ).replace(
            "## 档位执行门禁\n",
            "## 档位执行门禁\n先实现源码，稍后补齐。\n\n",
            1,
        )
        prompt = prompt.replace("受影响文档真实 diff：记录可核对的文件、命令和结果。", "稍后补文档。", 1)
        failures = adaptive.workflow_prompt_failures(prompt, tier="deep")
        self.assertTrue(any("运行时门禁缺少阶段：受影响文档真实 diff" in failure for failure in failures))

    def test_runtime_light_prompt_requires_red_before_code_unlock(self):
        prompt = self._valid_workflow_prompt("light").replace(
            "失败测试已确认 RED",
            "实现完成后补测试",
            1,
        )
        failures = adaptive.workflow_prompt_failures(prompt, tier="light")
        self.assertTrue(any("失败测试已确认 RED" in failure for failure in failures))

    def test_runtime_standard_prompt_requires_persisted_task_baseline(self):
        prompt = self._valid_workflow_prompt("standard").replace(
            "持久化模块任务清单",
            "在思考中记住模块任务",
            1,
        )
        failures = adaptive.workflow_prompt_failures(prompt, tier="standard")
        self.assertTrue(any("持久化模块任务清单" in failure for failure in failures))

    def test_runtime_full_docs_prompt_requires_artifact_audit_before_first_goal(self):
        prompt = self._valid_workflow_prompt("full-docs").replace(
            "文档与任务产物审计",
            "直接生成第一次目标",
            1,
        )
        failures = adaptive.workflow_prompt_failures(prompt, tier="full-docs")
        self.assertTrue(any("文档与任务产物审计" in failure for failure in failures))

    def test_runtime_prompt_requires_recoverable_flow_contract(self):
        prompt = self._valid_workflow_prompt("deep").replace(
            "上下文压缩后必须恢复本流程合同，不得重新猜测档位。",
            "上下文压缩后重新判断流程。",
            1,
        )
        failures = adaptive.workflow_prompt_failures(prompt, tier="deep")
        self.assertTrue(any("上下文压缩" in failure for failure in failures))

    def test_runtime_confirmation_rejects_split_acceptance_only_question(self):
        failures = adaptive.confirmation_delivery_failures(
            "验收责任需要现在确认",
            ["Codex 真机测试", "我自己测试"],
            prompt_generating=True,
        )
        self.assertTrue(any("同时确认需求" in failure for failure in failures))
        self.assertTrue(any("canonical" in failure or "prompt_generating" in failure for failure in failures))

    def test_runtime_confirmation_accepts_canonical_deep_options(self):
        failures = adaptive.confirmation_delivery_failures(
            "需求整理得对不对？改完后怎么测试？",
            adaptive.DEEP_NON_PAGE_OPTIONS,
            prompt_generating=True,
        )
        self.assertEqual([], failures)

    def test_runtime_validator_rejects_sanitized_real_failure_fixture(self):
        path = adaptive.ROOT / "tests/fixtures/deep-goal-runtime-failure.md"
        failures = adaptive.workflow_prompt_failures(
            path.read_text(encoding="utf-8"),
            tier="deep",
        )
        self.assertTrue(any("流程合同" in failure for failure in failures))
        self.assertTrue(any("受影响文档真实 diff" in failure for failure in failures))

    def test_executable_prompt_requires_unique_ordered_markdown_headings(self):
        prompt = self._valid_executable_prompt().replace(
            "## 二、当前场景", "## 二、当前场景\n\n## 二、当前场景", 1
        )
        failures = adaptive.executable_prompt_failures(prompt)
        self.assertTrue(any("必须唯一" in failure for failure in failures))

        reversed_prompt = self._valid_executable_prompt()
        first = reversed_prompt.index("## 二、当前场景")
        second = reversed_prompt.index("## 九、验证要求")
        second_end = second + len("## 九、验证要求")
        heading_two = reversed_prompt[first : first + len("## 二、当前场景")]
        heading_nine = reversed_prompt[second:second_end]
        reversed_prompt = (
            reversed_prompt[:first]
            + heading_nine
            + reversed_prompt[first + len(heading_two) : second]
            + heading_two
            + reversed_prompt[second_end:]
        )
        failures = adaptive.executable_prompt_failures(reversed_prompt)
        self.assertTrue(any("顺序错误" in failure for failure in failures))

    def test_flow_contract_round_trips_and_blocks_unsupported_upgrade(self):
        contract = adaptive.FlowContract(
            tier="deep",
            pre_score=63,
            goal_count=1,
            acceptance_owner="Codex 真机测试",
            visual_qa="不涉及页面",
            phase="准备阶段",
            unlocked_gates=("受影响文档真实 diff",),
        )
        restored = adaptive.FlowContract.from_json(contract.to_json())
        self.assertEqual(contract, restored)
        self.assertTrue(adaptive.flow_contract_failures(contract, resumed_tier="full-docs"))
        self.assertEqual(
            [],
            adaptive.flow_contract_failures(
                contract,
                resumed_tier="full-docs",
                post_score=75,
                upgrade_evidence=["真实 diff"],
            ),
        )

    def test_flow_contract_round_trips_explicit_state_and_gate_evidence(self):
        contract = adaptive.FlowContract(
            tier="deep",
            pre_score=63,
            goal_count=1,
            acceptance_owner="待确认",
            visual_qa="待确认",
            phase="需求整理中",
            state="需求整理中",
            completed_gates=("只读调查完成", "修改前评分已完成"),
            pending_gates=("详细总结已输出", "集中确认已完成"),
            allowed_next_actions=("继续整理需求",),
            forbidden_actions=("生成 /goal", "编辑实现源码"),
            entry_evidence=("用户需求已记录",),
            summary_output=False,
            summary_confirmed=False,
            acceptance_confirmed=False,
            prompt_status="未生成",
            artifact_audit=False,
            block_reason="不适用",
        )
        restored = adaptive.FlowContract.from_json(contract.to_json())
        self.assertEqual(contract, restored)

    def test_flow_contract_persists_entry_evidence_and_block_reason(self):
        contract = adaptive.FlowContract(
            tier="deep", pre_score=63, goal_count=1,
            acceptance_owner="Codex 真机测试", visual_qa="不涉及页面",
            phase="受阻", state="受阻",
            entry_evidence=("外部环境检查命令输出",),
            block_reason="真实设备未连接",
        )
        self.assertEqual(contract, adaptive.FlowContract.from_json(contract.to_json()))
        with self.assertRaises(ValueError):
            adaptive.FlowContract(
                tier="deep", pre_score=63, goal_count=1,
                acceptance_owner="Codex 真机测试", visual_qa="不涉及页面",
                phase="受阻", state="受阻",
            )

    def test_legacy_blocked_contract_gets_traceable_migration_reason(self):
        legacy = {
            "tier": "deep", "pre_score": 63, "goal_count": 1,
            "acceptance_owner": "Codex 真机测试", "visual_qa": "不涉及页面",
            "phase": "受阻", "state": "受阻",
        }
        restored = adaptive.FlowContract.from_dict(legacy)
        self.assertIn("历史合同迁移", restored.block_reason)

    def test_context_resume_rejects_goal_count_drift_without_new_evidence(self):
        contract = adaptive.FlowContract(
            tier="deep", pre_score=63, goal_count=1,
            acceptance_owner="Codex 真机测试", visual_qa="不涉及页面",
            phase="提示词已解锁", state="提示词已解锁",
        )
        failures = adaptive.flow_contract_failures(contract, goal_count=2)
        self.assertTrue(any("目标提示词数量" in failure for failure in failures))
        self.assertEqual([], adaptive.flow_contract_failures(
            contract, goal_count=2, post_score=75, upgrade_evidence=["范围扩大证据"]
        ))

    def test_state_transition_rejects_event_mismatch(self):
        contract = adaptive.FlowContract(
            tier="deep", pre_score=63, goal_count=1,
            acceptance_owner="待确认", visual_qa="待确认",
            phase="需求整理中", state="需求整理中",
        )
        failures = adaptive.flow_transition_failures(
            contract, target_state="待详细总结确认", event="开始写代码"
        )
        self.assertTrue(any("事件与目标状态不匹配" in failure for failure in failures))

    def test_goal_stage_blocks_cross_stage_state_transitions(self):
        cases = (
            ("deep", 2, 1, "documentation", "验收准备中", "编码已解锁", "编码解锁"),
            ("full-docs", 3, 1, "documentation", "产物审计中", "开发目标已解锁", "开发目标解锁"),
            ("full-docs", 3, 2, "development", "内部测试通过", "真机测试中", "开始真机测试"),
        )
        for tier, count, index, stage, state, target, event in cases:
            contract = adaptive.FlowContract(
                tier=tier, pre_score=65, base_goal_count=count, goal_count=count,
                goal_index=index, goal_stage=stage, ui_goal_enabled=False,
                acceptance_owner="Codex 真机测试", visual_qa="不涉及页面",
                phase=state, state=state, summary_output=True,
                summary_confirmed=True, acceptance_confirmed=True,
                prompt_status="已解锁", artifact_audit=True,
                completed_gates=adaptive.TIER_PRECODE_REQUIRED_GATES[tier],
            )
            failures = adaptive.flow_transition_failures(
                contract, target_state=target, event=event,
                evidence=list(adaptive.TIER_PRECODE_REQUIRED_GATES[tier]),
            )
            self.assertTrue(any("目标阶段" in item for item in failures), stage)

    def test_runtime_prompt_rejects_state_from_another_tier(self):
        prompt = self._valid_workflow_prompt("standard").replace(
            "当前状态：提示词已解锁", "当前状态：开发目标已解锁", 1
        )
        failures = adaptive.workflow_prompt_failures(prompt, tier="standard")
        self.assertTrue(any("不属于所选档位" in failure for failure in failures))

    def test_requirement_complete_event_cannot_unlock_prompt_directly(self):
        contract = adaptive.FlowContract(
            tier="deep",
            pre_score=63,
            goal_count=1,
            acceptance_owner="待确认",
            visual_qa="待确认",
            phase="需求整理中",
            state="需求整理中",
        )
        failures = adaptive.flow_transition_failures(
            contract,
            target_state="提示词已解锁",
            event="需求整理好了",
        )
        self.assertTrue(any("详细需求总结" in failure for failure in failures))

    def test_summary_output_must_precede_summary_confirmation_and_prompt_unlock(self):
        contract = adaptive.FlowContract(
            tier="deep",
            pre_score=63,
            goal_count=1,
            acceptance_owner="待确认",
            visual_qa="待确认",
            phase="待集中确认",
            state="待集中确认",
            summary_output=False,
        )
        failures = adaptive.flow_transition_failures(
            contract,
            target_state="提示词生成中",
            event="用户确认总结和验收责任",
        )
        self.assertTrue(any("总结已输出" in failure for failure in failures))

    def test_prompt_unlock_requires_acceptance_confirmation(self):
        contract = adaptive.FlowContract(
            tier="standard",
            pre_score=40,
            goal_count=1,
            acceptance_owner="待确认",
            visual_qa="不涉及页面",
            phase="待集中确认",
            state="待集中确认",
            summary_output=True,
            summary_confirmed=True,
            acceptance_confirmed=False,
        )
        failures = adaptive.flow_transition_failures(
            contract,
            target_state="提示词生成中",
            event="用户确认需求总结",
        )
        self.assertTrue(any("验收责任" in failure for failure in failures))

    def test_same_message_cannot_fake_summary_output_and_confirmation(self):
        contract = adaptive.FlowContract(
            tier="full-docs",
            pre_score=89,
            goal_count=1,
            acceptance_owner="待确认",
            visual_qa="待确认",
            phase="需求整理中",
            state="需求整理中",
        )
        failures = adaptive.flow_transition_failures(
            contract,
            target_state="提示词生成中",
            event="需求整理好了；本条同时确认总结无误并选择 Codex 真机测试",
        )
        self.assertTrue(any("同一条用户消息" in failure for failure in failures))

    def test_each_tier_rejects_skipping_its_required_precode_state(self):
        expected = {
            "light": "失败测试已确认 RED",
            "standard": "持久化模块任务清单",
            "deep": "全部微观任务写回",
            "full-docs": "文档与任务产物审计",
        }
        for tier, gate in expected.items():
            contract = adaptive.FlowContract(
                tier=tier,
                pre_score=60,
                goal_count=1,
                acceptance_owner="Codex 真机测试",
                visual_qa="不涉及页面",
                phase="提示词已解锁",
                state="提示词已解锁",
                summary_output=True,
                summary_confirmed=True,
                acceptance_confirmed=True,
            )
            failures = adaptive.flow_transition_failures(
                contract,
                target_state="编码已解锁",
                event="编码解锁",
                evidence=["依赖扫描完成"],
            )
            self.assertTrue(any(gate in failure for failure in failures), tier)

    def test_confirmation_rejects_noncanonical_wrapped_option(self):
        option = adaptive.build_prompt_option("临时自定义测试")
        failures = adaptive.confirmation_delivery_failures(
            "需求整理得对不对？改完后怎么测试？",
            [option],
            prompt_generating=True,
        )
        self.assertTrue(any("canonical builder" in failure for failure in failures))

    def test_native_and_text_confirmation_sets_share_canonical_builder(self):
        self.assertEqual(tuple(adaptive.PAGE_OPTIONS), adaptive.canonical_confirmation_options("page"))
        self.assertEqual(tuple(adaptive.FULL_FLOW_OPTIONS), adaptive.canonical_confirmation_options("full-flow"))
        with self.assertRaises(ValueError):
            adaptive.canonical_confirmation_options("temporary")

    def test_ui_route_uses_two_valid_native_selectors_or_one_plain_text_fallback(self):
        stages = (
            ("ui-route-primary", adaptive.UI_ROUTE_PRIMARY_OPTIONS, ["generate-prompt", "generate-prompt", "continue"]),
            ("ui-route-advanced", adaptive.UI_ROUTE_ADVANCED_OPTIONS, ["generate-prompt"] * 3),
        )
        for kind, options, actions in stages:
            self.assertEqual(
                [],
                adaptive.confirmation_delivery_failures(
                    "请选择 UI 路线",
                    options,
                    descriptions=["普通文本说明"] * len(options),
                    confirmation_kind=kind,
                    option_actions=actions,
                    prompt_generating=True,
                ),
            )
        fallback = "\n\n".join(
            f"选项{'一二三四五'[index]}：{option}"
            for index, option in enumerate(adaptive.UI_ROUTE_OPTIONS)
        )
        self.assertEqual(
            [], adaptive.text_confirmation_fallback_failures(fallback, adaptive.UI_ROUTE_OPTIONS)
        )

    def test_artifact_audit_requires_real_non_placeholder_diff(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            artifact = root / "04-开发追踪.md"
            artifact.write_text(
                "任务基线：模块任务、影响文件、依赖、测试和完成条件已写入真实文件，并附有可核对证据。",
                encoding="utf-8",
            )
            failures = adaptive.runtime_artifact_failures(
                "deep", [artifact], changed_paths=[artifact], root=root
            )
            self.assertEqual([], failures)
            failures = adaptive.runtime_artifact_failures("deep", [artifact], root=root)
            self.assertTrue(any("真实 diff" in failure for failure in failures))

    def test_cli_validates_real_prompt_and_failure_fixture(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            valid = root / "valid.md"
            valid.write_text(self._valid_workflow_prompt("deep"), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                status = adaptive.main(["--prompt-file", str(valid), "--prompt-tier", "deep"])
            self.assertEqual(0, status)
            self.assertIn("passed", output.getvalue())

            invalid = root / "invalid.md"
            invalid.write_text(
                (adaptive.ROOT / "tests/fixtures/deep-goal-runtime-failure.md").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                status = adaptive.main(["--prompt-file", str(invalid), "--prompt-tier", "deep"])
            self.assertEqual(1, status)
            self.assertIn("运行时门禁缺少阶段：受影响文档真实 diff", output.getvalue())
            failures = adaptive.workflow_prompt_failures(invalid.read_text(encoding="utf-8"), tier="deep")
            self.assertTrue(any("详细需求总结" in failure or "总结已输出" in failure for failure in failures))
            self.assertTrue(any("验收责任" in failure for failure in failures))

    def test_cli_confirmation_payload_rejects_split_and_accepts_canonical(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "confirmation.json"
            path.write_text(
                json.dumps(
                    {"question": "验收责任需要现在确认", "options": ["Codex 真机测试", "我自己测试"], "descriptions": ["Codex 执行", "用户执行"], "prompt_generating": True},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                status = adaptive.main(["--confirmation-file", str(path)])
            self.assertEqual(1, status)
            self.assertIn("确认问题必须同时确认需求", output.getvalue())

            path.write_text(
                json.dumps(
                    {"question": "需求整理得对不对？改完后怎么测试？", "options": adaptive.DEEP_NON_PAGE_OPTIONS, "descriptions": ["Codex 执行真机测试", "用户自行验收", "重新判断流程"], "prompt_generating": True},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                status = adaptive.main(["--confirmation-file", str(path)])
            self.assertEqual(0, status)

    def test_cli_state_transition_file_rejects_skipped_summary_gate(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "transition.json"
            contract = adaptive.FlowContract(
                tier="deep",
                pre_score=63,
                goal_count=1,
                acceptance_owner="待确认",
                visual_qa="待确认",
                phase="需求整理中",
                state="需求整理中",
            )
            path.write_text(
                json.dumps(
                    {
                        "contract": contract.to_dict(),
                        "target_state": "提示词已解锁",
                        "event": "需求整理好了",
                        "evidence": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                status = adaptive.main(["--state-transition-file", str(path)])
            self.assertEqual(1, status)
            self.assertIn("详细需求总结", output.getvalue())

    def test_cli_state_transition_file_accepts_next_state_with_evidence(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "transition.json"
            contract = adaptive.FlowContract(
                tier="deep",
                pre_score=63,
                goal_count=1,
                acceptance_owner="待确认",
                visual_qa="待确认",
                phase="需求整理中",
                state="需求整理中",
            )
            path.write_text(
                json.dumps(
                    {
                        "contract": contract.to_dict(),
                        "target_state": "待详细总结确认",
                        "event": "需求整理好了",
                        "evidence": ["用户明确说需求整理好了"],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            output = io.StringIO()
            with redirect_stdout(output):
                status = adaptive.main(["--state-transition-file", str(path)])
            self.assertEqual(0, status)
            self.assertIn("passed", output.getvalue())

    def test_copyable_prompt_delivery_requires_one_fenced_block(self):
        body = self._valid_executable_prompt()
        delivery = f"下面是可直接执行的提示词。\n\n```text\n{body}\n```"
        self.assertEqual([], adaptive.prompt_delivery_failures(delivery))
        failures = adaptive.prompt_delivery_failures(delivery + "\n\n```text\n补充要求\n```")
        self.assertTrue(any("一个独立 Markdown 代码块" in failure for failure in failures))

    def test_instance_repair_prompt_delivery_uses_special_validator(self):
        from scripts import check_codex_ui_flow_docs as ui_check

        body = (ui_check.ROOT / ui_check.STITCH_REPAIR_TEMPLATE).read_text(encoding="utf-8")
        delivery = f"直接复制下面的实例级复修提示词。\n\n```text\n{body}\n```"
        self.assertEqual(
            [],
            adaptive.prompt_delivery_failures(
                delivery,
                prompt_kind="stitch-instance-repair",
            ),
        )

    def test_copyable_prompt_delivery_rejects_requirements_after_block(self):
        body = self._valid_executable_prompt()
        delivery = f"请执行：\n```text\n{body}\n```\n还要运行全部测试。"
        failures = adaptive.prompt_delivery_failures(delivery)
        self.assertTrue(any("代码块后" in failure for failure in failures))

    def test_copyable_prompt_delivery_rejects_nested_fences(self):
        body = self._valid_executable_prompt() + "\n```js\nconst value = 1;\n```"
        delivery = f"请执行：\n```text\n{body}\n```"
        failures = adaptive.prompt_delivery_failures(delivery)
        self.assertTrue(any("一个独立 Markdown 代码块" in failure for failure in failures))

    def test_executable_prompt_no_longer_requires_3000_character_minimum(self):
        prompt = self._valid_executable_prompt(filler="完整视觉维度核对。" * 70)
        self.assertLess(len(prompt), 3000)
        self.assertEqual([], adaptive.executable_prompt_failures(prompt))

    def test_invalid_user_requested_tier_is_rejected(self):
        with self.assertRaises(ValueError):
            adaptive.route_tier(
                (0, 0, 0, 0, 0),
                user_requested="快速流程",
            )

    def test_critical_unknown_routes_to_deep_minimum(self):
        self.assertEqual(
            "深度流程",
            adaptive.route_tier(
                (0, 0, 2, 0, 0),
                critical_unknown=True,
            ),
        )

    def test_tilde_fence_cannot_hide_bold_status(self):
        text = "~~~text\n**当前流程：轻量流程（10/100）**\n~~~\n"
        failures = adaptive.fenced_status_failures("sample.md", text)
        self.assertTrue(failures)

    def test_score_table_parser_accepts_current_contract(self):
        text = (adaptive.ROOT / "references/四档自适应流程.md").read_text(
            encoding="utf-8"
        )
        self.assertEqual([], adaptive.score_table_failures(text))

    def test_score_bands_use_0_to_100_boundaries(self):
        expected = {
            0: "轻量流程",
            35: "轻量流程",
            36: "标准流程",
            69: "标准流程",
            70: "深度流程",
            89: "深度流程",
            90: "完整流程候选",
            100: "完整流程候选",
        }
        for total, tier in expected.items():
            self.assertEqual(tier, adaptive.score_band(total))

    def test_route_tier_requires_project_gate_for_full_flow(self):
        self.assertEqual("深度流程", adaptive.route_tier((18, 18, 18, 18, 18)))
        self.assertEqual("完整流程", adaptive.route_tier((14, 14, 14, 14, 14), full_gate=True))

    def test_small_scope_caps_routing_at_standard_without_overriding_safety(self):
        self.assertEqual(
            "标准流程",
            adaptive.route_tier((14, 14, 14, 14, 13), scope_cap="标准流程"),
        )
        self.assertEqual(
            "深度流程",
            adaptive.route_tier(
                (4, 4, 4, 14, 4),
                deep_gate=True,
                scope_cap="标准流程",
            ),
        )

    def test_task_scope_caps_match_user_facing_small_task_rules(self):
        self.assertEqual(
            "轻量流程",
            adaptive.scope_cap_for_task("老项目单文件局部修改"),
        )
        self.assertEqual(
            "标准流程",
            adaptive.scope_cap_for_task("老项目单模块小功能"),
        )
        self.assertEqual(
            "标准流程",
            adaptive.scope_cap_for_task("老项目单模块完整改造"),
        )
        self.assertEqual(
            "标准流程",
            adaptive.scope_cap_for_task("老项目简单多模块改造"),
        )
        self.assertEqual(
            "深度流程",
            adaptive.scope_cap_for_task("老项目复杂多模块改造"),
        )
        self.assertIsNone(adaptive.scope_cap_for_task("跨模块功能"))
        self.assertIsNone(adaptive.scope_cap_for_task("新项目或项目级改造"))

    def test_simple_multi_module_work_stays_standard(self):
        self.assertEqual(
            "标准流程",
            adaptive.route_tier(
                (8, 12, 12, 4, 8),
                scope_cap="标准流程",
            ),
        )

    def test_complex_multi_module_work_enters_deep(self):
        self.assertEqual(
            "深度流程",
            adaptive.route_tier(
                (10, 15, 15, 12, 12),
                task_scope="老项目复杂多模块改造",
            ),
        )

    def test_four_modules_alone_do_not_force_deep(self):
        self.assertEqual(
            "标准流程",
            adaptive.route_tier(
                (6, 12, 10, 5, 6),
                scope_cap="标准流程",
            ),
        )

    def test_score_90_without_project_gate_is_deep_execution(self):
        self.assertEqual(
            "深度流程",
            adaptive.route_tier((18, 18, 18, 18, 18)),
        )

    def test_project_full_gate_can_enter_full_below_score_90(self):
        self.assertEqual(
            "完整流程",
            adaptive.route_tier((4, 4, 4, 4, 4), full_gate=True),
        )
        self.assertEqual(
            "完整流程",
            adaptive.route_tier(
                (4, 4, 4, 4, 4),
                task_scope="新项目或项目级改造",
            ),
        )

    def test_deep_to_full_upgrade_requires_reconfirmation(self):
        self.assertTrue(adaptive.requires_full_reconfirmation("深度流程", "完整流程"))
        self.assertFalse(adaptive.requires_full_reconfirmation("标准流程", "深度流程"))
        self.assertFalse(adaptive.requires_full_reconfirmation("完整流程", "完整流程"))

    def test_full_flow_gate_cannot_be_bypassed_by_small_scope_cap(self):
        self.assertEqual(
            "完整流程",
            adaptive.route_tier(
                (14, 14, 14, 14, 14),
                full_gate=True,
                scope_cap="标准流程",
            ),
        )

    def test_explicit_full_flow_request_overrides_small_task_scope_cap(self):
        self.assertEqual(
            "完整流程",
            adaptive.route_tier(
                (2, 2, 2, 2, 2),
                scope_cap="标准流程",
                user_requested="完整流程",
            ),
        )

    def test_unknown_scores_are_not_counted_until_investigated(self):
        self.assertIsNone(adaptive.normalize_unknown(None))
        self.assertIsNone(adaptive.normalize_unknown(None, critical=True))

    def test_prompt_generating_options_use_skill_prefix_and_detail_suffix(self):
        actionable = (
            adaptive.PAGE_OPTIONS[:3]
            + adaptive.NON_PAGE_OPTIONS[:2]
            + adaptive.DEEP_PAGE_OPTIONS[:3]
            + adaptive.DEEP_NON_PAGE_OPTIONS[:2]
        )
        self.assertEqual(10, len(actionable))
        self.assertTrue(all(option.startswith(adaptive.OPTION_SKILL_PREFIX) for option in actionable))
        self.assertTrue(all(option.count(adaptive.OPTION_SKILL_PREFIX) == 1 for option in actionable))
        self.assertTrue(all(option.endswith(adaptive.OPTION_DETAIL_SUFFIX) for option in actionable))

        reroute_options = adaptive.NON_PAGE_OPTIONS[2:] + adaptive.DEEP_NON_PAGE_OPTIONS[2:]
        self.assertTrue(all(adaptive.OPTION_SKILL_PREFIX not in option for option in reroute_options))
        self.assertTrue(all(adaptive.OPTION_DETAIL_SUFFIX not in option for option in reroute_options))

    def test_ui_route_options_use_skill_prefix_and_detail_suffix(self):
        self.assertEqual(5, len(adaptive.UI_ROUTE_OPTIONS))
        self.assertIn("Codex 内嵌 Gemini 或其他生成的好看的模型生成前端 UI", adaptive.UI_ROUTE_OPTIONS[4])
        self.assertEqual(adaptive.OPTION_DETAIL_SUFFIX, "（额外要求：生成提示词里面的目标需求需要详细，不漏一点细节。）")
        self.assertTrue(all(option.startswith(adaptive.OPTION_SKILL_PREFIX) for option in adaptive.UI_ROUTE_OPTIONS))
        self.assertTrue(all(option.endswith(adaptive.OPTION_DETAIL_SUFFIX) for option in adaptive.UI_ROUTE_OPTIONS))

    def test_option_wrapper_validator_rejects_duplicate_prefix_and_bad_punctuation(self):
        duplicate_prefix = adaptive.UI_ROUTE_OPTIONS[0].replace(
            adaptive.OPTION_SKILL_PREFIX,
            adaptive.OPTION_SKILL_PREFIX * 2,
            1,
        )
        bad_punctuation = adaptive.UI_ROUTE_OPTIONS[1].removesuffix(
            adaptive.OPTION_DETAIL_SUFFIX
        ) + "（额外要求：生成提示词里面的目标需求需要详细，不漏一点细节）"
        failures = adaptive.option_wrapper_failures(
            [duplicate_prefix, bad_punctuation],
            expected_count=2,
        )
        self.assertTrue(any("exactly once" in failure for failure in failures))
        self.assertTrue(any("terminal detail suffix" in failure for failure in failures))

    def test_pressure_check_rejects_missing_fifth_ui_route(self):
        loaded = load_current_docs()
        rel = "references/功能3-高保真原型.md"
        loaded[rel] = loaded[rel].replace(adaptive.UI_ROUTE_OPTIONS[4], "")
        failures = adaptive.pressure_failures(loaded)
        self.assertTrue(any("UI route options are not synchronized" in failure for failure in failures))

    def test_pressure_check_rejects_embedded_route_semantic_drift(self):
        loaded = load_current_docs()
        rel = "references/功能3-高保真原型.md"
        loaded[rel] = loaded[rel].replace("OpenCodex 本地路由", "外部软件", 1)
        failures = adaptive.pressure_failures(loaded)
        self.assertTrue(any("embedded-model route semantics" in failure for failure in failures))

    def test_all_seventeen_prompt_generating_options_use_exact_wrappers(self):
        actionable = (
            adaptive.PAGE_OPTIONS[:3]
            + adaptive.NON_PAGE_OPTIONS[:2]
            + adaptive.DEEP_PAGE_OPTIONS[:3]
            + adaptive.DEEP_NON_PAGE_OPTIONS[:2]
            + adaptive.FULL_FLOW_OPTIONS
            + adaptive.UI_ROUTE_OPTIONS
        )
        self.assertEqual(17, len(actionable))
        self.assertTrue(all(option.startswith(adaptive.OPTION_SKILL_PREFIX) for option in actionable))
        self.assertTrue(all(option.count(adaptive.OPTION_SKILL_PREFIX) == 1 for option in actionable))
        self.assertTrue(all(option.endswith(adaptive.OPTION_DETAIL_SUFFIX) for option in actionable))

    def test_formal_prompt_templates_exclude_option_wrappers(self):
        for path in (adaptive.ROOT / "templates").glob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(adaptive.OPTION_SKILL_PREFIX, text, path.name)
            self.assertNotIn(adaptive.OPTION_DETAIL_SUFFIX, text, path.name)

    def test_copyable_tutorial_prompts_exclude_option_detail_suffix(self):
        markdown_files = (
            "references/提示词向导.md",
            "references/使用教程-常用提示词清单.md",
        )
        for rel in markdown_files:
            text = (adaptive.ROOT / rel).read_text(encoding="utf-8")
            fenced_bodies = re.findall(r"(?ms)^```[^\n]*\n(.*?)^```\s*$", text)
            self.assertTrue(fenced_bodies, rel)
            for body in fenced_bodies:
                self.assertNotIn(adaptive.OPTION_DETAIL_SUFFIX, body, rel)

        for rel in (
            "references/liran-plan-使用教程.html",
            "references/plan-docs-使用教程.html",
        ):
            text = (adaptive.ROOT / rel).read_text(encoding="utf-8")
            pre_bodies = re.findall(r"(?is)<pre[^>]*>(.*?)</pre>", text)
            self.assertTrue(pre_bodies, rel)
            for body in pre_bodies:
                self.assertNotIn(adaptive.OPTION_DETAIL_SUFFIX, body, rel)

    def test_active_docs_reject_legacy_score_examples(self):
        loaded = {"SKILL.md": "**当前流程：标准流程（4/10）**"}
        failures = adaptive.pressure_failures(loaded)
        self.assertTrue(any("0-10 score example" in failure for failure in failures))

    def test_skill_declares_every_project_level_full_flow_gate(self):
        text = (adaptive.ROOT / "SKILL.md").read_text(encoding="utf-8")
        for phrase in (
            "同时新增三个或以上独立功能模块",
            "大规模数据或技术栈迁移",
            "多个大型模块同时改造",
            "用户明确要求完整流程",
        ):
            self.assertIn(phrase, text)

    def test_score_table_parser_rejects_missing_dimension(self):
        text = (adaptive.ROOT / "references/四档自适应流程.md").read_text(
            encoding="utf-8"
        ).replace("| 验证复杂度 |", "| 验证难度 |", 1)
        failures = adaptive.score_table_failures(text)
        self.assertTrue(any("验证复杂度" in failure for failure in failures))

    def test_missing_local_markdown_link_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            failures = adaptive.markdown_link_failures(
                "docs/example.md",
                "[缺失文件](missing.md)",
                root=root,
            )
        self.assertTrue(failures)

    def test_missing_html_anchor_is_reported(self):
        failures = adaptive.html_anchor_failures(
            "example.html",
            '<a href="#missing">跳转</a><section id="present"></section>',
        )
        self.assertTrue(failures)

    def test_stale_current_version_is_reported(self):
        failures = adaptive.version_failures(
            {
                "README.md": "版本：`3.2`",
                "docs/技能设计文档.md": "# 技能设计文档：liran-plan 3.2",
                "SKILL.md": "当前版本 3.2",
                "references/liran-plan-使用教程.html": "<p>3.2 四档自适应</p>",
                "references/plan-docs-使用教程.html": "<p>3.2 四档自适应</p>",
                "references/使用教程-常用提示词清单.md": "3.2 核心",
            }
        )
        self.assertTrue(failures)

    def test_global_installation_check_detects_stale_prompt(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            base = Path(tmp_dir)
            root = base / "repo"
            codex_home = base / ".codex"
            root.mkdir()
            (root / "SKILL.md").write_text("skill", encoding="utf-8")
            (codex_home / "skills").mkdir(parents=True)
            (codex_home / "prompts").mkdir(parents=True)
            (codex_home / "skills" / "liran-plan").symlink_to(root)
            (codex_home / "skills" / "plan-docs").symlink_to(root)
            (codex_home / "prompts" / "liran-plan.md").write_text(
                "liran-plan 3.2",
                encoding="utf-8",
            )

            failures = adaptive.global_installation_failures(
                codex_home,
                root=root,
            )
        self.assertTrue(
            any(adaptive.CURRENT_VERSION in failure for failure in failures)
        )

    def test_new_project_mode_rejects_codex_only_completion_gate(self):
        failures = adaptive.legacy_wording_failures(
            "references/模式-新项目引导.md",
            "没有内部验证与真机实测通过，不要把模块标记为 `已完成`。",
        )
        self.assertTrue(failures)

    def test_mode_docs_reject_unconditional_real_device_handoff(self):
        new_project_failures = adaptive.legacy_wording_failures(
            "references/模式-新项目引导.md",
            "第一次 `/goal` 达到内部完成状态后，创建 `liran_docs/09-真机实测.md`，"
            "进入真实操作验证与问题回写闭环。",
        )
        old_project_failures = adaptive.legacy_wording_failures(
            "references/模式-老项目初始化.md",
            "开第一次 `/goal` 内部闭环，再走真机实测与回写（功能六）。",
        )
        self.assertTrue(new_project_failures)
        self.assertTrue(old_project_failures)

    def test_tutorial_prompts_reject_summary_confirmation_without_acceptance_owner(self):
        markdown_failures = adaptive.legacy_wording_failures(
            "references/使用教程-常用提示词清单.md",
            "先给我一份详细的需求整理总结让我确认；确认无误后，再给我一条提示词。",
        )
        html_failures = adaptive.legacy_wording_failures(
            "references/liran-plan-使用教程.html",
            "先给我一份详细的需求整理总结让我确认；确认无误后，再给我一条提示词。",
        )
        self.assertTrue(markdown_failures)
        self.assertTrue(html_failures)

    def test_full_flow_second_goal_respects_acceptance_owner(self):
        text = (adaptive.ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            "完整流程的最后验收目标按已确认的验收责任分支",
            text,
        )

    def test_deep_ui_only_runs_triggered_design_qa(self):
        text = (
            adaptive.ROOT / "references/功能3-高保真原型.md"
        ).read_text(encoding="utf-8")
        self.assertIn("已触发的 Design QA", text)

    def test_full_flow_summary_confirms_acceptance_owner_once(self):
        text = (adaptive.ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            "完整流程的验收责任和页面样式必须在同一个选择问题中确认",
            text,
        )

    def test_pressure_check_rejects_delayed_full_flow_acceptance_confirmation(self):
        loaded = {
            "SKILL.md": "完整流程第二次 `/goal` 按已确认的验收责任分支",
        }
        failures = adaptive.pressure_failures(loaded)
        self.assertTrue(any("S26" in failure for failure in failures))

    def test_full_flow_confirmation_contract_rejects_missing_wrappers_even_with_line_breaks(self):
        text = (
            "如果用户说需求整理好了，先给详细的需求整理总结。\n"
            "在同一个确认问题里选择 Codex 真机测试（额外要求：生成提示词里面的目标需求需要详细，不漏一点细节。）或我自己测试（额外要求：生成提示词里面的目标需求需要详细，不漏一点细节。）；\n"
            "确认总结和验收责任无误后再继续。"
        )
        failures = adaptive.pressure_failures({"SKILL.md": text})
        self.assertTrue(any("S26" in failure for failure in failures))

    def test_full_flow_confirmation_contract_rejects_summary_only_wording(self):
        text = (
            "完整流程的详细总结确认必须同时确认验收责任。\n"
            "如果用户说需求整理好了，先给详细的需求整理总结。\n"
            "确认无误后再继续。"
        )
        failures = adaptive.pressure_failures({"SKILL.md": text})
        self.assertTrue(any("S26" in failure for failure in failures))

    def test_full_flow_confirmation_ignores_formal_prompt_examples(self):
        text = (
            "需求整理结束后，先给详细的需求整理总结，"
            "在同一个确认问题里选择 $liran-plan Codex 真机测试"
            "（额外要求：生成提示词里面的目标需求需要详细，不漏一点细节。）或 $liran-plan 我自己测试"
            "（额外要求：生成提示词里面的目标需求需要详细，不漏一点细节。）；确认后继续。\n\n"
            "```text\n"
            "如果用户说需求整理好了，先给详细的需求整理总结，"
            "在同一个确认问题里选择 Codex 真机测试或我自己测试。\n"
            "```\n"
        )
        failures = adaptive.full_flow_confirmation_failures("guide.md", text)
        self.assertEqual([], failures)

    def test_full_flow_confirmation_checks_every_summary_entry(self):
        text = (
            "如果用户说需求整理好了，先给详细的需求整理总结，"
            "在同一个确认问题里选择 Codex 真机测试或我自己测试；"
            "确认总结和验收责任无误后再继续。\n\n"
            "如果用户说总结好了，先给详细的需求整理总结；"
            "确认无误后再继续。"
        )
        failures = adaptive.pressure_failures({"SKILL.md": text})
        self.assertTrue(any("S26" in failure for failure in failures))

    def test_unscoped_core_principle_cannot_force_full_requirement_summary(self):
        text = (
            "核心原则：\n\n"
            "需求没整理清楚前，不开干。\n"
            "每轮都先输出当前完整整理后的需求，再列新增、变更、待确认点。\n"
            "底层原则：按档位执行。\n"
        )
        failures = adaptive.pressure_failures({"SKILL.md": text})
        self.assertTrue(any("S27" in failure for failure in failures))

    def test_other_entry_cannot_force_multiround_requirement_clarification(self):
        text = (
            "6. **其他**：前 5 类以外的需求。"
            "先判断这类需求属于什么，再继续多轮需求整理。\n"
        )
        failures = adaptive.pressure_failures({"SKILL.md": text})
        self.assertTrue(any("S28" in failure for failure in failures))

    def test_unscoped_core_principle_rejects_semantic_rewording(self):
        text = (
            "核心原则：\n\n"
            "每轮均应给出当前完整需求和待确认事项。\n"
            "底层原则：按档位执行。\n"
        )
        failures = adaptive.pressure_failures({"SKILL.md": text})
        self.assertTrue(any("S27" in failure for failure in failures))

    def test_other_entry_rejects_semantic_multiround_rewording(self):
        text = (
            "6. **其他**：前 5 类以外的需求。"
            "识别任务类型后直接进入多轮整理。\n"
        )
        failures = adaptive.pressure_failures({"SKILL.md": text})
        self.assertTrue(any("S28" in failure for failure in failures))

    def test_scope_keywords_elsewhere_cannot_hide_unscoped_core_rule(self):
        text = (
            "核心原则：\n\n"
            "完整流程另见后文；每轮均应给出当前完整需求。\n"
            "底层原则：按档位执行。\n"
        )
        failures = adaptive.pressure_failures({"SKILL.md": text})
        self.assertTrue(any("S27" in failure for failure in failures))

    def test_routing_keywords_cannot_hide_forced_other_multiround_flow(self):
        text = (
            "6. **其他**：先了解四档和完整流程规则，"
            "但这类任务直接进入多轮整理。\n"
        )
        failures = adaptive.pressure_failures({"SKILL.md": text})
        self.assertTrue(any("S28" in failure for failure in failures))

    def test_confirmation_must_call_native_selector_when_available(self):
        loaded = {
            "SKILL.md": "显示一个 Codex 单选框；工具不可用时使用编号。",
            "references/提示词向导.md": "显示一个 Codex 单选框。",
            "references/四档自适应流程.md": "显示一个 Codex 单选框。",
        }
        failures = adaptive.pressure_failures(loaded)
        self.assertTrue(any("S29" in failure for failure in failures))

    def test_confirmed_selection_must_auto_deliver_prompt_same_turn(self):
        loaded = {
            "SKILL.md": "用户选择后可以生成提示词。",
            "references/提示词向导.md": "用户选择后可以生成提示词。",
            "references/四档自适应流程.md": "用户选择后可以生成提示词。",
        }
        failures = adaptive.pressure_failures(loaded)
        self.assertTrue(any("S30" in failure for failure in failures))

    def test_copyable_prompt_must_use_one_complete_fenced_block(self):
        loaded = {
            "SKILL.md": "提示词需要方便复制。",
            "references/提示词向导.md": "提示词需要方便复制。",
            "references/功能5-任务微观化与提示词.md": "提示词需要方便复制。",
        }
        failures = adaptive.pressure_failures(loaded)
        self.assertTrue(any("S31" in failure for failure in failures))

    def test_deep_goal_requires_full_document_to_acceptance_writeback_sequence(self):
        loaded = {
            "references/功能5-任务微观化与提示词.md": (
                "### 深度 /goal\n"
                "读取代码后直接实现，最后更新受影响文档。\n"
            )
        }
        failures = adaptive.pressure_failures(loaded)
        self.assertTrue(any("S32" in failure for failure in failures))

    def test_goal_requires_chrome_to_computer_fallback_without_user_handoff(self):
        loaded = {
            "SKILL.md": "Codex 真机测试时优先使用 @Chrome。",
            "references/功能5-任务微观化与提示词.md": "按已确认验收责任执行。",
            "references/功能6-真机实测与回写.md": "使用 @Chrome 真实操作。",
        }
        failures = adaptive.pressure_failures(loaded)
        self.assertTrue(any("S33" in failure for failure in failures))

    def test_explicit_full_delegation_disables_confirmation_and_user_handoff(self):
        loaded = {
            "SKILL.md": "用户授权 Codex 真机测试。",
            "references/提示词向导.md": "使用一个 Codex 单选框。",
            "references/功能6-真机实测与回写.md": "只有硬性阻塞时请求用户介入。",
        }
        failures = adaptive.pressure_failures(loaded)
        self.assertTrue(any("S34" in failure for failure in failures))

    def test_explicit_user_self_test_overrides_full_delegation_default(self):
        loaded = {
            "SKILL.md": "全权托管模式下默认由 Codex 测试。",
            "references/提示词向导.md": "不再显示验收选择框。",
            "references/功能6-真机实测与回写.md": "客观阻塞只记录为受阻。",
        }
        failures = adaptive.pressure_failures(loaded)
        self.assertTrue(any("S35" in failure for failure in failures))

    def test_full_delegation_cannot_bypass_stitch_repair(self):
        loaded = {
            "references/功能3-高保真原型.md": (
                "Stitch 路线不调用 Product Design Design QA\n"
                "可以进入实例级细节复修\n"
                "初次承接受阻\n"
                "复修通过后才允许生成业务接线 /goal\n"
                "其他 Product Design 路线仍保留 Design QA\n"
            ),
            "references/四档自适应流程.md": "全权托管可以直接接业务。",
        }

        failures = adaptive.pressure_failures(loaded)
        self.assertTrue(any("unattended mode" in failure for failure in failures))

    def test_tutorial_cannot_restore_text_only_confirmation_handoff(self):
        failures = adaptive.legacy_wording_failures(
            "references/liran-plan-使用教程.html",
            "用一个 Codex 单选框同时确认需求；我确认后只生成一条对应档位的 /goal。",
        )
        self.assertTrue(failures)

    def test_concrete_project_changes_create_task_document_but_read_only_requests_do_not(self):
        for task in (
            "帮我修 Bug",
            "新增功能",
            "优化现有功能",
            "删除旧功能",
            "重构模块",
            "继续上次开发",
            "整理需求",
            "修改 UI 和 API",
            "数据迁移与发布",
        ):
            self.assertTrue(adaptive.should_create_task_document(task), task)

        for task in ("解释一下代码", "查询当前状态", "只读审查", "知识问答"):
            self.assertFalse(adaptive.should_create_task_document(task), task)
        self.assertFalse(
            adaptive.should_create_task_document("修复 Bug", writes_forbidden=True)
        )
        self.assertTrue(
            adaptive.should_create_task_document("先解释原因，再修复这个 Bug")
        )
        self.assertFalse(
            adaptive.should_create_task_document("只解释一下这个 Bug 应该如何修复")
        )
        self.assertTrue(adaptive.should_create_task_document("修复这个 Bug，不要修改其他模块"))
        self.assertTrue(adaptive.should_create_task_document("优化功能，不要写无关文件"))
        self.assertTrue(adaptive.should_create_task_document("先只读调查，然后修复 Bug"))
        self.assertTrue(adaptive.should_create_task_document("先只解释根因，然后修复 Bug"))
        self.assertFalse(adaptive.should_create_task_document("修复这个 Bug，但不要修改任何文件"))

    def test_lifecycle_directory_resolution_uses_declared_priority_and_never_guesses(self):
        self.assertEqual(
            Path("/user/requirements"),
            adaptive.resolve_lifecycle_directory(
                user_path="/user/requirements",
                agents_path="/agents/requirements",
                index_path="/index/requirements",
                existing_path="/existing/requirements",
            ),
        )
        self.assertEqual(
            Path("/index/requirements"),
            adaptive.resolve_lifecycle_directory(
                index_path="/index/requirements",
                existing_path="/existing/requirements",
            ),
        )
        self.assertIsNone(adaptive.resolve_lifecycle_directory())

    def test_task_document_requires_complete_schema_and_stable_task_id(self):
        valid = "\n".join(
            f"{field}：有效内容" for field in adaptive.TASK_DOCUMENT_REQUIRED_FIELDS
        ).replace("任务 ID：有效内容", "任务 ID：TASK-20260902-01", 1)
        self.assertEqual([], adaptive.task_document_failures(valid))

        missing = valid.replace("验收标准：有效内容\n", "", 1)
        failures = adaptive.task_document_failures(missing)
        self.assertTrue(any("验收标准" in failure for failure in failures))

    def test_task_document_accepts_filled_markdown_sections_and_rejects_template_placeholders(self):
        metadata = "\n".join(
            f"- {field}：真实内容"
            for field in adaptive.TASK_DOCUMENT_REQUIRED_FIELDS[:7]
        ).replace("任务 ID：真实内容", "任务 ID：TASK-1", 1)
        sections = "\n\n".join(
            f"## {field}\n\n已确认的真实内容。"
            for field in adaptive.TASK_DOCUMENT_REQUIRED_FIELDS[7:]
        )
        self.assertEqual([], adaptive.task_document_failures(metadata + "\n\n" + sections))

        template = (adaptive.ROOT / "templates/需求整理工作文档.md").read_text(
            encoding="utf-8"
        )
        failures = adaptive.task_document_failures(template)
        self.assertTrue(any("占位" in failure or "稳定任务 ID" in failure for failure in failures))

    def test_flow_contract_round_trips_task_document_and_archive_context(self):
        contract = adaptive.FlowContract(
            tier="deep",
            pre_score=62,
            goal_count=1,
            acceptance_owner="Codex 真机测试",
            visual_qa="不涉及页面",
            phase="归档中",
            state="归档中",
            task_id="TASK-20260902-01",
            requirements_path="liran_docs/requirements/TASK-20260902-01.md",
            archive_path="liran_docs/archive/TASK-20260902-01/归档.md",
            archive_state="归档中",
        )
        self.assertEqual(contract, adaptive.FlowContract.from_json(contract.to_json()))

    def test_archive_state_recovery_requires_task_id_and_paths(self):
        contract = adaptive.FlowContract(
            tier="deep",
            pre_score=62,
            goal_count=1,
            acceptance_owner="Codex 真机测试",
            visual_qa="不涉及页面",
            phase="归档中",
            state="归档中",
            archive_state="归档中",
        )
        failures = adaptive.flow_contract_failures(contract)
        self.assertTrue(any("任务 ID" in failure for failure in failures))
        self.assertTrue(any("需求工作文档路径" in failure for failure in failures))
        self.assertTrue(any("归档路径" in failure for failure in failures))

    def test_completed_flow_contract_requires_archived_task_context(self):
        contract = adaptive.FlowContract(
            tier="deep",
            pre_score=62,
            goal_count=1,
            acceptance_owner="Codex 真机测试",
            visual_qa="不涉及页面",
            phase="已完成",
            state="已完成",
            archive_state="未开始",
        )
        failures = adaptive.flow_contract_failures(contract, resumed_tier="deep")
        self.assertTrue(any("已归档" in failure for failure in failures))
        self.assertTrue(any("任务 ID" in failure for failure in failures))

    def test_archive_lifecycle_rejects_unknown_contract_enums(self):
        payload = {
            "task_id": "TASK-1",
            "goal_stage": "typo",
            "acceptance_owner": "",
            "source_state": "真机测试通过",
            "archive_state": "已归档 typo",
            "final_state": "未完成",
            "artifact_task_ids": ["TASK-1"],
            "steps": [],
            "cleanup_performed": False,
        }
        failures = adaptive.archive_lifecycle_failures(payload)
        for expected in ("目标阶段", "验收责任", "归档状态"):
            self.assertTrue(any(expected in failure for failure in failures), expected)

    def test_both_acceptance_branches_can_enter_archive(self):
        for acceptance_owner, state, event in (
            ("Codex 真机测试", "真机测试通过", "开始归档"),
            ("用户自己测试", "用户验收通过", "开始归档"),
        ):
            contract = adaptive.FlowContract(
                tier="deep",
                pre_score=62,
                goal_count=1,
                acceptance_owner=acceptance_owner,
                visual_qa="不涉及页面",
                phase="待用户检查",
                state="待用户检查",
                task_id="TASK-1",
                requirements_path="liran_docs/requirements/TASK-1.md",
                archive_path="liran_docs/archive/TASK-1/归档.md",
                user_archive_confirmation=True,
                archive_confirmation_evidence="用户明确回复归档",
            )
            self.assertEqual(
                [],
                adaptive.flow_transition_failures(
                    contract,
                    target_state="归档中",
                    event=event,
                ),
            )

    def test_self_test_wording_uses_user_acceptance_branch(self):
        contract = adaptive.FlowContract(
            tier="deep",
            pre_score=62,
            goal_count=1,
            acceptance_owner="我自己测试",
            visual_qa="不涉及页面",
            phase="修改后复评中",
            state="修改后复评中",
            acceptance_confirmed=True,
        )
        self.assertEqual(
            [],
            adaptive.flow_transition_failures(
                contract,
                target_state="用户验收通过",
                event="用户验收通过",
            ),
        )
        failures = adaptive.flow_transition_failures(
            contract,
            target_state="真机测试通过",
            event="真机测试通过",
        )
        self.assertTrue(any("验收责任" in failure for failure in failures))

    def test_completed_transition_requires_consistent_archive_context(self):
        contract = adaptive.FlowContract(
            tier="deep",
            pre_score=62,
            goal_count=1,
            acceptance_owner="Codex 真机测试",
            visual_qa="不涉及页面",
            phase="已归档",
            state="已归档",
            archive_state="未开始",
        )
        failures = adaptive.flow_transition_failures(
            contract,
            target_state="已完成",
            event="完成",
        )
        self.assertTrue(any("已归档" in failure for failure in failures))
        self.assertTrue(any("任务 ID" in failure for failure in failures))

    def test_state_transition_cannot_jump_from_start_to_acceptance_passed(self):
        contract = adaptive.FlowContract(
            tier="deep",
            pre_score=62,
            goal_count=1,
            acceptance_owner="Codex 真机测试",
            visual_qa="不涉及页面",
            phase="未开始",
            state="未开始",
        )
        failures = adaptive.flow_transition_failures(
            contract,
            target_state="真机测试通过",
            event="真机测试通过",
        )
        self.assertTrue(any("不能跳" in failure or "不合法" in failure for failure in failures))

    def test_archive_lifecycle_accepts_codex_and_user_acceptance_branches(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            requirement = root / "requirements" / "TASK-1.md"
            archive = root / "archive" / "TASK-1" / "归档.md"
            requirement.parent.mkdir()
            archive.parent.mkdir(parents=True)
            requirement.write_text(self._valid_task_document(), encoding="utf-8")
            archive.write_text("# TASK-1 · 任务归档\n任务 ID：TASK-1\n归档状态：已归档\n", encoding="utf-8")
            payload = {
                "task_id": "TASK-1",
                "goal_stage": "final",
                "acceptance_owner": "Codex 真机测试",
                "source_state": "真机测试通过",
                "archive_state": "已归档",
                "final_state": "已完成",
                "user_archive_confirmation": True,
                "archive_confirmation_evidence": "用户明确回复归档",
                "archive_confirmation_at": "2026-09-13",
                "archive_trigger_source": "用户明确归档确认",
                "requirements_path": str(requirement),
                "archive_path": str(archive),
                "artifact_task_ids": ["TASK-1", "TASK-1", "TASK-1"],
                "unresolved_states": [],
                "steps": list(adaptive.ARCHIVE_SAFE_STEPS),
                "cleanup_performed": True,
                "other_active_tasks_preserved": True,
                "active_task_ids_before": ["TASK-1", "TASK-2"],
                "active_task_ids_after": ["TASK-2"],
                "current_index_valid": True,
                "completed_residue_absent": True,
                "scan_archive": False,
            }
            self.assertEqual([], adaptive.archive_lifecycle_failures(payload, root=root))

            payload["acceptance_owner"] = "用户自己测试"
            payload["source_state"] = "用户验收通过"
            self.assertEqual([], adaptive.archive_lifecycle_failures(payload, root=root))

    def test_archive_lifecycle_compares_active_task_ids_before_and_after(self):
        payload = {
            "task_id": "TASK-1",
            "goal_stage": "final",
            "acceptance_owner": "Codex 真机测试",
            "source_state": "真机测试通过",
            "archive_state": "已归档",
            "final_state": "已完成",
            "requirements_path": "/missing/requirements.md",
            "archive_path": "/missing/archive.md",
            "artifact_task_ids": ["TASK-1"],
            "unresolved_states": [],
            "steps": list(adaptive.ARCHIVE_SAFE_STEPS),
            "cleanup_performed": True,
            "other_active_tasks_preserved": True,
            "active_task_ids_before": ["TASK-1", "TASK-2", "TASK-3"],
            "active_task_ids_after": ["TASK-3"],
            "current_index_valid": True,
            "completed_residue_absent": True,
            "scan_archive": False,
        }
        failures = adaptive.archive_lifecycle_failures(payload)
        self.assertTrue(any("活动任务 ID" in failure for failure in failures))

    def test_archive_lifecycle_rejects_unrelated_existing_files_and_false_cleanup_claim(self):
        payload = {
            "task_id": "TASK-NOT-IN-FILES",
            "goal_stage": "final",
            "acceptance_owner": "Codex 真机测试",
            "source_state": "真机测试通过",
            "archive_state": "已归档",
            "final_state": "已完成",
            "requirements_path": str(adaptive.ROOT / "SKILL.md"),
            "archive_path": str(adaptive.ROOT / "README.md"),
            "artifact_task_ids": [],
            "unresolved_states": [],
            "steps": list(adaptive.ARCHIVE_SAFE_STEPS),
            "cleanup_performed": False,
            "other_active_tasks_preserved": True,
            "current_index_valid": True,
            "completed_residue_absent": True,
            "scan_archive": False,
        }
        failures = adaptive.archive_lifecycle_failures(payload)
        for expected in ("任务 ID", "清理", "正文"):
            self.assertTrue(any(expected in failure for failure in failures), expected)

    def test_archive_lifecycle_rejects_truthy_false_strings_and_non_archive_files(self):
        payload = {
            "task_id": "liran-plan",
            "goal_stage": "final",
            "acceptance_owner": "Codex 真机测试",
            "source_state": "真机测试通过",
            "archive_state": "已归档",
            "final_state": "已完成",
            "requirements_path": str(adaptive.ROOT / "SKILL.md"),
            "archive_path": str(adaptive.ROOT / "README.md"),
            "artifact_task_ids": ["liran-plan"],
            "unresolved_states": [],
            "steps": list(adaptive.ARCHIVE_SAFE_STEPS),
            "cleanup_performed": "false",
            "other_active_tasks_preserved": "false",
            "active_task_ids_before": ["liran-plan"],
            "active_task_ids_after": [],
            "current_index_valid": "false",
            "completed_residue_absent": "false",
            "scan_archive": "false",
            "archive_scan_reason": "用户要求",
        }
        failures = adaptive.archive_lifecycle_failures(payload)
        self.assertTrue(any("布尔" in failure for failure in failures))
        self.assertTrue(any("需求工作文档结构" in failure for failure in failures))
        self.assertTrue(any("归档正文" in failure for failure in failures))

    def test_archive_lifecycle_rejects_unresolved_or_mismatched_task_data(self):
        payload = {
            "task_id": "TASK-1",
            "goal_stage": "final",
            "acceptance_owner": "Codex 真机测试",
            "source_state": "待复测",
            "archive_state": "已归档",
            "final_state": "已完成",
            "requirements_path": "/missing/requirements.md",
            "archive_path": "/missing/archive.md",
            "artifact_task_ids": ["TASK-1", "TASK-2"],
            "unresolved_states": ["待复测"],
            "steps": list(adaptive.ARCHIVE_SAFE_STEPS),
            "cleanup_performed": True,
            "other_active_tasks_preserved": False,
            "current_index_valid": False,
            "completed_residue_absent": False,
            "scan_archive": False,
        }
        failures = adaptive.archive_lifecycle_failures(payload)
        for expected in ("验收通过", "未解决", "任务 ID", "其他活动任务", "归档路径"):
            self.assertTrue(any(expected in failure for failure in failures), expected)

    def test_archive_failure_preserves_active_content_and_rejects_cleanup(self):
        payload = {
            "task_id": "TASK-1",
            "goal_stage": "final",
            "acceptance_owner": "Codex 真机测试",
            "source_state": "真机测试通过",
            "archive_state": "归档受阻",
            "final_state": "未完成",
            "requirements_path": "/missing/requirements.md",
            "archive_path": "/missing/archive.md",
            "artifact_task_ids": ["TASK-1"],
            "unresolved_states": [],
            "steps": ["长期事实已更新"],
            "cleanup_performed": True,
            "other_active_tasks_preserved": True,
            "current_index_valid": True,
            "completed_residue_absent": False,
            "scan_archive": False,
        }
        failures = adaptive.archive_lifecycle_failures(payload)
        self.assertTrue(any("归档受阻" in failure and "清理" in failure for failure in failures))

    def test_archive_lifecycle_rejects_cleanup_before_archive_validation(self):
        payload = {
            "task_id": "TASK-1",
            "goal_stage": "final",
            "acceptance_owner": "Codex 真机测试",
            "source_state": "真机测试通过",
            "archive_state": "归档中",
            "final_state": "未完成",
            "requirements_path": "/requirements.md",
            "archive_path": "/archive.md",
            "artifact_task_ids": ["TASK-1"],
            "unresolved_states": [],
            "steps": ["长期事实已更新", "活动区已按任务 ID 清理"],
            "cleanup_performed": True,
            "other_active_tasks_preserved": True,
            "current_index_valid": True,
            "completed_residue_absent": False,
            "scan_archive": False,
        }
        failures = adaptive.archive_lifecycle_failures(payload)
        self.assertTrue(any("先创建并验证归档" in failure for failure in failures))

    def test_unresolved_or_closed_archive_cannot_cleanup_without_real_archive(self):
        base = {
            "task_id": "TASK-1",
            "goal_stage": "final",
            "acceptance_owner": "Codex 真机测试",
            "source_state": "待实测",
            "archive_state": "归档中",
            "final_state": "未完成",
            "requirements_path": "/missing/requirements.md",
            "archive_path": "/missing/archive.md",
            "artifact_task_ids": ["TASK-1"],
            "unresolved_states": ["待实测"],
            "steps": list(adaptive.ARCHIVE_SAFE_STEPS),
            "cleanup_performed": True,
            "other_active_tasks_preserved": True,
            "active_task_ids_before": ["TASK-1"],
            "active_task_ids_after": [],
            "current_index_valid": True,
            "completed_residue_absent": True,
        }
        failures = adaptive.archive_lifecycle_failures(base)
        self.assertTrue(any("未解决" in failure and "清理" in failure for failure in failures))
        self.assertTrue(any("归档路径" in failure for failure in failures))

        base.update(
            archive_state="已取消",
            source_state="已取消",
            unresolved_states=[],
            cleanup_performed=False,
            steps=[],
        )
        failures = adaptive.archive_lifecycle_failures(base)
        self.assertTrue(any("归档路径" in failure for failure in failures))

    def test_cancel_pause_and_replacement_must_not_be_reported_completed(self):
        for archive_state in ("已取消", "暂停归档", "被新任务替代"):
            payload = {
                "task_id": "TASK-1",
                "goal_stage": "final",
                "acceptance_owner": "Codex 真机测试",
                "source_state": archive_state,
                "archive_state": archive_state,
                "final_state": "已完成",
                "requirements_path": "/requirements.md",
                "archive_path": "/archive.md",
                "artifact_task_ids": ["TASK-1"],
                "unresolved_states": [],
                "steps": [],
                "cleanup_performed": False,
                "other_active_tasks_preserved": True,
                "active_task_ids_before": ["TASK-1", "TASK-2"],
                "active_task_ids_after": ["TASK-2"],
                "current_index_valid": True,
                "completed_residue_absent": True,
                "scan_archive": False,
            }
            failures = adaptive.archive_lifecycle_failures(payload)
            self.assertTrue(any("不得标记为已完成" in failure for failure in failures))

    def test_archive_history_is_ignored_unless_a_trace_reason_is_explicit(self):
        payload = {"scan_archive": True, "archive_scan_reason": ""}
        failures = adaptive.archive_lifecycle_failures(payload)
        self.assertTrue(any("历史归档默认不参与" in failure for failure in failures))
        payload["archive_scan_reason"] = "回归测试"
        failures = adaptive.archive_lifecycle_failures(payload)
        self.assertFalse(any("历史归档默认不参与" in failure for failure in failures))

    def test_final_goal_requires_archive_contract_and_full_first_goal_forbids_it(self):
        final_prompt = self._valid_workflow_prompt("deep")
        failures = adaptive.workflow_prompt_failures(
            final_prompt,
            tier="deep",
            archive_stage="final",
        )
        self.assertEqual([], failures)

        full_first = self._valid_workflow_prompt("full-docs") + "\n归档中：执行最终归档。"
        failures = adaptive.workflow_prompt_failures(
            full_first,
            tier="full-docs",
            archive_stage="full-first",
        )
        self.assertTrue(any("中间目标禁止" in failure for failure in failures))

    def test_single_goal_tiers_require_archive_contract_without_optional_flag(self):
        for tier in ("light", "standard", "deep"):
            failures = adaptive.workflow_prompt_failures(
                self._valid_workflow_prompt(tier),
                tier=tier,
            )
            self.assertEqual([], failures, tier)

    def test_final_goal_accepts_complete_archive_contract(self):
        prompt = self._valid_workflow_prompt("deep")
        self.assertEqual(
            [],
            adaptive.workflow_prompt_failures(
                prompt,
                tier="deep",
                archive_stage="final",
            ),
        )

    def test_final_goal_rejects_empty_placeholder_fields_and_wrong_archive_order(self):
        prompt = self._valid_workflow_prompt("deep")
        placeholder = prompt.replace("当前目标暂不执行正式归档", "当前目标执行正式归档", 1)
        failures = adaptive.workflow_prompt_failures(placeholder, tier="deep")
        self.assertTrue(any("暂不执行正式归档" in failure for failure in failures))

        wrong_order = prompt.replace(
            "当前目标暂不执行正式归档，不清理活动文档。",
            "当前目标自动创建归档并更新归档索引。",
            1,
        )
        failures = adaptive.workflow_prompt_failures(wrong_order, tier="deep")
        self.assertTrue(any("自动归档" in failure for failure in failures))
        self.assertEqual(
            [],
            adaptive.workflow_prompt_failures(
                self._valid_workflow_prompt("full-docs"),
                tier="full-docs",
                archive_stage="full-first",
            ),
        )

    def test_cli_validates_real_archive_contract_fixture(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            requirement = root / "requirements.md"
            archive = root / "archive.md"
            requirement.write_text(self._valid_task_document(), encoding="utf-8")
            archive.write_text("# TASK-1 · 任务归档\n任务 ID：TASK-1\n归档状态：已归档\n", encoding="utf-8")
            payload = {
                "task_id": "TASK-1",
                "goal_stage": "final",
                "acceptance_owner": "Codex 真机测试",
                "source_state": "真机测试通过",
                "archive_state": "已归档",
                "final_state": "已完成",
                "user_archive_confirmation": True,
                "archive_confirmation_evidence": "用户明确回复归档",
                "archive_confirmation_at": "2026-09-13",
                "archive_trigger_source": "用户明确归档确认",
                "requirements_path": str(requirement),
                "archive_path": str(archive),
                "artifact_task_ids": ["TASK-1"],
                "unresolved_states": [],
                "steps": list(adaptive.ARCHIVE_SAFE_STEPS),
                "cleanup_performed": True,
                "other_active_tasks_preserved": True,
                "active_task_ids_before": ["TASK-1", "TASK-2"],
                "active_task_ids_after": ["TASK-2"],
                "current_index_valid": True,
                "completed_residue_absent": True,
                "scan_archive": False,
            }
            fixture = root / "archive-contract.json"
            fixture.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                status = adaptive.main(["--archive-contract-file", str(fixture)])
            self.assertEqual(0, status, output.getvalue())

    def test_pressure_check_rejects_missing_task_document_lifecycle(self):
        loaded = {
            "SKILL.md": "只有四档流程，没有任务工作文档。",
            "references/四档自适应流程.md": "完整流程第一次目标禁止归档。",
            "references/提示词向导.md": "4.4 任务文档先行与最终归档。",
        }
        failures = adaptive.pressure_failures(loaded)
        self.assertTrue(any("S40-S49" in failure for failure in failures))
    def test_last_goal_uses_handoff_without_archive_contract(self):
        prompt = self._valid_staged_workflow_prompt(
            "deep", "development-and-acceptance", index=2, count=2
        )
        prompt = prompt.rsplit("\n任务 ID：TASK-1", 1)[0]
        prompt += "\n当前目标完成开发、测试、验收、问题回写和必要修复。"
        prompt += "\n当前目标暂不执行正式归档，不清理活动文档。"
        prompt += "\n当前目标结束后进入待用户检查和待归档确认。"
        prompt += "\n如果用户发现问题，回到问题回写、修复、测试和验收；如果用户提出新增需求或优化，回到需求整理或需求变更流程。"
        prompt += "\n只有用户明确回复“归档”后才调用正式归档模板。"
        "\n归档失败不得重新打开普通目标。"
        self.assertEqual(
            [],
            adaptive.workflow_prompt_failures(
                prompt, tier="deep", archive_stage="handoff"
            ),
        )

    def test_archive_prompt_is_a_separate_validation_kind(self):
        prompt = "\n".join(
            [
                adaptive.MULTI_AGENT_OPENING,
                "用户已经明确回复“归档”，确认消息已保存。",
                "任务 ID：TASK-1",
                "任务名称：示例任务",
                "正式 PRD：liran_docs/requirements/TASK-1-PRD.md",
                "需求整理文档：liran_docs/requirements/TASK-1-需求整理.md",
                "归档目录：liran_docs/archive/TASK-1/归档.md",
                "当前归档状态：待归档确认",
                "归档确认原始消息：用户回复归档。",
                "归档确认时间：2026-09-14",
                "归档触发来源：用户明确归档确认。",
                "最后一次普通目标已完成开发、测试、验收、问题回写和修复复测。",
                "无待确认项、无待实测、无待用户验收、无失败、无受阻、无未修复问题。",
                "先更新长期事实。",
                "创建单任务归档。",
                "校验归档内容和证据路径。",
                "更新归档索引。",
                "按任务 ID 清理活动区。",
                "其他活动任务未受影响。",
                "当前索引有效。",
                "活动区无本任务残留。",
                "归档失败时保留活动区原文。",
                "只有归档成功后才能标记已归档和已完成。",
            ]
        )
        self.assertEqual(
            [], adaptive.prompt_failures_for_kind(prompt, kind="archive")
        )

    def test_archive_lifecycle_requires_explicit_user_confirmation(self):
        payload = {
            "task_id": "TASK-1",
            "goal_stage": "archive",
            "acceptance_owner": "Codex 真机测试",
            "source_state": "待归档确认",
            "archive_state": "归档中",
            "final_state": "未完成",
            "user_archive_confirmation": False,
            "archive_confirmation_evidence": "",
            "requirements_path": "/missing/requirements.md",
            "archive_path": "/missing/archive.md",
            "artifact_task_ids": ["TASK-1"],
            "unresolved_states": [],
            "steps": [],
            "cleanup_performed": False,
            "other_active_tasks_preserved": True,
            "current_index_valid": True,
            "completed_residue_absent": True,
            "scan_archive": False,
        }
        failures = adaptive.archive_lifecycle_failures(payload)
        self.assertTrue(any("用户明确回复" in failure for failure in failures))

    def test_archive_transition_requires_confirmation_and_waiting_states_exist(self):
        contract = adaptive.FlowContract(
            tier="deep", pre_score=62, base_goal_count=2, goal_count=2,
            goal_index=2, goal_stage="development-and-acceptance",
            acceptance_owner="Codex 真机测试", visual_qa="不涉及页面",
            phase="修改后复评中", state="修改后复评中",
            acceptance_confirmed=True,
        )
        self.assertEqual(
            [],
            adaptive.flow_transition_failures(
                contract,
                target_state="待用户检查",
                event="当前目标完成开发、测试、验收、问题回写和必要修复，等待用户检查",
            ),
        )
        waiting = adaptive.FlowContract.from_dict(
            {**contract.to_dict(), "state": "待用户检查", "phase": "待用户检查"}
        )
        failures = adaptive.flow_transition_failures(
            waiting, target_state="归档中", event="开始归档"
        )
        self.assertTrue(any("归档" in failure and "确认" in failure for failure in failures))

    def _final_goal_reclaim_contract(self, **overrides):
        data = {
            "tier": "deep",
            "pre_score": 62,
            "base_goal_count": 2,
            "goal_count": 2,
            "goal_index": 2,
            "goal_stage": "development-and-acceptance",
            "acceptance_owner": "Codex 真机测试",
            "visual_qa": "不涉及页面",
            "phase": "修改后复评中",
            "state": "修改后复评中",
            "acceptance_confirmed": True,
            "goal_status": "active",
        }
        data.update(overrides)
        return adaptive.FlowContract(**data)

    def _valid_reclaim_payload(self, **overrides):
        payload = {
            "contract": self._final_goal_reclaim_contract().to_dict(),
            "task_id": "TASK-1",
            "goal_index": 2,
            "goal_count": 2,
            "goal_stage": "development-and-acceptance",
            "goal_status_before": "active",
            "goal_status_after": "reclaimed",
            "acceptance_result": "真机测试通过",
            "issue_writeback_complete": True,
            "retest_complete": True,
            "post_score_complete": True,
            "goal_completion_evidence": ["真实真机清单通过", "问题回写完成", "修复后复测完成", "修改后评分已记录"],
            "task_state_after": "待用户检查",
            "archive_state_after": "待归档确认",
            "user_check_notification_sent": True,
            "user_check_notification_evidence": "已发送固定用户检查通知",
            "archive_started": False,
            "archive_cleanup_performed": False,
            "archive_index_updated": False,
        }
        payload.update(overrides)
        return payload

    def test_final_goal_reclaim_requires_all_completion_evidence(self):
        self.assertEqual([], adaptive.goal_reclaim_failures(self._valid_reclaim_payload()))
        for field in ("issue_writeback_complete", "retest_complete", "post_score_complete"):
            payload = self._valid_reclaim_payload(**{field: False})
            self.assertTrue(adaptive.goal_reclaim_failures(payload), field)

    def test_final_goal_reclaim_rejects_non_final_goal_and_wrong_after_states(self):
        payload = self._valid_reclaim_payload(goal_index=1)
        self.assertTrue(any("最后" in item or "M/M" in item for item in adaptive.goal_reclaim_failures(payload)))
        payload = self._valid_reclaim_payload(task_state_after="归档中")
        self.assertTrue(any("待用户检查" in item for item in adaptive.goal_reclaim_failures(payload)))
        payload = self._valid_reclaim_payload(archive_state_after="已归档")
        self.assertTrue(any("待归档确认" in item for item in adaptive.goal_reclaim_failures(payload)))

    def test_final_goal_reclaim_does_not_start_archive_or_cleanup(self):
        for field in ("archive_started", "archive_cleanup_performed", "archive_index_updated"):
            payload = self._valid_reclaim_payload(**{field: True})
            failures = adaptive.goal_reclaim_failures(payload)
            self.assertTrue(any(field in item for item in failures), field)

    def test_reclaim_is_idempotent_and_repeated_reclaim_does_not_create_archive(self):
        payload = self._valid_reclaim_payload(
            goal_status_before="reclaimed",
            contract={**self._final_goal_reclaim_contract(goal_status="reclaimed").to_dict()},
        )
        self.assertEqual([], adaptive.goal_reclaim_failures(payload))

    def test_archive_requires_reclaimed_source_goal(self):
        payload = {
            "task_id": "TASK-1",
            "goal_stage": "archive",
            "source_goal_status": "active",
            "acceptance_owner": "Codex 真机测试",
            "source_state": "待归档确认",
            "archive_state": "归档中",
            "final_state": "未完成",
            "user_archive_confirmation": True,
            "archive_confirmation_evidence": "用户明确回复归档",
            "requirements_path": "/missing/requirements.md",
            "archive_path": "/missing/archive.md",
            "artifact_task_ids": ["TASK-1"],
            "unresolved_states": [],
            "steps": [],
            "cleanup_performed": False,
            "scan_archive": False,
        }
        self.assertTrue(any("reclaimed" in item or "回收" in item for item in adaptive.archive_lifecycle_failures(payload)))

    def test_archive_failure_preserves_reclaimed_source_goal(self):
        payload = {
            "task_id": "TASK-1",
            "goal_stage": "archive",
            "source_goal_status": "reclaimed",
            "archive_goal_status": "active",
            "acceptance_owner": "Codex 真机测试",
            "source_state": "待归档确认",
            "archive_state": "归档受阻",
            "final_state": "未完成",
            "user_archive_confirmation": True,
            "archive_confirmation_evidence": "用户明确回复归档",
            "requirements_path": "/missing/requirements.md",
            "archive_path": "/missing/archive.md",
            "artifact_task_ids": ["TASK-1"],
            "unresolved_states": [],
            "steps": ["长期事实已更新"],
            "cleanup_performed": False,
            "scan_archive": False,
        }
        self.assertFalse(any("普通目标" in item and "重新" in item for item in adaptive.archive_lifecycle_failures(payload)))

    def test_flow_contract_round_trips_goal_reclaim_fields_and_legacy_contract_does_not_fake_reclaimed(self):
        contract = self._final_goal_reclaim_contract(
            goal_status="reclaimed",
            goal_completion_evidence=("真实真机清单通过", "问题回写完成"),
            goal_reclaimed_at="2026-09-15T10:00:00+08:00",
            task_state_after_goal="待用户检查",
            archive_state_after_goal="待归档确认",
        )
        self.assertEqual(contract, adaptive.FlowContract.from_json(contract.to_json()))
        legacy = {**contract.to_dict()}
        legacy.pop("goal_status")
        legacy.pop("goal_completion_evidence")
        legacy.pop("goal_reclaimed_at")
        legacy.pop("task_state_after_goal")
        legacy.pop("archive_state_after_goal")
        restored = adaptive.FlowContract.from_dict(legacy)
        self.assertNotEqual("reclaimed", restored.goal_status)

    def test_cli_validates_goal_reclaim_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "goal-reclaim.json"
            path.write_text(json.dumps(self._valid_reclaim_payload(), ensure_ascii=False), encoding="utf-8")
            output = io.StringIO()
            with redirect_stdout(output):
                status = adaptive.main(["--goal-reclaim-file", str(path)])
            self.assertEqual(0, status, output.getvalue())

    def test_waiting_state_rejects_explicit_completion_without_reclaimed_goal_status(self):
        contract = self._final_goal_reclaim_contract(
            goal_completion_evidence=("验收通过",),
            task_state_after_goal="待用户检查",
            archive_state_after_goal="待归档确认",
        )
        failures = adaptive.flow_transition_failures(
            contract,
            target_state="待用户检查",
            event="开发、测试、验收、问题回写和必要修复完成，等待用户检查",
        )
        self.assertTrue(any("reclaimed" in item for item in failures))

    def test_waiting_state_accepts_reclaimed_goal_contract(self):
        contract = self._final_goal_reclaim_contract(
            goal_status="reclaimed",
            goal_completion_evidence=("验收通过", "问题回写完成", "修复后复测完成"),
            goal_reclaimed_at="2026-09-14T10:00:00+08:00",
            task_state_after_goal="待用户检查",
            archive_state_after_goal="待归档确认",
            user_check_notification_sent=True,
            user_check_notification_evidence="已发送用户检查通知",
        )
        self.assertEqual(
            [],
            adaptive.flow_transition_failures(
                contract,
                target_state="待用户检查",
                event="开发、测试、验收、问题回写和必要修复完成，等待用户检查",
            ),
        )

    def test_archive_stage_requires_reclaimed_source_and_archive_target_is_separate(self):
        payload = {
            "task_id": "TASK-1",
            "goal_stage": "archive",
            "source_goal_status": "reclaimed",
            "archive_goal_status": "reclaimed",
            "archive_goal_counted": False,
            "source_goal_index": 2,
            "source_goal_count": 2,
            "acceptance_owner": "Codex 真机测试",
            "source_state": "待归档确认",
            "archive_state": "已归档",
            "final_state": "已完成",
            "user_archive_confirmation": True,
            "archive_confirmation_evidence": "用户明确回复归档",
            "requirements_path": "/missing/requirements.md",
            "archive_path": "/missing/archive.md",
            "artifact_task_ids": ["TASK-1"],
            "unresolved_states": [],
            "steps": list(adaptive.ARCHIVE_SAFE_STEPS),
            "cleanup_performed": True,
            "other_active_tasks_preserved": True,
            "current_index_valid": True,
            "completed_residue_absent": True,
            "active_task_ids_before": ["TASK-1", "TASK-2"],
            "active_task_ids_after": ["TASK-2"],
            "scan_archive": False,
        }
        failures = adaptive.archive_lifecycle_failures(payload)
        self.assertFalse(any("reclaimed" in item for item in failures))

    def test_legacy_waiting_contract_with_complete_evidence_migrates_to_reclaimed(self):
        legacy = self._final_goal_reclaim_contract(
            goal_completion_evidence=("验收通过", "问题回写完成", "修复后复测完成"),
            task_state_after_goal="待用户检查",
            archive_state_after_goal="待归档确认",
            phase="待用户检查",
            state="待用户检查",
        ).to_dict()
        legacy.pop("goal_status")
        restored = adaptive.FlowContract.from_dict(legacy)
        self.assertEqual("reclaimed", restored.goal_status)

    def test_prd_conversion_audits_confirmed_source_details_without_copying_process(self):
        source = "\n".join(
            [
                "## 已确认的内容",
                "REQ-SOURCE-1",
                "接口路径：/api/status",
                "请求方法：GET",
                "字段名：channel_status",
                "阈值：30 秒",
                "页面规则：卡片宽度 320px，间距 12px",
                "异常处理：权限失败显示空态",
            ]
        )
        formal = self._valid_prd_document(status="正式 PRD", requirement_status="已确认", version="1.0")
        failures = adaptive.prd_conversion_failures(formal, source_text=source)
        self.assertTrue(any("来源需求细节" in failure for failure in failures))

        complete = formal + "\n" + "\n".join(
            [
                "REQ-SOURCE-1",
                "触发条件：用户打开状态页。",
                "前置条件：服务可访问。",
                "用户操作：打开页面。",
                "系统行为：GET /api/status 并读取 channel_status。",
                "数据变化：保留响应字段 channel_status。",
                "状态变化：30 秒未更新时进入临时失败。",
                "正常结果：显示状态卡片。",
                "异常处理：权限失败显示空态。",
                "禁止行为：不得展示无权限数据。",
                "对应 AC：AC-SOURCE-1。",
                "AC-SOURCE-1",
                "对应需求：REQ-SOURCE-1。",
                "验收步骤：调用 GET /api/status 并验证 channel_status、30 秒阈值、320px 卡片和 12px 间距。",
                "预期结果：字段、阈值和页面规则全部符合需求。",
                "失败条件：缺少字段、阈值、尺寸、间距或权限空态。",
            ]
        )
        self.assertFalse(adaptive.prd_conversion_failures(complete, source_text=source))


if __name__ == "__main__":
    unittest.main()
