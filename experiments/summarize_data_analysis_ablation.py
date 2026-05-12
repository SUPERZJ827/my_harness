import argparse
import csv
from pathlib import Path


MISSING = "-"


def parse_args():
    parser = argparse.ArgumentParser(description="Generate a Chinese Markdown summary for Data Analysis ablation metrics.")
    parser.add_argument("--summary-csv", required=True, help="CSV produced by evaluate_data_analysis_metrics.py.")
    parser.add_argument("--output-md", default=None, help="Markdown output path. Defaults to <summary-csv parent>/ABLATION_SUMMARY.md.")
    parser.add_argument(
        "--primary-metric",
        default="contract_success_rate",
        choices=["contract_success_rate", "artifact_present_rate", "nonempty_final_rate", "TSR"],
        help="Metric used for primary ranking.",
    )
    return parser.parse_args()


def parse_float(value: str):
    if value is None or value == MISSING or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def pct(value):
    parsed = parse_float(value)
    return MISSING if parsed is None else f"{parsed * 100:.1f}%"


def fmt_delta(value):
    if value is None:
        return MISSING
    sign = "+" if value >= 0 else ""
    return f"{sign}{value * 100:.1f}pp"


def load_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def by_variant(rows):
    result = {}
    for row in rows:
        result[row["variant_dir"]] = row
        tame_variant = row.get("tame_variant", "")
        if tame_variant:
            result[tame_variant] = row
    return result


def get_metric(row, metric):
    return parse_float(row.get(metric, MISSING)) if row else None


def compare(rows_by_name, left, right, metric):
    left_row = rows_by_name.get(left)
    right_row = rows_by_name.get(right)
    if not left_row or not right_row:
        return None
    left_value = get_metric(left_row, metric)
    right_value = get_metric(right_row, metric)
    if left_value is None or right_value is None:
        return None
    return right_value - left_value


def row_label(row):
    variant_dir = row.get("variant_dir", "")
    tame_variant = row.get("tame_variant", "")
    if tame_variant and tame_variant != variant_dir:
        return f"{variant_dir} (`{tame_variant}`)"
    return variant_dir


def main():
    args = parse_args()
    summary_csv = Path(args.summary_csv)
    output_md = Path(args.output_md) if args.output_md else summary_csv.parent / "ABLATION_SUMMARY.md"
    rows = load_rows(summary_csv)
    rows_by_name = by_variant(rows)

    ranked = sorted(
        rows,
        key=lambda row: (
            get_metric(row, args.primary_metric) is not None,
            get_metric(row, args.primary_metric) or -1,
            get_metric(row, "nonempty_final_rate") or -1,
            -(get_metric(row, "avg_time") or 10**9),
        ),
        reverse=True,
    )

    lines = [
        "# Data Analysis 消融实验汇总",
        "",
        f"- 输入指标文件：`{summary_csv}`",
        f"- 主排序指标：`{args.primary_metric}`",
        "- `TSR` 只有在数据集提供标准答案时才计算；不可计算时记为 `-`。",
        "- `GDR` 与 `RSR` 需要轨迹漂移判定或故障注入，本脚本暂记为 `-`。",
        "",
        "## 总体排序",
        "",
        "| 排名 | 配置 | TSR | Contract | Artifact | Non-empty Final | Exec Success | SC | EVR | Avg Time |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]

    for idx, row in enumerate(ranked, start=1):
        lines.append(
            "| "
            + " | ".join(
                [
                    str(idx),
                    row_label(row),
                    pct(row.get("TSR")),
                    pct(row.get("contract_success_rate")),
                    pct(row.get("artifact_present_rate")),
                    pct(row.get("nonempty_final_rate")),
                    pct(row.get("exec_success_rate")),
                    row.get("SC", MISSING),
                    pct(row.get("EVR")),
                    row.get("avg_time", MISSING),
                ]
            )
            + " |"
        )

    metric = args.primary_metric
    planned_pairs = [
        ("Minimal -> M", "minimal", "m"),
        ("M -> M + final_guard", "m", "m_final_guard"),
        ("A+T -> A+T + final_guard", "a_t_plus", "a_t_final_guard"),
        ("Full -> Full + final_guard", "full_tame", "full_tame_final_guard"),
        ("A+T -> Full", "a_t_plus", "full_tame"),
        ("A+T+final_guard -> Full+final_guard", "a_t_final_guard", "full_tame_final_guard"),
    ]

    lines.extend(
        [
            "",
            "## 关键对比",
            "",
            f"以下差值均基于主指标 `{metric}`，单位为百分点。",
            "",
            "| 对比 | 差值 | 解释 |",
            "|---|---:|---|",
        ]
    )

    explanations = {
        "Minimal -> M": "检验原始 M 层是否提升交付能力。",
        "M -> M + final_guard": "检验 final artifact guard 是否改善单独 M 层。",
        "A+T -> A+T + final_guard": "检验 final guard 与 A/T 结合是否有效。",
        "Full -> Full + final_guard": "检验 final guard 是否修复完整 TAME 的交付短板。",
        "A+T -> Full": "检验旧完整 M 层加入后是否带来额外收益。",
        "A+T+final_guard -> Full+final_guard": "检验完整 M 层在加入 final guard 后是否超过轻量 M。",
    }
    for name, left, right in planned_pairs:
        delta = compare(rows_by_name, left, right, metric)
        lines.append(f"| {name} | {fmt_delta(delta)} | {explanations[name]} |")

    top = ranked[0] if ranked else {}
    lines.extend(
        [
            "",
            "## 结论摘要",
            "",
            f"- 当前主指标最优配置是 `{row_label(top) if top else MISSING}`。",
            "- 如果 `TSR=-`，说明当前数据集/切分没有可用标准答案；此时结果只能解释为 contract-level completion，而不是最终正确率。",
            "- `artifact_present_rate` 与 `nonempty_final_rate` 用于衡量最终产物交付稳定性，适合 DABstep default 这类无标准答案的扩展实验。",
            "- `exec_success_rate` 是辅助指标；代码执行成功不等于最终任务交付成功。",
            "- `SC` 与 `EVR` 来自输出 JSONL 中的 plan step，可用于比较不同 TAME 变体的执行过程稳定性。",
        ]
    )

    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Saved ablation summary to {output_md}")


if __name__ == "__main__":
    main()
