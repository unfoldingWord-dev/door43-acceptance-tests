from __future__ import unicode_literals, print_function
import argparse
import json
import urllib
import sys
from urllib2 import HTTPError
from bs4 import BeautifulSoup
from general_tools.print_utils import print_error, print_notice, print_warning, print_ok
from general_tools.url_utils import get_url, join_url_parts


class BibleTest(object):

    def __init__(self, errors, warnings):
        """
        Class constructor
        :param list errors:
        :param list warnings:
        """
        self.errors = errors      # type: list
        self.warnings = warnings  # type: list

    def __enter__(self):
        return self

    # noinspection PyUnusedLocal
    def __exit__(self, exc_type, exc_val, exc_tb):
        # delete temp files
        # if os.path.isdir(self.temp_dir):
        #     shutil.rmtree(self.temp_dir, ignore_errors=True)
        pass

    def run(self, repo_url):
        """
        Run the acceptance test on the repository at repo_url
        :param str|unicode repo_url:
        :return: bool
        """

        # only supports git.door43.org
        print('* Checking the repository URL...', end=' ')
        if 'git.door43.org' not in repo_url:
            self.errors.append('Only git.door43.org repositories are supported.')
            print('')
            return False

        # get gogs user and repository name
        pos = repo_url.find('https://git.door43.org/')
        if pos != 0:
            self.errors.append('Invalid repository URL: {0}'.format(repo_url))
            print('')
            return False

        parts = filter(bool, repo_url[23:].split('/'))
        if len(parts) != 2:
            self.errors.append('Not able to determine user and project: {0}'.format(repo_url))
            print('')
            return False

        gogs_user = parts[0]
        repo_name = parts[1]
        print('finished.')

        # get most recent commit
        print('* Getting the most recent commit...', end=' ')
        commits_html = get_url(join_url_parts(repo_url, 'commits', 'master'))

        # parse the dom
        commits_dom = BeautifulSoup(commits_html, 'html.parser')
        commit_row = commits_dom.body.find('table', {'id': 'commits-table'}).find('tbody').find('tr')
        if not commit_row:
            self.errors.append('Commit data was not found for {0}'.format(repo_url))

        # commit values: 0=author, 1=sha_and_message, 2=date
        commit_values = commit_row.find_all('td')
        sha_a_tag = commit_values[1].find('a')
        short_sha = sha_a_tag.text
        print('finished.')

        # check the meta data

        # if not tS, check the usfm directory (1 file per book)

        # if tS, check the chapter directories (1 directory per chapter, 1 file per chunk)

        # check live.door43.org
        live_url = join_url_parts('https://live.door43.org/u', gogs_user, repo_name, short_sha)

        # first, check if the page exists
        print('* Verifying that the output file exists...', end=' ')
        try:
            get_url(live_url)
        except HTTPError as err:
            self.errors.append('Not able to open {0}, {1}'.format(live_url, str(err)))
            print('')
            return False
        print('finished.')

        # next, validate the HTML
        print('* Validating the generated HTML...', end=' ')
        validator_url = 'https://validator.nu/?out=json&charset=UTF-8&parser=html5&doc={0}'.format(
            urllib.quote(live_url))
        validator_results = json.loads(get_url(validator_url))

        html_warnings = [m for m in validator_results['messages'] if m['type'] == 'info' and m['subType'] == 'warning']
        if html_warnings:
            for html_warning in html_warnings:
                self.warnings.append('HTML Validation Warning: {0}'.format(html_warning['message']))
            self.warnings.append('For details check {0}'.format(validator_url))

        html_errors = [m for m in validator_results['messages'] if m['type'] == 'error']
        if html_errors:
            for html_error in html_errors:
                self.errors.append('HTML Validation Error: {0}'.format(html_error['message']))
            self.errors.append('For details check {0}'.format(validator_url))
            print('')
            return False
        print('finished.')

        return True


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-r', '--gitrepo', dest='gitrepo', default=False,
                        required=True, help='Repository on git.door43.org where the Bible source can be found.')

    args = parser.parse_args(sys.argv[1:])

    test_errors = []
    test_warnings = []

    print_ok('STARTING: ', 'Acceptance test for {0}\n'.format(args.gitrepo))
    with BibleTest(test_errors, test_warnings) as test:
        success = test.run(args.gitrepo)

    if test_errors:
        print_notice('Acceptance test generated errors:')
        for test_error in test_errors:
            print('  {0}'.format(test_error))

    if test_warnings:
        print_notice('Acceptance test generated warnings:')
        for test_warning in test_warnings:
            print('  {0}'.format(test_warning))

    if test_errors:
        print_error('Acceptance test failed with errors.')
    elif test_warnings:
        print_warning('Acceptance test passed with warnings.')
    else:
        print_ok('PASSED', 'no errors or warnings were generated.')
