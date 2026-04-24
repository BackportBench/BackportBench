# BackportBench: A Multilingual Benchmark for Automated Patch Backporting
BackportBench is a multilingual benchmark that contains 202 patch backporting problems from PyPI, Maven, and npm, each with executable Docker environments and relevant test cases.

This repository includes the code we used to collect and curate the BackportBench data, as well as the evaluation pipeline. The `eval` directory also contains metadata for each BackportBench task instance.

All the Docker images we used for evaluation were uploaded to [DockerHub](https://hub.docker.com/u/backportbench). 
We recommend you to pull the image manually first, for example, `docker pull backportbench/django:220`, to avoid potential network issues during automated pulling.
## Dataset Statistics
- `label.xlsx` contains the label we created for each commit pair in the vulnerability records, indicating whether the pair represents a backport relationship and describing the extent of changes between the backported patch and the original patch.
- `high_quality_backports.jsonl` contains additional information (such as dates and SemVer tags) for 619 backports confirmed in `label.xlsx`.
- `eval/final_backportbench.jsonl` contains the data needed to perform patch backporting and evaluation for the 202 BackportBench instances.
  
**Name Convention:** The `instance_id` in `eval/final_backportbench.jsonl` follows the format `{repo_name}_{line_no}`, where `{line_no}` is the line number of that instance in `label.xlsx`. Similarly, each entry in `high_quality_backports.jsonl` is identified by the field `line_no`, which indicates the corresponding line in `label.xlsx`. 

## Setup
We suggest using virtual environment (e.g., conda) with Python 3.12 installed for the evaluation. A `requirements.txt` for necessary Python dependencies is provided.


## Run Evaluation
- Go to the `eval` folder.
- Put the patch list and corresponding patch files for the backported patches to be evaluated in the same folder.
- Specify the paths for the patch list and evaluation report.
  
Below is an example that evaluates backported patches for `django_220`, `django_232` and `socket.io-parser_71`. The data for these examples is provided in the `example_patches/` directory.
```bash
python backport_run_evaluation.py \
--mode eval \
--patch_list example_patches/patches.json \
--output_path example_patches/
```


## Dataset Collection
To facilitate future extensions for BackportBench, we released the dataset collection and curation code in `collection` directory. That code produces an Excel file listing potential backport commit pairs to be labeled, which is the source of `label.xlsx`. More details can be found in [Collection README](./collection/README.md).

