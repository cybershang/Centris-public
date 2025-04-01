"""
Preprocessor.
Author:		Seunghoon Woo (seunghoonwoo@korea.ac.kr)
Modified: 	December 16, 2020.
Forked and modified by: Yingjie Shang (me@yingjie.dev)
Date of modification: 2025-03-30
"""

import os
import shutil
import json
import math
from pathlib import Path
import tlsh


from .config import (
    result_path,
    tag_date_path,
    initial_db_path,
    func_date_path,
    ver_idx_path,
    weight_path,
    meta_path,
    final_db_path,
)


func_date_dict = {}


def extract_ver_date(repo_name: str, tag_date_path: Path) -> dict:
    # For extracting version (tag) date
    ver_date_dict = {}
    tag_file_path = tag_date_path / repo_name
    if tag_file_path.is_file():
        with tag_file_path.open("r", encoding="UTF-8") as f:
            body = "".join(f.readlines()).strip()
            for each_line in body.split("\n"):
                version_list = []
                if "tag:" in each_line:
                    date = each_line[0:10]

                    if "," in each_line:
                        verList = [x for x in each_line.split("tag: ")]
                        for val in verList[1:]:
                            if "," in val:
                                version_list.append(val.split(",")[0])
                            elif ")" in val:
                                version_list.append(val.split(")")[0])
                    else:
                        version_list = [each_line.split("tag: ")[1][:-1]]

                    for each_version in version_list:
                        ver_date_dict[each_version] = date

    return ver_date_dict


def redundancy_elimination():
    for dir in result_path.iterdir():
        repo_name = dir.name

        func_date_dict = {}
        temp_date_dict = {}
        ver_date_dict = extract_ver_date(repo_name, tag_date_path)

        existed_sig = initial_db_path / f"{repo_name}_sig"
        if existed_sig.is_file():
            continue

        ver_temp_lst = []
        signature = {}  # mapping of function hash to idxs
        ver_dict = {}
        idx = 0

        for each_version in (result_path / repo_name).iterdir():
            if (
                each_version.is_file()
                and each_version.name.startswith("fuzzy_")
                and each_version.suffix == ".hidx"
            ):
                version_name = each_version.name.split("fuzzy_")[1].replace(".hidx", "")
            ver_temp_lst.append(version_name)
        ver_temp_lst.sort()

        try:
            for version_name in ver_temp_lst:
                with (result_path / repo_name / f"fuzzy_{version_name}.hidx").open(
                    "r", encoding="UTF-8"
                ) as fp:
                    data = json.load(fp)

                ver_dict[version_name] = idx
                idx += 1

                print(version_name)
                for hashval in data:
                    if hashval not in signature:
                        signature[hashval] = []
                        temp_date_dict[hashval] = []
                    signature[hashval].append(str(idx - 1))

                    if version_name in ver_date_dict:
                        temp_date_dict[hashval].append(ver_date_dict[version_name])
                    else:
                        temp_date_dict[hashval].append("NODATE")

        except Exception as e:
            print("Parsing error: ", e)
            continue

        # For storing function birthdate
        for hashval in temp_date_dict:
            temp_date_dict[hashval].sort()
            func_date_dict[hashval] = temp_date_dict[hashval][0]

        # the birthdate of each function
        with (func_date_path / f"{repo_name}_funcdate").open(
            "w", encoding="UTF-8"
        ) as fdate:
            for hashval, date in func_date_dict.items():
                fdate.write(f"{hashval}\t{date}\n")

        # For storing mapping of version name to indexes
        with (ver_idx_path / f"{repo_name}_idx").open("w", encoding="UTF-8") as fidx:
            save_json = [
                {"ver": ver_name, "idx": str(ver_dict[ver_name])}
                for ver_name in ver_temp_lst
            ]
            fidx.write(json.dumps(save_json))

        # For storing OSS signatures
        with (initial_db_path / f"{repo_name}_sig").open("w", encoding="UTF-8") as f:
            save_json = [
                {"hash": hashval, "vers": signature[hashval]} for hashval in signature
            ]
            f.write(json.dumps(save_json))
        f.close()


def save_meta_infos():
    ave_func_json = {}
    all_func_json = {}
    unique_json = []
    unique = {}
    weight_json = {}

    for OSS in initial_db_path.iterdir():
        repo_name = OSS.stem.replace("_sig", "")
        tot_funcs = 0
        tot_vers = len(list((result_path / repo_name).iterdir()))

        if tot_vers == 0:
            continue

        with (initial_db_path / OSS).open("r", encoding="UTF-8") as fs:
            json_str = json.load(fs)
            tot_funcs = len(json_str)

            for each_json in json_str:
                hashval = each_json["hash"]
                verlst = each_json["vers"]

                if hashval not in unique:
                    unique[hashval] = []

                unique[hashval].append(repo_name)
                weight_json[hashval] = math.log(float(tot_vers) / float(len(verlst)))

        ave_func_json[repo_name] = int(tot_funcs / tot_vers)
        all_func_json[repo_name] = int(tot_funcs)

        with (weight_path / f"{repo_name}_weights").open("w", encoding="UTF-8") as fwei:
            fwei.write(json.dumps(weight_json))
        fwei.close()

    for funcHash in unique:
        temp = {}
        temp["hash"] = funcHash
        temp["OSS"] = unique[funcHash]
        unique_json.append(temp)

    with (meta_path / "aveFuncs").open("w", encoding="UTF-8") as fave:
        fave.write(json.dumps(ave_func_json))

    with (meta_path / "allFuncs").open("w", encoding="UTF-8") as fall:
        fall.write(json.dumps(all_func_json))

    with (meta_path / "uniqueFuncs").open("w", encoding="UTF-8") as funi:
        funi.write(json.dumps(unique_json))


def read_ver_date(ver_date_dict, repo_name, func_date_path: Path):
    file_path = func_date_path / f"{repo_name}_funcdate"
    ver_date_dict[repo_name] = {}
    if file_path.is_file():
        with file_path.open("r", encoding="UTF-8") as fp:
            body = fp.read().strip()
            for each_line in body.split("\n"):
                hashval, date = each_line.split("\t")
                ver_date_dict[repo_name][hashval] = date
    return ver_date_dict


def get_ave_funcs(meta_path: Path):
    ave_funcs = {}
    with open(meta_path / "aveFuncs", "r", encoding="UTF-8") as fp:
        ave_funcs = json.load(fp)
    return ave_funcs


def code_segmentation(theta=0.1):
    ave_funcs = get_ave_funcs(meta_path=meta_path)

    # For printing process #
    l = 1
    tot = len(os.listdir(initial_db_path))
    print("[+] Read OSS signatures..")
    ########################

    oss_list = os.listdir(initial_db_path)

    vers_signatures = {}
    date_signatures = {}
    unique_funcs = {}

    with open(meta_path / "uniqueFuncs", "r", encoding="UTF-8") as fp:
        json_str = json.load(fp)
        for each_val in json_str:
            hashval = each_val["hash"]
            unique_funcs[hashval] = each_val["OSS"]

    ver_date_dict = {}

    for S_sig in oss_list:
        print(l, "/", tot, S_sig)

        S = S_sig.replace("_sig", "")
        l += 1

        possible_members = {}
        candiX = {}
        removed_funcs = []

        if S not in ver_date_dict:
            ver_date_dict = read_ver_date(
                ver_date_dict, S, func_date_path=func_date_path
            )

        with open(initial_db_path / S_sig, "r", encoding="UTF-8") as fs:
            json_str = json.load(fs)
            if len(json_str) == 0:
                continue
            else:
                temp = {}
                for each_val in json_str:
                    hashval = each_val["hash"]

                    for OSS in unique_funcs[hashval]:
                        if OSS == S:
                            continue

                        if OSS not in candiX:
                            temp[OSS] = []
                            candiX[OSS] = 0

                        if OSS not in ver_date_dict:
                            ver_date_dict = read_ver_date(
                                ver_date_dict, OSS, func_date_path=func_date_path
                            )

                        # try:
                        for S_hashval in ver_date_dict[S]:
                            score = tlsh.diffxlen(hashval, S_hashval)
                            if int(score) <= 30:
                                if (
                                    ver_date_dict[S][hashval] == "NODATE"
                                    or ver_date_dict[OSS][hashval] == "NODATE"
                                ):
                                    candiX[OSS] += 1
                                    temp[OSS].append(hashval)
                                elif (
                                    ver_date_dict[OSS][hashval]
                                    <= ver_date_dict[S][hashval]
                                ):
                                    candiX[OSS] += 1
                                    temp[OSS].append(hashval)
                        # except:
                        # pass

                for X in candiX:
                    if ave_funcs[X] == 0:
                        continue

                    elif len(ver_date_dict[X]) == 0:
                        continue

                    elif (float(candiX[X]) / float(ave_funcs[X])) >= theta:
                        if S not in possible_members:
                            possible_members[S] = []

                        possible_members[S].append(X)
                        removed_funcs.extend(temp[X])

                if S not in possible_members:
                    shutil.copy(
                        initial_db_path / f"{S}_sig",
                        final_db_path / f"{S}_sig",
                    )

                else:
                    removed_funcs = set(removed_funcs)
                    save_json = []

                    for each_val in json_str:
                        temp = {}
                        hashval = each_val["hash"]

                        if hashval not in removed_funcs:
                            versLst = each_val["vers"]
                            temp["hash"] = hashval
                            temp["vers"] = versLst
                            save_json.append(temp)

                    with open(
                        final_db_path / f"{S}_sig", "w", encoding="UTF-8"
                    ) as fres:
                        fres.write(json.dumps(save_json))


def preprocess():
    for each_dir in [
        ver_idx_path,
        initial_db_path,
        final_db_path,
        meta_path,
        func_date_path,
        weight_path,
    ]:
        each_dir.mkdir(exist_ok=True)

    redundancy_elimination()
    save_meta_infos()
    code_segmentation()
