import os
import argparse

from elasticgit.storage import StorageManager

from pyramid.paster import bootstrap
from pyramid.request import Request

from unicore.distribute.utils import get_repositories
from unicore.webhooks.events import WebhookEvent


class PollRepositories(object):

    # This gets set at run time or is overriden for tests
    notify = None

    def run(self, repo_dir, ini_file, base_url):
        request = Request.blank('/', base_url=base_url)
        env = bootstrap(ini_file, request=request)
        self.notify = env['registry'].notify
        for repo in get_repositories(repo_dir):
            self.pull_repo(env, repo)

        # http://docs.pylonsproject.org/projects/pyramid/en/1.3-branch/narr/commandline.html#cleanup # noqa
        env['closer']()

    def pull_repo(self, env, repo):
        sm = StorageManager(repo)
        remote = repo.remotes[0]
        head = repo.heads[0]
        original_commit = head.commit
        sm.pull(branch_name=head.name,
                remote_name=remote.name)
        last_commit = repo.heads[0].commit
        if original_commit.hexsha != last_commit.hexsha:
            name = os.path.basename(repo.working_dir)
            request = env['request']
            self.notify(
                WebhookEvent(
                    owner=None,
                    event_type='repo.push',
                    payload={
                        'repo': name,
                        'url': request.route_url(
                            'repositoryresource', name=name)
                    }))


def get_parser():  # pragma: no cover
    parser = argparse.ArgumentParser(
        description="unicore.distribute command line tools.")
    subparser = parser.add_subparsers(help='Commands')
    command = subparser.add_parser(
        'poll-repositories', help='poll repositories')
    command.add_argument(
        '-d', '--repo-dir',
        dest='repo_dir',
        help='The directory with repositories.',
        default='./repos')
    command.add_argument(
        '-i', '--ini-file',
        dest='ini_file',
        help='The project\'s ini file.',
        default='development.ini')
    command.add_argument(
        '-u', '--base-url',
        dest='base_url',
        help='This server\'s public URL (for webhooks)',
        default='http://localhost/')
    command.set_defaults(dispatcher=PollRepositories)

    return parser


def run(parser):  # pragma: no cover
    args = parser.parse_args()
    data = vars(args)
    dispatcher_class = data.pop('dispatcher')
    dispatcher = dispatcher_class()
    dispatcher.run(**data)


def main():  # pragma: no cover
    parser = get_parser()
    run(parser)
