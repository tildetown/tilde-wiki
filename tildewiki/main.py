import os
import re
from os.path import expanduser
import subprocess

import click
from click import ClickException, Abort
from click.types import Path
from shutil import rmtree

from .click_types import WikiRepo
from .compilation import compile_wiki
from . import git_wrapper as git

# TODO support reading from env
SITE_NAME = 'tilde.town'
PUBLISH_PATH = '/var/www/{site_name}/wiki'.format(site_name=SITE_NAME)
PREVIEW_PATH = expanduser('~/public_html/wiki')
LOCAL_REPOSITORY_PATH = expanduser('~/wiki')
REPOSITORY_PATH = '/wiki'
WIPE_PROMPT = 'This will wipe everything at {}. Proceed?'
LOCK_PATH = '/tmp/tildewiki.lock'

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
    if os.path.exists(os.path.join(local_repo_path)):
        raise ClickException(
            '{} already exists. Have you already run wiki init?'.format(
                local_repo_path))

    if os.path.exists(os.path.join(preview_path)):
        raise ClickException(
            '{} already exists. Have you already run wiki init?'.format(
                preview_path))

    click.echo('Cloning {} to {}...'.format(config.repo_path, local_repo_path))
    git.create_repo(
        config.repo_path,
        config.local_repo_path,
        config.author_name,
        config.author_email
    )

    click.echo('Creating {}...'.format(preview_path))
    os.makedirs(preview_path)

    click.echo('Compiling wiki preview for the first time...')
    _preview(preview_path, local_repo_path)

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
    click.confirm(
        WIPE_PROMPT.format(preview_path),
        abort=True)
    clear_directory(preview_path)
    _preview(preview_path, local_repo_path)

@main.command()
@click.option('--local-repo-path', default=LOCAL_REPOSITORY_PATH,
              help='Path to local clone of wiki repository.', type=WikiRepo(**DEFAULT_PATH_KWARGS))
@pass_config
def publish(config, local_repo_path):
    if os.path.exists(LOCK_PATH):
        raise ClickException('The wiki lock file already exists. Seems like someone else is compiling.')

    rm_error_paths = []
    onerror = lambda f,p,e: rm_error_paths.append(p)
    error = None
    lockf = open(LOCK_PATH, 'w')
    try:
        click.echo('Committing your changes locally...')
        git.make_commit(local_repo_path, config.author_name, config.author_email)
        git.pull_from_origin(local_repo_path)

        click.echo('Pushing your changes...')
        git.push_all(local_repo_path)

        click.echo('Compiling wiki to {}'.format(config.publish_path))
        click.confirm(WIPE_PROMPT.format(config.publish_path), abort=True)
        clear_directory(config.publish_path)
        compile_wiki(config.repo_path, config.publish_path)
    except ClickException:
        raise
    except Abort:
        raise
    except Exception as e:
        error = e
    finally:
        lockf.close()
        try:
            os.remove(LOCK_PATH)
        except FileNotFoundError:
            pass

    if error is not None:
        raise ClickException('Failed publishing wiki. Error: {}'.format(error))

@main.command()
@click.option('--preview', help='show pages from your local wiki', is_flag=True)
@click.option('--preview-path', default=PREVIEW_PATH,
              help='Local path to wiki for previewing.', type=Path(file_okay=False))
@click.argument('path')
@pass_config
def get(config, preview, preview_path, path):
    read_path = config.publish_path
    if preview:
        read_path = preview_path

    path = os.path.join(read_path, path) + '.html'

    subprocess.run(['sensible-browser', path])

@main.command()
@click.option('--local-repo-path', default=LOCAL_REPOSITORY_PATH,
              help='Path to shared wiki git repository.', type=WikiRepo(**DEFAULT_PATH_KWARGS))
@pass_config
def reset(config, local_repo_path):
    raise NotImplementedError()

def _preview(preview_path, local_repo_path):
    compile_wiki(local_repo_path, preview_path)
    click.echo('Your wiki preview is ready! navigate to ~{}/wiki'.format(
        os.environ.get('LOGNAME')))

def clear_directory(path:str) -> None:
    """Given a path to a directory, deletes everything in it. Use with
    caution."""
    if path in ['', '/', '~', '*']:
        raise ValueError('"{}" is not a valid path for clearing'.format(path))

    if not os.path.isdir(path):
        raise ValueError('{} is not a directory'.format(path))

    for root, dirs, files in os.walk(path):
        for f in files:
            os.unlink(os.path.join(root, f))
        for d in dirs:
            rmtree(os.path.join(root, d))

