"""
Dataset Collection Tool.
Author:		Seunghoon Woo (seunghoonwoo@korea.ac.kr)
Modified: 	December 16, 2020.
"""

import json
import os
import subprocess
import re
import tlsh  # Please intall python-tlsh
import chardet
from pathlib import Path
from multiprocessing import Pool, cpu_count
import threading
import logging


def compute_tlsh(string):
    string = str.encode(string)
    hs = tlsh.forcehash(string)
    return hs


def remove_comment(string):
    # Code for removing C/C++ style comments. (Imported from VUDDY and ReDeBug.)
    # ref: https://github.com/squizz617/vuddy
    c_regex = re.compile(
        r'(?P<comment>//.*?$|[{}]+)|(?P<multilinecomment>/\*.*?\*/)|(?P<noncomment>\'(\\.|[^\\\'])*\'|"(\\.|[^\\"])*"|.[^/\'"]*)',
        re.DOTALL | re.MULTILINE,
    )
    return "".join(
        [
            c.group("noncomment")
            for c in c_regex.finditer(string)
            if c.group("noncomment")
        ]
    )


def normalize(string):
    # Code for normalizing the input string.
    # LF and TAB literals, curly braces, and spaces are removed,
    # and all characters are lowercased.
    # ref: https://github.com/squizz617/vuddy
    return "".join(
        string.replace("\n", "")
        .replace("\r", "")
        .replace("\t", "")
        .replace("{", "")
        .replace("}", "")
        .split(" ")
    ).lower()


def hashing(repo_path):
    def get_encoding(filePath):
        return chardet.detect(open(filePath, "rb").read())["encoding"]

    # This function is for hashing C/C++ functions
    # Only consider ".c", ".cc", and ".cpp" files
    possible = (".c", ".cc", ".cpp")

    file_cnt = 0
    func_cnt = 0
    line_cnt = 0

    res_dict = {}

    for path, dir, files in os.walk(repo_path):
        for file in files:
            file_path = os.path.join(path, file)

            if file.endswith(possible):
                try:
                    # Execute Ctgas command
                    functionList = subprocess.check_output(
                        'ctags'
                        + ' -f - --kinds-C=* --fields=neKSt "'
                        + file_path
                        + '"',
                        stderr=subprocess.STDOUT,
                        shell=True,
                    ).decode()

                    f = open(file_path, "r", encoding=get_encoding(file_path))

                    # For parsing functions
                    lines = f.readlines()
                    all_funcs = str(functionList).split("\n")
                    func = re.compile(r"(function)")
                    number = re.compile(r"(\d+)")
                    func_search = re.compile(r"{([\S\s]*)}")
                    tmp_string = ""
                    func_body = ""

                    file_cnt += 1

                    for i in all_funcs:
                        elem_list = re.sub(r"[\t\s ]{2,}", "", i)
                        elem_list = elem_list.split("\t")
                        func_body = ""

                        if (
                            i != ""
                            and len(elem_list) >= 8
                            and func.fullmatch(elem_list[3])
                        ):
                            func_start_line = int(number.search(elem_list[4]).group(0))
                            func_end_line = int(number.search(elem_list[7]).group(0))

                            tmp_string = ""
                            tmp_string = tmp_string.join(
                                lines[func_start_line - 1 : func_end_line]
                            )

                            if func_search.search(tmp_string):
                                func_body = func_body + func_search.search(
                                    tmp_string
                                ).group(1)
                            else:
                                func_body = " "

                            func_body = remove_comment(func_body)
                            func_body = normalize(func_body)
                            func_hash = compute_tlsh(func_body)

                            if len(func_hash) == 72 and func_hash.startswith("T1"):
                                func_hash = func_hash[2:]
                            elif (
                                func_hash == "TNULL"
                                or func_hash == ""
                                or func_hash == "NULL"
                            ):
                                continue

                            stored_path = file_path.replace(str(repo_path), "")
                            if func_hash not in res_dict:
                                res_dict[func_hash] = []
                            # I modified here
                            res_dict[func_hash].append(
                                {"func": elem_list[0], "path": stored_path}
                            )

                            line_cnt += len(lines)
                            func_cnt += 1

                except subprocess.CalledProcessError as e:
                    print("Parser Error:", e)
                    continue
                except Exception as e:
                    print("Subprocess failed", e)
                    continue

    return res_dict, file_cnt, func_cnt, line_cnt


def indexing(res_dict, title, file_path):
    with open(file_path, "w") as f:
        json.dump(res_dict, f, indent=4)


def get_local_repos(parent_dir):
    try:
        # List all entries in the directory
        entries = os.listdir(parent_dir)

        # Filter and return only directories
        subdirs = [
            os.path.join(parent_dir, entry)
            for entry in entries
            if os.path.isdir(os.path.join(parent_dir, entry))
        ]
        return subdirs
    except FileNotFoundError:
        print(f"Error: Directory {parent_dir} does not exist.")
        return []
    except PermissionError:
        print(f"Error: Permission denied for directory {parent_dir}.")
        return []


def process_repo(local_repo, clone_path, tag_date_path, result_path):
    repo_name = Path(local_repo).name
    print("[+] Processing", repo_name)

    try:
        os.chdir(clone_path / Path(repo_name))

        # For storing tag dates
        date_cmd = 'git log --tags --simplify-by-decoration --pretty="format:%ai %d"'
        date_result = subprocess.check_output(
            date_cmd, stderr=subprocess.STDOUT, shell=True
        ).decode()

        with open(tag_date_path / Path(repo_name), "w") as f:
            f.write(str(date_result))

        tag_cmd = "git tag"
        tag_result = subprocess.check_output(
            tag_cmd, stderr=subprocess.STDOUT, shell=True
        ).decode()

        res_dict = {}
        file_cnt = 0
        func_cnt = 0
        line_cnt = 0

        if tag_result == "":
            # No tags, only master repo
            res_dict, file_cnt, func_cnt, line_cnt = hashing(clone_path + repo_name)
            if len(res_dict) > 0:
                if not os.path.isdir(result_path + repo_name):
                    os.mkdir(result_path + repo_name)
                title = "\t".join(
                    [repo_name, str(file_cnt), str(func_cnt), str(line_cnt)]
                )
                result_file_path = (
                    result_path / repo_name / f"fuzzy_{repo_name}.hidx"
                )  # Default file name: "fuzzy_OSSname.hidx"

                indexing(res_dict, title, result_file_path)

        else:
            for tag in str(tag_result).split("\n"):
                # Generate function hashes for each tag (version)
                checkout_cmd = subprocess.check_output(
                    "git checkout -f " + tag,
                    stderr=subprocess.STDOUT,
                    shell=True,
                )
                print(f"before {tag}, after {tag.replace('/', '-')}")
                if "/" in tag:
                    tag = tag.replace("/", "-")

                res_dict, file_cnt, func_cnt, line_cnt = hashing(clone_path / repo_name)

                if len(res_dict) > 0:
                    if not os.path.isdir(result_path / repo_name):
                        os.mkdir(result_path / repo_name)
                    title = "\t".join(
                        [repo_name, str(file_cnt), str(func_cnt), str(line_cnt)]
                    )
                    result_file_path = (
                        result_path / repo_name / Path(f"fuzzy_{tag}.hidx")
                    )

                    indexing(res_dict, title, result_file_path)

    except subprocess.CalledProcessError as e:
        print(f"Parser Error in {repo_name}:", e)
        return
    except Exception as e:
        print(f"Subprocess failed in {repo_name}", e)
        return


def clone_repo(url, dest):
    try:
        logging.basicConfig(level=logging.INFO)
        logging.info(f"start clone repo: {url} -> {dest}")
        result = subprocess.run(
            f"git clone --mirror {url} {dest}",
            shell=True,
            check=True,
            text=True,
            capture_output=True,
        )
        logging.info(f"clone successed: {url} -> {dest}")
    except subprocess.CalledProcessError as e:
        logging.error(f"clone failed: {url} -> {dest}")
        logging.error(e.stderr)
        logging.error(e.stdout)


def turn_to_working(src, dest):
    try:
        logging.basicConfig(level=logging.INFO)
        logging.info(f"start turn to working: {src} -> {dest}")
        result = subprocess.run(
            f"git clone {src} {dest}",
            shell=True,
            check=True,
            text=True,
            capture_output=True,
        )
        logging.info(f"turn to working successed: {src} -> {dest}")
    except subprocess.CalledProcessError as e:
        logging.error(f"turn to working failed: {src} -> {dest}")
        logging.error(e.stderr)
        logging.error(result.stdout)


def clone_repos(repo_list, bare_path, working_path):
    def clone_and_turn(url):
        get_bare_repo_name = lambda url: url.split("/")[-1]
        get_repo_name = lambda url: url.split("/")[-1].replace(".git", "")

        bare = bare_path / get_bare_repo_name(url)
        working = working_path / get_repo_name(url)
        clone_repo(url, bare)
        turn_to_working(bare, working)

    threads = []
    for url in repo_list:
        thread = threading.Thread(target=clone_and_turn, args=(url,))
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()


def collect(repo_list: list, collection_path: Path):
    bare_path = collection_path / Path("bare")
    clone_path = collection_path / Path("repo_src")
    tag_date_path = collection_path / Path("repo_date")
    result_path = collection_path / Path("repo_functions")

    for each_dir in [bare_path, clone_path, tag_date_path, result_path]:
        each_dir.mkdir(exist_ok=True, parents=True)

    if repo_list:
        # multi-threads download
        clone_repos(repo_list, bare_path, clone_path)

    # multi processing
    repos = get_local_repos(clone_path)
    num_processes = min(cpu_count(), len(repos))
    args = [(repo, clone_path, tag_date_path, result_path) for repo in repos]

    with Pool(processes=num_processes) as pool:
        pool.starmap(process_repo, args)
    
    return result_path, tag_date_path
