#!/usr/bin/env python3

import os
import pprint
import sys
import tempfile

from code2flow.engine import main
from tests.test_graphs import get_edges_set_from_file, get_nodes_set_from_file

DESCRIPTION = """
This file is a tool to generate test cases given a directory
"""

if __name__ == '__main__':
    output_filename = tempfile.NamedTemporaryFile(suffix='.gv').name
    args = sys.argv[1:] + ['--output', output_filename]
    main(args)
    output_file = open(output_filename, 'r')

    generated_edges = get_edges_set_from_file(output_file)
    generated_nodes = get_nodes_set_from_file(output_file)
    directory = os.path.split(sys.argv[1])[-1]

    ret = {
        'test_name': directory,
        'directory': directory,
        'kwargs': sys.argv[2:],
        'expected_edges': list(map(list, generated_edges)),
        'expected_nodes': list(generated_nodes),
    }

    ret = pprint.pformat(ret, sort_dicts=False)
    ret = " " + ret.replace("'", '"')[1:-1]
    print('\n'.join("           " + l for l in ret.split('\n')))
