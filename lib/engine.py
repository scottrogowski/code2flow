import logging
import random

from .model import Edge, SourceCode

# for generating UIDs for groups and nodes
random.seed(42)


def flatten(nested_list):
    """
    Given a list of lists, return a flattened list

    :param list[list] nested_list:
    :rtype: list
    """
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


def _get_groups_from_raw_files(raw_source_by_filename, lang):
    """
    Given a dictionary of raw source files, generate the SourceCode and
    the groups (which includes the nodes) for each file

    :param dict[str, str] raw_source_by_filename:
    :param BaseLang lang:
    :rtype: list[Group]
    """
    file_groups = []
    for filename, raw_source in raw_source_by_filename.items():
        logging.info(f"Processing {filename}...")

        # generate sourcecode (remove comments and add line numbers)
        source_code = SourceCode(raw_source, filename=filename, lang=lang)

        # Create all of the subgroups (classes) and nodes (functions) for this file
        file_group = lang.generate_file_group(filename=filename,
                                              source_code=source_code)
        logging.info("  Extracted %d namespaces and %d functions.",
                     len(file_group.subgroups), len(file_group.all_nodes()))
        file_groups.append(file_group)
    return file_groups


def _exclude_namespaces(groups, exclude_namespaces):
    """
    Exclude namespaces (classes/modules) which match any of the exclude_namespaces

    :param list[Group] groups:
    :param str exclude_namespaces: (comma delimited)
    :rtype: list[Group]
    """
    for namespace in exclude_namespaces.split(','):
        found = False
        for group in list(groups):
            if group.name == namespace:
                groups.remove(group)
                found = True
            for subgroup in list(group.subgroups):
                if subgroup.name == namespace:
                    group.subgroups.remove(subgroup)
                    found = True
        if not found:
            logging.warning(f"Could not exclude namespace '{namespace}' "
                            "because it was not found")
    return groups


def _exclude_functions(groups, exclude_functions):
    """
    Exclude nodes (functions) which match any of the exclude_functions

    :param list[Group] groups:
    :param str exclude_functions: (comma delimited)
    :rtype: list[Group]
    """
    for function_name in exclude_functions.split(','):
        found = False
        for group in list(groups):
            for node in list(group.nodes):
                if node.name == function_name:
                    group.nodes.remove(node)
                    found = True
            for subgroup in list(group.subgroups):
                for node in list(subgroup.nodes):
                    if node.name == function_name:
                        subgroup.nodes.remove(node)
                        found = True
        if not found:
            logging.warning(f"Could not exclude function '{function_name}' "
                            "because it was not found")
    return groups


def map_it(lang, filenames, no_trimming, exclude_namespaces, exclude_functions):
    '''
    Given a language implementation and a list of filenames, do these things:
    1. Read their raw source
    2. Find all groups (classes/modules/etc) and nodes (functions) in all sources
    3. Trim out groups without function nodes
    4. Determine what nodes connect to what other nodes
    5. Trim again

    :param BaseLang lang:
    :param list[str] filenames:
    :param bool no_trimming:
    :rtype: (list[Group], list[Node], list[Edge])
    '''

    # 1. Read raw sources
    raw_source_by_filename = {}
    for filename in sorted(filenames):
        with open(filename) as f:
            raw_source_by_filename[filename] = f.read()

    # 2. Find all groups and nodes in all sources
    file_groups = _get_groups_from_raw_files(raw_source_by_filename, lang)
    if exclude_namespaces:
        file_groups = _exclude_namespaces(file_groups, exclude_namespaces)
    if exclude_functions:
        file_groups = _exclude_functions(file_groups, exclude_functions)

    all_nodes = flatten(g.all_nodes() for g in file_groups)

    # 3. Trim groups without nodes
    if not no_trimming:
        logging.info("Trimming namespaces without functions...")
        lang.trim_groups(file_groups)

    # 4. Figure out what functions map to what
    logging.info("Generating edges...")
    edges = _generate_edges(all_nodes)

    # 5. Trim nodes that didn't connect to anything
    if no_trimming:
        final_nodes = all_nodes
    else:
        final_nodes = []
        for node in all_nodes:
            # final_nodes.append(node)
            if not lang.is_extraneous(node, edges):
                final_nodes.append(node)
            else:
                node.parent.nodes.remove(node)

    return file_groups, final_nodes, edges
