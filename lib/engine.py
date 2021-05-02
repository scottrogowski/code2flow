import json
import logging
import os
import subprocess
import time

from .python import Python
from .javascript import Javascript
from .model import TRUNK_COLOR, LEAF_COLOR, EDGE_COLOR, Edge, Group, is_installed

VERSION = '1.0.0'

VALID_EXTENSIONS = {'png', 'svg', 'dot', 'gv', 'json'}

DESCRIPTION = "Generate flow charts from your source code. " \
              "See the README at https://github.com/scottrogowski/code2flow."


LEGEND = """subgraph legend{
    rank = min;
    label = "legend";
    Legend [shape=none, margin=0, label = <
        <table cellspacing="0" cellpadding="0" border="1"><tr><td>Code2flow Legend</td></tr><tr><td>
        <table cellspacing="0">
        <tr><td>Regular function</td><td width="50px"></td></tr>
        <tr><td>Trunk function (nothing calls this)</td><td bgcolor='%s'></td></tr>
        <tr><td>Leaf function (this calls nothing else)</td><td bgcolor='%s'></td></tr>
        <tr><td>Function call</td><td><font color='%s'>&#8594;</font></td></tr>
        </table></td></tr></table>
        >];
}""" % (TRUNK_COLOR, LEAF_COLOR, EDGE_COLOR)


LANGUAGES = {
    'py': Python,
    'js': Javascript,
    # 'php': PHP,
    # 'rb': Ruby,
}


def generate_json(nodes, edges):
    '''
    Generate a json string from nodes and edges
    See https://github.com/jsongraph/json-graph-specification

    :param nodes list[Node]: functions
    :param edges list[Edge]: function calls
    :rtype: str
    '''
    nodes = [n.to_dict() for n in nodes]
    nodes = {n['uid']: n for n in nodes}
    edges = [e.to_dict() for e in edges]

    return json.dumps({"graph": {
        "directed": True,
        "nodes": nodes,
        "edges": edges,
    }})


def write_file(outfile, nodes, edges, groups, hide_legend=False,
               no_grouping=False, as_json=False):
    '''
    Write a dot file that can be read by graphviz

    :param outfile File:
    :param nodes list[Node]: functions
    :param edges list[Edge]: function calls
    :param groups list[Group]: classes and files
    :param hide_legend bool:
    :rtype: None
    '''

    if as_json:
        content = generate_json(nodes, edges)
        outfile.write(content)
        return

    content = "digraph G {\n"
    content += "concentrate=true;\n"
    content += 'splines="ortho";\n'
    content += 'rankdir="LR";\n'
    if not hide_legend:
        content += LEGEND
    for node in nodes:
        content += node.to_dot() + ';\n'
    for edge in edges:
        content += edge.to_dot() + ';\n'
    if not no_grouping:
        for group in groups:
            content += group.to_dot()
    content += '}\n'
    outfile.write(content)


def determine_language(individual_files):
    """
    Given a list of filepaths, determine the language from the first
    valid extension

    :param list[str] individual_files:
    :rtype: str
    """
    for source, _ in individual_files:
        suffix = source.rsplit('.', 1)[-1]
        if suffix in LANGUAGES:
            logging.info("Implicitly detected language as %r.", suffix)
            return suffix
    raise AssertionError(f"Language could not be detected from input {individual_files}. ",
                         "Try explicitly passing the language flag.")


def get_sources_and_language(raw_source_paths, language):
    """
    Given a list of files and directories, return just files.
    If we are not passed a language, determine it.
    Filter out files that are not of that language

    :param list[str] raw_source_paths: file or directory paths
    :param str|None language: Input language
    :rtype: (list, str)
    """

    individual_files = []
    for source in sorted(raw_source_paths):
        if os.path.isfile(source):
            individual_files.append((source, True))
            continue
        for root, _, files in os.walk(source):
            for f in files:
                individual_files.append((os.path.join(root, f), False))

    if not individual_files:
        raise AssertionError("No source files found from %r" % raw_source_paths)
    logging.info("Found %d files from sources argument.", len(individual_files))

    if not language:
        language = determine_language(individual_files)

    sources = set()
    for source, explicity_added in individual_files:
        if explicity_added or source.endswith('.' + language):
            sources.add(source)
        else:
            logging.info("Skipping %r which is not a %s file. "
                         "If this is incorrect, include it explicitly.",
                         source, language)

    if not sources:
        raise AssertionError("Could not find any source files given {raw_source_paths} "
                             "and language {language}")

    sources = sorted(list(sources))
    logging.info("Processing %d source file(s)." % (len(sources)))
    for source in sources:
        logging.info("  " + source)

    return sources, language


def _find_links(node_a, all_nodes, language):
    """
    Iterate through the calls on node_a to find everything the node links to.
    This will return a list of tuples of nodes and calls that were ambiguous.

    :param Node node_a:
    :param list[Node] all_nodes:
    :param BaseLanguage language:
    """
    links = []
    for call in node_a.calls:
        lfc = language.find_link_for_call(call, node_a, all_nodes)
        assert not isinstance(lfc, Group)
        links.append(lfc)
    return list(filter(None, links))


def map_it(sources, language, no_trimming, exclude_namespaces, exclude_functions):
    '''
    Given a language implementation and a list of filenames, do these things:
    1. Read source ASTs & find all groups (classes/modules) and nodes (functions)
       (a lot happens here)
    2. Trim namespaces / functions that we don't want
    3. Attempt to resolve the variables (point them to a node or group)
    4. Find all calls between all nodes
    5. Loudly complain about duplicate edges that were skipped
    6. Trim nodes that didn't connect to anything

    :param list[str] sources:
    :param Language lang:
    :param bool no_trimming:
    :param list exclude_namespaces:
    :param list exclude_functions:

    :rtype: (list[Group], list[Node], list[Edge])
    '''

    # 0. Assert dependencies
    language.assert_dependencies()

    # 1. Read sourcs ASTs & find all groups (classes/modules) and nodes (functions)
    #    (a lot happens here)
    file_groups = []
    all_nodes = []
    for source in sources:
        mod_tree = language.get_tree(source)
        file_group = language.make_file_group(mod_tree, source)
        file_groups.append(file_group)

    # 2. Trim namespaces / functions that we don't want
    if exclude_namespaces:
        file_groups = _exclude_namespaces(file_groups, exclude_namespaces)
    if exclude_functions:
        file_groups = _exclude_functions(file_groups, exclude_functions)

    # 3. Attempt to resolve the variables (point them to a node or group)
    for group in file_groups:
        all_nodes += group.all_nodes()
    for node in all_nodes:
        node.resolve_variables(file_groups)

    # 4. Find all calls between all nodes
    bad_calls = []
    edges = []
    for node_a in list(all_nodes):
        links = _find_links(node_a, all_nodes, language)
        for node_b, bad_call in links:
            if bad_call:
                bad_calls.append(bad_call)
            if not node_b:
                continue
            edges.append(Edge(node_a, node_b))

    # 5. Loudly complain about duplicate edges that were skipped
    bad_calls_strings = set()
    for bad_call in bad_calls:
        if not bad_call.owner_token and bad_call.token in language.RESERVED_KEYWORDS:
            continue
        bad_calls_strings.add(bad_call.to_string())
    bad_calls_strings = list(sorted(list(bad_calls_strings)))
    if bad_calls_strings:
        logging.info("Skipped processing these calls because the algorithm "
                     "linked them to multiple function definitions: %r" % bad_calls_strings)

    if no_trimming:
        return file_groups, all_nodes, edges

    # 6. Trim nodes that didn't connect to anything
    nodes_with_edges = set()
    for edge in edges:
        nodes_with_edges.add(edge.node0)
        nodes_with_edges.add(edge.node1)

    for node in all_nodes:
        if node not in nodes_with_edges:
            node.remove_from_parent()

    for file_group in file_groups:
        for group in file_group.all_groups():
            if not group.all_nodes():
                group.remove_from_parent()

    file_groups = [g for g in file_groups if g.all_nodes()]
    all_nodes = list(nodes_with_edges)

    return file_groups, all_nodes, edges


def _exclude_namespaces(file_groups, exclude_namespaces):
    """
    Exclude namespaces (classes/modules) which match any of the exclude_namespaces

    :param list[Group] file_groups:
    :param list exclude_namespaces:
    :rtype: list[Group]
    """
    for namespace in exclude_namespaces:
        found = False
        for group in list(file_groups):
            if group.token == namespace:
                file_groups.remove(group)
                found = True
            for subgroup in group.all_groups():
                if subgroup.token == namespace:
                    subgroup.remove_from_parent()
                    found = True
        if not found:
            logging.warning(f"Could not exclude namespace '{namespace}' "
                            "because it was not found")
    return file_groups


def _exclude_functions(file_groups, exclude_functions):
    """
    Exclude nodes (functions) which match any of the exclude_functions

    :param list[Group] file_groups:
    :param list exclude_functions:
    :rtype: list[Group]
    """
    for function_name in exclude_functions:
        found = False
        for group in list(file_groups):
            for node in group.all_nodes():
                if node.token == function_name:
                    node.remove_from_parent()
                    found = True
        if not found:
            logging.warning(f"Could not exclude function '{function_name}' "
                            "because it was not found")
    return file_groups


def code2flow(raw_source_paths, output_file, language=None, hide_legend=True,
              exclude_namespaces=None, exclude_functions=None,
              no_grouping=False, no_trimming=False, level=logging.INFO):
    """
    Top-level function. Generate a diagram based on source code.
    Can generate either a dotfile or an image.

    :param list[str] raw_source_paths: file or directory paths
    :param str|file output_file: path to the output file. SVG/PNG will generate an image.
    :param str language: input language extension
    :param bool hide_legend: Omit the legend from the output
    :param list exclude_namespaces: List of namespaces to exclude
    :param list exclude_functions: List of functions to exclude
    :param bool no_grouping: Don't group functions into namespaces in the final output
    :param bool no_trimming: Don't trim orphaned functions / namespaces
    :param int level: logging level
    :rtype: None
    """

    start_time = time.time()

    if not isinstance(raw_source_paths, list):
        raw_source_paths = [raw_source_paths]
    exclude_namespaces = exclude_namespaces or []
    assert isinstance(exclude_namespaces, list)
    exclude_functions = exclude_functions or []
    assert isinstance(exclude_functions, list)

    logging.basicConfig(format="Code2Flow: %(message)s", level=level)

    sources, language = get_sources_and_language(raw_source_paths, language)

    output_ext = None
    if isinstance(output_file, str):
        output_ext = output_file.rsplit('.', 1)[1] or ''
        if output_ext not in VALID_EXTENSIONS:
            raise AssertionError("Output filename must end in one of: %r" % VALID_EXTENSIONS)

    final_img_filename = None
    if output_ext and output_ext in ('png', 'svg'):
        if not is_installed('dot') and not is_installed('dot.exe'):
            raise AssertionError(
                "Can't generate a flowchart image because neither `dot` nor "
                "`dot.exe` was found. Either install graphviz (see the README) "
                "or set your --output argument to a 'dot' filename like out.dot "
                "or out.gz.")
        final_img_filename = output_file
        output_file, extension = output_file.rsplit('.', 1)
        output_file += '.gv'

    language = LANGUAGES[language]

    file_groups, all_nodes, edges = map_it(sources, language, no_trimming,
                                           exclude_namespaces, exclude_functions)

    logging.info("Generating dot file...")

    if isinstance(output_file, str):
        with open(output_file, 'w') as fh:
            as_json = output_ext == 'json'
            write_file(fh, nodes=all_nodes, edges=edges,
                       groups=file_groups, hide_legend=hide_legend,
                       no_grouping=no_grouping, as_json=as_json)
    else:
        write_file(output_file, nodes=all_nodes, edges=edges,
                   groups=file_groups, hide_legend=hide_legend,
                   no_grouping=no_grouping)

    logging.info("Code2flow finished processing in %.2f seconds" % (time.time() - start_time))

    # translate to an image if that was requested
    if final_img_filename:
        start_time = time.time()
        logging.info("Running graphviz to make the image. This might take a while...")
        command = ["dot", "-T" + extension, output_file]
        logging.info("If this takes too long, try running manually with the command below.")
        safety_command = list(command) + ['-v', '-outfile', final_img_filename]
        logging.info("`%s`", ' '.join(safety_command))
        with open(final_img_filename, 'w') as f:
            subprocess.run(command, stdout=f, check=True)
        logging.info("Graphviz finished in %.2f seconds" % (time.time() - start_time))

    logging.info("Completed your flowchart! To see it, open %r.",
                 final_img_filename or output_file)
