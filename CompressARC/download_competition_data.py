from pathlib import Path
import shutil

COMPETITION = 'neurogolf-2026'
DATASET_DIR = Path(__file__).parent / 'dataset'

def download_arc_data() -> Path:
    """
    kagglehub.competition_download(COMPETITION) でダウンロードし、
    ダウンロード先のJSONファイルを DATASET_DIR/ にコピーする。
    既にDATASET_DIRにファイルがあればスキップ（上書きしない）。
    戻り値: ダウンロードパス (Path)
    """
    import kagglehub
    path = Path(kagglehub.competition_download(COMPETITION))
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    for json_file in path.rglob('*.json'):
        dest = DATASET_DIR / json_file.name
        if not dest.exists():
            shutil.copy2(json_file, dest)
            print(f'  Copied: {json_file.name}')
        else:
            print(f'  Skip (exists): {json_file.name}')
    return path

def main() -> None:
    print(f'Downloading {COMPETITION}...')
    path = download_arc_data()
    print(f'Path to competition files: {path}')
    print(f'Dataset directory: {DATASET_DIR}')

if __name__ == '__main__':
    main()
