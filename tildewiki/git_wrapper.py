import git as gitpython

def reset_from_origin(repo_path:str) -> None:
    repo = gitpython.Repo(repo_path)
    repo.remotes['origin'].fetch()
    repo.git.reset('--hard', 'origin/master')


def create_repo(to_clone, local_path, author_name, author_email):
    origin = gitpython.Repo(to_clone)
    new_repo = origin.clone(local_path)
    with new_repo.config_writer() as cw:
        cw.add_section('user')
        cw.set('user', 'name', author_name)
        cw.set('user', 'email', author_email)

def dirty(repo_path:str):
    repo = gitpython.Repo(repo_path)
    status = repo.git.status()
    return 'nothing to commit, working directory clean' not in status

def make_commit(repo_path, author_name, author_email):
    """Given a path to a repository, adds everything and commits it. If there
    are no unstaged changes, does nothing."""
    if not dirty(repo_path):
        return
    repo = gitpython.Repo(repo_path)
    index = repo.index
    repo.git.add(['--all'])

    actor = gitpython.Actor(author_name, author_email)
    index.commit('wiki update', author=actor, committer=actor)

def push_hard(local_repo_path, remote_repo_path):
    local_repo = gitpython.Repo(local_repo_path)
    local_repo.remotes['origin'].push()
    remote = gitpython.Repo(remote_repo_path)
    remote.git.reset(['--hard', 'HEAD'])

def pull_from_origin(repo_path):
    repo = gitpython.Repo(repo_path)
    repo.remotes['origin'].pull()
