import json
import logging
import os
import shutil
import sys

import pytest

sys.path.append(os.getcwd().split('/tests')[0])

from lib.engine import code2flow
from lib import model

IMG_PATH = '/tmp/code2flow/output.png'
if os.path.exists("/tmp/code2flow"):
    shutil.rmtree('/tmp/code2flow')
os.mkdir('/tmp/code2flow')

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def test_generate_image():
    if os.path.exists(IMG_PATH):
        os.remove(IMG_PATH)
    code2flow(os.path.abspath(__file__),
              output_file=IMG_PATH,
              hide_legend=True)
    assert os.path.exists(IMG_PATH)
    os.remove(IMG_PATH)
    code2flow(os.path.abspath(__file__),
              output_file=IMG_PATH,
              hide_legend=False)
    assert os.path.exists(IMG_PATH)


def test_not_installed():
    if os.path.exists(IMG_PATH):
        os.remove(IMG_PATH)
    tmp_path = os.environ['PATH']
    os.environ['PATH'] = ''
    with pytest.raises(AssertionError):
        code2flow(os.path.abspath(__file__),
                  output_file=IMG_PATH)
    os.environ['PATH'] = tmp_path


def test_invalid_extension():
    with pytest.raises(AssertionError):
        code2flow(os.path.abspath(__file__),
                  output_file='out.pdf')


def test_no_files():
    with pytest.raises(AssertionError):
        code2flow(os.path.abspath(__file__) + "fakefile",
                  output_file=IMG_PATH)


def test_no_files_2():
    if not os.path.exists('/tmp/code2flow/no_source_dir'):
        os.mkdir('/tmp/code2flow/no_source_dir')
    if not os.path.exists('/tmp/code2flow/no_source_dir/fakefile'):
        with open('/tmp/code2flow/no_source_dir/fakefile', 'w') as f:
            f.write("hello world")

    with pytest.raises(AssertionError):
        code2flow('/tmp/code2flow/no_source_dir',
                  output_file=IMG_PATH)

    with pytest.raises(AssertionError):
        code2flow('/tmp/code2flow/no_source_dir',
                  language='py',
                  output_file=IMG_PATH)


def test_json():
    code2flow('test_code/py/simple_b',
              output_file='/tmp/code2flow/out.json',
              hide_legend=False)
    with open('/tmp/code2flow/out.json') as f:
        jobj = json.loads(f.read())
    assert set(jobj.keys()) == {'graph'}
    assert set(jobj['graph'].keys()) == {'nodes', 'edges', 'directed'}
    assert jobj['graph']['directed'] is True
    assert isinstance(jobj['graph']['nodes'], dict)
    assert len(jobj['graph']['nodes']) == 4
    assert set(n['name'] for n in jobj['graph']['nodes'].values()) == {'simple_b::a', 'simple_b::(global)', 'simple_b::c.d', 'simple_b::b'}

    assert isinstance(jobj['graph']['edges'], list)
    assert len(jobj['graph']['edges']) == 4
    assert len(set(n['source'] for n in jobj['graph']['edges'])) == 4
    assert len(set(n['target'] for n in jobj['graph']['edges'])) == 3


def test_repr():
    module = model.Group('my_file', model.GROUP_TYPE.FILE, [], 0)
    group = model.Group('Obj', model.GROUP_TYPE.CLASS, [], 0)
    call = model.Call('tostring', 'obj', 42)
    variable = model.Variable('the_string', call, 42)
    node_a = model.Node('tostring', [], [], [], 13, group)
    node_b = model.Node('main', [call], [], [], 59, module)
    edge = model.Edge(node_b, node_a)
    print(module)
    print(group)
    print(call)
    print(variable)
    print(node_a)
    print(node_b)
    print(edge)


def test_bad_acorn(mocker, caplog):
    caplog.set_level(logging.DEBUG)
    mocker.patch('lib.javascript.get_acorn_version', return_value=b'7.6.9')
    code2flow("test_code/js/simple_a_js", "/tmp/code2flow/out.json")
    assert "Acorn" in caplog.text and "8.*" in caplog.text


def test_bad_ruby_parse(mocker):
    mocker.patch('subprocess.check_output', return_value=b'blah blah')
    with pytest.raises(AssertionError) as ex:
        code2flow("test_code/rb/simple_b", "/tmp/code2flow/out.json")
        assert "ruby-parse" in ex and "syntax" in ex


def test_bad_php_parse_a():
    with pytest.raises(AssertionError) as ex:
        code2flow("test_code/php/bad_php/bad_php_a.php", "/tmp/code2flow/out.json")
        assert "parse" in ex and "syntax" in ex


def test_bad_php_parse_b():
    with pytest.raises(AssertionError) as ex:
        code2flow("test_code/php/bad_php/bad_php_b.php", "/tmp/code2flow/out.json")
        assert "parse" in ex and "php" in ex.lower()


# import functools
# def test_bad_php_parse_c(mocker):
#     mocker.patch('lib.php.run_ast_parser', return_value=b'', side_effect=subprocess.CalledProcessError)  # functools.partial(subprocess.CalledProcessError, '', ''))
#     with pytest.raises(AssertionError) as ex:
#         code2flow("test_code/rb/simple_b", "/tmp/code2flow/out.json")
#         # assert "composer" in ex


def test_no_source_type():
    with pytest.raises(AssertionError):
        code2flow('test_code/js/exclude_modules_es6',
                  output_file='/tmp/code2flow/out.json',
                  hide_legend=False)
