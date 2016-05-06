import glob
import json
import os
import re

from datetime import datetime

from ConfigParser import ConfigParser
from pyramid.exceptions import NotFound

from git import Repo
from git.exc import (
    InvalidGitRepositoryError, NoSuchPathError, GitCommandError, BadName)

import avro.schema

from elasticutils import get_es as get_es_object

from elasticgit.commands.avro import deserialize
from elasticgit.storage import StorageManager


class UCConfigParser(ConfigParser):
    """
    A config parser that understands lists and dictionaries.
    """

    def get_list(self, section, option):
        """
        This allows for loading of Pyramid list style configuration
        options:

        [foo]
        bar =
            baz
            qux
            zap

        ``get_list('foo', 'bar')`` returns ``['baz', 'qux', 'zap']``

        :param str section:
            The section to read.
        :param str option:
            The option to read from the section.
        :returns: list
        """
        value = self.get(section, option)
        return list(filter(None, (x.strip() for x in value.splitlines())))

    def get_dict(self, section, option):
        """
        This allows for loading of Pyramid dictionary style configuration
        options:

        [foo]
        bar =
            baz=qux
            zap=paz

        ``get_dict('foo', 'bar')`` returns ``{'baz': 'qux', 'zap': 'paz'}``

        :param str section:
            The section to read.
        :param str option:
            The option to read from the section.
        :returns: dict
        """
        return dict(re.split('\s*=\s*', value)
                    for value in self.get_list(section, option))


def get_repositories(path):
    """
    Return an array of tuples with the name and path for
    repositories found in a directory.

    :param str path:
        The path to find repositories in
    :returns: tuple
    """
    return [get_repository(os.path.join(path, subdir))
            for subdir in os.listdir(path)
            if os.path.isdir(
            os.path.join(path, subdir, '.git'))]


def get_repository_names(path):
    """
    Return an array of the path name for
    repositories found in a directory.

    :param str path:
        The path to find repositories in
    :returns: array
    """
    return [subdir
            for subdir in os.listdir(path)
            if os.path.isdir(os.path.join(path, subdir, '.git'))]


def get_repository(path):
    """
    Return a repository for whatever's at a path

    :param str path:
        The path to the repository
    :returns: Repo
    """
    try:
        return Repo(path)
    except (NoSuchPathError, InvalidGitRepositoryError):
        raise NotFound('Repository not found.')


def get_index_prefix(path):
    """
    Return the Elasticsearch index prefix for the repo at path.

    :param str repo_path:
        The path to the repositoy
    :returns: string
    """
    return os.path.basename(path).lower()


def list_schemas(repo):
    """
    Return a list of parsed avro schemas as dictionaries.

    :param Repo repo:
        The git repository.
    :returns: dict
    """
    schema_files = glob.glob(
        os.path.join(repo.working_dir, '_schemas', '*.avsc'))
    schemas = {}
    for schema_file in schema_files:
        with open(schema_file, 'r') as fp:
            schema = json.load(fp)
            schemas['%(namespace)s.%(name)s' % schema] = schema
    return schemas


def list_content_types(repo):
    """
    Return a list of content types in a repository.

    :param Repo repo:
        The git repository.
    :returns: list
    """
    schema_files = glob.glob(
        os.path.join(repo.working_dir, '_schemas', '*.avsc'))
    return [os.path.splitext(os.path.basename(schema_file))[0]
            for schema_file in schema_files]


def get_schema(repo, content_type):
    """
    Return a schema for a content type in a repository.

    :param Repo repo:
        The git repository.
    :returns: dict
    """
    try:
        with open(
                os.path.join(repo.working_dir,
                             '_schemas',
                             '%s.avsc' % (content_type,)), 'r') as fp:
            data = fp.read()
            return avro.schema.parse(data)
    except IOError:  # pragma: no cover
        raise NotFound('Schema does not exist.')


def get_mapping(repo, content_type):
    """
    Return an ES mapping for a content type in a repository.

    :param Repo repo:
        This git repository.
    :returns: dict
    """
    try:
        with open(
            os.path.join(repo.working_dir,
                         '_mappings',
                         '%s.json' % (content_type,)), 'r') as fp:
            return json.load(fp)
    except IOError:
        raise NotFound('Mapping does not exist.')


def format_repo(repo):
    """
    Return a dictionary representing the repository

    It returns ``None`` for things we do not support or are not
    relevant.

    :param str repo_name:
        The name of the repository.
    :param git.Repo repo:
        The repository object.
    :param str base_url:
        The base URL for the repository's links.
    :returns: dict

    """
    commit = repo.commit()
    return {
        'name': os.path.basename(repo.working_dir),
        'branch': repo.active_branch.name,
        'commit': commit.hexsha,
        'timestamp': datetime.fromtimestamp(
            commit.committed_date).isoformat(),
        'author': '%s <%s>' % (commit.author.name, commit.author.email),
        'schemas': list_schemas(repo)
    }


def format_diff_A(diff):
    return {
        'type': 'A',
        'path': diff.b_blob.path,
    }


def format_diff_D(diff):
    return {
        'type': 'D',
        'path': diff.a_blob.path,
    }


def format_diff_R(diff):
    return {
        'type': 'R',
        'rename_from': diff.rename_from,
        'rename_to': diff.rename_to,
    }


def format_diff_M(diff):
    return {
        'type': 'M',
        'path': diff.a_blob.path,
    }


def format_diffindex(diff_index):
    """
    Return a JSON formattable representation of a DiffIndex.

    Returns a generator that returns dictionaries representing the changes.

    .. code::
        [
            {
                'type': 'A',
                'path': 'path/to/added/file.txt',
            },
            {
                'type': 'D',
                'path': 'path/to/deleted/file.txt',
            },
            {
                'type': 'M',
                'path': 'path/to/modified/file.txt',
            },
            {
                'type': 'R',
                'rename_from': 'original/path/to/file.txt',
                'rename_to': 'new/path/to/file.txt',
            },
        ]

    :returns: generator

    """
    for diff in diff_index:
        if diff.new_file:
            yield format_diff_A(diff)
        elif diff.deleted_file:
            yield format_diff_D(diff)
        elif diff.renamed:
            yield format_diff_R(diff)
        elif diff.a_blob and diff.b_blob and diff.a_blob != diff.b_blob:
            yield format_diff_M(diff)


def format_content_type(repo, content_type):
    """
    Return a list of all content objects for a given content type
    in a repository.

    :param Repo repo:
        The git repository.
    :param str content_type:
        The content type to list
    :returns: list
    """
    storage_manager = StorageManager(repo)
    model_class = load_model_class(repo, content_type)
    return [dict(model_obj)
            for model_obj in storage_manager.iterate(model_class)]


def format_content_type_object(repo, content_type, uuid):
    """
    Return a content object from a repository for a given content_type
    and uuid

    :param Repo repo:
        The git repository.
    :param str content_type:
        The content type to list
    :returns: dict
    """
    try:
        storage_manager = StorageManager(repo)
        model_class = load_model_class(repo, content_type)
        return dict(storage_manager.get(model_class, uuid))
    except GitCommandError:
        raise NotFound('Object does not exist.')


def format_repo_status(repo):
    """
    Return a dictionary representing the repository status

    It returns ``None`` for things we do not support or are not
    relevant.

    :param str repo_name:
        The name of the repository.
    :returns: dict

    """
    commit = repo.commit()
    return {
        'name': os.path.basename(repo.working_dir),
        'commit': commit.hexsha,
        'timestamp': datetime.fromtimestamp(
            commit.committed_date).isoformat(),
    }


def save_content_type_object(repo, schema, uuid, data):
    """
    Save an object as a certain content type
    """
    storage_manager = StorageManager(repo)
    model_class = deserialize(schema,
                              module_name=schema['namespace'])
    model = model_class(data)
    commit = storage_manager.store(model, 'Updated via PUT request.')
    return commit, model


def delete_content_type_object(repo, content_type, uuid):
    """
    Delete an object of a certain content type
    """
    storage_manager = StorageManager(repo)
    model_class = load_model_class(repo, content_type)
    model = storage_manager.get(model_class, uuid)
    commit = storage_manager.delete(model, 'Deleted via DELETE request.')
    return commit, model


def get_config(request):  # pragma: no cover
    """
    Get the configuration for a request.

    :param Request request:
        The HTTP request
    """
    return request.registry.settings


def get_es_settings(config):
    """
    Return the Elasticsearch settings based on the config or ENV.

    :param dict config:
        The app configuration
    :returns: dict
    """
    es_host = os.environ.get('ES_HOST')
    return {
        'urls': [es_host or config.get('es.host', 'http://localhost:9200')]
    }


def get_es(config):
    """
    Return the :py:class:`elasticsearch.Elasticsearch` object based
    on the config.

    :param dict config:
        The app configuration
    :returns: Elasticsearch
    """
    return get_es_object(**get_es_settings(config))


def load_model_class(repo, content_type):
    """
    Return a model class for a content type in a repository.

    :param Repo repo:
        The git repository.
    :param str content_type:
        The content type to list
    :returns: class
    """
    schema = get_schema(repo, content_type).to_json()
    return deserialize(schema, module_name=schema['namespace'])


def add_model_item_to_pull_dict(storage_manager, path, pull_dict):
    if path.endswith(".json"):
        model = storage_manager.load(path)
        pull_dict[model.__module__ + "." +
                  model.__class__.__name__].append(dict(model))
        return True
    return False


def get_repository_diff(repo, commit_id):
    try:
        old_commit = repo.commit(commit_id)
        diff = old_commit.diff(repo.head)

        return {
            "name": os.path.basename(repo.working_dir),
            "previous-index": commit_id,
            "current-index": repo.commit().hexsha,
            "diff": list(format_diffindex(diff))
        }
    except (GitCommandError, BadName):
        raise NotFound("The git index does not exist")


def pull_repository_files(repo, commit_id):
    changed_files = {}
    for name in list_content_types(repo):
        changed_files[name] = []

    try:
        old_commit = repo.commit(commit_id)
        diff = old_commit.diff(repo.head)

        sm = StorageManager(repo)
        for diff_added in diff.iter_change_type('A'):
            add_model_item_to_pull_dict(
                sm, diff_added.b_blob.path, changed_files)

        for diff_modified in diff.iter_change_type('M'):
            add_model_item_to_pull_dict(
                sm, diff_modified.b_blob.path, changed_files)

        json_diff = []
        for diff_added in diff.iter_change_type('R'):
            json_diff.append(format_diff_R(diff_added))

        for diff_removed in diff.iter_change_type('D'):
            json_diff.append(format_diff_D(diff_removed))

        changed_files["other"] = json_diff
        changed_files["commit"] = repo.head.commit.hexsha
        return changed_files

    except (GitCommandError, BadName):
        raise NotFound("The git index does not exist")


def clone_repository(repo):
    files = {}
    for name in list_content_types(repo):
        files[name] = format_content_type(repo, name)

    files['commit'] = repo.head.commit.hexsha
    return files
