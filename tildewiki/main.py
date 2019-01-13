import os
import stat
import subprocess
from os.path import expanduser

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
REPOSITORY_PATH = '/town/wiki'
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
    """This tool helps manage a wiki that exists as a git repository on a
    social server."""
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
    Initializes a local copy of the shared wiki.
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
    """Compiles all the files in the local wiki repository."""
    click.confirm(
        WIPE_PROMPT.format(preview_path),
        abort=True)
    clear_directory(preview_path)
    _preview(preview_path, local_repo_path)

def _on_create(file_path: str) -> None:
    """This callback takes a path to a file or directory created on disk
    during compilation. We want to make sure that everything we create as part
    of publish compilation is world-writable so the next user can overwrite
    it."""
    flags = stat.S_ISGID
    flags |= stat.S_IWOTH | stat.S_IROTH
    flags |= stat.S_IRUSR | stat.S_IWUSR
    flags |= stat.S_IRGRP | stat.S_IWGRP
    if os.path.isdir(file_path):
        flags |= stat.S_IXOTH | stat.S_IXGRP | stat.S_IXUSR
    os.chmod(file_path, flags)

@main.command()
@click.option('--local-repo-path', default=LOCAL_REPOSITORY_PATH,
              help='Path to local clone of wiki repository.', type=WikiRepo(**DEFAULT_PATH_KWARGS))
@pass_config
def publish(config, local_repo_path):
    """Commits any local changes, syncs with the shared wiki repository (in
    both directions), and recompiles the shared wiki."""
    if os.path.exists(LOCK_PATH):
        raise ClickException('The wiki lock file already exists. Seems like someone else is compiling.')

    rm_error_paths = []
    error = None
    lockf = open(LOCK_PATH, 'w')
    try:
        click.echo('Committing your changes locally...')
        git.make_commit(local_repo_path, config.author_name, config.author_email)
        git.pull_from_origin(local_repo_path)

        click.echo('Pushing your changes...')
        git.push_hard(local_repo_path, config.repo_path)

        click.echo('Compiling wiki to {}'.format(config.publish_path))
        click.confirm(WIPE_PROMPT.format(config.publish_path), abort=True)
        clear_directory(config.publish_path)
        compile_wiki(config.repo_path, config.publish_path, on_create=_on_create)
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
    """Given a path to a file in the wiki, open it in a browser. Uses
    sensible-browser. No need to specify the extension; e.g., 'wiki get
    editors/emacs' will show /wiki/editors/emacs.html in the browser."""
    read_path = config.publish_path
    if preview:
        read_path = preview_path

    path = os.path.join(read_path, path)
    if os.path.exists(path)\
       and os.path.isdir(path)\
       and os.path.exists(os.path.join(path, 'index.html')):
        path = os.path.join(path, 'index.html')
    elif os.path.exists(path + '.html'):
        path = path + '.html'
    else:
        raise ClickException("Couldn't find path {}".format(path))

    subprocess.run(['sensible-browser', path])

@main.command()
@click.option('--local-repo-path', default=LOCAL_REPOSITORY_PATH,
              help='Path to shared wiki git repository.', type=WikiRepo(**DEFAULT_PATH_KWARGS))
@pass_config
def sync(config, local_repo_path):
    """Syncs a local copy of the wiki with the shared copy. Resets any
    outstanding changes. If those changes should be kept, publish them
    first."""
    if git.dirty(local_repo_path):
        click.confirm("This will overwrite any changes you've made locally. Proceed?", abort=True)
    git.reset_from_origin(local_repo_path)

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

