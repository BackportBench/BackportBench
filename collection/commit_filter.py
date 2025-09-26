import os
import sys
import re
import json
from collections import defaultdict


if __name__ == "__main__":
    eco = sys.argv[1]
    tag_pattern = re.compile(r'([1-9][0-9]*!)?(0|[1-9][0-9]*)(\.(0|[1-9][0-9]*))*((a|b|rc)(0|[1-9][0-9]*))?(\.post(0|[1-9][0-9]*))?(\.dev(0|[1-9][0-9]*))?')
    processed_data_dir = os.path.join(os.environ.get('Processed_data'), f'{eco}_new')
    filter_method = 'tag'
    debug_dict_ls = []
    filter_result = defaultdict(set)
    fault_repo_set = set()
    total_count = 0
    for tmp_file in sorted(os.listdir(processed_data_dir)):
        if not tmp_file.endswith('.json'):
            continue
        file_name = os.path.join(processed_data_dir, tmp_file)
        with open(file_name, 'r') as fp:
            json_file_tmp = json.load(fp)
        if len(json_file_tmp['references']) < 2:
            continue
        repo_commit_dict = {}
        for repository in json_file_tmp['git_repo']:
            # if the prefix of commit is equal to repository, we think it should belong to this repository.
            commit_ls = [ref for ref in json_file_tmp['references'] if ref[:ref.find('/commit/')] == repository]
            # add repository only if the number of commits belong to it is greater than 1
            if len(commit_ls) > 1:
                repo_commit_dict[repository[repository.rfind('/')+1:]] = commit_ls
        total_count += min(1, len(repo_commit_dict))
        for repo, commits in repo_commit_dict.items():
            flag = False
            if not os.path.exists(f'{eco}/{repo}'):
                print(f'{eco}/{repo} not exist')
                continue
            #logger.info(f'{eco}/{repo} starts')
            if filter_method == 'tag':
                with open(f'{eco}/{repo}/tagged_commit_new.json') as f:
                    tagged_commit = json.load(f)
                for ref in commits:
                    commit = ref[ref.find('/commit/')+8:]
                    if len(commit) > 40:
                        commit = commit[:40]  # truncate the commit

                    def filter_by_tag():
                        #global print_num
                        for tc in tagged_commit:
                            if tc.startswith(commit):
                                for tag in tagged_commit[tc]:
                                    if tag_pattern.search(tag):
                                        filter_result[f'{eco}/{tmp_file}/{repo}'].add(f'{ref[:ref.find("/commit/")+8]}{tc}')
                                        return 0
                                debug_dict_ls.append({'file name': f'{eco}/{tmp_file}', 'commit': f'{ref}', 'tags': f'{tagged_commit[tc]}', 'error': 'does not have semver tag'})
                                fault_repo_set.add(repo)
                                #if print_num < 10:
                                #    print(f'{repo}/{commit} {tagged_commit[tc]}')
                                #    print_num += 1
                                return 1
                        return 2
                    
                    if filter_by_tag() == 2:
                        fault_repo_set.add(repo)
                        debug_dict_ls.append({'file name': f'{eco}/{tmp_file}', 'commit': f'{ref}', 'error': 'does not find this commit in tagged commits'})
                if len(filter_result[f'{eco}/{tmp_file}/{repo}']) > 1:
                    break
    #print(fault_repo_set)
    print(total_count)
    potential_datapoints = {k: list(v) for k, v in filter_result.items() if len(v) > 1}
    filter_result = {k: list(v) for k, v in filter_result.items() if len(v) < 2}
    with open(f'{eco}_filter_commit_with_semvertag_without_pair_one_repo_for_vuln.json', 'w') as f:
        json.dump(filter_result, f)
        print(f'{len(filter_result)}')
    with open(f'{eco}_potential_datapoints_one_repo_for_vuln.jsonl', 'w') as f:
        print(f'{len(potential_datapoints)}')
        for k, v in potential_datapoints.items():
           f.write(json.dumps({k: v}) + '\n')
    with open(f'{eco}_filter_debug_by_{filter_method}_one_repo_for_vuln.jsonl', 'w') as f:
        print(f'{len(debug_dict_ls)}')
        for i in debug_dict_ls:
           f.write(json.dumps(i) + '\n')

