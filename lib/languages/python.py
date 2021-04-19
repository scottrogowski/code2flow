'''
'''

import re

from lib import model
from lib.languages import base


INDENT_PATTERN = re.compile(r"^([\t ]*)", re.MULTILINE)
NAMESPACE_BEFORE_DOT_PATTERN = re.compile(r'(?:[^\w\.]|\A)([\w\.]+)\.$', re.MULTILINE)
GROUP_CLASS_PATTERN = re.compile(r"^class ([a-zA-Z_][a-zA-Z0-9_]*) *\(.*?:\s*?$",
                                 re.MULTILINE | re.DOTALL)


def _get_indent(colon_pos, source_string):
    """
    Given the position of a colon and string, return the indent characters
    """
    return INDENT_PATTERN.search(source_string[colon_pos + 1:]).group(1)


def _get_def_regex_from_indent(indent):
    '''
    Return the regex for function definition at this indent level
    '''
    indent = indent.replace(' ', r'\s').replace('   ', r'\t')
    ret = re.compile(r"^%sdef ([a-zA-Z_][a-zA-Z0-9_]*) *\(.*?:\s*?$" % indent,
                     re.MULTILINE | re.DOTALL)
    return ret


def _generate_implicit_node_sources(group):
    '''
    Find all of the code not in any subnode, string it together,
    and return it as the implicit node
    '''
    source = group.source.copy()
    for node in group.nodes:
        source -= node.source
    for subgroup in group.subgroups:
        source -= subgroup.source
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

    begin_identifier_pos = def_match.start(1)
    end_identifier_pos = def_match.end(1)
    colon_pos = def_match.end(0)

    source_in_block = group.source.get_source_in_block(end_identifier_pos, colon_pos)
    line_number = group.source.get_line_number(begin_identifier_pos)
    return model.Node(name=name,
                      source=source_in_block,
                      parent=group, character_pos=begin_identifier_pos,
                      line_number=line_number, lang=Python)


def _generate_nodes(group, indent):
    '''
    Find all function definitions, generate the nodes, and append them
    '''
    nodes = []
    def_pattern = _get_def_regex_from_indent(indent)
    for def_match in group.source.finditer(def_pattern):
        nodes.append(_generate_node(group, def_match))
    return nodes


def _generate_subgroups(group):
    subgroups = []
    for class_match in GROUP_CLASS_PATTERN.finditer(group.source.source_string):
        name = class_match.group(1)
        end_identifier_pos = class_match.end(1)
        colon_pos = class_match.end(0)
        indent = _get_indent(colon_pos=colon_pos, source_string=group.source.source_string)
        source_code = group.source.get_source_in_block(end_identifier_pos, colon_pos)
        line_number = group.source.get_line_number(colon_pos)
        class_group = _generate_group(name=name, indent=indent,
                                      source_code=source_code, parent=group,
                                      line_number=line_number)
        subgroups.append(class_group)
    return subgroups


def _generate_root_node(group):
    name = group.root_node_name()
    source = _generate_implicit_node_sources(group)
    return model.Node(name=name, source=source,
                      parent=group, lang=Python)


def _generate_group(name, source_code,
                    parent=None, line_number=0, indent=''):
    '''
    Generate a new group

    The only thing special about groups in python is they are delimited by indent
    This makes things a little bit easier
    '''
    group = model.Group(
        name=name,
        source_code=source_code,
        parent=parent,
        line_number=line_number,
        lang=Python,
    )
    # with the indent set, we can now generate nodes
    group.nodes = _generate_nodes(group, indent)

    # If this is the root node, continue generating subgroups and nodes
    if not group.parent:
        group.subgroups = _generate_subgroups(group)
        group.nodes.append(_generate_root_node(group))
    return group


class Python(base.BaseLang):
    comments = {
        '"""': re.compile(r'([^\\]?)(""""""|""".*?[^\\]""")', re.DOTALL),
        "'''": re.compile(r"([^\\]?)(''''''|'''.*?[^\\]''')", re.DOTALL),
        '#': re.compile(r'([^\\]?)(#.*?)(\n)', re.DOTALL),
        '"': re.compile(r"([^\\]?)(''|'.*?[^\\]')", re.DOTALL),
        "'": re.compile(r'([^\\]?)(""|".*?[^\\]")', re.DOTALL),
    }

    @staticmethod
    def is_extraneous(node, edges):
        '''
        Returns whether we can safely delete this node
        '''
        for edge in edges:
            if edge.node0 == node or edge.node1 == node:
                return False
        return True

    @staticmethod
    def links_to(node, other, all_nodes):
        all_names = [n.name for n in all_nodes]
        if all_names.count(other.name) > 1:
            # We don't touch double nodes
            return False, other.name

        func_regex = re.compile(r'^(|.*?[^a-zA-Z0-9_]+)%s\s*\(' % other.name, re.MULTILINE)

        if func_regex.search(node.source.source_string):
            return True, None
        return False, None

    @staticmethod
    def trim_groups(groups):
        # TODO this probably needs to trim subgroups
        return groups
        # ret = []
        # for group in groups:
        #     if group.all_nodes():
        #         ret.append(group)
        # return ret

    @staticmethod
    def get_group_namespace(group_parent, name):
        '''
        Returns the full string namespace of this group including this groups name
        '''

        return group_parent.name if group_parent else name

    @staticmethod
    def get_source_in_block(source_code, end_identifier_pos, colon_pos):
        """

        """
        indent = _get_indent(colon_pos, source_code.source_string)

        end_pos = colon_pos

        lines = source_code.source_string[colon_pos:].split('\n')[1:]
        for line in lines:
            if line.startswith(indent) or line.strip() == '':
                end_pos += len(line) + 1  # +1 for the newlines lost
            else:
                break

        # colon_pos = colon_pos + 1
        return source_code[end_identifier_pos:end_pos]

    @staticmethod
    def generate_file_group(filename, source_code):
        '''
        Generate a group for the file. Indent is implicitly none for this group
        '''
        return _generate_group(name=filename, source_code=source_code, indent='')
