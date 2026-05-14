"""submit.py — ONNX ファイルを zip に固めて Kaggle コンペに提出する

使い方:
    uv run python submit.py "コメント"                  # outputs/models/ を zip して提出
    uv run python submit.py "コメント" --run-all        # 先に run_all.py を実行してから提出
    uv run python submit.py "コメント" --file my.zip    # 既存 zip を提出
"""

import argparse
import subprocess
import sys
import zipfile
from pathlib import Path

COMPETITION: str = "neurogolf-2026"
OUTPUT_DIR: Path = Path("outputs/models")
SUBMIT_ZIP: Path = Path("outputs/submission.zip")

def make_zip(model_dir: Path, zip_path: Path) -> int:
    """model_dir 内の *.onnx を zip_path にまとめる。ファイル数を返す。"""
    onnx_files = sorted(model_dir.glob("*.onnx"))
    if not onnx_files:
        raise FileNotFoundError(f"No .onnx files found in {model_dir}")
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in onnx_files:
            zf.write(f, f.name)
    print(f"Zipped {len(onnx_files)} ONNX files → {zip_path}")
    return len(onnx_files)

def kaggle_submit(zip_path: Path, message: str, competition: str) -> None:
    """kaggle CLI で提出する。"""
    kaggle_bin = Path(sys.executable).parent / "kaggle"
    cmd = [
        str(kaggle_bin),
        "competitions", "submit",
        "-c", competition,
        "-f", str(zip_path),
        "-m", message,
    ]
    print(f"Submitting: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        sys.exit(result.returncode)

def main() -> None:
    parser = argparse.ArgumentParser(description="Package ONNX files and submit to Kaggle")
    parser.add_argument("message",     type=str,
                        help="Submission comment / message")
    parser.add_argument("--file",      type=Path, default=None,
                        help="Use this zip instead of building from outputs/models/")
    parser.add_argument("--run-all",   action="store_true",
                        help="Run run_all.py first to generate ONNX files")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help="Directory containing .onnx files (default: outputs/models)")
    parser.add_argument("--zip-path",  type=Path, default=SUBMIT_ZIP,
                        help="Output zip path (default: outputs/submission.zip)")
    parser.add_argument("--competition", type=str, default=COMPETITION,
                        help=f"Kaggle competition ID (default: {COMPETITION})")
    parser.add_argument("--dry-run",   action="store_true",
                        help="Build zip but skip kaggle submit")
    args = parser.parse_args()

    # オプション: run_all.py を先に実行
    if args.run_all:
        print("Running run_all.py first...")
        result = subprocess.run([sys.executable, "run_all.py"], check=True)

    # zip 作成
    zip_path = args.file if args.file else args.zip_path
    if not args.file:
        make_zip(args.output_dir, zip_path)
    else:
        if not zip_path.exists():
            print(f"ERROR: --file {zip_path} does not exist")
            sys.exit(1)
        print(f"Using existing file: {zip_path}")

    # Kaggle 提出
    if args.dry_run:
        print(f"[dry-run] Would submit: {zip_path} to {args.competition}")
        print(f"[dry-run] Message: {args.message}")
    else:
        kaggle_submit(zip_path, args.message, args.competition)

if __name__ == "__main__":
    main()
