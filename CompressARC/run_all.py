"""run_all.py — 全タスクを解いて outputs/models/ に ONNX ファイルを生成する"""

import argparse
import json
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

from tqdm import tqdm

# 依存: onnx_export.solve_task, neurogolf_scorer.score_onnx_file

DATASET_PATH = Path("dataset/arc-agi_training_challenges.json")
OUTPUT_DIR   = Path("outputs/models")
RESULTS_PATH = Path("outputs/results.json")

def solve_one(args: tuple) -> dict:
    """ProcessPoolExecutor から呼ばれるワーカー関数。picklable である必要がある。
    
    args: (task_id, task_data_dict, output_dir, epochs)
    戻り値: {"task_id": str, "solved": bool, "arch": str|None,
              "score": float|None, "params": int|None, "bytes": int|None}
    """
    import json, tempfile
    from pathlib import Path
    from onnx_export import solve_task

    task_id, task_data, output_dir_str, epochs = args
    output_dir = Path(output_dir_str)
    output_dir.mkdir(parents=True, exist_ok=True)

    tmp = Path(tempfile.mktemp(suffix=".json"))
    tmp.write_text(json.dumps(task_data))
    try:
        result = solve_task(tmp, output_dir, task_id, epochs=epochs)
        if result:
            return {"task_id": task_id, "solved": True,
                    "arch": result.arch_name, "score": result.score,
                    "params": result.num_params, "bytes": result.file_bytes}
        return {"task_id": task_id, "solved": False,
                "arch": None, "score": None, "params": None, "bytes": None}
    finally:
        tmp.unlink(missing_ok=True)

def main() -> None:
    parser = argparse.ArgumentParser(description="Run TTO on all tasks and export ONNX")
    parser.add_argument("--dataset",  type=Path, default=DATASET_PATH,
                        help="Path to arc-agi challenges JSON")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help="Directory to save ONNX files")
    parser.add_argument("--epochs",   type=int,  default=1000,
                        help="TTO epochs per task")
    parser.add_argument("--workers",  type=int,  default=1,
                        help="Parallel workers (default 1 for CPU safety)")
    parser.add_argument("--resume",   action="store_true",
                        help="Skip tasks where ONNX already exists")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    # タスク一覧ロード
    with open(args.dataset) as f:
        all_tasks = json.load(f)
    print(f"Total tasks: {len(all_tasks)}")

    # resume: 既存ファイルはスキップ
    tasks_to_run = []
    for task_id, task_data in all_tasks.items():
        if args.resume and (args.output_dir / f"{task_id}.onnx").exists():
            continue
        tasks_to_run.append((task_id, task_data, str(args.output_dir), args.epochs))
    print(f"Tasks to run: {len(tasks_to_run)}")

    results: dict = {}
    start = time.time()

    if args.workers == 1:
        # シングルプロセス (デバッグしやすい)
        for job in tqdm(tasks_to_run, desc="Solving"):
            r = solve_one(job)
            results[r["task_id"]] = r
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            futures = {ex.submit(solve_one, job): job[0] for job in tasks_to_run}
            for fut in tqdm(as_completed(futures), total=len(futures), desc="Solving"):
                r = fut.result()
                results[r["task_id"]] = r

    # 既存結果とマージ
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH) as f:
            existing = json.load(f)
        existing.update(results)
        results = existing

    RESULTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)

    elapsed = time.time() - start
    solved = sum(1 for r in results.values() if r["solved"])
    total  = len(results)
    scores = [r["score"] for r in results.values() if r["score"] is not None]
    print(f"\n=== Summary ===")
    print(f"Solved:    {solved} / {total}")
    print(f"Avg score: {sum(scores)/len(scores):.4f}" if scores else "Avg score: N/A")
    print(f"Elapsed:   {elapsed:.1f}s")
    print(f"Results:   {RESULTS_PATH}")

if __name__ == "__main__":
    main()
