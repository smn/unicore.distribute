import os
import re

from ConfigParser import ConfigParser
from pyramid.exceptions import NotFound

from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError


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

    return {
        'name': os.path.basename(repo.working_dir),
    }


def get_config(request):
    """
    Get the configuration for a request.

    :param Request request:
        The HTTP request
    """
    cp = UCConfigParser()
    cp.read('setup.cfg')
    return cp
