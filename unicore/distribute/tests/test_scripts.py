import os.path

from ConfigParser import ConfigParser
from StringIO import StringIO

from pyramid.paster import bootstrap
from pyramid.request import Request

from elasticgit.tests.base import ToolBaseTest

from unicore.distribute.scripts import PollRepositories

from elasticgit.tests.base import TestPerson

from mock import Mock, patch


class TestScripts(ToolBaseTest):

    def setUp(self):
        self.workspace = self.mk_workspace()
        self.remote_workspace = self.mk_workspace(
            name='%s_remote' % (self.id().lower(),),
            index_prefix='%s_remote' % (self.workspace.index_prefix,))

        person1 = TestPerson({
            'age': 1,
            'name': 'Name'
        })

        self.remote_workspace.save(person1, 'Saving person1.')
        self.workspace.repo.create_remote(
            'origin', self.remote_workspace.working_dir)
        self.workspace.fast_forward()

    def mk_inifile(self, data):
        cp = ConfigParser()
        for section, key_data in data.items():
            cp.add_section(section)
            for key, value in key_data.items():
                cp.set(section, key, value)

        sio = StringIO()
        cp.write(sio)

        tmp_ini_data = sio.getvalue()
        tmp_ini_file = self.mk_tempfile(tmp_ini_data)
        return tmp_ini_file

    @patch.object(PollRepositories, 'pull_repo')
    def test_run(self, mocked_pull_repo):
        pr = PollRepositories()
        pr.run(self.WORKING_DIR, self.mk_inifile({
            'app:main': {
                'use': 'egg:unicore.distribute',
                'repo.storage_path': self.WORKING_DIR,
            }
        }), 'http://www.example.org')
        mocked_pull_repo.assert_called()
        # NOTE: the order of get_repositories is arbitrary
        (ws_call, remote_ws_call) = sorted(
            mocked_pull_repo.call_args_list,
            key=lambda call: call[0][1].working_dir)
        (args, kwargs) = ws_call
        (env, repo) = args
        self.assertEqual(repo, self.workspace.repo)

    def test_pull_repo(self):

        from pyramid.events import subscriber
        from unicore.webhooks.events import WebhookEvent

        mock = Mock()
        subscriber(WebhookEvent)(mock)

        request = Request.blank('/', base_url='http://example.org')

        tmp_ini_file = self.mk_inifile({
            'app:main': {
                'use': 'egg:unicore.distribute',
                'repo.storage_path': self.WORKING_DIR
            }
        })
        env = bootstrap(tmp_ini_file, request=request)

        mock = Mock()
        poll_repos = PollRepositories()
        poll_repos.notify = mock
        poll_repos.pull_repo(env, self.workspace.repo)

        mock.assert_not_called()

        self.remote_workspace.save(
            TestPerson({'age': 2, 'name': 'Foo'}), 'Saving person2')

        poll_repos.pull_repo(env, self.workspace.repo)
        mock.assert_called()
        (call,) = mock.call_args_list
        (args, kwargs) = call
        (event,) = args
        name = os.path.basename(self.workspace.working_dir)
        url = env['request'].route_url('repositoryresource', name=name)
        self.assertTrue('http://example.org' in url)
        self.assertEqual(event.owner, None)
        self.assertEqual(event.event_type, 'repo.push')
        self.assertEqual(event.payload, {
            'repo': name,
            'url': url,
        })
