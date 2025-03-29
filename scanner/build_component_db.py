import os
import sys

scanner_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(scanner_dir)

from scanner.oss_collector_modified import collect
from scanner.preprocessor_full_modified import preprocess


def main():
    collect(
        repo_list=[
            "https://github.com/nginx/nginx.git",
            "https://github.com/webserver-llc/angie.git",
            "https://github.com/alibaba/tengine.git",
        ]
    )
    preprocess()


if __name__ == "__main__":
    main()
