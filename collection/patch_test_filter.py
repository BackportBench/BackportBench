import sys
import re
import json
from subprocess import getstatusoutput
from collections import defaultdict
from tqdm import tqdm
from datetime import datetime
#import matplotlib.pyplot as plt


if __name__ == "__main__":
    eco = sys.argv[1]
    # used_file_suffix = [".py", ".js", ".ts", ".java"]
    #  The format of jsonl is "{}\n{}\n{}", so after "split('\n')" we get ["{}", "{}", "{}"], finally use json.loads to
    # get the json dictionary

    with open(f'{eco}_potential_datapoints_one_repo_for_vuln.jsonl') as f:
        json_tmp = [json.loads(i) for i in f.read().strip().split('\n')]

    # test_pattern is used to judge whether the file name includes "test" or not, if so, we assume it is a testcase
    test_pattern = re.compile(r'test')
    filter_result = defaultdict(list)
    maintained_suffix = {'pypi': {'source': [".py"], 'testcase':[".py", ".cc", ".c", ".cpp"]},
                        'npm': {'source': [".ts", ".js", ".mjs", ".mts"], 'testcase': [".ts", ".js", ".mjs", ".mts", ".json"]},
                        'maven': {'source':[".java"], 'testcase':[".java", ".test"]}}

    for i in tqdm(json_tmp):
        # k's format is {eco}/{vuln}/{repo}, v is a list of commits
        for k, v in i.items():
            repo = k[k.rfind('/'):]
            for ref in v:
                #  this command can get the name of changed files in the commit
                commit = ref[ref.find('/commit/')+8:]
                exitcode, file_ls = getstatusoutput(f'cd {eco}/{repo} && git diff-tree --no-commit-id --name-only -r {commit}')
                if exitcode:
                    print(f'{eco}/{repo} {commit} can not get the changed file list with error {exitcode}')
                    continue
                #  the command output is "name1\nname2\n", so we should split it firstly, and we just want to maintain the execuable files
                test_file_judge = []
                for file_name in file_ls.split('\n'):
                    suf = file_name[file_name.rfind('.'):]
                    if test_pattern.search(file_name):
                        if suf in maintained_suffix[eco]['testcase']:
                            test_file_judge.append(True)
                    else:
                        if suf in maintained_suffix[eco]['source']:
                            test_file_judge.append(False)
                # test_file_judge = [True if test_pattern.search(file_name) else False for file_name in file_ls.split('\n')]
                #  'any' return true represents there are more than 1 testcase,
                #  'not all' return true represents there are more than 1 patch
                if any(test_file_judge) and not all(test_file_judge):
                    exitcode, timestamp = getstatusoutput(f'cd {eco}/{repo} && git log -1 --format="%at" {commit}')
                    if exitcode:
                        print(f'{eco}/{repo} {commit} can not get the date info with error {exitcode}')
                        filter_result[k].append((ref, 0.))
                    # store the commit with its published date in timestamp
                    filter_result[k].append((ref, float(timestamp)))
    time_distribution = defaultdict(int)
    with open(f'{eco}_test_patch_filter_maintain.jsonl', 'w') as f:
        for k, v in filter_result.items():
            if len(v) > 1:
                #  sort the commit in ascending time order
                v = sorted(v, key=lambda x: x[1])
                f.write(json.dumps({k: [i[0] for i in v]}) + '\n')
                #  change the timestamp to date in "%Y-%M-%D" and update the distribution
                for i in v:
                    time_distribution[datetime.strftime(datetime.fromtimestamp(i[1]), "%Y-%m-%d")] += 1
    with open(f'{eco}_time_distribution_maintain.json', 'w') as f:
        json.dump(time_distribution, f)



