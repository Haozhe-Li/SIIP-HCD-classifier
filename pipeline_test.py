import asyncio
import os
import sys
import time

from dotenv import load_dotenv

from core.data_table import Student_HCD_Label, List_Student_HCD_Label
from core.processing import Processing
from core.processing_few_shot import ProcessingFewShot
from database.db import client, DATABASE_ID

load_dotenv()


async def fetch_labeled_activities(limit: int = 30) -> list[dict]:
    sql = """
        SELECT rowid, Activity, HCD_Space, HCD_Subspace, Reason, Annotator
        FROM labels
        WHERE HCD_Space IS NOT NULL AND HCD_Space != ''
          AND LOWER(HCD_Space) != 'unknown'
          AND LOWER(HCD_Subspace) != 'unknown'
        ORDER BY rowid ASC
        LIMIT ?
    """
    try:
        result = await client.query_db(db_id=DATABASE_ID, sql=sql, params=[limit])
        if result.success and result.results:
            return result.results[0].get("results", [])
    except Exception as e:
        print(f"Error fetching activities: {e}")
    return []


def parse_split(val: str) -> list[str]:
    if not val:
        return []
    # Normalize ' and ' and ' & ' to comma so they split properly
    val = val.replace(" and ", ",").replace(" & ", ",")
    return [x.strip() for x in val.split(",") if x.strip()]


def calculate_metrics(true_sets, pred_sets):
    tp = fp = fn = 0
    for true_set, pred_set in zip(true_sets, pred_sets):
        true_set_lower = {x.lower().strip() for x in true_set if x.strip()}
        pred_set_lower = {x.lower().strip() for x in pred_set if x.strip()}

        # If the single LLM predicted label is among the true labels, it's a complete match
        if len(pred_set_lower.intersection(true_set_lower)) > 0:
            tp += 1
        else:
            if len(pred_set_lower) > 0:
                fp += 1
            if len(true_set_lower) > 0:
                fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )

    return precision, recall, f1, tp, fp, fn


def calculate_latency_stats(latencies: list[float]) -> dict:
    if not latencies:
        return {}
    latencies.sort()
    n = len(latencies)
    return {
        "avg": sum(latencies) / n,
        "min": latencies[0],
        "max": latencies[-1],
        "p50": latencies[min(int(n * 0.50), n - 1)],
        "p90": latencies[min(int(n * 0.90), n - 1)],
        "p95": latencies[min(int(n * 0.95), n - 1)],
        "p99": latencies[min(int(n * 0.99), n - 1)],
    }


async def main():
    print("Fetching labeled activities from D1...")
    rows = await fetch_labeled_activities(limit=100)

    if not rows:
        print("No labeled activities found!")
        return

    print(f"Fetched {len(rows)} labeled activities.")

    student_labels = []
    for row in rows:
        activity_text = row.get("Activity", "")
        spaces = parse_split(row.get("HCD_Space", ""))
        subspaces = parse_split(row.get("HCD_Subspace", ""))

        student_labels.append(
            Student_HCD_Label(
                activity=activity_text, HCD_Spaces=spaces, HCD_Subspaces=subspaces
            )
        )

    student_data = List_Student_HCD_Label(tables=student_labels)

    print("\n--- Running AI Classifier (ProcessingFewShot) ---")
    processor = ProcessingFewShot()

    sem = asyncio.Semaphore(4)
    latencies = []

    async def classify_with_latency(entry):
        async with sem:
            req_start = time.time()
            res = await processor.aclassify_activity(entry.activity)
            req_end = time.time()
            latencies.append(req_end - req_start)
            return res

    start_time = time.time()
    tasks = [classify_with_latency(entry) for entry in student_data.tables]
    llm_labels = await asyncio.gather(*tasks)
    total_time = time.time() - start_time

    latency_stats = calculate_latency_stats(latencies)

    true_spaces = [set(s.HCD_Spaces) for s in student_data.tables]
    pred_spaces = [set(p.HCD_Spaces) for p in llm_labels]

    true_subspaces = [set(s.HCD_Subspaces) for s in student_data.tables]
    pred_subspaces = [set(p.HCD_Subspaces) for p in llm_labels]

    sp_p, sp_r, sp_f1, sp_tp, sp_fp, sp_fn = calculate_metrics(true_spaces, pred_spaces)
    ssp_p, ssp_r, ssp_f1, ssp_tp, ssp_fp, ssp_fn = calculate_metrics(
        true_subspaces, pred_subspaces
    )

    # Build report text
    report_lines = []
    report_lines.append("=== Few-Shot Pipeline Evaluation Text Report ===\n")
    report_lines.append("--- Subspace Labeling Differences ---")

    mismatch_count = 0
    for i in range(len(rows)):
        expected_sub = {
            x.lower().strip() for x in parse_split(rows[i].get("HCD_Subspace", ""))
        }
        classified_sub = {x.lower().strip() for x in llm_labels[i].HCD_Subspaces}

        expected_space = {
            x.lower().strip() for x in parse_split(rows[i].get("HCD_Space", ""))
        }
        classified_space = {x.lower().strip() for x in llm_labels[i].HCD_Spaces}

        # Treat as correct (no mismatch) if the classified label is among the expected labels
        space_mismatch = len(classified_space.intersection(expected_space)) == 0
        subspace_mismatch = len(classified_sub.intersection(expected_sub)) == 0

        if space_mismatch or subspace_mismatch:
            mismatch_count += 1
            activity = rows[i].get("Activity", "")
            reason = rows[i].get("Reason", "")
            if not reason:
                reason = "No reason provided"

            exp_space_str = ", ".join(expected_space) if expected_space else "None"
            exp_sub_str = ", ".join(expected_sub) if expected_sub else "None"
            cls_space_str = ", ".join(classified_space) if classified_space else "None"
            cls_sub_str = ", ".join(classified_sub) if classified_sub else "None"

            report_lines.append(f"\nActivity: {activity}")
            report_lines.append(f"Expected: [{exp_space_str}] {exp_sub_str}")
            report_lines.append(f"Classified: [{cls_space_str}] {cls_sub_str}")
            report_lines.append(f"Reason: {reason}")
            report_lines.append("-" * 40)

    if mismatch_count == 0:
        report_lines.append("\nNo mismatches found!")

    report_lines.append("\n--- Metrics ---")
    report_lines.append("Spaces (Micro-Averaged):")
    report_lines.append(f"  TP: {sp_tp}, FP: {sp_fp}, FN: {sp_fn}")
    report_lines.append(f"  Precision: {sp_p:.4f}")
    report_lines.append(f"  Recall:    {sp_r:.4f}")
    report_lines.append(f"  F1 Score:  {sp_f1:.4f}")

    report_lines.append("\nSubspaces (Micro-Averaged):")
    report_lines.append(f"  TP: {ssp_tp}, FP: {ssp_fp}, FN: {ssp_fn}")
    report_lines.append(f"  Precision: {ssp_p:.4f}")
    report_lines.append(f"  Recall:    {ssp_r:.4f}")
    report_lines.append(f"  F1 Score:  {ssp_f1:.4f}")

    if latency_stats:
        report_lines.append("\n--- Latency & Performance ---")
        report_lines.append(f"Total Pipeline Time: {total_time:.2f} seconds")
        report_lines.append(f"Average Request Latency: {latency_stats['avg']:.2f}s")
        report_lines.append(f"Min Latency: {latency_stats['min']:.2f}s")
        report_lines.append(f"Max Latency: {latency_stats['max']:.2f}s")
        report_lines.append(f"P50 Latency: {latency_stats['p50']:.2f}s")
        report_lines.append(f"P90 Latency: {latency_stats['p90']:.2f}s")
        report_lines.append(f"P95 Latency: {latency_stats['p95']:.2f}s")
        report_lines.append(f"P99 Latency: {latency_stats['p99']:.2f}s")

    report_text = "\n".join(report_lines)

    dataset_size = len(rows)
    filename = f"evaluation_report_few_shot_n{dataset_size}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\nFew-Shot Report with {mismatch_count} differences saved to '{filename}'.")


if __name__ == "__main__":
    asyncio.run(main())
