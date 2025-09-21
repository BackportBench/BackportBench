import os
import sys
import json
import re
from tqdm import tqdm

# given the original data directory, remove the multiple files corresponding to the same vulnerability
def deduplicate_vuln(dir_name):
    # new_dir = f'{dir_name}'
    ori_dir_name = os.path.join(os.environ.get('Original_data'), dir_name)
    target_dir_name = os.path.join(os.environ.get('Processed_data'), dir_name)
    map_dict = {}
    json_dict_ls = []
    for file_name in tqdm(os.listdir(ori_dir_name)):
        with open(os.path.join(ori_dir_name, file_name), 'r') as f:
            json_file = json.load(f)

        # vuln_id_ls is a list of identifies in different sources corresponding to the same vulnerability
        vuln_id_ls = [json_file['id']]
        if 'aliases' in json_file:
            vuln_id_ls.extend(json_file['aliases'])
        references = set()
        # remove the repeated references
        if 'references' in json_file:
            try:
                if isinstance(json_file['references'], dict) and 'url' in json_file['references']:
                        # references = set(json_file['references']['url'])
                    references = set([i for i in json_file['references']['url']])
                elif isinstance(json_file['references'], list):
                    if isinstance(json_file['references'][0], dict):
                        references = set([i['url'] for i in json_file['references']])
                    elif isinstance(json_file['references'][0], str):
                        references = set([i for i in json_file['references']])
                    else:
                        raise ValueError("Unknown references format")
                else:
                    raise ValueError("Unknown references format")
            except Exception as e:
                print(f"Error processing file {file_name}: {e}, instance_type: {type(json_file['references'])}")
                continue
                

        flag = False
        for vuln_id in vuln_id_ls:
            # the vulnerability has appeared before this file
            if vuln_id in map_dict:
                # just add some probable references into corresponding vulnerability
                json_dict_ls[map_dict[vuln_id]]['references'] |= references
                flag = True
                break
        # otherwise add a new vulnerability and use the dictionary to memorize the position in the list
        if not flag:
            n = len(json_dict_ls)
            json_dict_ls.append({'id': json_file['id'],
                                 'references': references})
            tmp = {k: n for k in vuln_id_ls}
            map_dict = dict(map_dict, **tmp)

    for new_file in json_dict_ls:
        dump_json_file = {'id': new_file['id'],
                          'references': list(new_file['references'])}
        with open(os.path.join(target_dir_name, new_file['id']+'.json'), 'w') as f:
            json.dump(dump_json_file, f)


# given the processed data directory, get the commits and repositories appear in the references
def get_unique_commit(target_dir):
    dir_name = os.path.join(os.environ.get('Processed_data'), f"{target_dir}")
    commit_pages = set()
    repo_set = set()
    commit_pattern = re.compile(r'.*github\.com.*commit/')
    for file_name in os.listdir(dir_name):
        if not file_name.endswith('.json'):
            continue
        with open(os.path.join(dir_name, file_name), 'r') as f:
            json_file = json.load(f)
        for ref in json_file['references']:
            result = commit_pattern.search(ref)
            # reference is a commit
            if result:
                end_idx = result.group().find("pull")
                if end_idx != -1:
                    repo = result.group()[:end_idx-1]
                    repo_set.add(repo)  # is a pull request, only need repository
                    commit_pages.add(repo + '/commit'+ ref[ref.rfind('/'):]) # doesn't need the '/pull/xxx'
                else:
                    repo_set.add(result.group()[:-7])
                    commit_pages.add(ref)

    with open(os.path.join(dir_name, f'commits_{target_dir}.txt'), 'w') as f:
        for commit in commit_pages:
            f.write(commit+'\n')
    with open(os.path.join(dir_name, f'repos_{target_dir}.txt'), 'w') as f:
        for repo in repo_set:
            f.write(repo+'\n')


if __name__ == "__main__":
    eco = sys.argv[1]
    deduplicate_vuln(eco)
    get_unique_commit(eco)
