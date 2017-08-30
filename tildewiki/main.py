"""TODO"""
import sys
from os.path import expanduser

import click
import pygit2
from click.types import Path

# TODO support reading from env
SITE_NAME = 'tilde.town'
PUBLISH_PATH = '/var/www/{site_name}/wiki'.format(site_name=SITE_NAME)
PREVIEW_PATH = expanduser('~/public_html/wiki')
LOCAL_REPOSITORY_PATH = expanduser('~/wiki')
REPOSITORY_PATH = '/wiki'

PATH_TYPE_KWARGS = dict(
    exists=True,
    writable=True,
    readable=True,
    file_okay=False,
    dir_okay=True,
)

class Config:
    def __init__(self):
        self.site_name = SITE_NAME
        self.publish_path = PUBLISH_PATH
        self.preview_path = PREVIEW_PATH
        self.local_repo_path = LOCAL_REPOSITORY_PATH
        self.repo_path = REPOSITORY_PATH

pass_config = click.make_pass_decorator(Config, ensure=True)

@click.group()
@click.option('--site-name', default=SITE_NAME, help='The root domain of the wiki.')
@click.option('--publish-path',
              default=PUBLISH_PATH,
              help='System level path to wiki for publishing.',
              type=Path(**PATH_TYPE_KWARGS))
@click.option('--preview-path',
              default=PREVIEW_PATH,
              help='Local path to wiki for previewing.',
              type=Path(**PATH_TYPE_KWARGS))
@click.option('--local-repo-path',
              default=LOCAL_REPOSITORY_PATH,
              help='Path to shared wiki git repository.',
              type=Path(**PATH_TYPE_KWARGS))
@click.option('--repo-path',
              default=REPOSITORY_PATH,
              help='Path to your clone of the shared git repository.',
              type=Path(**PATH_TYPE_KWARGS))
@pass_config
def main(config, site_name, publish_path, preview_path,
         local_repo_path, repo_path):
    config.site_name = site_name
    config.publish_path = publish_path
    config.preview_path = preview_path
    config.local_repo_path = local_repo_path
    config.repo_path = repo_path

    sys.exit(0)


@main.command()
@pass_config
def init(config):
    raise NotImplementedError()

@main.command()
@pass_config
def preview(config):
    raise NotImplementedError()

@main.command()
@pass_config
def publish(config):
    raise NotImplementedError()

@main.command()
@pass_config
def get(config):
    raise NotImplementedError()

@main.command()
@pass_config
def reset(config):
    raise NotImplementedError()
