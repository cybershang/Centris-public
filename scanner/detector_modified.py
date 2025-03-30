"""
Detector.
Author:		Seunghoon Woo (seunghoonwoo@korea.ac.kr)
Modified: 	December 16, 2020.
Forked and modified by: Yingjie Shang (me@yingjie.dev)
Date of modification: 2025-03-30
"""

import os
import json
import tlsh


from scanner.oss_collector_modified import hashing
from scanner.preprocessor_full_modified import get_ave_funcs
from scanner.config import (
    result_path as repo_func_path,
    ver_idx_path,
    initial_db_path,
    final_db_path,
    weight_path,
    meta_path,
)

theta = 0.1


def read_component_db() -> dict:
    component_db = {}
    json_lst = []

    for OSS in os.listdir(final_db_path):
        component_db[OSS] = []
        with open(final_db_path / OSS, "r", encoding="UTF-8") as fp:
            json_lst = json.load(fp)

            for each_hash in json_lst:
                hashval = each_hash["hash"]
                component_db[OSS].append(hashval)

    return component_db


def read_all_vers(repo_name):
    allVerList = []
    idx2Ver = {}

    with open(ver_idx_path / f"{repo_name}_idx", "r", encoding="UTF-8") as fp:
        tempVerList = json.load(fp)

        for eachVer in tempVerList:
            allVerList.append(eachVer["ver"])
            idx2Ver[eachVer["idx"]] = eachVer["ver"]

    return allVerList, idx2Ver


def read_weigts(repo_name):
    weightDict = {}

    with open(weight_path / f"{repo_name}_weights", "r", encoding="UTF-8") as fp:
        weightDict = json.load(fp)

    return weightDict


def detect(input_path: str, input_repo: str):
    res_dict, file_cnt, func_cnt, line_cnt = hashing(input_path)

    component_db = {}

    component_db = read_component_db()

    print("Detecting " + input_repo)
    result = {}
    ave_funcs = get_ave_funcs(meta_path)

    for OSS in component_db:
        common_func = []
        repo_name = OSS.split("_sig")[0]
        total_oss_funcs = float(ave_funcs[repo_name])
        if total_oss_funcs == 0.0:
            continue

        com_oss_funcs = 0.0
        for hashval in component_db[OSS]:
            if hashval in res_dict:
                common_func.append(hashval)
                com_oss_funcs += 1.0

        if (com_oss_funcs / total_oss_funcs) >= theta:
            ver_predict_dict = {}
            all_ver_list, idx_2_ver = read_all_vers(repo_name)

            for each_version in all_ver_list:
                if len(each_version) > 0:
                    ver_predict_dict[each_version] = 0.0

            weight_dict = read_weigts(repo_name)

            with open(initial_db_path / OSS, "r", encoding="UTF-8") as fi:
                json_lst = json.load(fi)
                for eachHash in json_lst:
                    hashval = eachHash["hash"]
                    verlist = eachHash["vers"]

                    if hashval in common_func:
                        for added_ver in verlist:
                            ver_predict_dict[idx_2_ver[added_ver]] += weight_dict[
                                hashval
                            ]

            sorted_by_weight = sorted(
                ver_predict_dict.items(), key=lambda x: x[1], reverse=True
            )
            predicted_ver = sorted_by_weight[0][0]

            # TODO: modify this part of code to add more information to the result
            #     "70F055D272EA6CC1A115BA21563BAA0D605D4CDF387406C1EAE1D9219B3CB88F406F1A": [
            #     {
            #         "func_name": "add_oid_section",
            #         "path": "\\apps\\apps.c"
            #     }
            # ],
            predict_oss_dict = {}
            with open(
                repo_func_path / repo_name / f"fuzzy_{predicted_ver}.hidx",
                "r",
                encoding="UTF-8",
            ) as f:
                json_dict = json.load(f)
                for func_hash in json_dict:
                    predict_oss_dict[func_hash] = json_dict[func_hash]

            used = 0
            unused = 0
            modified = 0
            structure_change = False
            reused_function_dict = {}
            for ohash in predict_oss_dict:

                if ohash not in component_db[OSS]:
                    continue

                flag = 0

                for thash in res_dict:
                    # Hit similar function
                    if ohash == thash:
                        used += 1

                        nflag = 0

                        # raw
                        # for opath in predictOSSDict[ohash]["path"]:
                        #     for tpath in inputDict[thash]:
                        #         if opath in tpath:
                        #             nflag = 1

                        # MOIDIFIED
                        for func in predict_oss_dict[ohash]:
                            for t_func in res_dict[thash]:
                                if func["path"] in t_func["path"]:
                                    nflag = 1

                        if nflag == 0:
                            structure_change = True

                        # NOTICE: MODIFIED HERE
                        reused_function_dict[ohash] = {
                            "type": "structure change" if nflag == 0 else "exact",
                            "target": res_dict[thash],
                            "component": predict_oss_dict[ohash],
                        }

                        flag = 1

                    else:
                        score = tlsh.diffxlen(ohash, thash)
                        if int(score) <= 30:
                            modified += 1

                        nflag = 0

                        # for opath in predictOSSDict[ohash]["path"]:
                        #     for tpath in inputDict[thash]:
                        #         if opath in tpath:
                        #             nflag = 1

                        for func in predict_oss_dict[ohash]:
                            for t_func in res_dict[thash]:
                                if func["path"] in t_func["path"]:
                                    nflag = 1

                        if nflag == 0:
                            structure_change = True

                        # NOTICE: MODIFIED HERE
                        if int(score) <= 30:
                            reused_function_dict[ohash] = {
                                "type": (
                                    "modified,structure change"
                                    if nflag == 0
                                    else "modified"
                                ),
                                "t_hash": thash,
                                "target": res_dict[thash],
                                "component": predict_oss_dict[ohash],
                            }

                        flag = 1

                    if flag == 0:
                        unused += 1

            result[OSS.replace("_sig", "")] = {
                "version": predicted_ver,
                "reused_functions": reused_function_dict,
            }

    return result
