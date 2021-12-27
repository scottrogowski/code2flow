import io
import os
import sys

import pygraphviz
import pytest

sys.path.append(os.getcwd().split('/tests')[0])

from code2flow.engine import code2flow, LanguageParams, SubsetParams
from tests.testdata import testdata

LANGUAGES = (
    'py',
    'js',
    'mjs',
    'rb',
    'php',
)

flattened_tests = {}
for lang, tests in testdata.items():
    if lang not in LANGUAGES:
        continue
    for test_dict in tests:
        flattened_tests[lang + ': ' + test_dict['test_name']] = (lang, test_dict)


def _edge(tup):
    return f"{tup[0]}->{tup[1]}"


def assert_eq(seq_a, seq_b):
    try:
        assert seq_a == seq_b
    except AssertionError:
        print("generated", file=sys.stderr)
        for el in seq_a:
            print(_edge(el), file=sys.stderr)
        print("expected", file=sys.stderr)
        for el in seq_b:
            print(_edge(el), file=sys.stderr)

        extra = seq_a - seq_b
        missing = seq_b - seq_a
        if extra:
            print("extra", file=sys.stderr)
            for el in extra:
                print(_edge(el), file=sys.stderr)
        if missing:
            print("missing", file=sys.stderr)
            for el in missing:
                print(_edge(el), file=sys.stderr)

        sys.stderr.flush()
        raise AssertionError()


@pytest.mark.parametrize("test_tup", flattened_tests)
def test_all(test_tup):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    (language, test_dict) = flattened_tests[test_tup]
    print("Running test %r..." % test_dict['test_name'])
    directory_path = os.path.join('test_code', language, test_dict['directory'])
    kwargs = test_dict.get('kwargs', {})
    kwargs['lang_params'] = LanguageParams(kwargs.pop('source_type', 'script'),
                                           kwargs.pop('ruby_version', '27'))
    kwargs['subset_params'] = SubsetParams.generate(kwargs.pop('target_function', ''),
                                                    int(kwargs.pop('upstream_depth', 0)),
                                                    int(kwargs.pop('downstream_depth', 0)))
    output_file = io.StringIO()
    code2flow([directory_path], output_file, language, **kwargs)

    generated_edges = get_edges_set_from_file(output_file)
    print("generated_edges eq", file=sys.stderr)
    assert_eq(generated_edges, set(map(tuple, test_dict['expected_edges'])))

    generated_nodes = get_nodes_set_from_file(output_file)
    print("generated_nodes eq", file=sys.stderr)
    assert_eq(generated_nodes, set(test_dict['expected_nodes']))


def get_nodes_set_from_file(dot_file):
    dot_file.seek(0)
    ag = pygraphviz.AGraph(dot_file.read())
    generated_nodes = []
    for node in ag.nodes():
        if not node.attr['name']:
            # skip the first which is a legend
            continue
        generated_nodes.append(node.attr['name'])
    ret = set(generated_nodes)
    assert_eq(set(list(ret)), set(generated_nodes))  # assert no dupes
    return ret


def get_edges_set_from_file(dot_file):
    dot_file.seek(0)
    ag = pygraphviz.AGraph(dot_file.read())
    generated_edges = []
    for edge in ag.edges():
        to_add = (edge[0].attr['name'],
                  edge[1].attr['name'])
        generated_edges.append(to_add)
    ret = set(generated_edges)
    assert_eq(set(list(ret)), set(generated_edges))  # assert no dupes
    return ret
