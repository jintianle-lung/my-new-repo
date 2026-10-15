#!/usr/bin/env python3
"""Validate the Markdown structure of a liran-plan real-device checklist.

Usage:
    python3 scripts/check_real_test_checklist.py <path/to/09-真机实测.md>
    python3 scripts/check_real_test_checklist.py <path/to/09-真机实测.md> --require-complete

The script validates structure only. It cannot prove that a real operation,
screenshot, user action, or test result actually happened.
"""

import argparse
import re
from pathlib import Path


PLACEHOLDER_PATTERN = re.compile(
    r"<[^>]{1,120}>|(?i:\bTODO\b|\bTBD\b)|待填写|待补充|待确认"
)
STEP_HEADING_PATTERN = re.compile(r"^##\s*第\s*(\d+)\s*步")
TABLE_ROW_PATTERN = re.compile(r"^\|.*\|\s*$")
REQUIRED_COLUMNS = (
    "步骤",
    "项目",
    "触发方式",
    "前置条件",
    "核心链路",
    "成功标准",
    "失败标准",
    "复测方式",
    "跑通",
)
EVIDENCE_COLUMNS = tuple(
    column for column in REQUIRED_COLUMNS if column not in ("步骤", "跑通")
)
EMPTY_ACTIVE_STATE = "当前没有待实测、失败或待复测任务；历史真机结果见 archive/README.md。"


def parse_table_row(line: str) -> list[str]:
    """Split one Markdown table row into trimmed cells."""
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [cell.strip() for cell in inner.split("|")]


def is_separator_row(cells: list[str]) -> bool:
    """Return True for a valid Markdown table separator row."""
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def is_checked(cell: str) -> bool:
    """Only an exact checkmark represents a passed row."""
    return cell.strip() == "✅"


def strip_fenced_content(lines: list[str]) -> list[str]:
    """Hide fenced examples while preserving source line positions."""
    visible: list[str] = []
    fence_char: str | None = None

    for line in lines:
        match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if match:
            marker_char = match.group(1)[0]
            if fence_char is None:
                fence_char = marker_char
            elif fence_char == marker_char:
                fence_char = None
            visible.append("")
            continue
        visible.append(line if fence_char is None else "")

    return visible


def find_steps(lines: list[str]) -> list[tuple[int, int, int]]:
    """Split the file into `(step_no, start, end)` sections."""
    starts: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        match = STEP_HEADING_PATTERN.match(line.strip())
        if match:
            starts.append((int(match.group(1)), index))

    steps: list[tuple[int, int, int]] = []
    for index, (step_no, start) in enumerate(starts):
        end = starts[index + 1][1] if index + 1 < len(starts) else len(lines)
        steps.append((step_no, start, end))
    return steps


def extract_tables(
    lines: list[str],
    start: int,
    end: int,
) -> list[tuple[list[str], list[tuple[int, list[str]]]]]:
    """Return valid contiguous Markdown tables inside one step."""
    tables: list[tuple[list[str], list[tuple[int, list[str]]]]] = []
    index = start

    while index < end:
        if not TABLE_ROW_PATTERN.match(lines[index]):
            index += 1
            continue

        block: list[tuple[int, list[str]]] = []
        while index < end and TABLE_ROW_PATTERN.match(lines[index]):
            block.append((index + 1, parse_table_row(lines[index])))
            index += 1

        if len(block) < 2:
            continue
        header = block[0][1]
        separator = block[1][1]
        if len(header) != len(separator) or not is_separator_row(separator):
            continue
        tables.append((header, block[2:]))

    return tables


def check_file(path: Path, *, require_complete: bool = False) -> int:
    text = path.read_text(encoding="utf-8")
    lines = strip_fenced_content(text.splitlines())
    steps = find_steps(lines)
    issues: list[str] = []
    summaries: list[tuple[int, int, int]] = []

    if not steps:
        if any(line.strip() == EMPTY_ACTIVE_STATE for line in lines):
            print(f"校验文件：{path}")
            print("空状态校验通过。")
            print("提醒：历史真机结果应保存在任务归档，当前文件不保留成功流水。")
            return 0
        print(f"校验文件：{path}")
        print("发现 1 处结构性问题：没有找到任何有效步骤。")
        print("清单必须在代码块外使用连续的 `## 第 N 步` 标题。")
        return 1

    actual_step_numbers = [step_no for step_no, _, _ in steps]
    expected_step_numbers = list(range(1, len(steps) + 1))
    if actual_step_numbers != expected_step_numbers:
        issues.append(
            "步骤标题编号必须从 1 连续递增；"
            f"当前为 {actual_step_numbers}，期望为 {expected_step_numbers}。"
        )

    previous_step_fully_checked = True
    previous_step_no: int | None = None

    for step_no, start, end in steps:
        tables = extract_tables(lines, start, end)
        run_table = next((table for table in tables if "跑通" in table[0]), None)
        if run_table is None:
            issues.append(f"第 {step_no} 步没有合法跑通表格。")
            summaries.append((step_no, 0, 0))
            previous_step_fully_checked = False
            previous_step_no = step_no
            continue

        header, raw_rows = run_table
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in header]
        if missing_columns:
            issues.append(
                f"第 {step_no} 步跑通表格缺少必填列：{', '.join(missing_columns)}。"
            )

        if not raw_rows:
            issues.append(f"第 {step_no} 步跑通表格没有任何数据行。")
            summaries.append((step_no, 0, 0))
            previous_step_fully_checked = False
            previous_step_no = step_no
            continue

        column_index = {name: index for index, name in enumerate(header)}
        checked_count = 0
        valid_row_count = 0

        for data_index, (line_no, cells) in enumerate(raw_rows, start=1):
            if len(cells) != len(header):
                issues.append(
                    f"第 {step_no} 步第 {data_index} 行（文件第 {line_no} 行）"
                    f"列数为 {len(cells)}，表头列数为 {len(header)}。"
                )
                continue

            valid_row_count += 1
            if "步骤" in column_index:
                expected_row_id = f"{step_no}.{data_index}"
                actual_row_id = cells[column_index["步骤"]]
                if actual_row_id != expected_row_id:
                    issues.append(
                        f"第 {step_no} 步第 {data_index} 个数据行编号应为 "
                        f"`{expected_row_id}`，当前为 `{actual_row_id}`。"
                    )

            status = cells[column_index["跑通"]]
            if status not in ("", "✅"):
                issues.append(
                    f"第 {step_no} 步第 {data_index} 行跑通状态只能留空或严格填写 "
                    f"`✅`，当前为 `{status}`。"
                )

            if not is_checked(status):
                continue

            checked_count += 1
            empty_evidence_columns = [
                column
                for column in EVIDENCE_COLUMNS
                if column in column_index and not cells[column_index[column]]
            ]
            if empty_evidence_columns:
                issues.append(
                    f"第 {step_no} 步第 {data_index} 行已填写 `✅`，"
                    "但必填证据列为空："
                    f"{', '.join(empty_evidence_columns)}。"
                )
            evidence_cells = [
                cell
                for index, cell in enumerate(cells)
                if index != column_index["跑通"]
            ]
            if any(PLACEHOLDER_PATTERN.search(cell) for cell in evidence_cells):
                issues.append(
                    f"第 {step_no} 步第 {data_index} 行已填写 `✅`，"
                    "但仍包含占位或待处理内容。"
                )

        summaries.append((step_no, checked_count, valid_row_count))

        if (
            checked_count > 0
            and previous_step_no is not None
            and not previous_step_fully_checked
        ):
            issues.append(
                f"第 {previous_step_no} 步还没有全部填写 `✅`，"
                f"但第 {step_no} 步已经出现通过项。"
            )

        current_fully_checked = (
            valid_row_count > 0 and checked_count == valid_row_count
        )
        if require_complete and not current_fully_checked:
            issues.append(
                f"第 {step_no} 步未完成：完成门禁要求全部数据行严格填写 `✅`。"
            )

        previous_step_fully_checked = current_fully_checked
        previous_step_no = step_no

    print(f"校验文件：{path}")
    print()
    print("各步骤打勾情况（严格 `✅` 行数 / 有效数据行）：")
    for step_no, checked_count, total in summaries:
        status = f"{checked_count}/{total}" if total else "没有有效数据行"
        print(f"  第 {step_no} 步：{status}")
    print()

    if issues:
        print(f"发现 {len(issues)} 处结构性问题：")
        for index, issue in enumerate(issues, start=1):
            print(f"  {index}. {issue}")
        print("提醒：修复结构问题后仍需真实操作证据，脚本不能证明真机测试发生过。")
        return 1

    mode = "完成门禁" if require_complete else "结构"
    print(f"{mode}校验通过。")
    print("提醒：脚本只能验证清单结构，不能证明真实操作、截图或用户验收发生过。")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="09-真机实测.md 的路径")
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="要求所有有效数据行严格填写 ✅，用于标记真机测试通过前的门禁",
    )
    args = parser.parse_args(argv)

    if not args.path.is_file():
        print(f"[错误] 文件不存在：{args.path}")
        return 2

    return check_file(args.path, require_complete=args.require_complete)


if __name__ == "__main__":
    raise SystemExit(main())
