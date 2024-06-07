import sys
import jenkins

def extract_data(build_info):
    fail_count = None
    skip_count = None
    total_count = None
    for action in build_info.get('actions', []):
        if '_class' in action and action['_class'] == 'hudson.tasks.junit.TestResultAction':
            fail_count = action.get('failCount')
            skip_count = action.get('skipCount')
            total_count = action.get('totalCount')
            break

    if fail_count is not None and total_count is not None:
        print("Build No:", build_info.get('number'))
        print("Passed Testcase:", total_count - fail_count - skip_count)
        print("Failed Testcase:", fail_count)
        print("Skipped Testcase:", skip_count)
        print("Total Testcases:", total_count)
        build_percentage = ((total_count - fail_count - skip_count) * 100)/total_count
        print("Passing percentage: {:.2f}".format(build_percentage))
    else:
        print("Testcases not found!")
    return None

def get_test_report(job_name, build_number):
    build_info = server.get_build_info(job_name, build_number)
    for action in build_info.get('actions', []):
        if '_class' in action and action['_class'] == 'hudson.tasks.junit.TestResultAction':
            test_report_url = action.get('urlName')
            if test_report_url:
                test_report = server.get_build_test_report(job_name, build_number)
                return test_report
    return None

def get_failing_tests(test_report):
    failing_tests = set()
    if test_report:
        for suite in test_report['suites']:
            for case in suite['cases']:
                if case['status'] in ['FAILED','REGRESSION']:
                    failing_tests.add((case['className'], case['name']))
    return failing_tests

def compare_reports(job_name, current_build_number, previous_build_number):
    current_test_report = get_test_report(job_name, current_build_number)
    previous_test_report = get_test_report(job_name, previous_build_number)

    current_failing_tests = get_failing_tests(current_test_report)
    previous_failing_tests = get_failing_tests(previous_test_report)

    new_failures = set()
    existing_failures = set()
    fixed_failures = set()

    for test_class, test_name in current_failing_tests:
        if (test_class, test_name) not in previous_failing_tests:
            new_failures.add((test_class, test_name))

    for test_class, test_name in current_failing_tests:
        if (test_class, test_name) in previous_failing_tests:
            existing_failures.add((test_class, test_name))

    for test_class, test_name in previous_failing_tests:
            if (test_class, test_name) not in current_failing_tests:
                fixed_failures.add((test_class, test_name))

    return new_failures, existing_failures, fixed_failures

def get_previous_build(job_name, build_number): 
  while build_number >= 1: 
    if server.get_build_info(job_name, build_number)['result'] != 'ABORTED':
      return build_number 
    build_number -= 1
  return None

try:
    server = jenkins.Jenkins(sys.argv[1], username=sys.argv[2], password=sys.argv[3])
    job_name = sys.argv[4]
    if server.job_exists(job_name):
        current_build_number = int(sys.argv[5])
                
        previous_build_number = get_previous_build(job_name, current_build_number-1)
        current_build_info = server.get_build_info(job_name, current_build_number)
        previous_build_info = server.get_build_info(job_name, previous_build_number)
        print("JOB NAME:",job_name)

        new_failures, existing_failures, fixed_failures = compare_reports(job_name, current_build_number, previous_build_number)

        print("\n###### Current Build Summary ######\n")
        extract_data(current_build_info)
        print("BUILD STATUS:",server.get_build_info(job_name,current_build_number)['result'])

        print("\n###### Previous Build Summary ######\n")
        extract_data(previous_build_info)
        print("BUILD STATUS:",server.get_build_info(job_name,previous_build_number)['result'])

        print("\n###### New Failures -",len(new_failures),"######\n")
        if new_failures:
            for test_class, test_name in new_failures:
                print(f"{test_class} - {test_name}")
        else:
            print("None")

        print("\n###### Existing Failures -",len(existing_failures),"######\n")
        if existing_failures:
            for test_class, test_name in existing_failures:
                print(f"{test_class} - {test_name}")
        else:
            print("None")

        print("\n###### Fixed Failures -",len(fixed_failures),"######\n")
        if fixed_failures:
            for test_class, test_name in fixed_failures:
                print(f"{test_class} - {test_name}")
        else:
            print("None")
    else:
        print("Job not found!")
except jenkins.JenkinsException as e:
    print(e)
