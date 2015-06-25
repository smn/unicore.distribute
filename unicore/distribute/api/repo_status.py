import os
from cornice.resource import resource, view
from unicore.distribute.utils import (
    get_config, format_repo_status, get_repository, get_repository_diff,
    pull_repository_files, clone_repository)


@resource(path='/repos/{name}/status.json')
class RepositoryStatusResource(object):
    def __init__(self, request):
        self.request = request
        self.config = get_config(request)

    @view(renderer='json')
    def get(self):
        name = self.request.matchdict['name']
        storage_path = self.config.get('repo.storage_path')
        return format_repo_status(get_repository(
            os.path.join(storage_path, name)))


@resource(path='/repos/{name}/diff/{commit_id}.json')
class RepositoryDiffResource(object):
    def __init__(self, request):
        self.request = request
        self.config = get_config(request)

    @view(renderer='json')
    def get(self):
        name = self.request.matchdict['name']
        commit_id = self.request.matchdict['commit_id']
        storage_path = self.config.get('repo.storage_path')
        return get_repository_diff(get_repository(
            os.path.join(storage_path, name)), commit_id)


@resource(path='/repos/{name}/pull/{commit_id}.json')
class RepositoryPullResource(object):
    def __init__(self, request):
        self.request = request
        self.config = get_config(request)

    @view(renderer='json')
    def get(self):
        name = self.request.matchdict['name']
        commit_id = self.request.matchdict['commit_id']
        storage_path = self.config.get('repo.storage_path')
        return pull_repository_files(get_repository(
            os.path.join(storage_path, name)), commit_id)


@resource(path='/repos/{name}/clone.json')
class RepositoryCloneResource(object):
    def __init__(self, request):
        self.request = request
        self.config = get_config(request)

    @view(renderer='json')
    def get(self):
        name = self.request.matchdict['name']
        storage_path = self.config.get('repo.storage_path')
        return clone_repository(
            get_repository(os.path.join(storage_path, name)))
