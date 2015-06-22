import os
from cornice.resource import resource, view
from unicore.distribute.utils import (get_config, format_repo_status,
                                      get_repository, get_repositories)


@resource(collection_path='status.json', path='/status/{name}.json')
class RepositoryStatusResource(object):
    def __init__(self, request):
        self.request = request
        self.config = get_config(request)

    def collection_get(self):
        storage_path = self.config.get('repo.storage_path')
        return [format_repo_status(repo) for repo
                in get_repositories(storage_path)]

    @view(renderer='json')
    def get(self):
        name = self.request.matchdict['name']
        storage_path = self.config.get('repo.storage_path')
        return format_repo_status(get_repository(
            os.path.join(storage_path, name)))


@resource(path='/status/{name}/{commit_id}.json')
class RepositoryDiffFilesResource(object):
    def __init__(self, request):
        self.request = request
        self.config = get_config(request)

    @view(renderer='json')
    def get(self):
        name = self.request.matchdict['name']
        commit_id = self.request.matchdict['commit_id']
        storage_path = self.config.get('repo.storage_path')
        return {
            "commit": commit_id,
            "commit_reversed": commit_id[::-1]
        }
