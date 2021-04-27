'''
'''

import os
import re

from .. import model
from . import base


INDENT_PATTERN = re.compile(r"^\b|^\t+|^ +", re.MULTILINE)
# NAMESPACE_BEFORE_DOT_PATTERN = re.compile(r'(?:[^\w\.]|\A)([\w\.]+)\.$', re.MULTILINE)
GROUP_CLASS_PATTERN = re.compile(r"^class ([a-zA-Z_]\w*) *\(.*?:\s*?$",
                                 re.MULTILINE | re.DOTALL)


def _get_indent(colon_pos, source_string):
    """
    Given the position of a colon and string, return the indent characters
    """
    return INDENT_PATTERN.search(source_string[colon_pos + 1:]).group(0)


def _get_def_regex_from_indent(indent):
    '''
    Return the regex for function definition at this indent level
    '''
    indent = indent.replace(' ', r'\s').replace('   ', r'\t')
    ret = re.compile(r"^%sdef ([a-zA-Z_]\w*) *\(.*?:\s*$" % indent,
                     re.MULTILINE | re.DOTALL | re.ASCII)
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
        class_group = _generate_group(name=name, long_name=name + "()",
                                      indent=indent, source_code=source_code,
                                      parent=group, line_number=line_number,
                                      group_type='class')
        subgroups.append(class_group)
    return subgroups


def _generate_root_node(group):
    source = _generate_implicit_node_sources(group)
    return model.Node(name='(global)', long_name=group.name + " (global scope)",
                      source=source, parent=group, lang=Python)


BUILTINS = ['ArithmeticError', 'AssertionError', 'AttributeError', 'BaseException',
            'BlockingIOError', 'BrokenPipeError', 'BufferError', 'BytesWarning',
            'ChildProcessError', 'ConnectionAbortedError', 'ConnectionError',
            'ConnectionRefusedError', 'ConnectionResetError', 'DeprecationWarning',
            'EOFError', 'Ellipsis', 'EnvironmentError', 'Exception', 'False',
            'FileExistsError', 'FileNotFoundError', 'FloatingPointError',
            'FutureWarning', 'GeneratorExit', 'IOError', 'ImportError', 'ImportWarning',
            'IndentationError', 'IndexError', 'InterruptedError', 'IsADirectoryError',
            'KeyError', 'KeyboardInterrupt', 'LookupError', 'MemoryError',
            'ModuleNotFoundError', 'NameError', 'None', 'NotADirectoryError',
            'NotImplemented', 'NotImplementedError', 'OSError', 'OverflowError',
            'PendingDeprecationWarning', 'PermissionError', 'ProcessLookupError',
            'RecursionError', 'ReferenceError', 'ResourceWarning', 'RuntimeError',
            'RuntimeWarning', 'StopAsyncIteration', 'StopIteration', 'SyntaxError',
            'SyntaxWarning', 'SystemError', 'SystemExit', 'TabError', 'TimeoutError',
            'True', 'TypeError', 'UnboundLocalError', 'UnicodeDecodeError',
            'UnicodeEncodeError', 'UnicodeError', 'UnicodeTranslateError',
            'UnicodeWarning', 'UserWarning', 'ValueError', 'Warning',
            'ZeroDivisionError', '_', '__build_class__', '__debug__', '__doc__',
            '__import__', '__loader__', '__name__', '__package__', '__spec__',
            'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'breakpoint', 'bytearray',
            'bytes', 'callable', 'chr', 'classmethod', 'compile', 'complex',
            'copyright', 'credits', 'delattr', 'dict', 'dir', 'divmod', 'enumerate',
            'eval', 'exec', 'exit', 'filter', 'float', 'format', 'frozenset', 'getattr',
            'globals', 'hasattr', 'hash', 'help', 'hex', 'id', 'input', 'int',
            'isinstance', 'issubclass', 'iter', 'len', 'license', 'list', 'locals', 'map',
            'max', 'memoryview', 'min', 'next', 'object', 'oct', 'open', 'ord', 'pow',
            'print', 'property', 'quit', 'range', 'repr', 'reversed', 'round', 'set',
            'setattr', 'slice', 'sorted', 'staticmethod', 'str', 'sum', 'super', 'tuple',
            'type', 'vars', 'zip']


"""
    I'm kind of thinking that to start, I just want to try to resolve for "self"
    and for top-level imports. Anything else might be too complicated.
    So let's start with that.

    When we generate a node, we want to find calls for that node.
"""



    # ASSIGNMENT = re.compile(rf'^{indent}(?P<var>(\w+\s*\.\s*)*\w+)\s*=\s*', re.MULTILINE)

    # for match in ASSIGNMENT.finditer(node.source.source_string):
    #     print("assignment", match)


def _generate_group(name, long_name, source_code, group_type,
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
        group_type=group_type,
    )
    # with the indent set, we can now generate nodes
    group.nodes = _generate_nodes(group, indent)

    # If this is the root node, continue generating subgroups and nodes
    if group.group_type == 'module':
        group.subgroups = _generate_subgroups(group)
        group.nodes.append(_generate_root_node(group))

    print("modules")
    print(_get_modules(source_code.source_string))

    return group


TOKDOT = r'(\w+\.)*\w+'
TOKCD = r'(\w+\s*\,\s*)*\w+\s*'


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
    for match in re.finditer(rf"^import\s+(?P<mod>{TOKDOT})\s*$",
                             source_string, re.MULTILINE):
        ret.append(
            {'filename': match['mod'].split('.')[-1] + '.py',
             'token': match['mod']})
    for match in re.finditer(rf"^from\s+(?P<mod>{TOKDOT})\s+import\s+(?P<tokens>{TOKCD})\s*$",
                             source_string, re.MULTILINE):
        filename = match['mod'].split('.')[-1] + '.py'
        tokens = match['tokens']
        for token in tokens.split(','):
            token = token.strip()
            ret.append(
                {'filename': filename,
                 'token': token})
    for match in re.finditer(r"^from\s+(?P<mod>{TOKDOT})\s+import\s+\(\s*(?P<tokens>{TOKCD})\s*\)\s*$",
                             source_string, re.MULTILINE):
        filename = match['mod'].split('.')[-1] + '.py'
        tokens = match['tokens']
        for token in tokens.split(','):
            token = token.strip()
            ret.append(
                {'filename': filename,
                 'token': token})
    for match in re.finditer(rf"^from\s+(?P<mod>{TOKDOT})\s+import\s+\*\s*$",
                             source_string, re.MULTILINE):
        filename = match['mod'].split('.')[-1] + '.py'
        ret.append({'filename': filename})
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


NAKED_RE = re.compile(r'(^|[^\.])\b(?P<token>\w+)\s*\(')
OBJECT_RE = re.compile(r'(?P<owner>(\w+\s*\.\s*)+)(?P<token>\w+)\s*\(')


class Python(base.BaseLang):
    comments = {
        '"""': re.compile(r'([^\\]?)(""""""|""".*?[^\\]""")', re.DOTALL),
        "'''": re.compile(r"([^\\]?)(''''''|'''.*?[^\\]''')", re.DOTALL),
        '#': re.compile(r'([^\\]?)(#.*?)(\n)', re.DOTALL),
        '"': re.compile(r"([^\\]?)(''|'.*?[^\\]')", re.DOTALL),
        "'": re.compile(r'([^\\]?)(""|".*?[^\\]")', re.DOTALL),
    }

    @staticmethod
    def find_calls(node):
        source = node.source
        calls = []
        for match in NAKED_RE.finditer(source.source_string):
            calls.append({'type': 'naked', 'token': match['token'], 'residence': None})
        for match in OBJECT_RE.finditer(source.source_string):
            calls.append({'type': 'object', 'token': match['token'], 'owner': match['owner'], 'residence': None})

        for call in calls:
            if call['type'] == 'object':
                if call['owner'] == 'self':
                    call['residence'] = node.parent
                    continue
                for group in node.iter_parents():
                    if group.name == call['owner']:
                        call['residence'] = group
                        break
                continue

            # naked calls
            assert call['type'] == 'naked'
            for group in node.iter_parents():
                if group.group_type == 'module':
                    for node in group.nodes:
                        if node.name == call['token']:
                            call['residence'] = group
                            break

        final_calls = []
        for call in calls:
            if call['type'] == 'naked' and not call['residence'] and call['token'] in BUILTINS:
                continue
            final_calls.append(call)

        return final_calls

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
        matching_calls = [call for call in node.calls
                          if call['token'] == other.name
                          and (not call['residence']
                               or call['residence'] == other.parent)]
        if not matching_calls:
            return False, None

        for call in matching_calls:
            all_possible_nodes = [n for n in all_nodes if n.name == call['token']]
            assert all_possible_nodes
            if len(all_possible_nodes) == 1:
                return True, None
        return False, None


        # all_other_nodes = [n]
        # if all_names.count(other.name) > 1:
        #     # We don't touch double nodes
        #     # TODO we should actually try to resolve
        #     return False, other.name

        # # if _is_local_to(node, other):
        # local_func_regex = re.compile(r'(|.*?\W+)%s\s*\(' % other.name,
        #                               re.MULTILINE)
        # if local_func_regex.search(node.source.source_string):
        #     return True, None
        # return False, None

        # func_regex = re.compile(r'\s+([\w.]+)\.%s\s*\(' % other.name, re.MULTILINE)
        # for match in func_regex.finditer(node.source.source_string):
        #     # TODO
        #     # from_var = match.group(1)
        #     # if from_var not in excluded_tokens:
        #     #     return True, None
        #     return True, None

        # return False, None

    """
    TODO I'm having a heck of a time solving this problem.

    Core issue first. I need to determine whether two nodes are connected. If
    they are in the same file and are named identically, connect them.

    If we have a situation like import re; re.search, and we have another function
    called search, don't connect those.

    If we have two functions in different files, and we can establish with certainty
    which we call, connect them

    I think we have two calls, naked call and object call.

    naked call is:
    doit()

    object call is:
    a.doit()

    in naked call, we can connect within the file or we can connect from
    very specific imports.

    in object call, we need to try to determine what the object is first.
    To do that, there are two options:
    1. We need to look back in the sourcecode before the call and
    see whether the object is an instantiation of a specific group.
    2. We need to look back through the encompassing scope and see whether the
    object is an instantiation of a specific group.

    I think it might make sense to go the other direction. If we can
    identify for every line what type every token is, then we have this
    dictionary and can connect them more rationally. It would most-likely
    follow standard programming language rules.

    so in the global scope, we move forward line-by-line marking
    known tokens.

    Shit, but what do we do in the case of branches?
    if blah
        a = objA()
    else:
        b = objB()

    this only really works if we have a single line:
    a = objA()

    So certainly, we can make a resolution heuristic for that.
    But how often does that actually happen? Not that often, really.
    The re.search case would then be another heuristic.

    So I think for each object call, we will first run a series of resolution
    heuristics to see if we can establish definitive group ownership over the
    function. If we can't, we just hope that only one matches.

    I think that's good.


    So we can resolve membership through a list of heuristics. Conflicting heuristics will be sorted by priority. Enclosing group will be checked first. Objects instantiated in the shallowest group always go before the deepest group. Then, I think line number can help as long as it's not in a branch

    We can only realistically check for a=A(), import a from Z or similar situations. Anything else will be too complex.

    Will need to be careful with "a = B() or C()" situations. For object instantiation, this has to be the last thing that happens on the line.

    "self." Can establish some level of membership. Certainly. Object subclassing might be an issue though.








    """

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
    def get_group_namespace(group):
        '''
        Returns the full string namespace of this group including this groups name
        '''
        if group.name.endswith('.py'):
            return group.name[:-3]
        return group.name

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
        return _generate_group(name=os.path.split(filename)[1], long_name=filename,
                               source_code=source_code, indent='', group_type='module')

    @staticmethod
    def get_tokens_to_exclude(source_code):
        return _get_modules(source_code.source_string)
