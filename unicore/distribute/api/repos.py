import os

from cornice import Service

from unicore.distribute.utils import (
    get_config, get_repositories, get_repository, format_repo)


repositories_index = Service(name='repositories_index', path='/repos/',
                             description='List of repositories')


@repositories_index.get()
def repositories_index(request):
    config = get_config(request)
    repo_path = config.get('unicore.distribute', 'repo.storage_path')
    return [format_repo(repo) for repo in get_repositories(repo_path)]


repository = Service(name='repository', path='/repos/{name}/',
                     description='Repository')


@repository.get()
def repository(request):
    config = get_config(request)
    name = request.matchdict['name']
    repo_path = config.get('unicore.distribute', 'repo.storage_path')
    return format_repo(get_repository(os.path.join(repo_path, name)))
