import os
import json

from avro.io import validate

from colander import MappingSchema, SchemaNode, String, Invalid

from unicore.distribute.utils import get_config, get_repository, get_schema


REPO_NAME_CHARS = set('abcdefghijklmnopqrstuvwxyz0123456789.-_')


def validate_schema(request):
    config = get_config(request)
    storage_path = config.get('repo.storage_path')
    repo = get_repository(
        os.path.join(storage_path, request.matchdict['name']))
    uuid = request.matchdict['uuid']
    content_type = request.matchdict['content_type']
    schema = get_schema(repo, content_type)
    data = json.loads(request.body)

    if not validate(schema, data):
        request.errors.status = 400
        request.errors.add(
            'body',
            'schema',
            'Data does not match the schema for %s' % (content_type,)
        )
    elif uuid is not None and data['uuid'] != uuid:
        request.errors.status = 400
        request.errors.add(
            'body',
            'uuid',
            'Payload UUID does not match URL UUID.'
        )
    else:
        request.schema = schema.to_json()
        request.schema_data = data


def repo_url_type_schema_validator(node, value):
    valid_prefixes = ['git://', 'http://', 'https://', 'ssh://']
    if not any([value.startswith(prefix) for prefix in valid_prefixes]):
        raise Invalid(node, '%r is not a valid repo_url' % (value,))


def repo_name_validator(node, value):
    chars = set(value)
    if not chars <= REPO_NAME_CHARS:
        raise Invalid(node, '%r contains invalid characters %r' % (
            value, chars - REPO_NAME_CHARS))
    if value in ('.', '..'):
        raise Invalid(node, '%r is not a valid repo_name' % (value,))


class CreateRepoColanderSchema(MappingSchema):
    repo_url = SchemaNode(
        String(), location='body', validator=repo_url_type_schema_validator)
    repo_name = SchemaNode(
        String(), location='body', validator=repo_name_validator, missing=None)
