# Dataset Construction Pipeline

1. From [OSV Data Dump](https://google.github.io/osv.dev/data/) get the original dataset. Here is an example for downloading pypi. We unzip all osv records (i.e., json files) of each ecosystem to a folder called `osv_records/{ecosystem}`. Here {ecosystem} can be pypi, maven, or npm.
    
    
2. Create and configure processed_data folders:
```
mkdir -p processed_records/maven
mkdir -p processed_records/pypi
mkdir -p processed_records/npm
# original is the above absolute path of the cp source(the unzip path)
export Original_data=${original}
# processed is the above absolute path of the cp destination
export Processed_data=${processed}
```

3. Run the `deduplicate.py {eco}`, where ${eco} means the ecosystem that you want to process(like pypi, npm or maven)
4. Create `git_repos_dir` by `mkdir -p git_repos_dir/maven git_repos_dir/pypi git_repos_dir/npm` and Run the `get_git_repo_clones.py` to get the git repositories
5. Run the `tag_backpropagation.py {eco}`, ${eco} is the same as (3) step. This step is to obtain each repo's tag list and give the commit a semver tag (the source of semver regular pattern is [semver pattern](https://github.com/semver/semver/blob/master/semver.md))
6. Run the `commit_filter.py {eco}` to obtain all potential datapoints
7. Run the `patch_test_filter.py {eco}` to obtain the final datapoints to be labeled
8. Run the `generate_label_excel.py` to get the excel table, and label the commit pair manually
