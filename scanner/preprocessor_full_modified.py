"""
Preprocessor.
Author:		Seunghoon Woo (seunghoonwoo@korea.ac.kr)
Modified: 	December 16, 2020.
"""

import os
import shutil
import json
import math
import tlsh

"""GLOBALS"""
current_path = os.getcwd()
separator = "#@#"
sep_len = len(separator)
# So far, do not change

theta = 0.1  # Default value (0.1)
tag_date_path = "../osscollector/repo_date/"  # Default path
result_path = "../osscollector/repo_functions/"  # Default path
ver_idx_path = current_path + "/verIDX/"  # Default path
initial_db_path = current_path + "/initialSigs/"  # Default path
final_db_path = current_path + "/componentDB/"  # Default path of the final Component DB
meta_path = (
    current_path + "/metaInfos/"
)  # Default path, for saving pieces of meta-information of collected repositories
weight_path = meta_path + "/weights/"  # Default path, for version prediction
func_date_path = current_path + "/funcDate/"  # Default path

# Generate directories
should_make = [
    ver_idx_path,
    initial_db_path,
    final_db_path,
    meta_path,
    func_date_path,
    weight_path,
]
for each_repo in should_make:
    if not os.path.isdir(each_repo):
        os.mkdir(each_repo)

funcDateDict = {}


def extract_ver_date(repo_name: str):
    # For extracting version (tag) date

    ver_date_dict = {}
    if os.path.isfile(os.path.join(tag_date_path, repo_name)):
        with open(os.path.join(tag_date_path, repo_name), "r", encoding="UTF-8") as fp:
            body = "".join(fp.readlines()).strip()
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
                        version_list = [(each_line.split("tag: ")[1][:-1])]

                    for each_version in version_list:
                        ver_date_dict[each_version] = date

    return ver_date_dict


def redundancy_elimination():
    for repo_name in os.listdir(result_path):
        print(repo_name)

        func_date_dict = {}
        temp_date_dict = {}
        ver_date_dict = extract_ver_date(repo_name)

        # if os.path.isfile(os.path.join(initialDBPath, repo_name + "_sig")):
        # 	continue
        ## For skipping already generated Sigs

        ver_temp_lst = []
        signature = {}  # mapping of function hash to idxs
        ver_dict = {}
        idx = 0

        for each_version in os.listdir(os.path.join(result_path, repo_name)):
            version_name = each_version.split("fuzzy_")[1].replace(".hidx", "")
            if version_name == "" or version_name == " ":
                continue
            ver_temp_lst.append(version_name)
        ver_temp_lst.sort()

        try:
            for version_name in ver_temp_lst:
                with open(
                    os.path.join(
                        result_path, repo_name, ("fuzzy_" + version_name + ".hidx")
                    ),
                    "r",
                    encoding="UTF-8",
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
        fdate = open(func_date_path + repo_name + "_funcdate", "w")
        for hashval in func_date_dict:
            fdate.write(hashval + "\t" + func_date_dict[hashval] + "\n")
        fdate.close()

        # For storing mapping of version name to indexes
        fidx = open(ver_idx_path + repo_name + "_idx", "w")
        save_json = []

        for ver_name in ver_temp_lst:
            temp = {}
            temp["ver"] = ver_name
            temp["idx"] = str(ver_dict[ver_name])
            save_json.append(temp)

        fidx.write(json.dumps(save_json))
        fidx.close()

        # For storing OSS signatures
        f = open(initial_db_path + repo_name + "_sig", "w")

        save_json = []
        for hashval in signature:
            temp = {}
            temp["hash"] = hashval
            temp["vers"] = signature[hashval]
            save_json.append(temp)
        f.write(json.dumps(save_json))
        f.close()


def save_meta_infos():
    ave_func_json = {}
    all_func_json = {}
    unique_json = []
    unique = {}
    weight_json = {}

    fave = open(meta_path + "aveFuncs", "w")
    fall = open(meta_path + "allFuncs", "w")
    funi = open(meta_path + "uniqueFuncs", "w")

    for OSS in os.listdir(initial_db_path):
        repo_name = OSS.replace("_sig", "")
        tot_funcs = 0
        tot_vers = len(os.listdir(result_path + repo_name))

        if tot_vers == 0:
            continue

        fwei = open(weight_path + "/" + repo_name + "_weights", "w")

        with open(initial_db_path + OSS, "r", encoding="UTF-8") as fs:
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

        fwei.write(json.dumps(weight_json))
        fwei.close()

    for funcHash in unique:
        temp = {}
        temp["hash"] = funcHash
        temp["OSS"] = unique[funcHash]
        unique_json.append(temp)

    fave.write(json.dumps(ave_func_json))
    fall.write(json.dumps(all_func_json))
    funi.write(json.dumps(unique_json))

    fave.close()
    fall.close()
    funi.close()


def readVerDate(ver_date_dict, repo_name):
    ver_date_dict[repo_name] = {}

    if os.path.isfile(func_date_path + repo_name + "_funcdate"):
        with open(
            func_date_path + repo_name + "_funcdate", "r", encoding="UTF-8"
        ) as fp:
            body = "".join(fp.readlines()).strip()
            for each_line in body.split("\n"):
                hashval = each_line.split("\t")[0]
                date = each_line.split("\t")[1]
                ver_date_dict[repo_name][hashval] = date
    return ver_date_dict


def getave_funcs():
    ave_funcs = {}
    with open(meta_path + "aveFuncs", "r", encoding="UTF-8") as fp:
        ave_funcs = json.load(fp)
    return ave_funcs


def code_segmentation():
    ave_funcs = getave_funcs()

    # For printing process #
    l = 1
    tot = len(os.listdir(initial_db_path))
    print("[+] Read OSS signatures..")
    ########################

    oss_list = os.listdir(initial_db_path)

    vers_signatures = {}
    date_signatures = {}
    unique_funcs = {}

    with open(meta_path + "uniqueFuncs", "r", encoding="UTF-8") as fp:
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
            ver_date_dict = readVerDate(ver_date_dict, S)

        with open(initial_db_path + S_sig, "r", encoding="UTF-8") as fs:
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
                            ver_date_dict = readVerDate(ver_date_dict, OSS)

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
                        os.path.join(initial_db_path, S) + "_sig",
                        os.path.join(final_db_path, S) + "_sig",
                    )

                else:
                    removed_funcs = set(removed_funcs)
                    save_json = []
                    fres = open(os.path.join(final_db_path, S) + "_sig", "w")

                    for each_val in json_str:
                        temp = {}
                        hashval = each_val["hash"]

                        if hashval not in removed_funcs:
                            versLst = each_val["vers"]
                            temp["hash"] = hashval
                            temp["vers"] = versLst
                            save_json.append(temp)

                    fres.write(json.dumps(save_json))
                    fres.close()


def main():
    redundancy_elimination()
    save_meta_infos()
    code_segmentation()


""" EXECUTE """
if __name__ == "__main__":
    main()
