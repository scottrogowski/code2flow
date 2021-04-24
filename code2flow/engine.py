import logging
import os
import random
import subprocess

from .model import Edge, SourceCode, TRUNK_COLOR, LEAF_COLOR, EDGE_COLOR

from .languages.python import Python
# from .languages.javascript import Javascript


# for generating UIDs for groups and nodes
random.seed(42)

LANGUAGES = {
    'py': Python
    # 'js': Javascript,
    # 'php': PHP,
    # 'rb': Ruby,
}
VALID_EXTENSIONS = {'.png', '.svg', '.dot', '.gv', '.jgv'}


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


def flatten(nested_list):
    """
    Given a list of lists, return a flattened list

    :param list[list] nested_list:
    :rtype: list
    """
    return [el for sublist in nested_list for el in sublist]


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


def _generate_edges(nodes):
    '''
    When a function calls another function, that is an edge
    This is in the global scope because edges can exist between any node and not just between groups
    '''
    edges = []
    dup_names = set()
    for node0 in nodes:
        for node1 in nodes:
            does_link, dup_name = node0.links_to(node1, nodes)
            dup_names.add(dup_name)
            if does_link:
                logging.debug("  %s->%s", node0.chained_name(), node1.chained_name())
                edges.append(Edge(node0, node1))
    dup_names = sorted(filter(None, list(dup_names)))
    if dup_names:
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
        sgs = file_group.subgroups
        nodes = file_group.all_nodes()
        logging.info("  Extracted %d namespaces and %d functions.",
                     len(sgs), len(nodes))
        if sgs:
            logging.debug("  Subgroups:")
            for sg in sgs:
                logging.debug("    " + sg.long_name)

        if nodes:
            logging.debug("  Nodes:")
            for node in nodes:
                logging.debug("    " + node.long_name)
        file_groups.append(file_group)
    return file_groups


def _exclude_namespaces(groups, exclude_namespaces):
    """
    Exclude namespaces (classes/modules) which match any of the exclude_namespaces

    :param list[Group] groups:
    :param list exclude_namespaces:
    :rtype: list[Group]
    """
    for namespace in exclude_namespaces:
        found = False
        for group in list(groups):
            print('\a'); from icecream import ic; ic(group.get_namespace())
            if group.get_namespace() == namespace:
                groups.remove(group)
                found = True
            for subgroup in list(group.subgroups):
                if subgroup.get_namespace() == namespace:
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
    :param list exclude_functions:
    :rtype: list[Group]
    """
    for function_name in exclude_functions:
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


def map_it(lang, filenames, exclude_namespaces, exclude_functions,
           no_trimming=False):
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
    :param list exclude_namespaces:
    :param list exclude_functions:

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

    if no_trimming:
        return file_groups, all_nodes, edges

    # 5. Trim nodes that didn't connect to anything
    final_nodes = []
    for node in all_nodes:
        # final_nodes.append(node)
        if not lang.is_extraneous(node, edges):
            final_nodes.append(node)
        else:
            node.parent.nodes.remove(node)

    return file_groups, final_nodes, edges


def write_dot_file(outfile, nodes, edges, groups, hide_legend=False,
                   no_grouping=False):
    '''
    Write a dot file that can be read by graphviz

    :param outfile File:
    :param nodes list[Node]: functions
    :param edges list[Edge]: function calls
    :param groups list[Group]: classes and files
    :param hide_legend bool:
    :rtype: None
    '''

    content = "digraph G {\n"
    content += "concentrate=true;\n"
    content += 'splines="ortho";\n'
    content += 'rankdir="LR";\n'
    if not hide_legend:
        content += LEGEND
    for node in nodes:
        content += node.to_dot(no_grouping) + ';\n'
    for edge in edges:
        content += edge.to_dot() + ';\n'
    if not no_grouping:
        for group in groups:
            content += group.to_dot()
    content += '}\n'

    outfile.write(content)


def _is_installed(executable_cmd):
    """
    Determine whether a command can be run or not

    :param list[str] individual_files:
    :rtype: str
    """
    for path in os.environ["PATH"].split(os.pathsep):
        path = path.strip('"')
        exe_file = os.path.join(path, executable_cmd)
        if os.path.isfile(exe_file) and os.access(exe_file, os.X_OK):
            return True
    return False


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

    if not isinstance(raw_source_paths, list):
        raw_source_paths = [raw_source_paths]
    exclude_namespaces = exclude_namespaces or []
    assert isinstance(exclude_namespaces, list)
    exclude_functions = exclude_functions or []
    assert isinstance(exclude_functions, list)

    logging.basicConfig(format="Code2Flow: %(message)s", level=level)

    sources, language = get_sources_and_language(raw_source_paths, language)

    if isinstance(output_file, str) and (not any(output_file.endswith(ext) for ext in VALID_EXTENSIONS)):
        raise AssertionError("Output filename must end in one of: %r" % VALID_EXTENSIONS)

    final_img_filename = None
    if isinstance(output_file, str) and (output_file.endswith('.png') or output_file.endswith('.svg')):
        if not _is_installed('dot') and not _is_installed('dot.exe'):
            raise AssertionError(
                "Can't generate a flowchart image because neither `dot` nor "
                "`dot.exe` was found. Either install graphviz (see the README) "
                "or set your --output argument to a 'dot' filename like out.dot "
                "or out.gz.")
        final_img_filename = output_file
        output_file, extension = output_file.rsplit('.', 1)
        output_file += '.gv'

    lang = LANGUAGES[language]

    # Do the mapping (where the magic happens)
    groups, nodes, edges = map_it(lang, sources, no_trimming=no_trimming,
                                  exclude_namespaces=exclude_namespaces,
                                  exclude_functions=exclude_functions)

    logging.info("Generating dot file...")
    if isinstance(output_file, str):
        with open(output_file, 'w') as fh:
            write_dot_file(fh, nodes=nodes, edges=edges,
                           groups=groups, hide_legend=hide_legend,
                           no_grouping=no_grouping)
    else:
        write_dot_file(output_file, nodes=nodes, edges=edges,
                       groups=groups, hide_legend=hide_legend,
                       no_grouping=no_grouping)

    # translate to an image if that was requested
    if final_img_filename:
        logging.info("Translating dot file to image... %s", output_file)
        command = ["dot", "-T" + extension, output_file]
        with open(final_img_filename, 'w') as f:
            subprocess.run(command, stdout=f, check=True)

    logging.info("Completed your flowchart! To see it, open %r.",
                 final_img_filename or output_file)
