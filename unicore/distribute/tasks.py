from pyramid_celery import celery_app as app

from elasticgit import EG
from elasticgit.commands.avro import deserialize
from unicore.content.models import Page, Category, Localisation

from unicore.distribute.utils import list_schemas


@app.task(ignore_result=True)
def fastforward(repo_path, index_prefix, es={}):
    workspace = EG.workspace(repo_path, index_prefix=index_prefix, es=es)
    workspace.fast_forward()
    workspace.reindex(Page)
    workspace.reindex(Category)
    workspace.reindex(Localisation)


@app.task(ignore_result=True)
def reindex(repo_path, index_prefix, es={}):
    workspace = EG.workspace(repo_path, index_prefix=index_prefix, es=es)
    model_classes = map(
        lambda schema: deserialize(schema, module_name=schema['namespace']),
        list_schemas(workspace.repo))
    model_classes = model_classes or [Page, Category, Localisation]
    for model_class in model_classes:
        workspace.reindex(model_class)
