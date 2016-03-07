from git import Repo


class RepositoryEvent(object):

    def __init__(self, config, repo=None, repo_dir=None, repo_url=None):
        self.config = config
        if repo is None:
            repo = Repo(repo_dir)
        self.repo = repo
        self.repo_url = repo_url


class RepositoryCloned(RepositoryEvent):
    pass


class RepositoryUpdated(RepositoryEvent):

    def __init__(self, changes, branch, *args, **kwargs):
        super(RepositoryUpdated, self).__init__(*args, **kwargs)
        self.changes = changes
        self.branch = branch


class ContentTypeObjectUpdated(RepositoryEvent):

    def __init__(self, model, change_type, *args, **kwargs):
        super(ContentTypeObjectUpdated, self).__init__(*args, **kwargs)
        self.model = model
        self.change_type = change_type
