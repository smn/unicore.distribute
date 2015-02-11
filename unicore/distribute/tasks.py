from pyramid_celery import celery_app as app

from elasticgit import EG
from unicore.content.models import Page, Category, Localisation


@app.task(ignore_result=True)
def fastforward(repo_path, index_prefix, es_host='http://localhost:9200'):
    workspace = EG.workspace(
        repo_path, index_prefix=index_prefix, es={'urls': [es_host]})
    workspace.fast_forward()
    workspace.reindex(Page)
    workspace.reindex(Category)
    workspace.reindex(Localisation)
