import ast as ast
import logging
import os

from .model import Group, Node, Call, Variable, BaseLanguage, djoin


def _get_call_from_func_element(func):
    """
    Given a python ast that represents a function call, clear and create our
    generic Call object. Some calls have no chance at resolution (e.g. array[2](param))
    so we return nothing instead.

    :param func ast:
    :rtype: Call|None
    """
    assert type(func) in (ast.Attribute, ast.Name, ast.Subscript, ast.Call)
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
        owner_token = djoin(*reversed(owner_token))
        return Call(token=func.attr, line_number=func.lineno, owner_token=owner_token)
    if type(func) == ast.Name:
        return Call(token=func.id, line_number=func.lineno)
    if type(func) in (ast.Subscript, ast.Call):
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

    if type(element.value) != ast.Call:
        return []
    call = _get_call_from_func_element(element.value.func)

    ret = []
    for target in element.targets:
        if type(target) != ast.Name:
            continue
        token = target.id
        ret.append(Variable(token, call, element.lineno))
    return ret


def _process_import(element):
    """
    Given an element from the ast which is an import statement, return a
    Variable that points_to the module being imported. For now, the
    points_to is a string but that is resolved later.

    :param element ast:
    :rtype: Variable
    """
    ret = []

    for single_import in element.names:
        assert isinstance(single_import, ast.alias)
        token = single_import.asname or single_import.name
        rhs = single_import.name

        if hasattr(element, 'module'):
            rhs = djoin(element.module, rhs)

        ret.append(Variable(token, points_to=rhs, line_number=element.lineno))
    return ret


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
                variables += _process_assign(element)
            if type(element) in (ast.Import, ast.ImportFrom):
                variables += _process_import(element)
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
    is_constructor = False
    if parent.group_type == "CLASS" and token in ['__init__', '__new__']:
        is_constructor = True
    return Node(token, line_number, calls, variables, parent=parent, is_constructor=is_constructor)


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
