import os
import re
from datetime import datetime
from shutil import copy
from typing import Optional, Callable

from markdown import markdown

DOUBLE_NEWLINE_RE = re.compile(r'\n\n', flags=re.MULTILINE|re.DOTALL)
HEADER_TITLE_RE = re.compile(r'<h([12])>(.*?)</h\1>')
TITLE_RE = re.compile(r'<title>.*?</title>')
LINK_RE = re.compile(r'href="\/wiki')
SRC_RE = re.compile(r'src="\/wiki')

DEFAULT_ON_CREATE = lambda _: None

def relativize_links(content:str, depth:int) -> str:
    """Given compiled html content, change URLs that start in "/wiki" to be
    relative instead of absolute. Depth indicates how many pairs of dots we
    should use to traverse upward."""
    dots = os.path.join(*['..' for _ in range(depth)])
    href_repl = 'href="{}'.format(os.path.join(dots, 'wiki'))
    src_repl = 'src="{}'.format(os.path.join(dots, 'wiki'))
    out = re.sub(LINK_RE, href_repl, content)
    return re.sub(SRC_RE, src_repl, out)

def depth_from(root: str, path: str) -> int:
    """Given a root path and a path below it, returns how many levels below
    the root the path is."""
    if root == path:
      return 1
    relpath = os.path.relpath(path, root)
    first = os.path.split(relpath)[0]
    depth = 2
    while first != '':
      depth += 1
      first = os.path.split(first)[0]
    return depth

def generate_toc(header_content, articles):
    """given header_content and a list of dicts with keys title, href, and path this function
    generates the toc page's content"""

    toc_content = '{}\n'.format(update_title(header_content, 'table of contents'))

    toplevel_articles = [a for a in articles if a['path'] == '']
    articles = [a for a in articles if a['path'] != '']
    sorted(articles, key=lambda a: a['path'])
    toc_content += '<h1>Table of Contents</h1>\n'
    toc_content += '<h2>unsorted articles</h2>\n<ul>\n'
    for a in toplevel_articles:
        toc_content += '<li><a href="{}">{}</a></li>\n'.format(a['href'], a['title'])

    seen = set()
    for article in articles:
        if article['path'] not in seen:
            path = article['path']
            components = path.split('/')
            hlvl = len(components) + 1
            toc_content += '</ul>'
            toc_content += f'<h{hlvl}>' + path.split('/')[-1] + f'</h{hlvl}>'
            toc_content += '<ul>'
            seen.add(path)
        toc_content += '<li><a href="{href}">{title}</a></li>'.format(**article)

    toc_content += '</ul>'
    return toc_content

def compile_wiki(source_path: str,
                 dest_path: str,
                 on_create: Callable[[str], None]=DEFAULT_ON_CREATE) -> None:
    """Given a source path (presumably a git repository) and a destination
    path, compiles the files found in {source_path}/articles and compiles them all
    to {dest_path}/.

    THIS FUNCTION CLEARS {dest_path}/!

    Be absolutely sure you know what you are doing when you call this ^_^

    If passed, on_create will be called per directory and file created by the
    compiler. The default is to take no action.
    """
    last_compiled = '<hr><p><em>last compiled: {}</em></p>'.format(datetime.utcnow())

    header_content = compile_markdown(os.path.join(source_path, 'src/header.md'))
    footer_content = last_compiled + compile_markdown(os.path.join(source_path, 'src/footer.md'))
    logo_path = os.path.join(source_path, 'src/logo.png')
    css_path = os.path.join(source_path, 'src/main.css')

    articles_root = os.path.join(source_path, 'src/articles')

    articles = []

    copy(logo_path, dest_path)
    copy(css_path, dest_path)

    for source_root, dirs, files in os.walk(articles_root):
        depth = depth_from(articles_root, source_root)
        current_suffix = source_root.replace(articles_root, '')
        if current_suffix and current_suffix[0] == '/':
            current_suffix = current_suffix[1:]

        dest_root = os.path.join(dest_path, current_suffix)

        for directory in dirs:
            dir_path = os.path.join(dest_root, directory)
            os.mkdir(dir_path)
            on_create(dir_path)

        for source_filename in files:
            if source_filename.startswith('.'):
                continue
            source_file_path = os.path.join(source_root, source_filename)
            output = compile_source_file(
                source_file_path,
                header_content,
                footer_content)
            output = relativize_links(output, depth)
            dest_filename = source_filename.split('.')[0] + '.html'
            articles.append({
                'title': dest_filename.split('.')[0],
                'href': os.path.join(current_suffix, dest_filename),
                'path': current_suffix})
            final_path = os.path.join(dest_root, dest_filename)
            with open(final_path, 'w') as f:
                f.write(output)
            on_create(final_path)


    toc_content = generate_toc(header_content, articles)
    toc_path = os.path.join(dest_path, 'toc.html')
    with open(toc_path, 'w') as f:
        f.write(relativize_links(toc_content, 1))
        f.write(footer_content)
    on_create(toc_path)

def slurp(file_path:str) -> str:
    """Convenience function for reading a file and returning its contents."""
    content = None
    with open(file_path, 'r') as f:
        content = f.read()
    return content

def compile_source_file(source_file_path:str, header_content:str, footer_content:str) -> str:
    """Given a path to a source file, this function:
    - picks an appropriate compiler for the file extension
    - compiles the file
    - sandwiches it between the provided header and footer content
    - returns the constructed string
    """
    if not os.path.isabs(source_file_path):
        raise ValueError(
            '{} is not an absolute path.'.format(source_file_path))

    # pick a compiler
    if source_file_path.endswith('.md'):
        compiler = compile_markdown
    elif source_file_path.endswith('.txt'):
        compiler = compile_plaintext
    else:
        # this just copies through any files that we don't recognize as needing
        # conversion.
        compiler = slurp

    content = compiler(source_file_path)

    title = extract_title(content)
    if title is not None:
        header_content = update_title(header_content, title)

    return '{}\n{}\n{}'.format(header_content, content, footer_content)

def update_title(content:str, title:str) -> str:
    """Given a chunk of HTML, finds, updates, and returns the title element to
    be the given title. If there is no title element, the content is returned
    unmodified."""
    return re.sub(TITLE_RE, '<title>{}</title>'.format(title), content)

def extract_title(content:str) -> Optional[str]:
    """Given a string of page content, look for a header in the first line.
    Returns it if found; returns None otherwise."""
    first_line = content.split('\n')[0]
    matches = re.match(HEADER_TITLE_RE, first_line)
    if matches is not None:
        return matches.groups()[1]
    return None

def compile_markdown(file_path:str) -> str:
    """Given a string of markdown, compiles it and returns the result."""
    return markdown(
        slurp(file_path),
        output_format='html5')

def compile_plaintext(file_path:str) -> str:
    output = '<p>\n'
    output += re.sub(
        DOUBLE_NEWLINE_RE,
        '</p><p>',
        slurp(file_path))
    output += '\n</p>\n'
    return output
