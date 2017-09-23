import os
import re
from datetime import datetime
from os.path import join as path_join

from markdown import markdown

DOUBLE_NEWLINE_RE = re.compile(r'\n\n', flags=re.MULTILINE|re.DOTALL)
HEADER_TITLE_RE = re.compile(r'<h([12])>(.*?)</h\1>')
TITLE_RE = re.compile(r'<title>.*?</title>')

def compile_wiki(source_path: str, dest_path: str) -> None:
    """Given a source path (presumably a git repository) and a destination
    path, compiles the files found in {source_path}/articles and compiles them all
    to {dest_path}/.

    THIS FUNCTION CLEARS {dest_path}/!

    Be absolutely sure you know what you are doing when you call this ^_^
    """
    last_compiled = '<p><em>last compiled: {}</em></p>'.format(datetime.utcnow())

    header_content = compile_markdown(path_join(source_path, 'src/header.md'))
    footer_content = last_compiled + compile_markdown(path_join(source_path, 'src/footer.md'))

    articles_root = path_join(source_path, 'src/articles')

    toc_content = '{}\n<ul>'.format(update_title(header_content, 'table of contents'))

    for root, dirs, files in os.walk(articles_root):
        current_suffix = root.replace(articles_root, '')
        if current_suffix and current_suffix[0] == '/':
            current_suffix = current_suffix[1:]
        preview_root = path_join(dest_path, current_suffix)

        for directory in dirs:
            os.mkdir(path_join(preview_root, directory))

        for source_filename in files:
            source_file_path = path_join(root, source_filename)
            output = compile_source_file(
                source_file_path,
                header_content,
                footer_content)
            dest_filename = source_filename.split('.')[0] + '.html'
            toc_content += '<li><a href="{}">{}</a></li>\n'.format(
                path_join(current_suffix, dest_filename),
                path_join(current_suffix,dest_filename.split('.')[0]))
            with open(path_join(preview_root, dest_filename), 'w') as f:
                f.write(output)

    toc_content += '\n</ul>'
    with open(path_join(dest_path, 'toc.html'), 'w') as f:
        f.write(toc_content)
        f.write(footer_content)

def slurp(file_path):
    content = None
    with open(file_path, 'r') as f:
        content = f.read()
    return content

def compile_source_file(source_file_path, header_content, footer_content):
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

    title = extract_title(content)
    if title is not None:
        header_content = update_title(header_content, title)

    return '{}\n{}\n{}'.format(header_content, content, footer_content)

def update_title(content, title):
    """Given a chunk of HTML, finds, updates, and returns the title element to
    be the given title. If there is no title element, the content is returned
    unmodified."""
    return re.sub(TITLE_RE, '<title>{}</title>'.format(title), content)

def extract_title(content):
    """Given a string of page content, look for a header in the first line.
    Returns it if found; returns None otherwise."""
    first_line = content.split('\n')[0]
    matches = re.match(HEADER_TITLE_RE, first_line)
    if matches is not None:
        return matches.groups()[1]
    return None

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
