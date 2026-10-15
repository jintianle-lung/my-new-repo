import unittest

from scripts import check_codex_ui_flow_docs as ui_check


def load_current_docs() -> dict[str, str]:
    return {
        rel: (ui_check.ROOT / rel).read_text(encoding="utf-8")
        for rel in ui_check.CHECK_FILES
    }


def filled_stitch_generation_prompt() -> str:
    template = (ui_check.ROOT / ui_check.STITCH_GENERATION_TEMPLATE).read_text(
        encoding="utf-8"
    )
    return ui_check.STITCH_GENERATION_PLACEHOLDER_RE.sub("已填", template)


class CodexUiFlowValidatorTests(unittest.TestCase):
    def test_stitch_repair_template_starts_with_multi_agent_opening(self):
        text = (ui_check.ROOT / ui_check.STITCH_REPAIR_TEMPLATE).read_text(encoding="utf-8")
        self.assertTrue(text.startswith(ui_check.MULTI_AGENT_OPENING + "\n"))

    def test_current_contract_has_no_scoped_conflicts(self):
        self.assertEqual([], ui_check.contract_failures(load_current_docs()))

    def test_wrong_deep_page_option_fails_even_if_correct_phrase_exists_elsewhere(self):
        loaded = load_current_docs()
        rel = "references/功能3-高保真原型.md"
        correct = "需求没问题，直接生成完整提示词，完成后我自己测试"
        wrong = "需求没问题，但让 Codex 重新判断是否需要深度流程"
        loaded[rel] = loaded[rel].replace(correct, wrong, 1) + f"\n{correct}\n"

        failures = ui_check.contract_failures(loaded)
        self.assertTrue(any("深度页面" in failure for failure in failures))

    def test_unconditional_tutorial_qa_gate_fails(self):
        loaded = load_current_docs()
        rel = "references/liran-plan-使用教程.html"
        loaded[rel] = loaded[rel].replace(
            "Design QA 已触发时，QA 不通过不能收口",
            "QA 不通过不能收口",
            1,
        )

        failures = ui_check.contract_failures(loaded)
        self.assertTrue(any("Design QA" in failure for failure in failures))

    def test_html_tutorials_must_match(self):
        loaded = load_current_docs()
        loaded["references/plan-docs-使用教程.html"] += "\n<!-- drift -->\n"

        failures = ui_check.contract_failures(loaded)
        self.assertTrue(any("HTML 教程" in failure for failure in failures))

    def test_stitch_repair_template_cannot_be_shortened(self):
        loaded = load_current_docs()
        loaded[ui_check.STITCH_REPAIR_TEMPLATE] = "请直接一比一修复 Stitch UI。"

        failures = ui_check.contract_failures(loaded)
        self.assertTrue(any("固定正文" in failure for failure in failures))

    def test_stitch_repair_template_preserves_original_body_when_expanded(self):
        loaded = load_current_docs()
        rel = ui_check.STITCH_REPAIR_TEMPLATE
        loaded[rel] = loaded[rel].replace(
            "2. 重点修正图标、按钮、输入控件、表格、文本和操作区的尺寸、间距、比例及排版流。",
            "2. 只修按钮大小。",
            1,
        )

        failures = ui_check.contract_failures(loaded)
        self.assertTrue(any("原固定正文" in failure for failure in failures))

    def test_stitch_repair_template_requires_all_visual_dimensions(self):
        dimension_phrases = {
            "页面结构与布局": "布局",
            "字体与文本排版": "字体",
            "颜色和视觉样式": "颜色",
            "图片和视觉资源": "资源",
            "层级与组合关系": "层级",
            "状态表现": "状态",
            "响应式与不同视口": "响应式",
        }
        for phrase, label in dimension_phrases.items():
            with self.subTest(phrase=phrase):
                loaded = load_current_docs()
                rel = ui_check.STITCH_REPAIR_TEMPLATE
                loaded[rel] = loaded[rel].replace(phrase, f"已删除{label}维度", 1)
                failures = ui_check.contract_failures(loaded)
                self.assertTrue(any(label in failure for failure in failures))

    def test_stitch_repair_template_uses_unified_length_gate(self):
        loaded = load_current_docs()
        loaded[ui_check.STITCH_REPAIR_TEMPLATE] += "项目专属限制：" + "补充事实。" * 2000

        failures = ui_check.contract_failures(loaded)
        self.assertTrue(any("3000–10000" in failure or "字符" in failure for failure in failures))

    def test_stitch_instance_repair_prompt_stays_within_unified_range(self):
        template = (ui_check.ROOT / ui_check.STITCH_REPAIR_TEMPLATE).read_text(encoding="utf-8")
        prompt = template + "\n" + "\n".join(
            f"项目专属限制：事实 {index}" for index in range(100)
        )
        self.assertGreaterEqual(len(prompt), 3000)
        self.assertLessEqual(len(prompt), 10000)
        self.assertEqual([], ui_check.stitch_instance_repair_prompt_failures(prompt))

    def test_stitch_instance_repair_prompt_rejects_over_unified_maximum(self):
        template = (ui_check.ROOT / ui_check.STITCH_REPAIR_TEMPLATE).read_text(encoding="utf-8")
        prompt = template + "\n项目专属限制：" + "补充事实。" * 2500
        failures = ui_check.stitch_instance_repair_prompt_failures(prompt)
        self.assertTrue(any("10000" in failure for failure in failures))

    def test_stitch_instance_repair_prompt_rejects_workflow_contract(self):
        template = (ui_check.ROOT / ui_check.STITCH_REPAIR_TEMPLATE).read_text(encoding="utf-8")
        failures = ui_check.stitch_instance_repair_prompt_failures(
            template + "\n## 流程合同\n流程档位：深度流程"
        )
        self.assertTrue(any("流程字段" in failure for failure in failures))

    def test_stitch_instance_repair_prompt_rejects_unapproved_appended_text(self):
        template = (ui_check.ROOT / ui_check.STITCH_REPAIR_TEMPLATE).read_text(encoding="utf-8")
        failures = ui_check.stitch_instance_repair_prompt_failures(
            template + "\n请顺便修改业务逻辑。"
        )
        self.assertTrue(any("未授权项目资料" in failure for failure in failures))

    def test_stitch_instance_repair_prompt_requires_unchanged_template_prefix(self):
        template = (ui_check.ROOT / ui_check.STITCH_REPAIR_TEMPLATE).read_text(encoding="utf-8")
        modified = template.replace("请直接开始执行下面步骤。", "请先解释再执行。", 1)
        failures = ui_check.stitch_instance_repair_prompt_failures(modified)
        self.assertTrue(any("固定模板正文原样开头" in failure for failure in failures))

    def test_stitch_runtime_tuning_cannot_delete_inapplicable_sections(self):
        loaded = load_current_docs()
        rel = ui_check.STITCH_REPAIR_TEMPLATE
        loaded[rel] = loaded[rel].replace(
            "不适用：当前 Stitch 原始产物中不存在该元素。",
            "当前项目可删除不适用章节。",
            1,
        )

        failures = ui_check.contract_failures(loaded)
        self.assertTrue(any("不适用" in failure for failure in failures))

    def test_stitch_repair_template_states_controls_are_only_one_dimension(self):
        loaded = load_current_docs()
        rel = ui_check.STITCH_REPAIR_TEMPLATE
        loaded[rel] = loaded[rel].replace(
            "控件规格是完整视觉保真的一个维度",
            "控件规格是唯一检查维度",
            1,
        )

        failures = ui_check.contract_failures(loaded)
        self.assertTrue(any("控件规格不能遮蔽" in failure for failure in failures))

    def test_stitch_design_qa_regression_fails(self):
        loaded = load_current_docs()
        loaded["SKILL.md"] += "\nStitch 和明确高保真任务必须 Design QA\n"

        failures = ui_check.contract_failures(loaded)
        self.assertTrue(any("Stitch 路线仍残留" in failure for failure in failures))

    def test_stitch_gate_requires_both_initial_outcomes(self):
        loaded = load_current_docs()
        loaded["references/功能3-高保真原型.md"] = loaded[
            "references/功能3-高保真原型.md"
        ].replace("初次承接受阻", "承接失败")

        failures = ui_check.contract_failures(loaded)
        self.assertTrue(any("初次承接受阻" in failure for failure in failures))

    def test_stitch_prompt_rejects_fixed_page_count_limits(self):
        limits = (
            "首版核心页面必须控制在 2–4 页。",
            "首版核心页面必须控制在 3–6 页。",
            "Stitch 最多只生成 5 页。",
        )
        for limit in limits:
            with self.subTest(limit=limit):
                loaded = load_current_docs()
                loaded["SKILL.md"] += f"\n{limit}\n"
                failures = ui_check.contract_failures(loaded)
                self.assertTrue(any("固定页数" in failure for failure in failures))

    def test_stitch_prompt_requires_exact_page_inventory_in_every_entry(self):
        contract_files = (
            "SKILL.md",
            "references/功能3-高保真原型.md",
            "references/提示词向导.md",
            "references/使用教程-常用提示词清单.md",
        )
        required = "页面数量不设置固定上限或下限。"

        for rel in contract_files:
            with self.subTest(rel=rel):
                loaded = load_current_docs()
                loaded[rel] = loaded[rel].replace(required, "", 1)
                failures = ui_check.contract_failures(loaded)
                self.assertTrue(
                    any(rel in failure and "完整页面清单" in failure for failure in failures)
                )

    def test_stitch_generation_template_allows_placeholders(self):
        template = (ui_check.ROOT / ui_check.STITCH_GENERATION_TEMPLATE).read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            [],
            ui_check.stitch_generation_prompt_failures(
                template, allow_placeholders=True
            ),
        )

    def test_stitch_generation_filled_prompt_passes(self):
        self.assertEqual(
            [],
            ui_check.stitch_generation_prompt_failures(
                filled_stitch_generation_prompt()
            ),
        )

    def test_stitch_generation_missing_constraints_fails(self):
        prompt = filled_stitch_generation_prompt().replace("额外设计约束：", "设计备注：", 1)
        failures = ui_check.stitch_generation_prompt_failures(prompt)
        self.assertTrue(
            any("额外设计约束" in failure for failure in failures)
        )

    def test_stitch_generation_placeholders_in_delivery_fail(self):
        template = (ui_check.ROOT / ui_check.STITCH_GENERATION_TEMPLATE).read_text(
            encoding="utf-8"
        )
        failures = ui_check.stitch_generation_prompt_failures(template)
        self.assertTrue(any("未填占位符" in failure for failure in failures))

    def test_stitch_generation_constraints_must_follow_title(self):
        prompt = "前言\n" + filled_stitch_generation_prompt()
        failures = ui_check.stitch_generation_prompt_failures(prompt)
        self.assertTrue(
            any("一级标题后紧接额外设计约束" in failure for failure in failures)
        )


if __name__ == "__main__":
    unittest.main()
