import os
import sys
import json
import re


# give the original data directory, remove the multiple files corresponding to the same vulnerability
def deduplicate_vuln(dir_name):
    process_data_dir = os.environ.get('Processed_data')
    original_data_dir = os.environ.get('Original_data')

    original_target_dir = os.path.join(original_data_dir, dir_name)
    processed_target_dir = os.path.join(process_data_dir, f'{dir_name}_new')
    
    if not os.path.exists(processed_target_dir):
        os.mkdir(processed_target_dir)
    map_dict = {}
    json_dict_ls = []
    for f_name in sorted(os.listdir(original_target_dir)):
        with open(os.path.join(original_target_dir, f_name), 'r') as f:
            json_file = json.load(f)

        # vuln_id_ls is a list of identifies in different sources corresponding to the same vulnerability
        vuln_id_ls = [json_file['id']]
        if 'aliases' in json_file:
            vuln_id_ls.extend(json_file['aliases'])
        references = set()
        # remove the repeated references
        if 'references' in json_file:
            references = set([i['url'] for i in json_file['references']])

        # affected package name or GIT (uniformly in lowercase)
        affected_package_name = json_file['affected'][0]['package']['name'].lower()
        git_repo = set()

        if 'ranges' in json_file['affected'][0]:
            for i in json_file['affected'][0]['ranges']:
                if i['type'] == 'GIT':
                    git_repo.add(i['repo'].lower())

        flag = False
        for vuln_id in vuln_id_ls:
            # the vulnerability has appeared before this file
            if vuln_id in map_dict:
                # just add some probable references into corresponding vulnerability
                json_dict_ls[map_dict[vuln_id]]['references'] |= references
                json_dict_ls[map_dict[vuln_id]]['git_repo'] |= git_repo
                flag = True
                break
        # otherwise add a new vulnerability and use the dictionary to memorize the position in the list
        if not flag:
            n = len(json_dict_ls)
            json_dict_ls.append({'id': json_file['id'],
                                 'references': references,
                                 'git_repo': git_repo,
                                 'affected_package_name': affected_package_name})
            tmp = {k: n for k in vuln_id_ls}
            map_dict = dict(map_dict, **tmp)

    for new_file in json_dict_ls:
        dump_json_file = {'id': new_file['id'],
                          'references': list(new_file['references']),
                          'git_repo': list(new_file['git_repo']),
                          'affected_package_name': new_file['affected_package_name']}
        with open(os.path.join(processed_target_dir, new_file['id'] + '.json'), 'w') as f:
            json.dump(dump_json_file, f)


# filter commits don't belong to affected package
def filter_commit(json_file, repo):
    # this repo only maintains the name of repository, which is not the url format
    repo_name = repo[repo.rfind('/')+1:]
    apn = json_file['affected_package_name']
    tmp_ls = []
    # for java package, we need to preprocess the package name
    if tar_dir == 'maven':
        tmp_ls = apn.split(':')
        if len(tmp_ls) == 2:
            apn = tmp_ls[1]
            if tmp_ls[0].endswith('plugins'):
                apn += '-plugin'
        else:
            apn = tmp_ls[0]
    # some package name may be git repo
    if apn.startswith('github.com'):
        return apn == repo[repo.find('github.com'):]
    # the affected package has git repository name
    # if json_file['git_repo']:
    #     return json_file['git_repo'][json_file['git_repo'].find('github.com'):] == repo[repo.find('github.com'):]
    if json_file['git_repo'] and repo[repo.find('github.com'):] in {i[i.find('github.com'):] for i in json_file['git_repo']}:
        return True
    # affected package name is a substring of repo
    if repo_name.find(apn) != -1:
        return True
    # repo is a substring of affected package name
    if apn.find(repo_name) != -1:
        return True
    # there may be some special delimiters making the judgment wrong
    repo_without_delimiter = re.sub(r'[\._-]', '', repo_name)
    apn_without_delimiter = re.sub(r'[@/\._-]', '', apn)
    if repo_without_delimiter.find(apn_without_delimiter) != -1:
        return True
    if apn_without_delimiter.find(repo_without_delimiter) != -1:
        return True

    # for maven, we can have another filter method. org.apache.santuario:xmlsec and https://github.com/apache/santuario-java,
    # package's parent is apache and the repo's parent is also apache, and they both have 'santuario'; org.openrefine:main
    # and https://github.com/openrefine/openrefine, org.springframework and https://github.com/spring-projects/spring-framework
    # take 'openrefine' and 'springframework' from package to compare with repo_name
    if tar_dir == 'maven' and len(tmp_ls) == 2:
        maven_relation = tmp_ls[0].split('.')
        if len(maven_relation) == 2:
            apn = maven_relation[1]
            # one special case
            if apn == 'postgresql' and repo == 'https://github.com/pgjdbc/pgjdbc':
                return True
        elif len(maven_relation) > 2:
            try:
                parent = maven_relation[1]
            except IndexError:
                return False
            apn = maven_relation[2]
            parent_repo = repo[:-len(repo_name)-1]
            parent_repo = parent_repo[parent_repo.rfind('/')+1:]
            if parent.find(parent_repo) != -1 or parent_repo.find(parent) != -1:
                return True
        else:
            return False
        # affected package name is a substring of repo
        if repo_name.find(apn) != -1:
            return True
        # repo is a substring of affected package name
        if apn.find(repo_name) != -1:
            return True
        apn_without_delimiter = re.sub(r'[@/\._-]', '', apn)
        if repo_without_delimiter.find(apn_without_delimiter) != -1:
            return True
        if apn_without_delimiter.find(repo_without_delimiter) != -1:
            return True
    return False


# filer references in the json file
def filter_reference(f_name):
    commit_pattern = re.compile(r'.*github\.com.*/commits?/')
    commit_pages = set()
    with open(f_name, 'r') as f:
        json_file = json.load(f)

    git_repo_set = set() if not json_file['git_repo'] else set(json_file['git_repo'])
    for ref in json_file['references']:
        result = commit_pattern.search(ref)
        # reference is a commit
        if result:
            commit_url = result.group()
            end_idx = commit_url.find("/pull/")
            if end_idx != -1:
                repo = commit_url[:end_idx].lower()  # this repo's format is github.com/xxx/xxx
                commit_prefix = repo + '/commit'  # doesn't need the '/pull/xxx'
            else:
                repo = commit_url[:-8].lower()
                commit_prefix = commit_url[:-1]
            res = commit_prefix + ref[ref.rfind('/'):]
            flag = filter_commit(json_file, repo)
            if flag:
                commit_pages.add(res)
                git_repo_set.add(repo)
            # else:
            #     print(f"file name: {json_file['id']}.json, package name: {json_file['affected_package_name']}, repo name: {repo}, commit: {res}")
    json_file['references'] = list(commit_pages)
    json_file['git_repo'] = list(git_repo_set)
    with open(f_name, 'w') as f:
        json.dump(json_file, f)


if __name__ == "__main__":
    tar_dir = sys.argv[1]
    deduplicate_vuln(tar_dir)  # get the processed json(remove duplicated vulnerability and maintain the key info)

    # filter the references and only maintain the commits to affected package
    processed_data_dir = os.path.join(os.environ.get('Processed_data'), tar_dir+'_new')
    for tmp_file in sorted(os.listdir(processed_data_dir)):
        if not tmp_file.endswith('.json'):
            continue
        file_name = os.path.join(processed_data_dir, tmp_file)
        filter_reference(file_name)

    # counting the number of commits for each repository in a vulnerability json file,
    # if the number less than 2, we will ignore the repository and don't fetch its tags
    repo_set = set()
    for tmp_file in sorted(os.listdir(processed_data_dir)):
        if not tmp_file.endswith('.json'):
            continue
        file_name = os.path.join(processed_data_dir, tmp_file)
        with open(file_name, 'r') as fp:
            json_file = json.load(fp)
        if len(json_file['references']) < 2:
            continue
        for repository in json_file['git_repo']:
            # if the prefix of commit is equal to repository, we think it should belong to this repository.
            num = len([ref for ref in json_file['references'] if ref[:ref.find('/commit/')] == repository])
            # add repository only if the number of commits belong to it is greater than 1
            if num > 1:
                repo_set.add(repository)
    with open(os.path.join(processed_data_dir, f'repos_{tar_dir}.txt'), 'w') as fp:
        for i in repo_set:
            fp.write(i+'\n')
