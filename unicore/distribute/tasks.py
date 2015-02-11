from pyramid_celery import celery_app as app

from elasticgit import EG
from unicore.content.models import Page, Category, Localisation


@app.task(ignore_result=True)
def fastforward(repo_path, index_prefix, es={}):
    workspace = EG.workspace(repo_path, index_prefix=index_prefix, es=es)
    workspace.fast_forward()
    workspace.reindex(Page)
    workspace.reindex(Category)
    workspace.reindex(Localisation)
