import os
import json

from cornice.resource import resource, view

from avro.io import validate

from unicore.distribute.utils import (
    get_config, get_repositories, get_repository, format_repo,
    format_content_type, format_content_type_object,
    save_content_type_object, get_schema)


def validate_schema(request):
    config = get_config(request)
    repo_path = config.get('repo.storage_path')
    repo = get_repository(os.path.join(repo_path, request.matchdict['name']))
    schema = get_schema(repo, request.matchdict['content_type'])
    print 'schema', schema.to_json()
    from pprint import pprint
    pprint(schema.props)
    print 'ct?', request.matchdict['content_type']
    print 'loads?', json.loads(request.body)
    valid = validate(schema, json.loads(request.body))
    print 'valid?', valid


@resource(collection_path='/repos.json', path='/repos/{name}.json')
class RepositoryResource(object):

    def __init__(self, request):
        self.request = request
        self.config = get_config(request)

    def collection_get(self):
        repo_path = self.config.get('repo.storage_path')
        return [format_repo(repo) for repo in get_repositories(repo_path)]

    @view(renderer='json')
    def get(self):
        name = self.request.matchdict['name']
        repo_path = self.config.get('repo.storage_path')
        return format_repo(get_repository(os.path.join(repo_path, name)))


@resource(collection_path='/repos/{name}/{content_type}.json',
          path='/repos/{name}/{content_type}/{uuid}.json')
class ContentTypeResource(object):

    def __init__(self, request):
        self.request = request
        self.config = get_config(request)

    def collection_get(self):
        name = self.request.matchdict['name']
        content_type = self.request.matchdict['content_type']
        repo_path = self.config.get('repo.storage_path')
        return format_content_type(
            get_repository(os.path.join(repo_path, name)),
            content_type)

    @view(renderer='json', validators=validate_schema)
    def put(self):
        name = self.request.matchdict['name']
        content_type = self.request.matchdict['content_type']
        uuid = self.request.matchdict['uuid']
        repo_path = self.config.get('repo.storage_path')
        return save_content_type_object(
            get_repository(os.path.join(repo_path, name)),
            content_type, uuid, self.request.body)

    @view(renderer='json')
    def get(self):
        name = self.request.matchdict['name']
        content_type = self.request.matchdict['content_type']
        uuid = self.request.matchdict['uuid']
        repo_path = self.config.get('repo.storage_path')
        return format_content_type_object(
            get_repository(os.path.join(repo_path, name)),
            content_type, uuid)
