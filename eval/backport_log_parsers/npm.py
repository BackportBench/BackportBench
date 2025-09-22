import re


def log_parser_node_tar(log_text):
    """
    Parse TAP-formatted test logs to extract test case details and overall summary
    Currently used for node-tar
    Parameters:
        log_text (str): TAP-formatted log text

    Returns:
        list[dict]: Dictionary with the following structure:
            [{
                "id": str,            # Test ID
                "status": str,        # "pass" or "fail"
            }]
    """
    lines = log_text.split('\n')
    results = []

    # Regular expressions to match TAP lines
    ok_pattern = re.compile(r'^ok (\d+) (.*)$')
    not_ok_pattern = re.compile(r'^not ok (\d+) (.*)$')
    time_pattern = re.compile(r'# time=[\w.]+')
    for line in lines:
        if ok_match := ok_pattern.match(line):
            test_id = ok_match.group(1)
            if ok_match.group(2):
                test_id += f' {ok_match.group(2)}'
            if time_pattern.search(test_id):
                test_id=time_pattern.sub('', test_id).strip()
            results.append({
                "id": test_id,
                "status": "pass"
            })
        elif not_ok_match := not_ok_pattern.match(line):
            test_id = not_ok_match.group(1)
            if not_ok_match.group(2):
                test_id += f' {not_ok_match.group(2)}'
            if time_pattern.search(test_id):
                test_id=time_pattern.sub('', test_id).strip()
            results.append({
                "id": test_id,
                "status": "fail",
            })

    tot_num = len(results)
    err_num = len([i for i in results if i['status']=='fail'])
    skip_num = len([i for i in results if i['status']=='skipped'])
    summary = {'total': tot_num, 'pass': tot_num-err_num-skip_num, 'fail':err_num, 'skip':skip_num}
    return results, summary

def log_parser_vite(log_text):
    # For vite, the log format is special: pass/skip are at the test suite (file) level, while failures are at the test case level
    # Therefore, when checking fail2pass, we need to see if failed test cases disappear after applying the patch, 
    # and if so, check whether failures decrease while the total test case count remains unchanged in the summary
    # P.S.: The summary counts are at the test case level
    results = []
    
    # Extract passing test cases.
    passed_matches = re.finditer(r'✓\s*([^\s]+)', log_text)
    for match in passed_matches:
        test_suite = match.group(1)
        results.append({
            'id': test_suite,
            'status': 'pass'
        })
    
    # Extract skipped test cases
    skipped_matches = re.finditer(r'↓\s*([^\s]+).*', log_text)
    for match in skipped_matches:
        test_suite = match.group(1)
        results.append({
            'id': test_suite,
            'status': 'skipped'
        })
    
    # Extract failed test cases
    failed_matches = re.finditer(r'FAIL\s+(.*)', log_text)
    for match in failed_matches:
        test_suite = match.group(1)
        results.append({
            'id': test_suite,
            'status': 'fail'
        })
    info_lines = [i.strip() for i in log_text.split('\n')if i.strip().startswith("Tests ")]
    if len(info_lines) != 1:
        print(info_lines)
    tot_num = re.search(r'\(([0-9]+)\)', info_lines[0]).group(1)
    detail_pattern = re.compile(r'([0-9]+)\s*(failed|passed|skipped|todo)')
    summary = {'total': int(tot_num), 'fail': 0, 'pass': 0}
    for m in detail_pattern.finditer(info_lines[0]):
        count = int(m.group(1))
        status = m.group(2)[:-2]
        if status == "skipp":status = "skip"
        elif status == "to": status = "todo"
        summary[status] = count
    return results, summary

def log_parser_ws(log_text):
    results = []
    summary = {}
    success_pattern = re.compile(r'✔ *(.*)')
    fail_pattern = re.compile(r'^\s*\d+\) *(.*)', re.M)
    passing_pattern = re.compile(r'(\d+)\s*passing')
    failing_pattern = re.compile(r'(\d+)\s*failing')
    pass_cnt = passing_pattern.search(log_text)
    fail_cnt = failing_pattern.search(log_text)
    testcase_part_end = len(log_text)
    if pass_cnt:
        testcase_part_end = min(testcase_part_end, pass_cnt.start())
    if fail_cnt:
        testcase_part_end = min(testcase_part_end, fail_cnt.start())
    for m in success_pattern.finditer(log_text[:testcase_part_end]):
        results.append({
            'id': m.group(1),
            'status': 'pass'
        })
    for m in fail_pattern.finditer(log_text[:testcase_part_end]):
        results.append({
            'id': m.group(1),
            'status': 'fail'
        })
    summary['pass'] = 0 if not pass_cnt else int(pass_cnt.group(1))
    summary['fail'] = 0 if not fail_cnt else int(fail_cnt.group(1))
    summary['total'] = summary['pass'] + summary['fail']
    return results, summary

def log_parser_socket_io_parser(log_text):
    """ Similar to ws """
    return log_parser_ws(log_text)

def log_parser_qs(log_text):
    """Similar to node-tar"""
    return log_parser_node_tar(log_text)