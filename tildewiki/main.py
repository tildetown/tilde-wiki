"""TODO"""
import os
import sys
from os.path import expanduser
from os.path import exists as path_exists
from os.path import join as path_join

import click
import pygit2
from click import ClickException
from click.types import Path

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

class GitRepo(Path):
    name = 'git repository'

    def convert(self, value, param, ctx):
        path = super().convert(value, param, ctx)
        if not path_exists(path_join(path, '.git')):
            self.fail('No .git directory found in {}'.format(path))

        return path


class WikiRepo(GitRepo):
    name = 'wiki repository'

    def convert(self, value, param, ctx):
        path = super().convert(value, param, ctx)

        if not path_exists(path_join(path, 'src/articles')):
            self.fail(
                '{} does not appear to be a wiki repository; missing src/articles.'.format(
                path))

        return path


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
              type=Path(**DEFAULT_PATH_KWARGS))
@click.option('--repo-path',
              default=REPOSITORY_PATH,
              help='Path to your clone of the shared git repository.',
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
@click.option('--local-repo-path',
              default=LOCAL_REPOSITORY_PATH,
              help='Path to shared wiki git repository.',
              type=Path(file_okay=False))
@click.option('--preview-path',
              default=PREVIEW_PATH,
              help='Local path to wiki for previewing.',
              type=Path(file_okay=False))
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
    pygit2.clone_repository(
        config.repo_path,
        local_repo_path
    )

@main.command()
@click.option('--local-repo-path',
              default=LOCAL_REPOSITORY_PATH,
              help='Path to shared wiki git repository.',
              type=WikiRepo(**DEFAULT_PATH_KWARGS))
@click.option('--preview-path',
              default=PREVIEW_PATH,
              help='Local path to wiki for previewing.',
              type=Path(**DEFAULT_PATH_KWARGS))
@pass_config
def preview(config, local_repo_path):
    raise NotImplementedError()

@main.command()
@click.option('--local-repo-path',
              default=LOCAL_REPOSITORY_PATH,
              help='Path to shared wiki git repository.',
              type=WikiRepo(**DEFAULT_PATH_KWARGS))
@pass_config
def publish(config, local_repo_path):
    raise NotImplementedError()

@main.command()
@pass_config
def get(config):
    raise NotImplementedError()

@main.command()
@click.option('--local-repo-path',
              default=LOCAL_REPOSITORY_PATH,
              help='Path to shared wiki git repository.',
              type=WikiRepo(**DEFAULT_PATH_KWARGS))
@pass_config
def reset(config, local_repo_path):
    raise NotImplementedError()
