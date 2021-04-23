import json
import io
import os
import sys

import pygraphviz

sys.path.append(os.getcwd().split('/tests')[0])

from code2flow import code2flow


def test_all():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    with open("expected.json") as f:
        expected_dict = json.loads(f.read())

    for language in os.listdir('test_code'):
        for directory in os.listdir(os.path.join('test_code', language)):
            directory_path = os.path.join('test_code', language, directory)
            output_file = io.StringIO()
            code2flow([directory_path], output_file, language)
            # lang = c2f.LANGUAGES[language]
            # sources, _ = c2f.get_sources_and_language([directory], language)
            # groups, nodes, edges = c2f.engine.map_it(lang, sources)
            # c2f.dotgenerator.write_dot_file(output_file, nodes=nodes,
            #                                 edges=edges, groups=groups)
            generated_edges = get_edges_set_from_file(output_file)
            expected = expected_dict[language][directory]
            assert generated_edges == set(map(tuple, expected['edges']))


def get_edges_set_from_file(dot_file):
    dot_file.seek(0)
    ag = pygraphviz.AGraph(dot_file.read())
    generated_edges = set()
    for edge in ag.edges():
        to_add = (edge[0].attr['name'],
                  edge[1].attr['name'])
        generated_edges.add(to_add)
    return generated_edges
