import os
from urlparse import urlparse

from cornice.resource import resource, view

from elasticgit.storage import StorageManager

from unicore.distribute.api.validators import (
    validate_schema, CreateRepoColanderSchema)
from unicore.webhooks.events import WebhookEvent
from unicore.distribute.utils import (
    get_config, get_repositories, get_repository, format_repo,
    format_content_type, format_content_type_object,
    save_content_type_object, delete_content_type_object,
    format_diffindex)

from git.exc import GitCommandError
from elasticgit import EG


@resource(collection_path='/repos.json', path='/repos/{name}.json')
class RepositoryResource(object):

    def __init__(self, request):
        self.request = request
        self.config = get_config(request)

    def collection_get(self):
        storage_path = self.config.get('repo.storage_path')
        return [format_repo(repo) for repo in get_repositories(storage_path)]

    @view(schema=CreateRepoColanderSchema)
    def collection_post(self):
        storage_path = self.config.get('repo.storage_path')
        repo_url = self.request.validated['repo_url']
        repo_url_info = urlparse(repo_url)
        repo_name_dot_git = os.path.basename(repo_url_info.path)
        repo_name = repo_name_dot_git.partition('.git')[0]
        try:
            EG.clone_repo(repo_url, os.path.join(storage_path, repo_name))
            self.request.response.headers['Location'] = self.request.route_url(
                'repositoryresource', name=repo_name)
            self.request.response.status = 301
            return ''
        except (GitCommandError,), e:
            self.request.errors.status = 400
            self.request.errors.add(
                'body', 'repo_url', e.stderr)

    @view(renderer='json')
    def get(self):
        name = self.request.matchdict['name']
        storage_path = self.config.get('repo.storage_path')
        return format_repo(get_repository(os.path.join(storage_path, name)))

    @view(renderer='json')
    def post(self):
        name = self.request.matchdict['name']
        branch_name = self.request.params.get('branch', 'master')
        remote_name = self.request.params.get('remote')
        storage_path = self.config.get('repo.storage_path')
        repo = get_repository(os.path.join(storage_path, name))
        storage_manager = StorageManager(repo)
        changes = storage_manager.pull(branch_name=branch_name,
                                       remote_name=remote_name)
        # Fire an event
        self.request.registry.notify(
            WebhookEvent(
                owner=self.request.authenticated_userid,
                event_type='repo.push',
                payload={
                    'repo': name,
                    'url': self.request.route_url('repositoryresource',
                                                  name=name)
                }))
        return format_diffindex(changes)


@resource(collection_path='/repos/{name}/{content_type}.json',
          path='/repos/{name}/{content_type}/{uuid}.json')
class ContentTypeResource(object):

    def __init__(self, request):
        self.request = request
        self.config = get_config(request)

    def collection_get(self):
        name = self.request.matchdict['name']
        content_type = self.request.matchdict['content_type']
        storage_path = self.config.get('repo.storage_path')
        return format_content_type(
            get_repository(os.path.join(storage_path, name)),
            content_type)

    @view(renderer='json', validators=validate_schema)
    def put(self):
        name = self.request.matchdict['name']
        uuid = self.request.matchdict['uuid']
        storage_path = self.config.get('repo.storage_path')
        commit, model = save_content_type_object(
            get_repository(os.path.join(storage_path, name)),
            self.request.schema, uuid, self.request.schema_data)
        return dict(model)

    @view(renderer='json')
    def get(self):
        name = self.request.matchdict['name']
        content_type = self.request.matchdict['content_type']
        uuid = self.request.matchdict['uuid']
        storage_path = self.config.get('repo.storage_path')
        return format_content_type_object(
            get_repository(os.path.join(storage_path, name)),
            content_type, uuid)

    @view(renderer='json')
    def delete(self):
        name = self.request.matchdict['name']
        content_type = self.request.matchdict['content_type']
        uuid = self.request.matchdict['uuid']
        storage_path = self.config.get('repo.storage_path')
        commit, model = delete_content_type_object(
            get_repository(os.path.join(storage_path, name)),
            content_type, uuid)
        return dict(model)
