import sys
import os

import pytest

sys.path.append(os.getcwd().split('/tests')[0])

from lib.engine import code2flow

IMG_PATH = '/tmp/output.png'


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
    if not os.path.exists('/tmp/no_source_dir'):
        os.mkdir('/tmp/no_source_dir')
    if not os.path.exists('/tmp/no_source_dir/fakefile'):
        with open('/tmp/no_source_dir/fakefile', 'w') as f:
            f.write("hello world")

    with pytest.raises(AssertionError):
        code2flow('/tmp/no_source_dir',
                  output_file=IMG_PATH)

    with pytest.raises(AssertionError):
        code2flow('/tmp/no_source_dir',
                  language='py',
                  output_file=IMG_PATH)
