import json
import locale
import logging
import os
import shutil
import sys

import pytest

sys.path.append(os.getcwd().split('/tests')[0])

from code2flow.engine import code2flow, main, _generate_graphviz, SubsetParams
from code2flow import model

IMG_PATH = '/tmp/code2flow/output.png'
if os.path.exists("/tmp/code2flow"):
    try:
        shutil.rmtree('/tmp/code2flow')
    except FileNotFoundError:
        os.remove('/tmp/code2flow')
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


def test_graphviz_error(caplog):
    caplog.set_level(logging.DEBUG)
    _generate_graphviz("/tmp/code2flow/nothing", "/tmp/code2flow/nothing",
                       "/tmp/code2flow/nothing")
    assert "non-zero exit" in caplog.text


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


def test_weird_encoding():
    """
    To address https://github.com/scottrogowski/code2flow/issues/28
    The windows user had an error b/c their default encoding was cp1252
    and they were trying to read a unicode file with emojis
    I don't have that installed but was able to reproduce by changing to
    US-ASCII which I assume is a little more universal anyway.
    """

    locale.setlocale(locale.LC_ALL, 'en_US.US-ASCII')
    code2flow('test_code/py/weird_encoding',
              output_file='/tmp/code2flow/out.json',
              hide_legend=False)
    with open('/tmp/code2flow/out.json') as f:
        jobj = json.loads(f.read())
    assert set(jobj.keys()) == {'graph'}


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
    mocker.patch('code2flow.javascript.get_acorn_version', return_value='7.6.9')
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


def test_no_source_type():
    with pytest.raises(AssertionError):
        code2flow('test_code/js/exclude_modules_es6',
                  output_file='/tmp/code2flow/out.json',
                  hide_legend=False)


def test_cli_no_args(capsys):
    with pytest.raises(SystemExit):
        main([])
    assert 'the following arguments are required' in capsys.readouterr().err


def test_cli_verbose_quiet(capsys):
    with pytest.raises(AssertionError):
        main(['test_code/py/simple_a', '--verbose', '--quiet'])


def test_cli_log_default(mocker):
    logging.basicConfig = mocker.MagicMock()
    main(['test_code/py/simple_a'])
    logging.basicConfig.assert_called_once_with(format="Code2Flow: %(message)s",
                                                level=logging.INFO)


def test_cli_log_verbose(mocker):
    logging.basicConfig = mocker.MagicMock()
    main(['test_code/py/simple_a', '--verbose'])
    logging.basicConfig.assert_called_once_with(format="Code2Flow: %(message)s",
                                                level=logging.DEBUG)


def test_cli_log_quiet(mocker):
    logging.basicConfig = mocker.MagicMock()
    main(['test_code/py/simple_a', '--quiet'])
    logging.basicConfig.assert_called_once_with(format="Code2Flow: %(message)s",
                                                level=logging.WARNING)

def test_subset_cli(mocker):
    with pytest.raises(AssertionError):
        SubsetParams.generate(target_function='', upstream_depth=1, downstream_depth=0)
    with pytest.raises(AssertionError):
        SubsetParams.generate(target_function='', upstream_depth=0, downstream_depth=1)
    with pytest.raises(AssertionError):
        SubsetParams.generate(target_function='test', upstream_depth=0, downstream_depth=0)
    with pytest.raises(AssertionError):
        SubsetParams.generate(target_function='test', upstream_depth=-1, downstream_depth=0)
    with pytest.raises(AssertionError):
        SubsetParams.generate(target_function='test', upstream_depth=0, downstream_depth=-1)

    with pytest.raises(AssertionError):
        main(['test_code/py/subset_find_exception/zero.py', '--target-function', 'func', '--upstream-depth', '1'])

    with pytest.raises(AssertionError):
        main(['test_code/py/subset_find_exception/two.py', '--target-function', 'func', '--upstream-depth', '1'])


