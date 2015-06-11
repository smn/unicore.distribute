from git import Repo


class RepositoryEvent(object):

    def __init__(self, repo=None, repo_dir=None, repo_url=None):
        if repo is None:
            repo = Repo(repo_dir)
        self.repo = repo
        self.repo_url = repo_url


class RepositoryCloned(RepositoryEvent):

    def __init__(self, mapping, **kwargs):
        super(RepositoryCloned, self).__init__(**kwargs)
        self.mapping = mapping


class RepositoryUpdated(RepositoryEvent):

    def __init__(self, changes, **kwargs):
        super(RepositoryUpdated, self).__init__(**kwargs)
        self.changes = changes
