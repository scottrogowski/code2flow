#!/usr/bin/env python3

import io
import pprint
import sys

from tests.test_graphs import get_edges_set_from_file

from code2flow import code2flow

DESCRIPTION = """
This file is a tool to generate test cases given a directory
"""

if __name__ == '__main__':
    filename = sys.argv[1]
    output_file = io.StringIO()
    code2flow([filename], output_file)
    generated_edges = get_edges_set_from_file(output_file)

    ret = {
        filename.rsplit('/', 1)[1]: {
            'edges': list(map(list, generated_edges))
        }
    }
    ret = pprint.pformat(ret)
    ret = " " + ret.replace("'", '"')[1:-1]
    print('\n'.join("       " + l for l in ret.split('\n')))
    # print(json.dumps(ret, indent=4))
