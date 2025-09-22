from backport_log_parsers.npm import *
from backport_log_parsers.pypi import *
from backport_log_parsers.maven import *
import re


PASS_STATUS_ls = ['ok', 'pass']
FAIL_STATUS_ls = ['error', 'fail', 'ERROR', 'FAIL']


class LogParser:
  def __init__(self, repo_name: str):
    self.repo = repo_name

  def parse_test_logs(self, log_text, pattern=None):
    try:
      if pattern:
        return  globals()[f"log_parser_{re.sub('[-.]', '_', self.repo)}"](log_text, pattern)
      else:
        return globals()[f"log_parser_{re.sub('[-.]', '_', self.repo)}"](log_text)
    except KeyError:
      print(f'{self.repo} not in our list, please check the name of repository')


if __name__ == "__main__":
    # example logs
    log_text = """
Traceback (most recent call last):
  File "tests/runtests.py", line 324, in <module>
    options.failfast, args)
  File "tests/runtests.py", line 167, in django_tests
    failures = test_runner.run_tests(test_labels, extra_tests=extra_tests)
  File "/django/django/test/simple.py", line 380, in run_tests
    suite = self.build_suite(test_labels, extra_tests)
  File "/django/django/test/simple.py", line 264, in build_suite
    suite.addTest(build_suite(app))
  File "/django/django/test/simple.py", line 79, in build_suite
    test_module = get_tests(app_module)
  File "/django/django/test/simple.py", line 36, in get_tests
    test_module = import_module('.'.join(prefix + [TEST_MODULE]))
  File "/django/django/utils/importlib.py", line 35, in import_module
    __import__(name)
  File "/django/tests/regressiontests/views/tests/__init__.py", line 15, in <module>
    from .static import StaticHelperTest, StaticTests
  File "/django/tests/regressiontests/views/tests/static.py", line 10, in <module>
    from django.views.static import STREAM_CHUNK_SIZE
ImportError: cannot import name STREAM_CHUNK_SIZE
    """

    # parse the log
    log_parser = LogParser('django')
    # print(re.sub('[-.]', '_', 'socket.io-parser'))
    result, summary = log_parser.parse_test_logs(log_text)
    print(result)
    print(len(result))
    print(summary)
