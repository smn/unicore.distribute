import os

from cornice.resource import resource, view


from unicore.distribute.utils import (
    get_config, get_repositories, get_repository, format_repo)


@resource(collection_path='/repos/', path='/repos/{name}/')
class Repository(object):

    def __init__(self, request):
        self.request = request
        self.config = get_config(request)

    def collection_get(self):
        repo_path = self.config.get('unicore.distribute', 'repo.storage_path')
        return [format_repo(repo) for repo in get_repositories(repo_path)]

    @view(renderer='json')
    def get(self):
        name = self.request.matchdict['name']
        repo_path = self.config.get('unicore.distribute', 'repo.storage_path')
        return format_repo(get_repository(os.path.join(repo_path, name)))
