from pathlib import Path
import json
import sys
from pydantic import BaseModel

from scanner.detector_modified import detect


class PackageInfo(BaseModel):
    name: str
    version: str


def main():
    input_repo = "te"
    input_path = Path("/home/shang/Repo/osvs/scanner/data/collection/repo_src/tengine")
    result = detect(input_path, input_repo)
    dependency_list = []

    for pkg in result:
        dependency_list.append(
            PackageInfo(name=pkg, version=result[pkg]["version"])
        )

    print(dependency_list)
    with open(f"/home/shang/Repo/osvs/{input_repo}.json", "w") as f:
        json.dump(result, f, indent=4)


if __name__ == "__main__":
    main()
