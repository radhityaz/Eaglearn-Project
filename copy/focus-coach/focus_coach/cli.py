"""Command-line interface for the Focus Coach utility."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .analyzer import SessionAnalyzer, load_events_from_csv
from .simulation import generate_session_events, write_events_to_csv


def _format_minutes(value: float) -> str:
    hours = int(value // 60)
    minutes = value % 60
    if hours:
        return f"{hours}h {minutes:.1f}m"
    return f"{minutes:.1f}m"


def _render_text_summary(summary, limit_blocks: int) -> str:  # noqa: ANN001
    lines: list[str] = []
    lines.append("=== Focus Coach Session Summary ===")
    lines.append(f"Total focus time : {_format_minutes(summary.focus_minutes)}")
    lines.append(f"Total break time : {_format_minutes(summary.break_minutes)}")
    lines.append(f"Focus ratio      : {summary.focus_ratio * 100:.1f}%")
    lines.append(
        f"Avg focus streak : {summary.average_focus_streak_minutes:.1f} minutes "
        f"(longest {summary.longest_focus_streak_minutes:.1f} minutes)"
    )
    if summary.attention_average is not None:
        lines.append(
            "Attention score  : "
            f"{summary.attention_average:.1f} ± {summary.attention_stddev or 0:.1f} "
            f"(n={summary.attention_samples})"
        )
    else:
        lines.append("Attention score  : n/a")
    lines.append(f"Stress events    : {summary.stress_event_count}")

    if summary.focus_blocks:
        lines.append("")
        lines.append("Focus blocks:")
        for idx, block in enumerate(summary.focus_blocks[:limit_blocks], start=1):
            lines.append(
                f"  {idx:02d}. {block.start.isoformat()} → {block.end.isoformat()} "
                f"({_format_minutes(block.minutes)})"
            )
        remaining = len(summary.focus_blocks) - limit_blocks
        if remaining > 0:
            lines.append(f"  ... {remaining} more blocks.")

    if summary.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warn in summary.warnings:
            lines.append(f"  - {warn}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="focus-coach",
        description="Analyse study session timelines and generate synthetic datasets.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyse a session CSV.")
    analyze_parser.add_argument("path", type=Path, help="Path to CSV session log.")
    analyze_parser.add_argument(
        "--json",
        action="store_true",
        help="Output summary as JSON instead of formatted text.",
    )
    analyze_parser.add_argument(
        "--limit-blocks",
        type=int,
        default=5,
        help="Maximum number of focus blocks to list (default: 5).",
    )

    simulate_parser = subparsers.add_parser("simulate", help="Generate a synthetic session log.")
    simulate_parser.add_argument("output", type=Path, help="Output CSV path.")
    simulate_parser.add_argument(
        "--study-minutes",
        type=int,
        default=120,
        help="Total study minutes to simulate (default: 120).",
    )
    simulate_parser.add_argument(
        "--focus-block",
        type=int,
        default=25,
        help="Default focus block length in minutes (default: 25).",
    )
    simulate_parser.add_argument(
        "--break-block",
        type=int,
        default=5,
        help="Default break length in minutes (default: 5).",
    )
    simulate_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed for reproducible simulations.",
    )
    simulate_parser.add_argument(
        "--attention-baseline",
        type=float,
        default=78.0,
        help="Baseline attention score (default: 78).",
    )
    simulate_parser.add_argument(
        "--attention-noise",
        type=float,
        default=6.0,
        help="Standard deviation for attention score noise (default: 6).",
    )
    simulate_parser.add_argument(
        "--stress-probability",
        type=float,
        default=0.08,
        help="Probability (0-1) of emitting a stress event per attention sample.",
    )
    return parser


def cmd_analyze(path: Path, as_json: bool, limit_blocks: int) -> None:
    events = load_events_from_csv(path)
    summary = SessionAnalyzer().analyze(events)
    if as_json:
        print(json.dumps(summary.as_dict(), indent=2))
    else:
        print(_render_text_summary(summary, limit_blocks))


def cmd_simulate(
    output: Path,
    study_minutes: int,
    focus_block: int,
    break_block: int,
    seed: Optional[int],
    attention_baseline: float,
    attention_noise: float,
    stress_probability: float,
) -> None:
    events = generate_session_events(
        study_minutes=study_minutes,
        focus_block=focus_block,
        break_block=break_block,
        seed=seed,
        attention_baseline=attention_baseline,
        attention_noise=attention_noise,
        stress_probability=stress_probability,
    )
    write_events_to_csv(events, output)
    print(f"Generated {len(events)} events → {output}")
    summary = SessionAnalyzer().analyze(events)
    print()
    print(_render_text_summary(summary, limit_blocks=5))


def main(argv: Optional[list[str]] = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "analyze":
        cmd_analyze(args.path, args.json, args.limit_blocks)
    elif args.command == "simulate":
        cmd_simulate(
            output=args.output,
            study_minutes=args.study_minutes,
            focus_block=args.focus_block,
            break_block=args.break_block,
            seed=args.seed,
            attention_baseline=args.attention_baseline,
            attention_noise=args.attention_noise,
            stress_probability=args.stress_probability,
        )
    else:  # pragma: no cover
        parser.error(f"Unknown command {args.command}")
