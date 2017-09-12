from os.path import exists as path_exists
from os.path import join as path_join

from click.types import Path

class GitRepo(Path):
    name = 'git repository'

    def convert(self, value, param, ctx):
        path = super().convert(value, param, ctx)
        if not path_exists(path_join(path, '.git')):
            self.fail('No .git directory found in {}'.format(path))

        return path


class WikiRepo(GitRepo):
    name = 'wiki repository'
    invalid_wiki_error = '{} does not appear to be a wiki repository: missing {}'

    def convert(self, value, param, ctx):
        path = super().convert(value, param, ctx)

        for filepath in ('articles', 'header.md', 'footer.md'):
            test_path = path_join('src', filepath)
            if not path_exists(path_join(path, test_path)):
                self.fail(self.invalid_wiki_error.format(
                    path, test_path))

        return path
