import os
from urlparse import urlparse

from cornice.resource import resource, view

from git.exc import GitCommandError

from elasticsearch import ElasticsearchException
from elasticgit import EG
from elasticgit.workspace import Workspace
from elasticgit.storage import StorageManager
from elasticgit.search import ESManager

from unicore.distribute.api.validators import (
    validate_schema, CreateRepoColanderSchema)
from unicore.distribute.events import (
    RepositoryCloned, RepositoryUpdated, ContentTypeObjectUpdated)
from unicore.webhooks.events import WebhookEvent
from unicore.distribute.utils import (
    get_config, get_repositories, get_repository, format_repo,
    format_content_type, format_content_type_object,
    save_content_type_object, delete_content_type_object,
    format_diffindex, get_index_prefix, load_model_class,
    get_es, get_es_settings, get_mapping, list_content_types,
    get_repository_names)


@resource(collection_path='/repos.json', path='/repos/{name}.json')
class RepositoryResource(object):

    def __init__(self, request):
        self.request = request
        self.config = get_config(request)

    def collection_get(self):
        storage_path = self.config.get('repo.storage_path')
        if self.request.GET.get('name_only'):
            return [
                {'name': repo_path}
                for repo_path in get_repository_names(storage_path)]
        return [format_repo(repo) for repo in get_repositories(storage_path)]

    @view(schema=CreateRepoColanderSchema)
    def collection_post(self):
        storage_path = self.config.get('repo.storage_path')
        repo_url = self.request.validated['repo_url']
        repo_name = self.request.validated['repo_name']
        if not repo_name:
            repo_url_info = urlparse(repo_url)
            repo_name_dot_git = os.path.basename(repo_url_info.path)
            repo_name = repo_name_dot_git.partition('.git')[0]

        try:
            repo = EG.clone_repo(
                repo_url, os.path.join(storage_path, repo_name))
            self.request.registry.notify(
                RepositoryCloned(
                    config=self.config,
                    repo=repo))
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
        # Fire events
        self.request.registry.notify(
            RepositoryUpdated(
                config=self.config,
                repo=repo,
                changes=changes,
                branch=branch_name))
        self.request.registry.notify(
            WebhookEvent(
                owner=self.request.authenticated_userid,
                event_type='repo.push',
                payload={
                    'repo': name,
                    'url': self.request.route_url('repositoryresource',
                                                  name=name)
                }))
        return list(format_diffindex(changes))

    def delete(self):
        name = self.request.matchdict['name']
        storage_path = self.config.get('repo.storage_path')
        repo = get_repository(os.path.join(storage_path, name))
        workspace = Workspace(
            repo=repo,
            es=get_es_settings(self.config),
            index_prefix=get_index_prefix(repo.working_dir))
        # NOTE: destroys both the repo and index, if it exists,
        # irrespective of es.indexing_enabled value.
        workspace.destroy()
        self.request.response.status = 204


def initialize_repo_index(event):
    repo = event.repo
    # load models and mappings before creating index in case of errors
    model_mappings = [(load_model_class(repo, content_type),
                       get_mapping(repo, content_type))
                      for content_type in list_content_types(repo)]
    sm = StorageManager(repo)
    im = ESManager(
        storage_manager=sm,
        es=get_es(event.config),
        index_prefix=get_index_prefix(repo.working_dir))

    if im.index_exists(sm.active_branch()):
        im.destroy_index(sm.active_branch())
    im.create_index(sm.active_branch())
    while not im.index_ready(sm.active_branch()):
        pass

    try:
        for model_class, mapping in model_mappings:
            im.setup_custom_mapping(
                sm.active_branch(), model_class, mapping)

        for model_class, _ in model_mappings:
            for model in sm.iterate(model_class):
                im.index(model)
    except ElasticsearchException:
        im.destroy_index(sm.active_branch())
        raise


def update_repo_index(event):
    repo = event.repo
    workspace = Workspace(
        repo=repo,
        es=get_es_settings(event.config),
        index_prefix=get_index_prefix(repo.working_dir))

    old_branch = repo.head.ref
    repo.heads[event.branch].checkout()
    workspace.index_diff(event.changes)
    old_branch.checkout()


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
        repo = get_repository(os.path.join(storage_path, name))
        commit, model = save_content_type_object(
            repo, self.request.schema, uuid, self.request.schema_data)
        # Fire event
        self.request.registry.notify(ContentTypeObjectUpdated(
            config=self.config,
            repo=repo,
            model=model,
            change_type='update'))
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
        repo = get_repository(os.path.join(storage_path, name))
        commit, model = delete_content_type_object(
            repo, content_type, uuid)
        # Fire event
        self.request.registry.notify(ContentTypeObjectUpdated(
            config=self.config,
            repo=repo,
            model=model,
            change_type='delete'))
        return dict(model)


def index_content_type_object(event):
    repo = event.repo
    model = event.model
    im = ESManager(
        storage_manager=StorageManager(repo),
        es=get_es(event.config),
        index_prefix=get_index_prefix(repo.working_dir))
    if event.change_type == 'delete':
        im.unindex(model)
    else:
        im.index(model)
