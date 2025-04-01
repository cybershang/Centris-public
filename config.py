from pathlib import Path
from app.config import config

root_path = Path(config.scan_data)

collection = root_path / "collection"

preprocess = root_path / "preprocess"

detection = root_path / "result"


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
