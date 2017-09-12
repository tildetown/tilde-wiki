import git as gitpython
import pygit2

def create_repo(to_clone, local_path, author_name, author_email):
    repo = pygit2.clone_repository(to_clone, local_path)
    repo.config['user.name'] = author_name
    repo.config['user.email'] = author_email


def make_commit(repo_path, author_name, author_email):
    """Given a path to a repository, adds everything and commits it. If there
    are no unstaged changes, does nothing."""
    # TODO do nothing if no changes
    repo = pygit2.Repository(repo_path)
    repo.index.add_all()
    repo.index.write()
    tree = repo.index.write_tree()
    author = pygit2.Signature(author_name, author_email)
    committer = pygit2.Signature(author_name, author_email)
    oid = repo.create_commit(
        'refs/head/master',
        author,
        committer,
        'wiki update'.format(author_name),
        tree,
        [repo.head.get_object().hex])
    repo.reset(oid, pygit2.GIT_RESET_HARD)

# These next two functions use GitPython because libgit2 was having issues with
# a local repo. it sucks. honestly this is a more pleasant interface anyway so
# i might eventually just use GitPython.
def push_all(repo_path):
    repo = gitpython.Repo(repo_path)
    repo.remotes['origin'].push()

def pull_from_origin(repo_path):
    repo = gitpython.Repo(repo_path)
    repo.remotes['origin'].pull()
