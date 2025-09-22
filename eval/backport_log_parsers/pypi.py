import re


def log_parser_nova(log_text):
    """
    Parse test logs to extract test case details and overall statistics.

    Args:
       log_text (str): Multi-line test log text.

    Returns:
       list[dict]: A list of dictionaries with the following structure:
           [{
               "id": str,   # Test path
               "status": str       # Result status
            }]
           """
    lines = log_text.strip().split('\n')
    results = []

    # Regular expression pattern (matches e.g., {6} path.to.test [0.123s] ... ok)
    pattern = re.compile(
        r'\{\d+}'  # Group ID {number}
        r'\s*([\w\.]+)'  # Test path (letters/numbers/dots)
        r'[\s\[\]\d\w\.]*\.\.\.\s*(\w+)'  # Result status
    )

    for line in lines:
        match = pattern.search(line)
        if match:
            test_path = match.group(1)
            status = match.group(2).lower()

            results.append({
                "id": test_path,
                "status": status
            })
    tot_num = len(results)
    err_num = len([i for i in results if i['status'] in ['Fail', 'Error']])
    skip_num = len([i for i in results if i['status']=='skipped'])
    summary = {'total': tot_num, 'pass': tot_num-err_num-skip_num, 'fail':err_num, 'skip':skip_num}
    return results, summary


def log_parser_keystone(log_text):
    """
    Parse Keystone unit test logs to extract test case details and overall statistics.
    If there are returns before applying the patch but none after, default to F2P (Fail to Pass),
    as some logs do not return names of passed test cases.

    Args:
        log_text (str): Multi-line test log text.

    Returns:
        list[dict]: A list of dictionaries with the following structure:
            [{
                "id": str,   # Test path (dot-separated format)
                "status": str,      # Result status (lowercase)
            }]
    """
    lines = [line.strip() for line in log_text.split('\n') if line.strip()]
    results = []

    # Regular expression pattern (matches e.g., package.module.ClassName.test_method ... status)
    pattern = re.compile(
        r'^([\w\._\d]+)\s*\.\.\.\s*(\w+)$'
    )
    fail_pattern = re.compile(r'^FAIL:\s*([\w\._\d]+)')

    for line in lines:
        match = pattern.match(line)
        if match:
            test_path = match.group(1)
            status = match.group(2).lower()
            results.append({
                "id": test_path,
                "status": status,
            })
    if not results:
        ok_flag = False
        k = min(5, len(lines))
        for line in lines[-k:]:
            if line.find('OK') != -1:
                ok_flag = True
                break
        if not ok_flag:
            for line in lines:
                match = fail_pattern.match(line)
                if match:
                    test_path = match.group(1)
                    results.append({
                        "id": test_path,
                        "status": 'fail',
                    })
    tot_num = len(results)
    err_num = len([i for i in results if i['status'] in ['fail', 'error']])
    skip_num = len([i for i in results if i['status']=='skipped'])
    summary = {'total': tot_num, 'pass': tot_num-err_num-skip_num, 'fail':err_num, 'skip':skip_num}
    return results, summary


def log_parser_django(log_text, pattern=None):
    """
    Parse Django unit test logs to extract test case details and overall statistics.
    If there are returns before applying the patch but none after, default to F2P (Fail to Pass),
    as some logs do not return names of passed test cases.

    Args:
        log_text (str): Multi-line test log text.

    Returns:
        list[dict]: A list of dictionaries with the following structure:
            [{
                "id": str,   # Test path (dot-separated format)
                "status": str,      # Result status (lowercase)
            }]
        dict: Summary information
    """
    if not pattern:
        pattern = re.compile(r'^(.*?)\s*(?:\(([^)]+?)\))?\s*?(?:\.\.\.)?\s*?(ok|FAIL|skipped|ERROR|expected fail)$', re.M | re.I)
    lines = [line.strip() for line in log_text.split('\n') if line.strip()]
    results = []
    # Check if the number of test cases matches the final total
    id_set = set()
    # Process logs in different formats
    for m in pattern.finditer(log_text):
        case_name = m.group(1)
        if re.match(r'Ran \d+ tests', case_name):
            continue
        if m.group().strip().startswith('File '):continue
        test_class_name = m.group(2) if m.group(2) else ''
        status = m.group(3)
        if not status:continue
        id_name = test_class_name+'.'+case_name if test_class_name else case_name
        if id_name in id_set:continue
        # When a test case expected to fail actually runs with an error, it should be considered as ok
        if status and status.find('expected fail')!=-1:status='ok'
        results.append({'id': id_name,
                        'status': status})
        id_set.add(id_name)
        
    ok_flag = False
    k = min(5, len(lines))
    for line in lines[-k:]:
        if line.find('OK') != -1:
            ok_flag = True
            break
    err_num = re.findall(r'FAILED \((?:failures|errors)=(\d+)', log_text)
    if err_num:ok_flag=False
    # Besides the first format of errors, there are specific failure patterns
    fail_pattern = re.compile(r'(?:ERROR|FAIL):\s*(\w+)\s*\((.*?)\)')
    if not ok_flag:
        for match in fail_pattern.finditer(log_text):
            case_name = match.group(1)
            test_class_name = match.group(2)
            id_name = test_class_name+'.'+case_name
            if id_name in id_set:continue
            results.append({
                "id": id_name,
                "status": 'fail',
            })
            id_set.add(id_name)
    tot_num = re.search(r'Ran (\d+) tests?', log_text)
    tot_cnt = 0 if not tot_num else int(tot_num.group(1))
    if tot_cnt < len(id_set):
        tot_cnt = len(id_set)
    skip_num = re.search(r'FAILED.*?(?<=skipped)=(\d+)', log_text)
    err_cnt = 0 if not err_num else sum([int(i) for i in err_num])
    skip_cnt = 0 if not skip_num else int(skip_num.group(1))
    summary = {'total': tot_cnt, 'pass': tot_cnt-err_cnt-skip_cnt, 'fail':err_cnt, 'skip':skip_cnt}
    return results, summary

def log_parser_glance(log_text):
    # Similar to the Django format but with slight differences in test case paths; reusable with minor adjustments.
    err_cnt, pass_cnt, skip_cnt = 0, 0, 0
    pattern = re.compile(r'([\w.]+?)\s*\.\.\.\s*(ok|FAIL|skipped|ERROR)', re.S)
    lines = [line.strip() for line in log_text.split('\n') if line.strip()]
    results = []
    # Process logs in different formats
    for m in pattern.finditer(log_text):
        case_name = m.group(1)
        status = m.group(2)
        results.append({'id': case_name,
                        'status': status})
        if status == 'ok':
            pass_cnt += 1
        elif status == 'skipped':
            skip_cnt += 1
        else:
            err_cnt += 1
        
    if not results:
        ok_flag = False
        k = min(5, len(lines))
        for line in lines[-k:]:
            if line.find('OK') != -1:
                ok_flag = True
                break
        fail_pattern = re.compile(r'^(?:ERROR|FAIL):\s*(\w+)\s*\((.*)\)')
        if not ok_flag:
            for line in lines:
                match = fail_pattern.match(line)
                if match:
                    case_name = match.group(1)
                    test_class_name = match.group(2)
                    results.append({
                        "id": test_class_name+'.'+case_name,
                        "status": 'fail',
                    })
                    err_cnt += 1
    tot_num = len(results)
    summary = {'total': tot_num, 'pass': pass_cnt, 'fail':err_cnt, 'skip':skip_cnt}
    return results, summary

def log_parser_wagtail(log_text):
    # Wagtail format is similar to Django; directly call the Django parser.
    return log_parser_django(log_text)
