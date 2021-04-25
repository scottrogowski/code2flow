'''
All of these classes subclass engine.py classes

Functions that begin with an "_" are local and do not replace anything in engine.py
'''

import re
import logging

from lib import engine
from lib.languages import base


PATTERNS = [
    {'type': 'function', 'pattern': re.compile(r".*?\W(function\s+(\w+)\s*\(.*?\)\s*\Z)", re.DOTALL)},
    {'type': 'function', 'pattern': re.compile(r".*?[^a-zA-Z0-9_\.]+(([\w\.]+)\s*[\:\=]\s*function\s*\(.*?\)\s*\Z)", re.DOTALL)},
    {'type': 'object', 'pattern': re.compile(r".*?\W(([\w\.]+)\s*\=\s*\Z)", re.DOTALL)},
    {'type': 'anon_function', 'pattern': re.compile(r".*?\(\s*(function\s*\(.*?\)\s*\Z)", re.DOTALL)},
]


def _generate_namespaces(ns):
    return [
        ns,
        'window.' + ns if ns else 'window'
    ]


def _generate_implicit_node(group, blocks_to_remove):
    # Get source by subtracting all of the 'spoken for' blocks
    source = group.source.copy()

    for block in blocks_to_remove:
        source -= block.full_source

    # Depending on whether or not this is the file root (global frame)
    # , set a flag and the node name
    if group.parent:
        is_file_root = False
        name = group.name
    else:
        is_file_root = True
        name = group.root_node_name(group.name.rsplit('/', 1)[-1])

    # generate and append the node
    return engine.Node(name=name, source=source, definition_string=group.definition_string,
                       parent=group, line_number=group.line_number, is_file_root=is_file_root,
                       lang=group.lang)  # isImplicit=True


def _new_group_from_block(group, open_bracket, close_bracket):
    '''
    Using the sourcecode before the block, try generating a function using all of the patterns we know about
    If we can generate it, return a new group with the sourcecode within the block
    '''
    pre_block_source = group.source[:open_bracket]
    block_source = group.source[open_bracket:close_bracket + 1]

    for pattern in PATTERNS:
        new_group = _new_from_from_sources_and_patterns(group, pre_block_source,
                                                        block_source, pattern)
        if new_group:
            return new_group

    # TODO2021
    logging.info("====================")
    logging.info(pre_block_source.source_string[-100:])
    logging.info('what is this?')


def _new_from_from_sources_and_patterns(_group, pre_block_source, block_source, pattern):
    '''
    Given a functionPattern to test for, sourcecode before the block, and sourcecode within the block,
    Try to generate a new group


    '''

    # We are looking for a function name
    # Start by limiting the search area to that inbetween the last closed bracket and here
    # Then, try to match the pattern
    last_bracket = pre_block_source.source_string.rfind('}')
    if last_bracket == -1:
        last_bracket = 0
    match = pattern['pattern'].match(pre_block_source.source_string[last_bracket:])

    # If we found a match, generate a group
    if match:
        # name the function
        if pattern['type'] == 'anon_function':
            name = "(anon)"
        else:
            name = match.group(2)

        # determine what group to attach this to.
        # if there was a dot in the namespace, we might need to attach this to
        # something other than the group it was defined within
        attach_to = _group
        if '.' in name:
            namespace, name = name.rsplit('.', 1)
            group = _find_namespace(_group, namespace, _group)
            if group:
                attach_to = group

        # generate the definition and line number
        definition_string = match.group(1)
        line_number = pre_block_source.get_line_number(match.start(1) + last_bracket)
        full_source = pre_block_source[last_bracket + match.start(1):] + block_source

        # finally, generate the group
        return _generate_group(
            name=name,
            source_code=block_source[1:-1],  # source without the brackets
            full_source=full_source,
            definition_string=definition_string,
            parent=attach_to,
            line_number=line_number,
            is_function=pattern['type'] in ('function', 'anon_function'),
            is_anon=pattern['type'] == 'anon_function',
            lang=_group.lang
        )


def _find_namespace(self_group, namespace, calling_group=None):
    if any(map(lambda this_ns: this_ns == namespace, _generate_namespaces(self_group.get_namespace()))):
        return self_group
    else:
        for group in self_group.subgroups:
            if group != calling_group and _find_namespace(group, namespace=namespace, calling_group=self_group):
                return group
        if self_group.parent and self_group.parent != calling_group:
            return _find_namespace(self_group.parent, namespace=namespace, calling_group=self_group)
        else:
            return False


def _generate_group(name, source_code, lang=None, definition_string='',
                    full_source=None, parent=None, line_number=0,
                    is_function=True, is_anon=False):
    '''
    Generate a new group

    Iteratively find blocks (objects and functions delimited by brackets) within
    this group and generate subgroups from them
    If this is a functional group (can call functions and is not a simple array)
    , remove the subgroups found from the sourcecode and use those to generate the implicit node

    is_function means the group is a regular function and has an implicit node
    not is_function would mean the group is an object meant for grouping like a = {b=function,c=function}

    is_anon means the function has no name and is not likely to be called outside of this scope
    '''
    ret = engine.Group(
        name=name,
        source_code=source_code,
        full_source=full_source,
        definition_string=definition_string,
        parent=parent,
        line_number=line_number,
        lang=lang
    )
    ret.is_anon = is_anon

    blocks_to_remove = []

    open_bracket = ret.source.find('{')

    while open_bracket != -1:
        '''
        While we do have a "next function/object" to handle:
        * find the close bracket for this block
        * extract the source of the block and the source immediately prior to this block
        * generate a group from this source and the prior source
        * if we managed to create a group, see below
        '''

        close_bracket = ret.source.matching_bracket_pos(open_bracket)
        if close_bracket == -1:
            logging.info("Could not find closing bracket for open bracket on line %d in file %s" %
                         (ret.source.get_line_number(open_bracket), ret.name))
            logging.info("You might have a syntax error. Setting closing bracket position to EOF")
            close_bracket = len(ret.source)

        # Try generating a new group
        # This will fail if it is a function pattern we do not understand
        new_group = _new_group_from_block(ret, open_bracket, close_bracket)

        if new_group:
            '''
            Append this new group to the proper namespace

            Either
            A. The new group was not anonymous, and contained more than an implicit node
            B. The new group was anonymous but had subgroups in which case we want those
               subgroups to be our subgroups

            Either way:
            1. push the newly created group to it's parent  which is probably us
               unless something like MainMap.blah = function happened
            2. append this group to the groups we will later have to remove when
               generating the implicit node
            '''

            if not (new_group.is_anon and len(new_group.nodes) == 1 and new_group.nodes[0].name == new_group.name):
                new_group.parent.subgroups.append(new_group)
                blocks_to_remove.append(new_group)
            elif new_group.subgroups:
                for group in new_group.subgroups:
                    if group.parent == new_group:
                        group.parent = ret
                    group.parent.subgroups.append(group)
                blocks_to_remove.append(new_group)

        # get the next block to handle
        open_bracket = ret.source.find('{', close_bracket)

    if is_function:
        new_node = _generate_implicit_node(ret, blocks_to_remove)
        ret.nodes.append(new_node)
    return ret


class Lang(base.BaseLang):

    global_frame_name = 'window'

    comments = [
        {
            '/*': re.compile(r'([^\\]?)\/\*(.*?[^\\])\*\/', re.DOTALL),
        },
        {
            '//': re.compile(r'([^\\]?)(\/\/.*?)\n', re.DOTALL)
        },
        {
            '"': re.compile(r"([^\\]?)'(.*?[^\\])'", re.DOTALL),
            "'": re.compile(r'([^\\]?)"(.*?[^\\])"', re.DOTALL),
        }
    ]

    # @staticmethod
    # def generate_same_scope_patterns(name):
    #     return [re.compile(r"(?:\W|\A)%s\.%s\s*\(" % ('this', name), re.MULTILINE | re.DOTALL)]

    @staticmethod
    def generate_scope_patterns(full_name):
        '''
        How you would call this node from any scope
        '''
        asp = [
            re.compile(r"(?:[^a-zA-Z0-9\.]|\A)%s\s*\(" % (full_name), re.MULTILINE | re.DOTALL)
        ]
        return asp + [
            re.compile(r"(?:[^a-zA-Z0-9\.]|\A)window\.%s\s*\(" % (full_name), re.MULTILINE | re.DOTALL)
        ]

    @staticmethod
    def is_init_node(name):
        '''
        Dummy meant to be subclassed if we do extra calculations to determine node type
        '''
        return False

    @staticmethod
    def is_extraneous(node, edges):
        '''
        Dummy function meant to be subclassed
        Will contain logic that will determine whether this node can be removed during trimming
        '''
        return False

    @staticmethod
    def get_node_namespace(parent_group, name):
        if parent_group.name != name:
            return parent_group.get_namespace()
        else:
            return parent_group.parent.get_namespace()

    @staticmethod
    def links_to(node, other):
        # Can either line in local scope using 'this' keyword
        # Or can link in namespaced/global scope
        # window.any.namespace is exactly the same as any.namespace
        # TODO when a function is defined within another function, there is no need for self keyword

        # if they are part of the same namespace, we can use the self keyword
        if other.parent == node.parent:
            if any(map(lambda pattern: pattern.search(node.source.source_string), other.same_scope_patterns)):
                return True

        # Otherwise, they can always be linked by a shared namespace
        # must generate namespace here because we are trimming the groups AFTER init of the node
        if any(map(lambda pattern: pattern.search(node.source.source_string),
                   Lang.generate_any_scope_patterns(other.get_full_name()))):
            return True

        return False

    @staticmethod
    def get_group_namespace(parent_group, name):
        '''
        Returns the full string namespace of this group including this group's name

        '''
        if not parent_group:
            return ''
        else:
            ret = name
            if parent_group.get_namespace():
                ret = parent_group.get_namespace() + '.' + ret
            return ret

    @staticmethod
    def trim_groups(_group):
        '''
        If a group has only the implicit node, make that into a node and trim it
        '''

        saved_subgroups = []

        for group in _group.subgroups:
            Lang.trim_groups(group)
            if not group.subgroups:
                if not group.nodes:
                    continue
                if len(group.nodes) == 1 and group.nodes[0].name == group.name:
                    group.nodes[0].parent = _group
                    _group.nodes.append(group.nodes[0])
                    continue
            saved_subgroups.append(group)
        _group.subgroups = saved_subgroups

    @staticmethod
    def generate_new_object_pattern(name):
        return re.compile(r'new\s+%s\s*\(' % name)

    @staticmethod
    def generate_new_object_assigned_pattern(name):
        return re.compile(r'(\w)\s*=\s*new\s+%s\s*\(' % name)

    """
    def generateNodes(self):
        '''
        for each match, generate the node
        '''
        functionPatterns = self.generateFunctionPatterns()
        for pattern in functionPatterns:
            matches = pattern.finditer(self.source.source_string)
            for match in matches:
                node = self.generateNode(match)
                self.nodes.append(node)
                self.generateOrAppendToGroup(node)
    """

    # def generateOrAppendToGroup(self, node):
    #     openDelimPos = self.source.openDelimPos(node.characterPos)

    #     if self.source.source_string[openDelimPos] == '{':
    #         # this is a regular function, generate the group
    #         group = self.generateGroup(openDelimPos, node)  # TODO2021 LOL. OMG
    #     elif self.source.source_string[openDelimPos] == '(':
    #         # declare as an anonymous function
    #         # the caller shall still be found by going one higher
    #         while self.source.source_string[openDelimPos] == '(':
    #             openDelimPos = self.source.openDelimPos(openDelimPos - 1)
    #     else:
    #         logging.info('what is this?')  # TODO2021

    # block_comments = [
    #     {'start': "/*", 'end': "*/"},
    #     {'start': '"', 'end': '"'},
    #     {'start': "'", 'end': "'"},
    #     # {'start': re.compile(r'[\=\(]\s*\/[^/]'), 'end': re.compile(r'[^\\]/')}
    # ]
    # inline_comments = "//"

    # TODO drop full_source

    @staticmethod
    def get_source_in_block(source_code, start_pos, full_source=False):
        '''
        Get the source within two matching brackets
        '''
        other_bracket_position = source_code.matching_bracket_pos(start_pos)

        if start_pos < other_bracket_position:
            start_bracker_pos = start_pos
            end_bracket_pos = other_bracket_position
        else:
            start_bracker_pos = other_bracket_position
            end_bracket_pos = start_pos

        ret = source_code[start_bracker_pos + 1:end_bracket_pos]
        return ret

    @staticmethod
    def generate_file_group(filename, source_code, lang):
        '''
        Generate a group for the file. This will be a function group (is_function=True)
        A function group can possibly call other groups.
        '''
        return _generate_group(name=filename, source_code=source_code,
                               is_function=True,
                               lang=lang)
