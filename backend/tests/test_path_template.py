import pytest
import importlib.util
import sys
from pathlib import Path

# Direct import to avoid app.services.__init__ pulling in unrelated dependencies
_spec = importlib.util.spec_from_file_location(
    'path_template_service',
    Path(__file__).resolve().parent.parent / 'app' / 'services' / 'path_template_service.py',
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
render_path = _mod.render_path
PathContext = _mod.PathContext

def test_basic_tokens():
    ctx = PathContext(author='Brandon Sanderson', title='The Way of Kings', year='2010')
    result = render_path('{Author}/{Title} ({Year})', ctx)
    assert result == 'Brandon Sanderson/The Way of Kings (2010)'

def test_series_conditional_present():
    ctx = PathContext(author='Brandon Sanderson', title='The Way of Kings', series='The Stormlight Archive', series_position='1')
    result = render_path('{Author}/{Series?{Series}/{SeriesPosition} - }{Title}', ctx)
    assert result == 'Brandon Sanderson/The Stormlight Archive/1 - The Way of Kings'

def test_series_conditional_absent():
    ctx = PathContext(author='Brandon Sanderson', title='Elantris')
    result = render_path('{Author}/{Series?{Series}/{SeriesPosition} - }{Title}', ctx)
    assert result == 'Brandon Sanderson/Elantris'

def test_truncation():
    ctx = PathContext(title='A Very Long Book Title That Should Be Truncated')
    result = render_path('{Title:20}', ctx)
    assert len(result) <= 20
    assert result.endswith('...')

def test_sort_name():
    ctx = PathContext(author='Brandon Sanderson', title='Test')
    result = render_path('{Author SortName}/{Title}', ctx)
    assert result == 'Sanderson, Brandon/Test'

def test_sanitize_special_chars():
    ctx = PathContext(author='Author: Name?', title='Title <Bad>')
    result = render_path('{Author}/{Title}', ctx)
    assert ':' not in result
    assert '<' not in result
    assert '>' not in result

def test_empty_tokens_collapse():
    ctx = PathContext(author='Author', title='Title')
    result = render_path('{Author}/{Series?{Series}/}{Title}', ctx)
    assert '//' not in result

def test_language_and_edition():
    ctx = PathContext(author='Author', title='Book', language='no', edition='Norwegian')
    result = render_path('{Author}/{Title} [{Language}]', ctx)
    assert result == 'Author/Book [no]'
