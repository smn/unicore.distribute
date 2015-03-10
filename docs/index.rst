.. unicore.distribute documentation master file, created by
   sphinx-quickstart on Fri Feb 13 17:39:38 2015.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to unicore.distribute's documentation!
==============================================

unicore.distribute is a collection of APIs and tools for dealing with
Universal Core content repositories.

.. image:: https://travis-ci.org/universalcore/unicore.distribute.svg?branch=develop
    :target: https://travis-ci.org/universalcore/unicore.distribute
    :alt: Continuous Integration

.. image:: https://coveralls.io/repos/universalcore/unicore.distribute/badge.png?branch=develop
    :target: https://coveralls.io/r/universalcore/unicore.distribute?branch=develop
    :alt: Code Coverage

.. image:: https://readthedocs.org/projects/unicoredistribute/badge/?version=latest
    :target: https://unicoredistribute.readthedocs.org
    :alt: unicore.distribute Documentation

.. image:: https://pypip.in/version/unicore.distribute/badge.svg
    :target: https://pypi.python.org/pypi/unicore.distribute
    :alt: Pypi Package


Installation
============

The recommended way to install this for development is to install
it in a virtualenv_ but it's not necessary.

.. code-block:: bash

    pip install unicore.distribute

Configuration
=============

Put the following in a file called ``development.ini``

::

    [app:main]
    use = egg:unicore.distribute
    repo.storage_path = repos/

    [server:main]
    use = egg:waitress#main
    host = 0.0.0.0
    port = 6543

Running
=======

Clone a Universal Core content repository and run the server::

    $ git https://github.com/smn/unicore-sample-content \
        repos/unicore-sample-content
    $ pserve development.ini
    $ curl http://localhost:6543/repos.json

.. image:: unicore.distribute.gif


.. _virtualenv: https://virtualenv.pypa.io/en/latest/
