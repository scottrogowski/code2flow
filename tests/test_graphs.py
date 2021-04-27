import json
import io
import os
import sys

import pygraphviz

sys.path.append(os.getcwd().split('/tests')[0])

from lib.engine import code2flow


def test_all():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with open("tests.json") as f:
        tests_dict = json.loads(f.read())

    for language, language_tests in tests_dict.items():
        for test_dict in language_tests:
            print("running", test_dict['test_name'])
            directory_path = os.path.join('test_code', language, test_dict['directory'])
            kwargs = test_dict.get('kwargs', {})
            output_file = io.StringIO()
            code2flow([directory_path], output_file, language, **kwargs)

            generated_edges = get_edges_set_from_file(output_file)
            assert generated_edges == set(map(tuple, test_dict['expected_edges']))

            generated_nodes = get_nodes_set_from_file(output_file)
            assert generated_nodes == set(test_dict['expected_nodes'])


def get_nodes_set_from_file(dot_file):
    dot_file.seek(0)
    ag = pygraphviz.AGraph(dot_file.read())
    generated_nodes = []
    for node in ag.nodes():
        generated_nodes.append(node.attr['name'])
    ret = set(generated_nodes)
    assert len(ret) == len(generated_nodes)
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
    assert len(ret) == len(generated_edges)
    return ret
