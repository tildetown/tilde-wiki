import git as gitpython
import pygit2

# it's fucking weird to be using two different git libraries, i know.
# gitpython:
# - couldn't figure out how to check repo status
# pygit2:
# - had trouble with committing after a merge
# - can't push to local repos
#
# i want to standardize on gitpython, but gotta figure out the repo status and
# also do the cloning

def create_repo(to_clone, local_path, author_name, author_email):
    # TODO port to GitPython
    repo = pygit2.clone_repository(to_clone, local_path)
    repo.config['user.name'] = author_name
    repo.config['user.email'] = author_email

def dirty(repo_path):
    # TODO figure out how to do with GitPython
    repo = pygit2.Repository(repo_path)
    return repo.status() == {}

def make_commit(repo_path, author_name, author_email):
    """Given a path to a repository, adds everything and commits it. If there
    are no unstaged changes, does nothing."""
    if not dirty(repo_path):
        return
    repo = gitpython.Repo(repo_path)
    index = repo.index

    index.add([path for (path, _), __ in index.entries.items()])

    actor = gitpython.Actor(author_name, author_email)
    index.commit('wiki update', author=actor, committer=actor)

def push_all(repo_path):
    repo = gitpython.Repo(repo_path)
    repo.remotes['origin'].push()

def pull_from_origin(repo_path):
    repo = gitpython.Repo(repo_path)
    repo.remotes['origin'].pull()
