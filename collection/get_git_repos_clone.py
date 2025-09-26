import os
import json


if __name__ == "__main__":
    processed_data = os.environ.get("Processed_data")
    ecosystem = ['pypi', 'npm', 'maven']
    for eco in ecosystem:
        processed_data_dir = os.path.join(processed_data, f'{eco}_new')
        if not os.path.exists(processed_data_dir):continue
        if not os.path.exists(eco):
            os.mkdir(eco)
        repos_set = set()
        for tmp_file in os.listdir(processed_data_dir):
            if not tmp_file.endswith('.json'):
                continue
            file_name = os.path.join(processed_data_dir, tmp_file)
            with open(file_name, 'r') as fp:
                json_file_tmp = json.load(fp)
            if len(json_file_tmp['references']) < 2:
                continue
            for repository in json_file_tmp['git_repo']:
                # if the prefix of commit is equal to repository, we think it should belong to this repository.
                repo_commits = [ref for ref in json_file_tmp['references'] if ref[:ref.find('/commit/')].lower() == repository]
                # add repository only if the number of commits belong to it is greater than 1
                if len(repo_commits) > 1:
                    repos_set.add(repo_commits[0][:repo_commits[0].find('/commit/')])
        for repo in repos_set:
            ret_code = os.system(f"cd {eco} && git clone {repo}.git")
            if ret_code == 0 or ret_code == 32768:
                print(f'{repo} clone successfully')
            else:
                print(f'{repo} fail to be cloned')
