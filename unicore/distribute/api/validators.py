import os
import json

from avro.io import validate

from colander import (
    MappingSchema, SchemaNode, String, Invalid, Mapping)

from unicore.distribute.utils import get_config, get_repository, get_schema


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


def model_mapping_preparer(value):
    if not isinstance(value, dict):
        return value

    for model_name, mapping in value.iteritems():
        if not mapping:
            value[model_name] = None
        # drop all keys aside from properties
        value[model_name] = {'properties': mapping.get('properties')}

    return value


class CreateRepoColanderSchema(MappingSchema):
    repo_url = SchemaNode(
        String(), location='body', validator=repo_url_type_schema_validator)
    models = SchemaNode(
        Mapping(unknown='preserve'), location='body',
        preparer=model_mapping_preparer, missing={})
