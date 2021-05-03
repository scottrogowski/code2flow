import ast as ast
import logging
import os

from .model import Group, Node, Call, Variable, BaseLanguage


def _get_call_from_func_element(func):
    """
    Given a python ast that represents a function call, clear and create our
    generic Call object. Some calls have no chance at resolution (e.g. array[2](param))
    so we return nothing instead.

    :param func ast:
    :rtype: Call|None
    """
    if type(func) == ast.Attribute:
        owner_token = []
        val = func.value
        while True:
            try:
                owner_token.append(getattr(val, 'attr', val.id))
            except AttributeError:
                pass
            val = getattr(val, 'value', None)
            if not val:
                break
        owner_token = '.'.join(reversed(owner_token))
        return Call(token=func.attr, line_number=func.lineno, owner_token=owner_token)
    if type(func) == ast.Name:
        return Call(token=func.id, line_number=func.lineno)
    if type(func) in (ast.Subscript, ast.Call):
        return None
    logging.warning("Unknown function type %r" % type(func))
    return None


def _make_calls(lines):
    """
    Given a list of lines, find all calls in this list.

    :param lines list[ast]:
    :rtype: list[Call]
    """

    calls = []
    for tree in lines:
        for element in ast.walk(tree):
            if type(element) != ast.Call:
                continue
            call = _get_call_from_func_element(element.func)
            if call:
                calls.append(call)
    return calls


def _process_assign(element):
    """
    Given an element from the ast which is an assignment statement, return a
    Variable that points_to the type of object being assigned. For now, the
    points_to is a string but that is resolved later.

    :param element ast:
    :rtype: Variable
    """

    if len(element.targets) > 1:
        return
    target = element.targets[0]
    if type(target) != ast.Name:
        return
    token = target.id

    if type(element.value) != ast.Call:
        return
    call = _get_call_from_func_element(element.value.func)
    return Variable(token, call, element.lineno)


def _process_import(element):
    """
    Given an element from the ast which is an import statement, return a
    Variable that points_to the module being imported. For now, the
    points_to is a string but that is resolved later.

    :param element ast:
    :rtype: Variable
    """

    if len(element.names) > 1:
        return None

    if not isinstance(element.names[0], ast.alias):
        return None

    alias = element.names[0]
    token = alias.asname or alias.name
    rhs = alias.name

    if hasattr(element, 'module'):
        rhs = element.module

    return Variable(token, rhs, element.lineno)


def _make_variables(lines, parent):
    """
    Given an ast of all the lines in a function, generate a list of
    variables in that function. Variables are tokens and what they link to.
    In this case, what it links to is just a string. However, that is resolved
    later.

    :param lines list[ast]:
    :param parent Group:
    :rtype: list[Variable]
    """
    variables = []
    for tree in lines:
        for element in ast.walk(tree):
            if type(element) == ast.Assign:
                variables.append(_process_assign(element))
            if type(element) in (ast.Import, ast.ImportFrom):
                variables.append(_process_import(element))
    if parent.group_type == 'CLASS':
        variables.append(Variable('self', parent, lines[0].lineno))

    variables = list(filter(None, variables))
    return variables


def _make_node(tree, parent):
    """
    Given an ast of all the lines in a function, create the node along with the
    calls and variables internal to it.

    :param tree ast:
    :param parent Group:
    :rtype: Node
    """
    token = tree.name
    line_number = tree.lineno
    calls = _make_calls(tree.body)
    variables = _make_variables(tree.body, parent)
    return Node(token, line_number, calls, variables, parent=parent)


def _make_root_node(lines, parent):
    """
    The "root_node" are is an implict node of lines which are executed in the global
    scope on the file itself and not otherwise part of any function.

    :param lines list[ast]:
    :param parent Group:
    :rtype: Node
    """
    token = "(global)"
    line_number = 0
    calls = _make_calls(lines)
    variables = _make_variables(lines, parent)
    return Node(token, line_number, calls, variables, parent=parent)


def _make_class_group(tree, parent):
    """
    Given an AST for the subgroup (a class), generate that subgroup.
    In this function, we will also need to generate all of the nodes internal
    to the group.

    :param tree ast:
    :param parent Group:
    :rtype: Group
    """
    assert type(tree) == ast.ClassDef
    subgroup_trees, node_trees, body_trees = Python.separate_namespaces(tree)

    group_type = 'CLASS'
    token = tree.name
    line_number = tree.lineno

    class_group = Group(token, line_number, group_type, parent=parent)

    for node_tree in node_trees:
        class_group.add_node(_make_node(node_tree, parent=class_group))

    for subgroup_tree in subgroup_trees:
        logging.warning("Code2flow does not support nested classes. Skipping %r in %r.",
                        subgroup_tree.name, parent.token)
    return class_group


class Python(BaseLanguage):
    RESERVED_KEYWORDS = [
        'ArithmeticError', 'AssertionError', 'AttributeError', 'BaseException',
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

    @staticmethod
    def assert_dependencies():
        pass

    @staticmethod
    def get_tree(filename, _):
        """
        Get the entire AST for this file

        :param filename str:
        :rtype: ast
        """
        with open(filename) as f:
            tree = ast.parse(f.read())
        return tree

    @staticmethod
    def separate_namespaces(tree):
        """
        Given an AST, recursively separate that AST into lists of ASTs for the
        subgroups, nodes, and body. This is an intermediate step to allow for
        clearner processing downstream

        :param tree ast:
        :returns: tuple of group, node, and body trees. These are processed
                  downstream into real Groups and Nodes.
        :rtype: (list[ast], list[ast], list[ast])
        """
        groups = []
        nodes = []
        body = []
        for el in tree.body:
            if type(el) == ast.FunctionDef:
                nodes.append(el)
            elif type(el) == ast.ClassDef:
                groups.append(el)
            elif getattr(el, 'body', None):
                tup = Python.separate_namespaces(el)
                groups += tup[0]
                nodes += tup[1]
                body += tup[2]
            else:
                body.append(el)
        return groups, nodes, body

    @staticmethod
    def find_link_for_call(call, node_a, all_nodes):
        """
        Given a call that happened on a node (node_a), return the node
        that the call links to and the call itself if >1 node matched.

        :param call Call:
        :param node_a Node:
        :param all_nodes list[Node]:

        :returns: The node it links to and the call if >1 node matched.
        :rtype: (Node|None, Call|None)
        """
        all_vars = node_a.get_variables(call.line_number)

        for var in all_vars:
            var_match = call.matches_variable(var)
            if var_match:
                if var_match == 'UNKNOWN_MODULE':
                    return None, None
                assert isinstance(var_match, Node)
                return var_match, None

        possible_nodes = []
        if call.is_attr():
            for node in all_nodes:
                if call.token != node.token:
                    continue
                possible_nodes.append(node)
        else:
            for node in all_nodes:
                if call.token == node.token and node.parent.group_type == 'MODULE':
                    possible_nodes.append(node)

        if len(possible_nodes) == 1:
            return possible_nodes[0], None
        if len(possible_nodes) > 1:
            return None, call
        return None, None

    @staticmethod
    def make_file_group(tree, filename):
        """
        Given an AST for the entire file, generate a file group complete with
        subgroups, nodes, etc.

        :param tree ast:
        :param filename Str:

        :rtype: Group
        """
        subgroup_trees, node_trees, body_trees = Python.separate_namespaces(tree)
        group_type = 'MODULE'
        token = os.path.split(filename)[-1].rsplit('.py', 1)[0]
        line_number = 0

        file_group = Group(token, line_number, group_type, parent=None)

        for node_tree in node_trees:
            file_group.add_node(_make_node(node_tree, parent=file_group))
        file_group.add_node(_make_root_node(body_trees, parent=file_group), is_root=True)

        for subgroup_tree in subgroup_trees:
            file_group.add_subgroup(_make_class_group(subgroup_tree, parent=file_group))

        return file_group
