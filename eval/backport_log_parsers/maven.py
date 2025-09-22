import re


def log_parser_uaa(log_text):
    results = []
    err_cnt = 0
    fail_test_suite = set()
    # Patterns to identify test results
    passed_pattern = re.compile(r'(.*?)(?: took \d+ms|:\d+: warning:)')
    failed_pattern = re.compile(r'(.*?) > (.*?) FAILED')
    error_pattern = re.compile(r'(.*test.*?):\d+:\s*error', re.I)
    
    # Find the section containing only test case logs
    lines = log_text.split('\n')
    end_of_testcase_log = len(lines)
    for idx, line in enumerate(lines):
        if line.startswith("Gradle Test Executor"):
            end_of_testcase_log = idx
            break
    log_text = '\n'.join(lines[:end_of_testcase_log])
    for m in failed_pattern.finditer(log_text):
        # testsuite is group(1), and testcase is group(2)
        results.append({
            'id': f'{m.group(1)} > {m.group(2)}',
            'status': 'fail'
        })
        err_cnt += 1
        fail_test_suite.add(m.group(1))
    for m in error_pattern.finditer(log_text):
        # testsuite is group(1), and testcase is group(2)
        results.append({
            'id': m.group(1),
            'status': 'fail'
        })
        err_cnt += 1
        fail_test_suite.add(m.group(1))
    for m in passed_pattern.finditer(log_text):
        if m.group(1) not in fail_test_suite:
            results.append({
                'id': m.group(1),
                'status': 'pass'
            })

    summary = {'total': len(results), 'pass': len(results)-err_cnt, 'fail':err_cnt}
    return results, summary

def log_parser_cxf(log_text):
    """Parse CXF test logs with Maven-specific format."""
    results = []
    err_case = set()
    testcase_pattern = re.compile(r'\[INFO\] --- .*?test.*?\((.*?)\).*? @ cxf-rt-rs-security-jose ---')
    error_pattern = re.compile(r'\[ERROR\] Failed to execute goal .*? \((.*?)\) on project cxf-rt-rs-security-jose')
    test_result_pattern = re.compile(r'\[INFO\] Tests run: (?P<total>\d+), Failures: (?P<fail>\d+), Errors: (?P<err>\d+), Skipped: (?P<skip>\d+)')
    
    for m in error_pattern.finditer(log_text):
        err_case.add(m.group(1))
        results.append({
            'id': m.group(1),
            'status': 'fail'
        })
    for m in testcase_pattern.finditer(log_text):
        if m.group(1) not in err_case:
            results.append({
                'id': m.group(1),
                'status': 'pass'
            })
    log_summary = test_result_pattern.search(log_text)
    if not log_summary:
        summary = {'total': len(results), 'pass': len(results)-len(err_case), 'fail':len(err_case)}
    else:
        err_cnt = int(log_summary.group('fail')) + int(log_summary.group('err'))
        tot_num = int(log_summary.group('total'))
        summary = {'total': tot_num, 'pass': tot_num-err_cnt, 'fail': err_cnt, 'skip': int(log_summary.group('skip'))}
    return results, summary

def log_parser_tomcat(log_text):
    """Parse Tomcat test logs from the tail section."""
    results = []
    # compile error would not have testcase running status, take it as all fail, but as SWE says, this case should be discarded
    # if log_text.find('Compile failed') != -1 and log_text.find('BUILD FAILED') != -1:
    #     return results, {'total': 1, 'pass': 0, 'fail': 1}
    err_case = set()
    testcase_pattern = re.compile(r'Testcase: ([\w\[\]]+) took.*(\s*FAILED)?')
    test_result_pattern = re.compile(r'Tests run: (?P<total>\d+), Failures: (?P<fail>\d+), Errors: (?P<err>\d+), Skipped: (?P<skip>\d+)')
    lines = log_text.split('\n')
    idx = len(lines) - 1
    while idx:
        if lines[idx].find('Standard Error') != -1:
            idx -= 1
            break
        idx -= 1
    log_part = '\n'.join(lines[idx:])
    for m in testcase_pattern.finditer(log_part):
        testcase_name = m.group(1)
        if m.group(2):
            results.append({
                'id': testcase_name,
                'status': 'fail'
            })
            err_case.add(testcase_name)
        else:
            results.append({
                'id': testcase_name,
                'status': 'pass'
            })
    log_summary = test_result_pattern.search(log_part)
    if not log_summary:
        summary = {'total': len(results), 'pass': len(results)-len(err_case), 'fail':len(err_case)}
    else:
        err_cnt = int(log_summary.group('fail')) + int(log_summary.group('err'))
        tot_num = int(log_summary.group('total'))
        summary = {'total': tot_num, 'pass': tot_num-err_cnt, 'fail': err_cnt, 'skip': int(log_summary.group('skip'))}
    return results, summary

def log_parser_quarkus(log_text):
    """Parse Quarkus test logs with Maven-specific format."""
    results = []
    err_case = set()
    
    # Extract test log section
    lines = log_text.split('\n')
    start_idx = 0
    for idx, line in enumerate(lines):
        if line.startswith('[INFO]  T E S T S'):
            start_idx = idx
            break
    log_part = '\n'.join(lines[start_idx:])
    error_pattern = re.compile(r'\[ERROR\]\s*([\w.]+).*?<<< FAILURE!$', re.M)
    test_result_pattern = re.compile(r'Tests run: (?P<total>\d+), Failures: (?P<fail>\d+), Errors: (?P<err>\d+), Skipped: (?P<skip>\d+)')
    
    for m in error_pattern.finditer(log_part):
        err_case.add(m.group(1))
        results.append({
            'id': m.group(1),
            'status': 'fail'
        })
    log_summary = test_result_pattern.search(log_part)
    if not log_summary:
        summary = {'total': len(results), 'pass': len(results)-len(err_case), 'fail':len(err_case)}
    else:
        err_cnt = int(log_summary.group('fail')) + int(log_summary.group('err'))
        tot_num = int(log_summary.group('total'))
        summary = {'total': tot_num, 'pass': tot_num-err_cnt, 'fail': err_cnt, 'skip': int(log_summary.group('skip'))}
    return results, summary

def log_parser_xwiki_platform(log_text):
    """Parse XWiki Platform test logs using Quarkus parser logic."""
    return log_parser_quarkus(log_text)



