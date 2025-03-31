import os
from pathlib import Path

root_path = Path(os.getenv("scanner_data"))

collection = root_path / "collection"
collection.mkdir(exist_ok=True)

preprocess = root_path / "preprocess"
preprocess.mkdir(exist_ok=True)

detection = root_path / "result"
detection.mkdir(exist_ok=True)


bare_path = collection / "bare"
clone_path = collection / "repo_src"
tag_date_path = collection / "repo_date"
result_path = collection / "repo_functions"

ver_idx_path = preprocess / "ver_idx"
initial_db_path = preprocess / "initial_sigs"
final_db_path = preprocess / "component_db"
meta_path = preprocess / "meta_infos"
weight_path = meta_path / "weights"
func_date_path = preprocess / "func_date"
