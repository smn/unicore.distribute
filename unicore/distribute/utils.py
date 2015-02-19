import glob
import json
import os
import re

from datetime import datetime

from ConfigParser import ConfigParser
from pyramid.exceptions import NotFound

from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError, GitCommandError

import avro.schema

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
            print json.dumps(json.loads(data), indent=2)
            return avro.schema.parse(data)
    except IOError:  # pragma: no cover
        raise NotFound('Schema does not exist.')


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
        'commit': commit.hexsha,
        'timestamp': datetime.fromtimestamp(
            commit.committed_date).isoformat(),
        'author': '%s <%s>' % (commit.author.name, commit.author.email),
        'schemas': list_schemas(repo)
    }


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
    schema = get_schema(repo, content_type).to_json()
    model_class = deserialize(schema, module_name=schema['namespace'])
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
        schema = get_schema(repo, content_type).to_json()
        model_class = deserialize(schema, module_name=schema['namespace'])
        return dict(storage_manager.get(model_class, uuid))
    except GitCommandError:
        raise NotFound('Object does not exist.')


def save_content_type_object(repo, content_type, uuid, data):
    """
    Save an object as a certain content type
    """
    storage_manager = StorageManager(repo)
    storage_manager



def get_config(request):  # pragma: no cover
    """
    Get the configuration for a request.

    :param Request request:
        The HTTP request
    """
    return request.registry.settings
