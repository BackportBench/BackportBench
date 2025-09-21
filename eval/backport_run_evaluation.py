import docker
from docker.errors import ImageNotFound, APIError
from backport_log_parsers.log_parser import LogParser, PASS_STATUS_ls, FAIL_STATUS_ls
import re
import os
import json
from tqdm import tqdm
import time
import tarfile
from pathlib import Path, PurePosixPath
import argparse
from concurrent.futures import ThreadPoolExecutor



def copy_to_container(container, src: Path, dst: Path):
    """
    Copy a file from local to a docker container

    Args:
        container (Container): Docker container to copy to
        src (Path): Source file path
        dst (Path): Destination file path in the container
    """
    # Check if destination path is valid
    if os.path.dirname(dst) == "":
        raise ValueError(
            f"Destination path parent directory cannot be empty!, dst: {dst}"
        )

    # temporary tar file
    tar_path = src.with_suffix(".tar")
    with tarfile.open(tar_path, "w") as tar:
        tar.add(
            src, arcname=dst.name
        )  # use destination name, so after `put_archive`, name is correct

    # get bytes for put_archive cmd
    with open(tar_path, "rb") as tar_file:
        data = tar_file.read()

    # Make directory if necessary
    container.exec_run(f"mkdir -p {dst.parent}")

    # Send tar file to container and extract
    container.put_archive(os.path.dirname(dst), data)

    # clean up in locally and in container
    tar_path.unlink()



def prepare_image(client, img_name, max_retries=3, retry_delay=5):
    try:
        # Check if the image exists locally
        image = client.images.get(img_name)
        print(f"Image '{img_name}' found locally.")
        return image
    except ImageNotFound:
        print(f"Image '{img_name}' not found locally. Attempting to pull...\nWe strongly recommend you to pull the image manually first, e.g., 'docker pull {img_name}', to avoid potential network issues during automated pulling.")
        retry_count = 0
        while retry_count < max_retries:
            try:
                # Attempt to pull the image
                client.images.pull(img_name)
                print(f"Successfully pulled image '{img_name}'.")
                # Get the pulled image
                image = client.images.get(img_name)
                return image
            except APIError as e:
                retry_count += 1
                print(f"Pull attempt {retry_count} failed: {e}")
                if retry_count >= max_retries:
                    print(f"Maximum retries ({max_retries}) exceeded. Failed to pull image '{img_name}'.")
                    raise
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        # Handle other exceptions if needed


def preprocess_patch(preds_file_name, patch_file_name):
    diff_pattern = re.compile(r'(?:^|\n)(diff --git .*?(?=(?:\ndiff --git)|$))', re.DOTALL)
    with open(preds_file_name) as f:
        content = f.read()

    gold_patch = []
    for m in re.finditer(diff_pattern, content):
        match_item = m.group(1)
        lines = match_item.split('\n')
        if lines[0].find('test') == -1:
            gold_patch.append(match_item)
    with open(patch_file_name, 'w') as f:
        for i in gold_patch:
            f.write(i + '\n')
    return gold_patch != []

def load_and_run_tar_image(instance, client, args):
    container = None
    image = None
    instance_id = instance['instance_id']
    FAIL_TO_PASS = []
    PASS_TO_PASS = []
    tot_summary = {
        'before_fail': 0,
        'before_pass': 0,
        'after_fail': 0,
        'after_pass': 0
    }
    try:

        repo = instance['repo']

        # if instance['repo'] in ['quarkus', 'xwiki-platform', 'vite', 'wagtail']:
        img_id = f'backportbench/{"_".join(instance_id.split("_")[:-1])}:{instance_id.split("_")[-1]}'
        image = prepare_image(client, img_id)
        if image == None:
            raise ValueError(f"Image {img_id} is not found")

        # run the container
        time.sleep(5)
        env_var = ["JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64"] if instance['repo'] == 'quarkus' or instance_id in ['xwiki-platform_1415', 'xwiki-platform_1527'] else []

        name_str = f"{instance_id}_{args.output_path.rstrip('/').split('/')[-1]}"
        print(f"launching container: {name_str}")
        container = client.containers.run(
            image.id,
            # instance_id,
            command="tail -f /dev/null",  # keep container running
            detach=True,
            tty=True,
            remove=True,
            name=name_str,
            working_dir=f'/{repo}',
            environment=env_var
        )
        print(f"Container Launched Successfully - Name: {container.name}")
        if instance['ecosystem']=='pypi':
            container.exec_run(
                "conda activate testbed"
            )
        if instance['repo']=='quarkus' or instance_id in ['xwiki-platform_1415', 'xwiki-platform_1527']:
            container.exec_run(
                'export PATH=$JAVA_HOME/bin:$PATH'
            )
        time.sleep(2)
        container.exec_run(
            "/bin/bash /check/before_apply.sh"
        )
        log_pattern = re.compile(r'(run_.*)_before.log')
        output = container.exec_run(
            "ls",
            stream=False
        ).output.decode('utf-8').strip()
        all_log_prefix = log_pattern.findall(output)

        # parsing log
        log_parser = LogParser(repo)
        pattern = None
        if instance_id in ['django_416', 'django_414', 'django_305', 'django_409', 'django_382', 'django_421', 
                           'django_422', 'django_275', 'django_277', 'django_330', 'django_193', 'django_430',
                           'django_528', 'django_214', 'django_215']:
            if instance_id in ['django_421', 'django_422']:
                pattern = re.compile(r'(?:^|\. )(test\w*)\s*(?:\(([^)]+?)\))?\s*?.*(?:\.\.\.)?\s*(ok$|FAIL|ERROR$|skipped|expected fail)', re.I | re.M)
            elif instance_id == 'django_382':
                pattern = re.compile(r'(.*?)\s*(?:\(([^)]+?)\))?.*?\.\.\.\s*?(ok|FAIL|skipped|ERROR|expected fail)', re.I | re.S)
            elif instance_id in ['django_330', 'django_414', 'django_416']:
                pattern = re.compile(r'(test\w*)\s+\(([^)]+?)\).*?\.\.\.\s*(ok|FAIL|ERROR|skipped)?', re.I | re.S)
            elif instance_id == 'django_409':
                pattern = re.compile(r'(?:^|\.)(test\w*)\s*(?:\(([^)]+?)\))?\s*?.*(?:\.\.\.)?\s*(ok$|FAIL|ERROR$|skipped)', re.I | re.M)
            elif instance_id == 'django_277':
                pattern = re.compile(r'(?:^|\. )(test\w*)\s+\(([^)]+?)\)\s*?[^.]*?\.\.\.\s*(ok$|FAIL|ERROR$|skipped|expected fail)', re.I | re.M)
            else:
                pattern = re.compile(r'^(test\w*)\s*(?:\(([^)]+?)\))?\s*?.*(?:\.\.\.)?\s*(ok$|FAIL|ERROR$|skipped|expected fail)', re.I | re.M)
        before_testcase_fail_set = set()
        before_testcase_pass_set = set()
        before_fail_tot = 0
        before_pass_tot = 0
        for n in all_log_prefix:
            log_text = container.exec_run(
                f"cat {n}_before.log",
                stream=False
            ).output.decode('utf-8').strip()
            # special case
            if pattern:
                # print(pattern)
                before_result, before_summary = log_parser.parse_test_logs(log_text, pattern)              
            else:
                before_result, before_summary = log_parser.parse_test_logs(log_text)
            before_testcase_fail_set |= set([i['id'] for i in before_result if i['status'] in FAIL_STATUS_ls])
            before_testcase_pass_set |= set([i['id'] for i in before_result if i['status'] in PASS_STATUS_ls])
            before_fail_tot += before_summary['fail']
            before_pass_tot += before_summary['pass']
        # Use gold patch
        print(f"{name_str}: Testing backported patch...")
        
        if args.mode == 'groundtruth':
            container.exec_run(
                "git apply /check/gold_patch.diff"
            )
        else:
            patch_dir = "/".join(args.patch_list.split("/")[:-1])
            preds_file_name = Path(f'{patch_dir}/{instance_id}.patch')
            
            if not os.path.exists(preds_file_name):
                print(f"patch file of {instance_id} is not found")
                if container:
                    container.stop(timeout=5)                            
                return "empty patch"
            patch_file_name = f"{patch_dir}/{args.mode}_{instance_id}.patch"
            if not preprocess_patch(preds_file_name, patch_file_name):
                print(f"{instance_id} has empty patch")
                if container:
                    container.stop(timeout=5)                            
                return "empty patch"
            patch_file = Path(patch_file_name)
            copy_to_container(container, patch_file, PurePosixPath(f"/check/{patch_file_name}"))
            exit_code, output = container.exec_run(                             
                f'git apply /check/{patch_file_name}'
            )
            if exit_code:
                print(f"{instance_id} apply fail\n{output.decode('utf-8')}")
                if container:
                    container.stop(timeout=5)
                return "apply fail"
            
        container.exec_run(
            "/bin/bash /check/after_apply.sh"
        )
        after_fail_tot = 0
        after_pass_tot = 0
        after_testcase_fail_set = set()
        after_testcase_pass_set = set()
        for n in all_log_prefix:
            log_text = container.exec_run(
                f"cat {n}_after.log",
                stream=False
            ).output.decode('utf-8').strip()
            if pattern:
                after_result, after_summary = log_parser.parse_test_logs(log_text, pattern)
            else:
                after_result, after_summary = log_parser.parse_test_logs(log_text)
            after_testcase_fail_set |= set([i['id'] for i in after_result if i['status'] in FAIL_STATUS_ls])
            after_testcase_pass_set |= set([i['id'] for i in after_result if i['status'] in PASS_STATUS_ls])
            after_fail_tot += after_summary['fail']
            after_pass_tot += after_summary['pass']

        # parsing fail to pass      
        FAIL_TO_PASS = list(before_testcase_fail_set - after_testcase_fail_set)
        PASS_TO_PASS = list(after_testcase_pass_set & before_testcase_pass_set)
        tot_summary = {'before_fail': before_fail_tot,
                       'before_pass': before_pass_tot,
                       'after_fail': after_fail_tot,
                       'after_pass': after_pass_tot}
        print(f"{name_str}: Backported patch validated")

    except Exception as e:
        print(f"{instance_id} unknown error occurrs during loading and evaluating: {str(e)}")
    try:
        if container:
            container.stop(timeout=5)
    except:
        pass
    # if instance['repo'] not in ['quarkus', 'xwiki-platform', 'vite', 'wagtail']:
    #     client.images.remove(image=image.id, force=True)
    return FAIL_TO_PASS, PASS_TO_PASS, tot_summary

if __name__ == "__main__":
    with open('final_backportbench.jsonl') as f:
        c = [json.loads(i) for i in f.read().strip().split('\n')]

    # Create a Docker client
    client = docker.from_env()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--patch_list",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--output_path",
        type=str,
        required=True,
    )

    # mode parameter is a option from ['groundtruth', 'eval'], by default is "eval", and is required.
    parser.add_argument(
        "--mode",
        choices=['groundtruth', "eval"],
        default="eval",
        type=str,
        required=True,
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=10,
    )
    
    args = parser.parse_args()
    with open(args.patch_list) as f:
        patch_info = json.load(f)

    to_eval = [i for i in c if i["instance_id"] in patch_info]
    os.makedirs(args.output_path, exist_ok=True)
    empty_num = 0
    apply_fail_num = 0
    only_f2p_fail = []
    both_fail = []
    only_p2p_fail = []
    backport_success = []
    tot_test_case = 0
    max_test_case = 0
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                load_and_run_tar_image, i, client, args
            ): i
            for i in to_eval
        }
        for future in tqdm(futures, total=len(to_eval), colour="MAGENTA"):
            try:
                res = future.result(timeout=600)
            except TimeoutError:
                ins_id = futures[future]['instance_id']
                if args.model and args.eco:
                    container_name = f"{ins_id}_{args.output_path.rstrip('/').split('/')[-1]}"
                print(f'{ins_id} timeout')
                apply_fail_num += 1
                try:
                    ct = client.containers.get(container_name)
                    ct.stop(timeout=5)
                except:
                    pass
                continue
            if res == 'apply fail':apply_fail_num += 1
            elif res == 'empty patch':empty_num += 1
            else:
                i = futures[future]
                F2P, P2P, ts = res
                instance_case = ts["after_fail"]+ts["after_pass"]
                tot_test_case += instance_case
                max_test_case = max(max_test_case, instance_case)
                diff_f2p = set(i['FAIL TO PASS']) - set(F2P)
                diff_p2p = set(i['PASS TO PASS']) - set(P2P)
                if not diff_f2p and not diff_p2p:
                    print(f'{i["instance_id"]} has been successfully backported')
                    print(f'{i["instance_id"]} includes {ts["after_fail"]+ts["after_pass"]} test cases')
                    backport_success.append(i['instance_id'])
                else:
                    print(f'{i["instance_id"]} has F2P {diff_f2p} not solved, and has P2P {diff_p2p} failed')
                    if diff_f2p and diff_p2p:both_fail.append(i['instance_id'])
                    elif diff_f2p and not diff_p2p:only_f2p_fail.append(i['instance_id'])
                    else:only_p2p_fail.append(i['instance_id'])

    report = {
        'backport_success': backport_success,
        'only_p2p_fail': only_p2p_fail,
        'only_f2p_fail': only_f2p_fail,
        'both_fail': both_fail,
        'empty_num': empty_num,
        'apply_fail_num': apply_fail_num,
    }

    print(f'backport success: {backport_success}')
    print(f'only p2p fail: {only_p2p_fail}')
    print(f'only f2p fail: {only_f2p_fail}')
    print(f'both fail: {both_fail}')
    print(f'empty patch number = {empty_num}')
    print(f'apply failed number = {apply_fail_num}')
    with open(os.path.join(args.output_path, "report.json"), 'w') as f:
        json.dump(report, f, indent=4)
    # print(f'{args.eco} has average testcase={tot_test_case/len(c)}, max testcase={max_test_case}')
    if args.mode == "eval":
        os.system(f'rm {"/".join(args.patch_list.split("/")[:-1])}/{args.mode}_*.patch')
