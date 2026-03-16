import re
from dataclasses import dataclass

@dataclass
class PathContext:
    author: str = ''
    title: str = ''
    series: str = ''
    series_position: str = ''
    year: str = ''
    isbn: str = ''
    language: str = ''
    format: str = ''
    edition: str = ''
    original_name: str = ''

# Token syntax: {TokenName} or {TokenName:30} for truncation
TOKEN_RE = re.compile(r'\{(\w[\w ]*?)(?::(-?\d+))?\}')

def _sanitize_filename(name: str) -> str:
    # Remove characters invalid in file paths
    name = re.sub(r'[<>:"/\\|?*]', '', name).strip()
    # Strip trailing dots but preserve truncation ellipsis
    if not name.endswith('...'):
        name = name.rstrip('.')
    return name

def _resolve_token(name: str, ctx: PathContext) -> str:
    mapping = {
        'Author': ctx.author,
        'Author SortName': _sort_name(ctx.author),
        'Title': ctx.title,
        'Series': ctx.series,
        'SeriesPosition': ctx.series_position,
        'Year': ctx.year,
        'ISBN': ctx.isbn,
        'Language': ctx.language,
        'Format': ctx.format,
        'Edition': ctx.edition,
        'OriginalName': ctx.original_name,
    }
    return mapping.get(name, '')

def _sort_name(name: str) -> str:
    parts = name.rsplit(' ', 1)
    if len(parts) == 2:
        return f'{parts[1]}, {parts[0]}'
    return name

def _process_conditionals(template: str, ctx: PathContext) -> str:
    """Parse {Token?content} with balanced braces so content can contain {Token} refs."""
    result = []
    i = 0
    while i < len(template):
        if template[i] == '{':
            # Check if this is a conditional: {Word?
            m = re.match(r'\{(\w+)\?', template[i:])
            if m:
                token_name = m.group(1)
                # Find the matching closing brace with brace counting
                start = i + len(m.group(0))
                depth = 1
                j = start
                while j < len(template) and depth > 0:
                    if template[j] == '{':
                        depth += 1
                    elif template[j] == '}':
                        depth -= 1
                    j += 1
                content = template[start:j - 1]
                value = _resolve_token(token_name, ctx)
                if value:
                    content = TOKEN_RE.sub(
                        lambda tm: _truncate(_resolve_token(tm.group(1), ctx), tm.group(2)),
                        content,
                    )
                    result.append(content)
                i = j
                continue
        result.append(template[i])
        i += 1
    return ''.join(result)

def render_path(template: str, ctx: PathContext) -> str:
    result = template

    # Process conditionals first: {Series?{Series}/}
    # Uses a balanced-brace parser to handle nested {Token} refs inside conditionals
    result = _process_conditionals(result, ctx)

    # Process remaining tokens
    def replace_token(m):
        value = _resolve_token(m.group(1), ctx)
        return _truncate(value, m.group(2))

    result = TOKEN_RE.sub(replace_token, result)

    # Clean up double slashes and sanitize each path component
    parts = [_sanitize_filename(p) for p in result.split('/') if p.strip()]
    return '/'.join(parts)

def _truncate(value: str, length_str: str | None) -> str:
    if not length_str or not value:
        return value
    length = int(length_str)
    if length > 0 and len(value) > length:
        return value[:length-3] + '...'
    elif length < 0 and len(value) > abs(length):
        return '...' + value[length+3:]
    return value

DEFAULT_TEMPLATES = {
    'ebook': '{Author}/{Series?{Series}/{SeriesPosition} - }{Title}',
    'audiobook': '{Author}/{Series?{Series}/{SeriesPosition} - }{Title}',
    'comic': '{Author}/{Series?{Series}/}{Title}',
}
