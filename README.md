# BackportBench: A Multilingual Benchmark for Automated Patch Backporting
BackportBench is a multilingual benchmark that contains 202 patch backporting problems from PyPI, Maven, and npm, each with executable Docker environments and relevant test cases.

This repository includes the code we used to collect the initial data of BackportBench and the evaluation pipeline.

All the Docker images we used for evaluation were uploaded to [DockerHub](https://hub.docker.com/u/backportbench). 
We recommend you to pull the image manually first, e.g., `docker pull backportbench/django:220`, to avoid potential network issues during automated pulling.

## Setup
We suggest using virtual environment with Python 3.12 installed for the evaluation. A `requirements.txt` for necessary Python dependencies is provided.


## Run Evaluation
- Go to the `eval` folder.
- Put the list and corresponding patch files of backported patches to be evaluated in the same folder.
- Specify the path for the patch list and evaluation report.
Below is an example for evaluating backported patches for `django_220`, `django_232` and `socket.io-parser_71`.

`python backport_run_evaluation.py --mode eval  --patch_list example_patches/patches.json --output_path example_patches/`


## Dataset Collection
To facilitate future extension for BackportBench, we released code for dataset collection in `collection`. More details can be found in [Collection README](./collection/README.md).

