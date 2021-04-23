'''
'''

import os
import re

from .. import model
from . import base


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
                      long_name=name + '()',
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
        class_group = _generate_group(name=name, long_name=f"class {name}()",
                                      indent=indent, source_code=source_code,
                                      parent=group, line_number=line_number)
        subgroups.append(class_group)
    return subgroups


def _generate_root_node(group):
    source = _generate_implicit_node_sources(group)
    return model.Node(name='(global)', long_name=group.name + " (global scope)",
                      source=source, parent=group, lang=Python)


def _generate_group(name, long_name, source_code,
                    parent=None, line_number=0, indent=''):
    '''
    Generate a new group

    The only thing special about groups in python is they are delimited by indent
    This makes things a little bit easier
    '''
    group = model.Group(
        name=name,
        long_name=long_name,
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


def _get_modules(source_string):
    """
    Given a source string, return all of the module imports including their filename
    Any token with a filename that we don't process is filtered out of the final
    results

    # TODO import as

    :param source_string str:
    :rtype: list[dict]
    """
    ret = []
    for match in re.finditer(r"^import\s+([a-zA-Z0-9_.]+)\s*$",
                             source_string, re.MULTILINE):
        ret.append(
            {'filename': match.group(1).split('.')[-1] + '.py',
             'token': match.group(1)})
    for match in re.finditer(r"^from\s+([a-zA-Z0-9_.]+)\s+import\s+([a-zA-Z0-9_., ]+)\s*$",
                             source_string, re.MULTILINE):
        filename = match.group(1).split('.')[-1] + '.py'
        tokens = match.group(2)
        for token in tokens.split(','):
            token = token.strip()
            ret.append(
                {'filename': filename,
                 'token': token})
    for match in re.finditer(r"^from\s+([a-zA-Z0-9_.]+)\s+import\s+\((.*?)\)\s*",
                             source_string, re.MULTILINE):
        filename = match.group(1).split('.')[-1] + '.py'
        tokens = match.group(2)
        for token in tokens.split(','):
            token = token.strip()
            ret.append(
                {'filename': filename,
                 'token': token})
    return ret


def _is_local_to(node, other):
    """
    Checkes whether other is in node's local scope.
    If it is, downstream, it will be important to handle it as a local-only regex

    :param node Node:
    :param other Node:
    :rtype: bool
    """

    # Must be in same file
    if other.source.filename != node.source.filename:
        return False
    # Other must be in global scope
    if other.parent.parent is not None:
        return False
    return True


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
        """
        Determine whether anything in node calls the other.
        Returns whether one calls the other. If they don't, return the name of
        the other node if it is a duplicate node and that's why we couldn't
        resolve

        :param node Node:
        :param other Node:
        :param all_nodes list[Node]:
        :rype: bool, str
        """
        all_names = [n.name for n in all_nodes]
        if all_names.count(other.name) > 1:
            # We don't touch double nodes
            # TODO we should actually try to resolve
            return False, other.name

        # if _is_local_to(node, other):
        local_func_regex = re.compile(r'(|.*?[^a-zA-Z0-9_]+)%s\s*\(' % other.name,
                                      re.MULTILINE)
        if local_func_regex.search(node.source.source_string):
            return True, None
        return False, None

        func_regex = re.compile(r'\s+([a-zA-Z0-9_.]+)\.%s\s*\(' % other.name, re.MULTILINE)
        for match in func_regex.finditer(node.source.source_string):
            # TODO
            # from_var = match.group(1)
            # if from_var not in excluded_tokens:
            #     return True, None
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

        return source_code[end_identifier_pos:end_pos]

    @staticmethod
    def generate_file_group(filename, source_code):
        '''
        Generate a group for the file. Indent is implicitly none for this group
        '''
        return _generate_group(name=os.path.split(filename)[1], long_name=filename, source_code=source_code, indent='')

    @staticmethod
    def get_tokens_to_exclude(source_code):
        return _get_modules(source_code.source_string)
