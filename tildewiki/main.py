"""TODO"""
import os
import re
import sys
from os.path import expanduser
from os.path import exists as path_exists
from os.path import join as path_join

import click
import pygit2
from click import ClickException
from click.types import Path
from markdown import markdown

# TODO support reading from env
SITE_NAME = 'tilde.town'
PUBLISH_PATH = '/var/www/{site_name}/wiki'.format(site_name=SITE_NAME)
PREVIEW_PATH = expanduser('~/public_html/wiki')
LOCAL_REPOSITORY_PATH = expanduser('~/wiki')
REPOSITORY_PATH = '/wiki'

DOUBLE_NEWLINE_RE = re.compile(r'\n\n', flags=re.MULTILINE|re.DOTALL)
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
    click.echo('Cloning {} to {}...'.format(config.repo_path, local_repo_path))
    pygit2.clone_repository(config.repo_path, local_repo_path)
    click.echo('Creating {}...'.format(preview_path))
    os.makedirs(preview_path)
    click.echo('TODO once we have compliation, this will compile')
    click.echo('~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~*~')
    click.echo("Congrats, you are ready to contribute to {}'s wiki!")

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
def preview(config, preview_path, local_repo_path):
    preview_prompt = 'This will wipe everything at {}. Proceed?'
    click.confirm(
        preview_prompt.format(preview_path),
        abort=True)
    compile_wiki(local_repo_path, preview_path)
    # TODO print some stuff about what just happend

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


def compile_wiki(source_path, dest_path):
    """Given a source path (presumably a git repository) and a destination
    path, compiles the files found in {source_path}/articles and compiles them all
    to {dest_path}/.

    THIS FUNCTION CLEARS {dest_path}/!

    Be absolutely sure you know what you are doing when you call this ^_^
    """
    # TODO progress bar
    # TODO recursively delete dest_path (maybe after gzipping, backing up)
    # TODO lockfile on dest_path

    articles_root = path_join(source_path, 'src/articles')

    for root, dirs, files in os.walk(articles_root):
        # given root, i need to "diff" it against articles_root to get whatever
        # point i should be at in preview_root.
        current_suffix = root.replace(articles_root, '')
        if current_suffix and current_suffix[0] == '/':
            current_suffix = current_suffix[1:]
        preview_root = path_join(dest_path, current_suffix)

        for directory in dirs:
            os.mkdir(path_join(preview_root, directory))

        for source_filename in files:
            source_file_path = path_join(root, source_filename)
            output = compile_source_file(source_file_path)
            dest_filename = source_filename.split('.')[0] + '.html'
            with open(path_join(preview_root, dest_filename), 'w') as f:
                f.write(output)

def slurp(file_path):
    content = None
    with open(file_path, 'r') as f:
        content = f.read()
    return content

def compile_source_file(source_file_path):
    if not os.path.isabs(source_file_path):
        raise ValueError(
            '{} is not an absolute path.'.format(source_file_path))

    compiler = None
    if source_file_path.endswith('.md'):
        compiler = compile_markdown
    elif source_file_path.endswith('.txt'):
        compiler = compile_plaintext
    elif source_file_path.endswith('.html'):
        compiler = slurp

    if compiler is None:
        raise ValueError(
            '{} is not a recognized file type.'.format(source_file_path))

    content = compiler(source_file_path)

    # TODO wrap content with header/footer
    # TODO regenerate sitemap? might be error in rfc here

    return content

def compile_markdown(source_file_path):
    return markdown(
        slurp(source_file_path),
        output_format='html5')

def compile_plaintext(source_file_path):
    output = '<p>\n'
    output += re.sub(
        DOUBLE_NEWLINE_RE,
        '</p><p>',
        slurp(source_file_path))
    output += '\n</p>\n'
    return output

