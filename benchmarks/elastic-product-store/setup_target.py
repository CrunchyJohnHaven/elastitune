from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TARGET_ROOT = ROOT / ".benchmarks" / "elastic-product-store"
REPO_DIR = TARGET_ROOT / "elasticsearch-labs"
REPO_URL = "https://github.com/elastic/elasticsearch-labs.git"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=cwd, check=True)


def main() -> None:
    TARGET_ROOT.mkdir(parents=True, exist_ok=True)

    if REPO_DIR.exists():
        print(f"Refreshing existing checkout in {REPO_DIR}")
        run(["git", "-C", str(REPO_DIR), "pull", "--ff-only"])
    else:
        print(f"Cloning {REPO_URL} into {REPO_DIR}")
        run(["git", "clone", "--depth=1", REPO_URL, str(REPO_DIR)])

    print()
    print("Elastic benchmark target is ready.")
    print(f"Repo root: {REPO_DIR}")
    print("Next:")
    print("  1. Start Docker from the upstream product-store-search/docker folder")
    print("  2. Run create_index.py")
    print("  3. Run ingest_products.py")


if __name__ == "__main__":
    main()
