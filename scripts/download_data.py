import sys
import urllib.request
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
BASE_URL = (
    "https://huggingface.co/api/datasets/koutch/stackoverflow_python"
    "/parquet/default/train/{i}.parquet"
)
NUM_SHARDS = 5


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for i in range(NUM_SHARDS):
        dest = RAW_DIR / f"train-{i}.parquet"
        if dest.exists() and dest.stat().st_size > 0:
            print(f"[skip] {dest.name} already exists")
            continue
        url = BASE_URL.format(i=i)
        print(f"[get ] {url}")
        urllib.request.urlretrieve(url, dest)
        print(f"[done] {dest.name} ({dest.stat().st_size / 1e6:.0f} MB)")
    print("All shards downloaded to", RAW_DIR)


if __name__ == "__main__":
    sys.exit(main())
