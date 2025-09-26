import pandas as pd
import json
import os


if __name__ == "__main__":
    json_list = []
    for eco in ['npm', 'pypi', 'maven']:
        file_name = f'{eco}_test_patch_filter_maintain.jsonl'
        if not os.path.exists(file_name):continue
        with open(file_name) as f:
            json_list.extend([json.loads(i) for i in f.read().strip().split('\n')])

    to_be_label_ls = []
    commit_pair_set = set()
    for i in json_list:
        for k, v in i.items():
            eco, file_name, repo = k.split('/')
            vuln_id = f"https://osv.dev/vulnerability/{file_name[:-5]}"
            for j, old_commit in enumerate(v):
                for new_commit in v[j+1:]:
                    if (old_commit, new_commit, repo, eco) in commit_pair_set:
                        continue
                    commit_pair_set.add((old_commit, new_commit, repo, eco))
                    to_be_label_ls.append([vuln_id, "", "", "", "", old_commit, new_commit, repo, eco])

    df = pd.DataFrame(to_be_label_ls, columns=['vulnerability url', 'file change', 'content change',
                                               'have backport relationship',
                                               'which commit is source',
                                               'commit1 url', 'commit2 url', 'repository', 'ecosystem'])
    with pd.ExcelWriter("to_be_labeled.xlsx") as f:
        df.to_excel(f, sheet_name="main backport", index=False)
