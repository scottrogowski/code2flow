#!/usr/bin/env python3

import io
import os
import pprint
import sys

from code2flow import code2flow
from tests.test_graphs import get_edges_set_from_file, get_nodes_set_from_file

DESCRIPTION = """
This file is a tool to generate test cases given a directory
"""

if __name__ == '__main__':
    filename = sys.argv[1]
    output_file = io.StringIO()
    code2flow(filename, output_file)
    generated_edges = get_edges_set_from_file(output_file)
    generated_nodes = get_nodes_set_from_file(output_file)
    directory = os.path.split(filename)[-1]

    ret = {
        'test_name': directory,
        'directory': directory,
        'expected_edges': list(map(list, generated_edges)),
        'expected_nodes': list(generated_nodes),
    }

    ret = pprint.pformat(ret, sort_dicts=False)
    ret = " " + ret.replace("'", '"')[1:-1]
    print('\n'.join("           " + l for l in ret.split('\n')))
