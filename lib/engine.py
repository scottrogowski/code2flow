import logging
import random

from .model import Edge, SourceCode

# for generating UIDs for groups and nodes
random.seed(42)


def flatten(nested_list):
    return [el for sublist in nested_list for el in sublist]


def _generate_edges(nodes):
    '''
    When a function calls another function, that is an edge
    This is in the global scope because edges can exist between any node and not just between groups
    '''
    edges = []
    dup_names = set()
    for node0 in nodes:
        for node1 in nodes:
            # logging.info(f'"{node0.name}" links to "{node1.name}"?')
            does_link, dup_name = node0.links_to(node1, nodes)
            dup_names.add(dup_name)
            if does_link:
                # logging.info("Yes. Edge created")
                edges.append(Edge(node0, node1))
    dup_names = sorted(filter(None, list(dup_names)))
    logging.warning("WARNING: Could not link %d duplicate function identifiers "
                    "%r. Code2flow works by matching function identifiers. For "
                    "better results, make your function names unique.", len(dup_names), dup_names)
    return edges


def _get_char_to_line_map(string_data):
    line_number = 1
    char_to_line_map = {}
    for i, c in enumerate(string_data):
        char_to_line_map[i] = line_number
        if c == '\n':
            line_number += 1
    return char_to_line_map


def _get_groups_from_raw_files(raw_source_by_filename, lang):
    """

    """
    file_groups = []
    for filename, raw_source in raw_source_by_filename.items():
        # remove .py from filename
        logging.info(f"Processing {filename}...")

        # generate sourcecode (remove comments and add line numbers)
        source_code = SourceCode(raw_source, filename=filename, lang=lang)

        # Create all of the subgroups (classes) and nodes (functions) for this file
        file_group = lang.generate_file_group(name=filename,
                                              source_code=source_code,
                                              lang=lang)
        logging.info("  Extracted %d namespaces and %d functions.",
                     len(file_group.subgroups), len(file_group.all_nodes()))
        file_groups.append(file_group)
    return file_groups


def map_it(lang, filenames, no_trimming):
    '''
    I. For each file passed,
        1. Generate the sourcecode for that file
        2. Generate a group from that file's sourcecode
            a. The group init will recursively generate all of the subgroups and function nodes for that file
    II.  Trim the groups bascially removing those which have no function nodes
    III. Generate the edges
    IV.  Return the file groups, function nodes, and edges
    '''

    # get the filename and the file_raw_source
    # only first file for now

    raw_source_by_filename = {}
    for filename in sorted(filenames):
        with open(filename) as f:
            raw_source_by_filename[filename] = f.read()

    file_groups = _get_groups_from_raw_files(raw_source_by_filename, lang)
    nodes = flatten(g.all_nodes() for g in file_groups)

    # Trimming the groups mostly removes those groups with no function nodes
    if not no_trimming:
        logging.info("Trimming namespaces without functions...")
        lang.trim_groups(file_groups)

    # Figure out what functions map to what
    logging.info("Generating edges...")
    edges = _generate_edges(nodes)

    # Trim off the nodes (mostly global-frame nodes that don't do anything)
    if no_trimming:
        final_nodes = nodes
    else:
        final_nodes = []
        for node in nodes:
            # final_nodes.append(node)
            if not lang.is_extraneous(node, edges):
                final_nodes.append(node)
            else:
                node.parent.nodes.remove(node)

    # return everything we have done
    return file_groups, final_nodes, edges
