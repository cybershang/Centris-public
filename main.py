from scanner.oss_collector_modified import collect
from pathlib import Path
from scanner.preprocessor_full_modified import preprocess


def main():
    root_path = Path("/home/shang/Repo/osvs/scanner/data/")
    collection_path = root_path / Path("collection")
    collection_path.mkdir(exist_ok=True)
    result_path, tag_date_path = collect(
        repo_list=[
            # "https://github.com/nginx/nginx.git",
            # "https://github.com/webserver-llc/angie.git",
            # "https://github.com/alibaba/tengine.git",
        ],
        collection_path=collection_path,
    )
    preprocess_path = root_path / Path("preprocess")
    preprocess_path.mkdir(exist_ok=True)
    preprocess(
        tag_date_path=tag_date_path,
        result_path=result_path,
        preprocess_path=preprocess_path,
    )


if __name__ == "__main__":
    main()
