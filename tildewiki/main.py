"""TODO"""
import os
import re
from os.path import expanduser

import click
import pygit2
from click import ClickException
from click.types import Path
from shutil import rmtree

from .click_types import (
    WikiRepo
)

from .compilation import (
    compile_wiki
)

from . import git_wrapper as git

# TODO support reading from env
SITE_NAME = 'tilde.town'
PUBLISH_PATH = '/var/www/{site_name}/wiki'.format(site_name=SITE_NAME)
PREVIEW_PATH = expanduser('~/public_html/wiki')
LOCAL_REPOSITORY_PATH = expanduser('~/wiki')
REPOSITORY_PATH = '/wiki'

DEFAULT_PATH_KWARGS = dict(
    exists=True,
    writable=True,
    readable=True,
    file_okay=False,
    dir_okay=True)

class Config:
    def __init__(self):
        self.site_name = SITE_NAME
        self.publish_path = PUBLISH_PATH
        self.preview_path = PREVIEW_PATH
        self.local_repo_path = LOCAL_REPOSITORY_PATH
        self.repo_path = REPOSITORY_PATH
        self.author_name = os.environ.get('LOGNAME')

    @property
    def author_email(self):
        return '{}@{}'.format(self.author_name, self.site_name)

pass_config = click.make_pass_decorator(Config, ensure=True)

@click.group()
@click.option('--site-name', default=SITE_NAME, help='The root domain of the wiki.')
@click.option('--publish-path',
              default=PUBLISH_PATH,
              help='System level path to wiki for publishing.',
              type=Path(**DEFAULT_PATH_KWARGS))
@click.option('--repo-path',
              default=REPOSITORY_PATH,
              help='Path to the shared wiki repository.',
              type=WikiRepo(**DEFAULT_PATH_KWARGS))
@pass_config
def main(config, site_name, publish_path, repo_path):
    # TODO click does not appear to call expanduser on things. it'd be nice to
    # opt into that with the Path type. Should click be patched? Or should we
    # use a custom Path type?
    config.site_name = site_name
    config.publish_path = publish_path
    config.repo_path = repo_path

@main.command()
@click.option('--local-repo-path', default=LOCAL_REPOSITORY_PATH,
              help='Path to shared wiki git repository.', type=Path(file_okay=False))
@click.option('--preview-path', default=PREVIEW_PATH,
              help='Local path to wiki for previewing.', type=Path(file_okay=False))
@pass_config
def init(config, local_repo_path, preview_path):
    """
    This command, `wiki init`, does the following:
      - clones REPOSITORY_PATH to LOCAL_REPOSITORY_PATH
      - creates PREVIEW_PATH
      - calls the preview command
    """
    if path_exists(path_join(local_repo_path)):
        raise ClickException(
            '{} already exists. Have you already run wiki init?'.format(
                local_repo_path))

    if path_exists(path_join(preview_path)):
        raise ClickException(
            '{} already exists. Have you already run wiki init?'.format(
                preview_path))

    click.echo('Cloning {} to {}...'.format(config.repo_path, local_repo_path))
    create_repo(
        config.repo_path,
        config.local_repo_path,
        config.author_name,
        config.author_email
    )

    click.echo('Creating {}...'.format(preview_path))
    os.makedirs(preview_path)

    click.echo('Compiling wiki preview for the first time...')
    _preview(config, preview_path, local_repo_path)

    click.echo('~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~')
    click.echo("Congrats, you are ready to contribute to {}'s wiki!".format(
        config.site_name
    ))

@main.command()
@click.option('--local-repo-path', default=LOCAL_REPOSITORY_PATH,
              help='Path to local clone of wiki repository.', type=WikiRepo(**DEFAULT_PATH_KWARGS))
@click.option('--preview-path',
              default=PREVIEW_PATH,
              help='Local path to wiki for previewing.',
              type=Path(**DEFAULT_PATH_KWARGS))
@pass_config
def preview(config, preview_path, local_repo_path):
    preview_prompt = 'This will wipe everything at {}. Proceed?'
    click.confirm(
        preview_prompt.format(preview_path),
        abort=True)
    # TODO actually perform removal
    _preview(config, preview_path, local_repo_path)

@main.command()
@click.option('--local-repo-path', default=LOCAL_REPOSITORY_PATH,
              help='Path to local clone of wiki repository.', type=WikiRepo(**DEFAULT_PATH_KWARGS))
@pass_config
def publish(config, local_repo_path):
    # use config.repo_path and config.publish_path
    make_commit(local_repo_path, config.author_name, config.author_email)
    # TODO push to repository path
    # TODO compile from config.repo_path to config.publish_path
    raise NotImplementedError()

@main.command()
@pass_config
def get(config):
    raise NotImplementedError()

@main.command()
@click.option('--local-repo-path', default=LOCAL_REPOSITORY_PATH,
              help='Path to shared wiki git repository.', type=WikiRepo(**DEFAULT_PATH_KWARGS))
@pass_config
def reset(config, local_repo_path):
    raise NotImplementedError()

def _preview(config, preview_path, local_repo_path):
    compile_wiki(local_repo_path, preview_path)
    click.echo('Your wiki preview is ready! navigate to ~{}/wiki'.format(
        os.environ.get('LOGNAME')))
