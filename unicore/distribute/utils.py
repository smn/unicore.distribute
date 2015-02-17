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

    def get_list(self, section, option):
        value = self.get(section, option)
        return list(filter(None, (x.strip() for x in value.splitlines())))

    def get_dict(self, section, option):
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
    schema_files = glob.glob(
        os.path.join(repo.working_dir, '_schemas', '*.avsc'))
    schemas = []
    for schema_file in schema_files:
        with open(schema_file, 'r') as fp:
            schema = json.load(fp)
            schemas.append({
                '%(namespace)s.%(name)s' % schema: schema
            })
    return schemas


def get_schema(repo, content_type):
    try:
        with open(
            os.path.join(repo.working_dir,
                         '_schemas',
                         '%s.avsc' % (content_type,)), 'r') as fp:
            return avro.schema.parse(fp.read()).to_json()
    except IOError:
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
    storage_manager = StorageManager(repo)
    schema = get_schema(repo, content_type)
    model_class = deserialize(schema, module_name=schema['namespace'])
    return [dict(model_obj)
            for model_obj in storage_manager.iterate(model_class)]


def format_content_type_object(repo, content_type, uuid):
    try:
        storage_manager = StorageManager(repo)
        schema = get_schema(repo, content_type)
        model_class = deserialize(schema, module_name=schema['namespace'])
        return dict(storage_manager.get(model_class, uuid))
    except GitCommandError:
        raise NotFound('Object does not exist.')


def get_config(request):
    """
    Get the configuration for a request.

    :param Request request:
        The HTTP request
    """
    cp = UCConfigParser()
    cp.read('setup.cfg')
    return cp
