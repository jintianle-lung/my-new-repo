import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from scripts import check_real_test_checklist as checklist


HEADER = (
    "| 步骤 | 项目 | 触发方式 | 前置条件 | 核心链路 | "
    "成功标准 | 失败标准 | 复测方式 | 跑通 |"
)
SEPARATOR = "|---|---|---|---|---|---|---|---|---|"


def step(step_no: int, rows: list[str], *, heading_no: int | None = None) -> str:
    visible_no = step_no if heading_no is None else heading_no
    return "\n".join(
        [
            f"## 第 {visible_no} 步：阶段",
            "",
            HEADER,
            SEPARATOR,
            *rows,
        ]
    )


def row(step_id: str, status: str = "", *, item: str = "检查项") -> str:
    return (
        f"| {step_id} | {item} | 点击 | 已打开 | click -> result | "
        f"显示成功 | 出现错误 | 重新点击 | {status} |"
    )


class RealTestChecklistValidationTests(unittest.TestCase):
    def run_check(self, text: str, *, require_complete: bool = False) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "09-真机实测.md"
            path.write_text(text, encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = checklist.check_file(
                    path,
                    require_complete=require_complete,
                )
            return result, output.getvalue()

    def test_empty_file_fails(self):
        result, output = self.run_check("")
        self.assertEqual(1, result)
        self.assertIn("没有找到任何有效步骤", output)

    def test_explicit_archived_empty_state_passes(self):
        text = (
            "# 真机实测\n\n"
            "当前没有待实测、失败或待复测任务；历史真机结果见 archive/README.md。\n"
        )
        result, output = self.run_check(text, require_complete=True)
        self.assertEqual(0, result)
        self.assertIn("空状态校验通过", output)

    def test_fenced_or_quoted_empty_state_cannot_fake_a_real_empty_file(self):
        for text in (
            "```text\n当前没有待实测、失败或待复测任务；历史真机结果见 archive/README.md。\n```\n",
            "> 当前没有待实测、失败或待复测任务；历史真机结果见 archive/README.md。\n",
        ):
            result, output = self.run_check(text, require_complete=True)
            self.assertEqual(1, result)
            self.assertIn("没有找到任何有效步骤", output)

    def test_step_without_table_fails(self):
        result, output = self.run_check("## 第 1 步：阶段\n\n只有说明，没有表格。\n")
        self.assertEqual(1, result)
        self.assertIn("没有合法跑通表格", output)

    def test_step_headings_must_be_continuous(self):
        text = "\n\n".join(
            [
                step(1, [row("1.1")]),
                step(3, [row("3.1")]),
            ]
        )
        result, output = self.run_check(text)
        self.assertEqual(1, result)
        self.assertIn("步骤标题编号必须从 1 连续递增", output)

    def test_row_ids_must_be_continuous_within_step(self):
        text = step(1, [row("1.1"), row("1.3")])
        result, output = self.run_check(text)
        self.assertEqual(1, result)
        self.assertIn("数据行编号应为 `1.2`", output)

    def test_required_columns_are_enforced(self):
        text = "\n".join(
            [
                "## 第 1 步：阶段",
                "",
                "| 步骤 | 项目 | 跑通 |",
                "|---|---|---|",
                "| 1.1 | 检查项 | ✅ |",
            ]
        )
        result, output = self.run_check(text)
        self.assertEqual(1, result)
        self.assertIn("缺少必填列", output)

    def test_status_must_equal_checkmark_exactly(self):
        text = step(1, [row("1.1", "❌ 未通过，禁止填写 ✅")])
        result, output = self.run_check(text)
        self.assertEqual(1, result)
        self.assertIn("跑通状态只能留空或严格填写 `✅`", output)

    def test_checked_row_with_placeholder_fails(self):
        text = step(1, [row("1.1", "✅", item="<检查项>")])
        result, output = self.run_check(text)
        self.assertEqual(1, result)
        self.assertIn("仍包含占位或待处理内容", output)

    def test_checked_row_with_todo_fails(self):
        text = step(1, [row("1.1", "✅", item="TODO 补真实检查项")])
        result, output = self.run_check(text)
        self.assertEqual(1, result)
        self.assertIn("仍包含占位或待处理内容", output)

    def test_checked_row_with_empty_required_evidence_fails(self):
        text = step(
            1,
            ["| 1.1 | 检查项 |  | 已打开 | click -> result | 显示成功 | 出现错误 | 重新点击 | ✅ |"],
        )
        result, output = self.run_check(text, require_complete=True)
        self.assertEqual(1, result)
        self.assertIn("已填写 `✅`，但必填证据列为空", output)

    def test_fenced_fake_step_and_table_are_ignored(self):
        text = "\n".join(
            [
                "```markdown",
                step(1, [row("1.1", "✅")]),
                "```",
            ]
        )
        result, output = self.run_check(text)
        self.assertEqual(1, result)
        self.assertIn("没有找到任何有效步骤", output)

    def test_partial_checklist_can_pass_structure_check(self):
        text = step(1, [row("1.1", "✅"), row("1.2")])
        result, _ = self.run_check(text)
        self.assertEqual(0, result)

    def test_require_complete_rejects_unchecked_rows(self):
        text = step(1, [row("1.1", "✅"), row("1.2")])
        result, output = self.run_check(text, require_complete=True)
        self.assertEqual(1, result)
        self.assertIn("完成门禁要求全部数据行严格填写 `✅`", output)

    def test_require_complete_accepts_valid_completed_checklist(self):
        text = "\n\n".join(
            [
                step(1, [row("1.1", "✅"), row("1.2", "✅")]),
                step(2, [row("2.1", "✅")]),
            ]
        )
        result, _ = self.run_check(text, require_complete=True)
        self.assertEqual(0, result)


if __name__ == "__main__":
    unittest.main()
