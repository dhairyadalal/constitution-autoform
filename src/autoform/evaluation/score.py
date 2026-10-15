"""Aggregate independent agent votes and score solver results."""

from __future__ import annotations

from collections import Counter


def aggregate_votes(vote_batches: list[dict], case_ids: list[str]) -> dict:
    reference = {}
    for case_id in case_ids:
        votes = []
        for batch in vote_batches:
            matching = [item for item in batch.get("judgments", []) if item.get("case_id") == case_id]
            if len(matching) == 1 and matching[0].get("answer") in {"yes", "no", "unresolved"}:
                votes.append(matching[0])
        counts = Counter(item["answer"] for item in votes)
        top_answer, top_count = counts.most_common(1)[0] if counts else ("unresolved", 0)
        answer = top_answer if top_count >= 2 and top_answer != "unresolved" else "unresolved"
        reference[case_id] = {
            "answer": answer,
            "votes": votes,
            "vote_counts": dict(counts),
            "disagreement": len(counts) > 1 or len(votes) < len(vote_batches),
        }
    return reference


def score_candidate(case_results: list[dict], reference: dict) -> dict:
    summary = {
        "cases": len(case_results), "determinate_reference": 0, "correct": 0,
        "false_acceptance": 0, "false_rejection": 0,
        "unresolved_output": 0, "invalid_output": 0, "reference_unresolved": 0,
    }
    for item in case_results:
        expected = reference[item["case_id"]]["answer"]
        actual = item["result"].get("answer")
        status = item["result"].get("status")
        if status != "valid":
            summary["invalid_output"] += 1
        if expected == "unresolved":
            summary["reference_unresolved"] += 1
            continue
        summary["determinate_reference"] += 1
        if status == "valid" and actual == expected:
            summary["correct"] += 1
        elif status == "valid" and actual == "unresolved":
            summary["unresolved_output"] += 1
        elif status == "valid" and actual == "yes" and expected == "no":
            summary["false_acceptance"] += 1
        elif status == "valid" and actual == "no" and expected == "yes":
            summary["false_rejection"] += 1
    denominator = summary["determinate_reference"]
    summary["overall_accuracy"] = summary["correct"] / denominator if denominator else None
    summary["executable"] = summary["invalid_output"] == 0
    return summary
