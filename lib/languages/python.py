'''
All of these classes subclass engine.py classes

Functions that begin with an "_" are local and do not replace anything in engine.py
'''

from lib import engine
from lib.languages import base

import re
import os

INDENT_PATTERN = re.compile(r"^([\t ]*)\S", re.MULTILINE)
NAMESPACE_BEFORE_DOT_PATTERN = re.compile(r'(?:[^\w\.]|\A)([\w\.]+)\.$', re.MULTILINE)
GROUP_CLASS_PATTERN = re.compile(r"^class\s(\w+)\s*(\(.*?\))?\s*\:", re.MULTILINE)


def _get_indent(colon_pos, source_string):
    """
    Given the position of a colon and string, return the indent characters
    """
    return INDENT_PATTERN.search(source_string[colon_pos:]).group(1)


def _node_is_root(node):
    if node.parent.parent:
        return False
    return True


def _get_absolute_import_paths(filename):
    paths = []

    path_array = os.path.realpath(filename).split('/')[::-1]
    build_path_list = path_array[0]
    path_array = path_array[1:]

    paths.append(build_path_list)
    for elem in path_array:
        if elem:
            build_path_list = elem + '.' + build_path_list
            paths.append(build_path_list)
    return paths


def _get_def_regex_from_indent(indent):
    '''
    Return the regex for function definition at this indent level
    '''
    indent = indent.replace(' ', r'\s').replace('   ', r'\t')
    ret = re.compile(r"^%sdef ([a-zA-Z_][a-zA-Z0-9_]*) *\(" % indent, re.MULTILINE)
    print("regex is", ret)
    return ret


def _generate_implicit_node_sources(group):
    '''
    Find all of the code not in any subnode, string it together,
    and return it as the implicit node
    '''

    source = group.source.copy()
    print('\a'); import ipdb; ipdb.set_trace()
    try:
        for node in group.nodes:
            source -= node.source
        for subgroup in group.subgroups:
            source -= subgroup.source
    except:
        print('\a'); import ipdb; ipdb.set_trace()
    return source


def _generate_node(group, def_match):
    '''
    Using the name match, generate the name, source, and parent of this node

    group(0) is the entire definition line ending at the new block delimiter like:
        def myFunction(a,b,c):
    group(1) is the identifier name like:
        myFunction
    '''
    name = def_match.group(1)

    new_block_delim_pos = def_match.end(0)
    begin_identifier_pos = def_match.start(1)

    source_in_block = group.source.get_source_in_block(new_block_delim_pos)
    line_number = group.source.get_line_number(begin_identifier_pos)
    return engine.Node(name=name,
                       source=source_in_block,
                       parent=group, character_pos=begin_identifier_pos,
                       line_number=line_number, lang=group.lang)


def _generate_nodes(group, indent):
    '''
    Find all function definitions, generate the nodes, and append them
    '''
    nodes = []
    def_pattern = _get_def_regex_from_indent(indent)
    for def_match in def_pattern.finditer(group.source.source_string):
        nodes.append(_generate_node(group, def_match))
    return nodes


def _generate_subgroups(group):
    subgroups = []
    for class_match in GROUP_CLASS_PATTERN.finditer(group.source.source_string):
        name = class_match.group(1)
        colon_pos = class_match.end(0)
        indent = _get_indent(colon_pos=colon_pos, source_string=group.source.source_string)
        source_code = group.source.get_source_in_block(start_pos=colon_pos)
        line_number = group.source.get_line_number(colon_pos)
        class_group = _generate_group(name=name,
                                      indent=indent, source_code=source_code,
                                      parent=group,
                                      line_number=line_number, lang=group.lang)
        subgroups.append(class_group)
    return subgroups


def _get_import_paths(group_filename, node_filename):
    '''
    Return the relative and absolute paths the other filename would use to import this module
    '''
    paths = _get_relative_import_paths(group_filename, node_filename) + _get_absolute_import_paths(group_filename)
    return paths


def _get_relative_import_paths(filename, importer_filename):
    # split paths into their directories
    this_full_path = os.path.abspath(filename)
    this_full_path_list = this_full_path.split('/')

    importer_full_path = os.path.abspath(importer_filename)
    importer_full_path_list = importer_full_path.split('/')

    # pop off shared directories
    while True:
        try:
            assert this_full_path_list[0] == importer_full_path_list[0]
            this_full_path_list.pop(0)
            importer_full_path_list.pop(0)
        except AssertionError:
            break

    relative_path = ''

    # if the importer's unique directory path is longer than 1,
    # then we will have to back up a bit to the last common shared directory
    relative_path += '.' * len(importer_full_path_list)

    # add this path from the last common shared directory
    relative_path += '.'.join(this_full_path_list)
    paths = []

    paths.append(relative_path)

    try:
        paths.append(this_full_path_list[-2:-1][0])
    except Exception:
        pass

    return paths


def _generate_root_node(group):
    name = group.root_node_name()
    source = _generate_implicit_node_sources(group)
    return engine.Node(name=name, source=source,
                       parent=group, lang=group.lang)


def _generate_group(name, source_code, lang=None,
                    parent=None, line_number=0, indent=''):
    '''
    Generate a new group

    The only thing special about groups in python is they are delimited by indent
    This makes things a little bit easier
    '''
    group = engine.Group(
        name=name,
        source_code=source_code,
        parent=parent,
        line_number=line_number,
        lang=lang
    )

    # with the indent set, we can now generate nodes
    group.nodes = _generate_nodes(group, indent)
    print("group nodes", group.nodes)

    # If this is the root node, continue generating subgroups and nodes
    if not group.parent:
        print("not parent a")
        group.subgroups = _generate_subgroups(group)
        print("not parent b")
        group.nodes.append(_generate_root_node(group))
    return group


class Lang(base.BaseLang):
    global_frame_name = 'module'

    comments = [
        {
            '"""': re.compile(r'([^\\]?)(""".*?[^\\]""")()', re.DOTALL),
            "'''": re.compile(r"([^\\]?)('''.*?[^\\]''')()", re.DOTALL),
        },
        {
            '#': re.compile(r'([^\\]?)(#.*?)(\n)', re.DOTALL)
        },
        {
            '"': re.compile(r"([^\\]?)('.*?[^\\]')()", re.DOTALL),
            "'": re.compile(r'([^\\]?)(".*?[^\\]")()', re.DOTALL),
        }
    ]

    # @staticmethod
    # def generate_same_scope_patterns(name):
    #     return [re.compile(r"(?:\W|\A)%s\.%s\s*\(" % ('self', name), re.MULTILINE | re.DOTALL)]

    @staticmethod
    def generate_scope_patterns(full_name):
        return [
            re.compile(r"(?:[^a-zA-Z0-9\.]|\A)%s\s*\(" % (full_name), re.MULTILINE | re.DOTALL)
        ]

    @staticmethod
    def is_init_node(name):
        if name == '__init__':
            return True
        return

    @staticmethod
    def is_extraneous(node, edges):
        '''
        Returns whether we can safely delete this node
        '''
        if _node_is_root(node):
            for edge in edges:
                if edge.node0 == node or edge.node1 == node:
                    return False
            return True
        return False

    @staticmethod
    def get_node_namespace(parent, name):
        return parent.get_namespace()

    @staticmethod
    def links_to(node, other, all_nodes):
        all_names = [n.name for n in all_nodes]
        if all_names.count(other.name) > 1:
            # We don't touch double nodes
            return False

        func_regex = re.compile(r'^(|.*?[^a-zA-Z0-9]+)%s\s*\(' % other.name, re.MULTILINE)

        if func_regex.search(node.source.source_string):
            return True
        return False

    # @staticmethod
    # def links_to(node, other):
    #     """
    #     :param node Node:
    #     :param other None:

    #     """

    #     import_namespace = ''

    #     # If this is in a different file, figure out what namespace to use
    #     if node.get_file_group() != other.get_file_group():
    #         group_filename = other.parent.get_file_name()
    #         node_filename = node.get_file_name()
    #         import_paths = _get_import_paths(group_filename, node_filename)

    #         for import_path in import_paths:
    #             regular_import = re.compile(r"^import\s+%s\s*$" % re.escape(import_path), re.MULTILINE)
    #             complex_import = re.compile('^from\s%s\simport\s(?:\*|(?:.*?\W%s\W.*?))\s*$' %
    #                                         (re.escape(import_path), re.escape(other.name)), re.MULTILINE)
    #             if regular_import.search(node.get_file_group().source.source_string):
    #                 import_namespace += import_path
    #                 break
    #             elif complex_import.search(node.get_file_group().source.source_string):
    #                 break
    #         else:
    #             return False

    #     if not _node_is_root(other):
    #         if import_namespace:
    #             import_namespace = import_namespace + '.' + other.parent.name
    #         else:
    #             import_namespace = other.parent.name

    #     # If the naive functionName (e.g. \Wmyfunc\( ) appears anywhere in this
    #     # source_string, check whether it is actually THAT function
    #     match = other.pattern.search(node.source.source_string)
    #     if match:
    #         match_pos = match.start(1)
    #         hasDot = node.source.source_string[match_pos - 1] == '.'

    #         # if the other function is in the global namespace and this call is
    #         # not referring to any namespace, return true
    #         if _node_is_root(other) and not hasDot:  # TODO js will require the 'window' namespace integrated somehow
    #             return True

    #         # if the other is part of a namespace and we are looking for a namspace
    #         if hasDot:

    #             # try finding the namespace of the called object
    #             try:
    #                 prefix_search_line = node.source.source_string[:match_pos].split('\n')[-1]
    #                 namespace = NAMESPACE_BEFORE_DOT_PATTERN.search(prefix_search_line).group(1)
    #             except AttributeError:
    #                 # will not find a namespace if the object is in an array or something else weird
    #                 # fall through this function because we can still check for init node
    #                 namespace = None

    #             # If the namespaces are the same, that is a match
    #             if namespace == import_namespace:  # and node.get_file_group() == other.get_file_group(): #+ other.name
    #                 return True

    #             # if they are part of the same namespace, we can check for the 'node' keyword
    #             if other.parent == node.parent and namespace == 'self':
    #                 return True

    #             # If a new object was created prior to this call and that object calls this function, that is a match
    #             new_obj_match = other.parent.new_object_assigned_pattern.search(node.source.source_string)
    #             if new_obj_match and namespace == import_namespace + new_obj_match.group(1):
    #                 return True

    #     # TODO put in try in case is_init_node not defined
    #     if other.is_init_node and other.parent.new_object_pattern.search(node.source.source_string):
    #         return True

    #     return False

    @staticmethod
    def trim_groups(group):
        pass

    @staticmethod
    def get_group_namespace(group_parent, name):
        '''
        Returns the full string namespace of this group including this groups name
        '''
        # TODO more complex namespaces involving parents and modules
        # js implements something a bit more complicated already
        # python uses this

        return name

    @staticmethod
    def generate_new_object_pattern(name):
        return re.compile(r'%s\s*\(' % name)

    @staticmethod
    def generate_new_object_assigned_pattern(name):
        return re.compile(r'(\w)\s*=\s*%s\s*\(' % name)

    @staticmethod
    def get_source_in_block(source_code, start_pos):
        """

        """
        indent = _get_indent(start_pos, source_code.source_string)

        end_pos = start_pos

        lines = source_code.source_string[start_pos:].split('\n')[1:]
        for line in lines:
            if line.startswith(indent) or line.strip() == '':
                end_pos += len(line) + 1  # +1 for the newlines lost
            else:
                break

        start_pos = start_pos + 1
        return source_code[start_pos:end_pos]

    @staticmethod
    def generate_file_group(name, source_code, lang):
        '''
        Generate a group for the file. Indent is implicitly none for this group
        '''
        return _generate_group(name=name, source_code=source_code,
                               indent='', lang=lang)
