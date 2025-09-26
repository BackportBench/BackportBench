# Dataset Construction Pipeline

1. Download [OSV Data Dump](https://google.github.io/osv.dev/data/) as original dataset for further curation. As an example, we use the Maven data dump from 2024-08-27 in `all.zip`. Unzip the data dumps and extract their vulnerabilities (in JSON files) for each ecosystem into a newly created folder named `osv_records/{eco}`, where {eco} can be `pypi`, `maven`, or `npm`. Remember to remove the zip files from the `osv_records/{eco}` after the records are extracted.

2. Create and configure data folders to be processed:
    ```
    mkdir -p processed_records
    export Original_data=<absolute path to osv_records/>
    export Processed_data=<absolute path to processed_records/>
    ```

3. Run `python get_commit_ref_for_vuln.py {eco}`. This step deduplicates vulnerabilities, finds commits in references that are relevant to the affected repositories, and filters out vulnerabilities that have fewer than two relevant commits.
4. Run `python get_git_repo_clones.py` to clone all GitHub repositories referenced by the vulnerabilities. Since cloning all repositories can take a long time, you can manually clone an example repository in the expected output path (i.e., `collection/{eco}/`) and proceed to the next step. For example, `cd maven && git clone https://github.com/apache/cxf.git`
5. Run `python tag_backpropagation.py {eco}`. This step retrieves each repository's commit tags and parse any available SemVer information. We use the regular expression pattern from [SemVer Source Code](https://github.com/semver/semver/blob/master/semver.md).
6. Run `python commit_filter.py {eco}` to keep only commits that are included in SemVer tags.
7. Run `python patch_test_filter.py {eco}` to further filter commits to those that modify both test files and non-test files.
8. Run `python generate_label_excel.py`. his produces an Excel file containing combinations of the filtered commits. Use this Excel file to label commit pairs for backport relationships and to assign their categories.
