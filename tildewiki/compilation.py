import os
import re
from datetime import datetime
from typing import Optional

from markdown import markdown

DOUBLE_NEWLINE_RE = re.compile(r'\n\n', flags=re.MULTILINE|re.DOTALL)
HEADER_TITLE_RE = re.compile(r'<h([12])>(.*?)</h\1>')
TITLE_RE = re.compile(r'<title>.*?</title>')
LINK_RE = re.compile(r'\/wiki')

def update_header_links(header_content:str) -> str:
    """Given compiled header content, change absolute URLs in the header to be
    relative to the root URL. this is a dirty hack to save links during
    preview."""
    return re.sub(LINK_RE, '../wiki', header_content)

def compile_wiki(source_path: str, dest_path: str) -> None:
    """Given a source path (presumably a git repository) and a destination
    path, compiles the files found in {source_path}/articles and compiles them all
    to {dest_path}/.

    THIS FUNCTION CLEARS {dest_path}/!

    Be absolutely sure you know what you are doing when you call this ^_^
    """
    last_compiled = '<p><em>last compiled: {}</em></p>'.format(datetime.utcnow())

    header_content = update_header_links(compile_markdown(os.path.join(source_path, 'src/header.md')))
    footer_content = last_compiled + compile_markdown(os.path.join(source_path, 'src/footer.md'))

    # TODO fix any links in header/footer to work with preview path

    articles_root = os.path.join(source_path, 'src/articles')

    toc_content = '{}\n<ul>'.format(update_title(header_content, 'table of contents'))

    for source_root, dirs, files in os.walk(articles_root):
        current_suffix = source_root.replace(articles_root, '')
        if current_suffix and current_suffix[0] == '/':
            current_suffix = current_suffix[1:]

        dest_root = os.path.join(dest_path, current_suffix)

        for directory in dirs:
            os.mkdir(os.path.join(dest_root, directory))

        for source_filename in files:
            source_file_path = os.path.join(source_root, source_filename)
            output = compile_source_file(
                source_file_path,
                header_content,
                footer_content)
            dest_filename = source_filename.split('.')[0] + '.html'
            toc_content += '<li><a href="{}">{}</a></li>\n'.format(
                os.path.join(current_suffix, dest_filename),
                os.path.join(current_suffix,dest_filename.split('.')[0]))
            with open(os.path.join(dest_root, dest_filename), 'w') as f:
                f.write(output)

    toc_content += '\n</ul>'
    with open(os.path.join(dest_path, 'toc.html'), 'w') as f:
        f.write(toc_content)
        f.write(footer_content)

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

    compiler = None
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

def compile_markdown(source_file_path:str) -> str:
    """Given a string of markdown, compiles it and returns the result."""
    return markdown(
        slurp(source_file_path),
        output_format='html5')

def compile_plaintext(source_file_path:str) -> str:
    output = '<p>\n'
    output += re.sub(
        DOUBLE_NEWLINE_RE,
        '</p><p>',
        slurp(source_file_path))
    output += '\n</p>\n'
    return output
