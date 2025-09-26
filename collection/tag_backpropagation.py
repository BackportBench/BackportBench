import sys
from subprocess import getstatusoutput
import os
from tqdm import tqdm
import re
import json


if __name__ == "__main__":
    eco = sys.argv[1]
    tag_pattern = re.compile(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$')
    commit_pattern = re.compile(r'[\da-z]{40}')
    for repo in os.listdir(eco):
        commit_set = set()
        tagged_commit_dict = {}  # key is commit and value is tag
        #  get tag list
        exitcode, output = getstatusoutput(f'cd {eco}/{repo} && git tag')
        if exitcode:
            print(f"{eco}/{repo} can't show the tag_list")
            continue
        tag_list = [i for i in output.split('\n') if i]
        with open(f'{eco}/{repo}/tags_list.txt', 'w') as f:
            for tag in tag_list:
                f.write(tag + '\n')

        for tag in tag_list:
            #  get the commits tagged by the corresponding tag
            if not tag_pattern.search(tag):
                continue
            exitcode, output = getstatusoutput(f'cd {eco}/{repo} && git rev-parse {tag}' + '^{commit}')
            if exitcode:
                print(f"in {eco}/{repo} {tag} can't show the commit")
                continue
            for c in output.split('\n'):
                if commit_pattern.match(c):
                    if c not in commit_set:
                        commit_set.add(c)
                        tagged_commit_dict[c] = set()
                    tagged_commit_dict[c].add(tag)

        for commit in tqdm(commit_set):
            commit_ls = [commit]
            #  use bfs to back_propagate the tag to all the ancestors
            while commit_ls:
                #  get the parent of the commit and back_propagate the tag to the parent
                exitcode, parents = getstatusoutput(f'cd {eco}/{repo} && git rev-parse {commit_ls[0]}^@')
                if exitcode:
                    print(f"in {eco}/{repo} {commit_ls[0]} can't get the parents")
                    print(f"error code {exitcode}")
                    commit_ls.pop(0)
                    continue

                if not parents:
                    commit_ls.pop(0)
                    continue
                for parent in parents.split('\n'):
                    if not commit_pattern.match(parent):
                        continue
                    if parent not in tagged_commit_dict:
                        commit_ls.append(parent)
                        tagged_commit_dict[parent] = set()
                    tagged_commit_dict[parent] |= tagged_commit_dict[commit_ls[0]]
                commit_ls.pop(0)

        with open(f'{eco}/{repo}/tagged_commit_new.json', 'w') as f:
            json.dump({k: list(v) for k, v in tagged_commit_dict.items()}, f)
        print(f'finish {eco}/{repo}')

