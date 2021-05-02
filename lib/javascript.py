import logging
import os
import json
import subprocess

from .model import is_installed, Group, Node, Call, Variable, BaseLanguage


def lineno(el):
    ret = el['loc']['start']['line']
    assert type(ret) == int
    return ret


# def walk(tree):
#     while isinstance(tree, dict):
#         tree = tree['body']

#     ret = []
#     for el in tree:
#         ret.append(el)
#         if 'body' in el:
#             ret += walk(el['body'])
#     return ret


def walk(tree):
    ret = []
    if type(tree) == list:
        for el in tree:
            if el.get('type'):
                ret.append(el)
                ret += walk(el)
    elif type(tree) == dict:
        for k, v in tree.items():
            if type(v) == dict and v.get('type'):
                ret.append(v)
                ret += walk(v)
            if type(v) == list:
                ret += walk(v)
    return ret


def _get_call_from_func_element(func):
    """
    Given a python ast that represents a function call, clear and create our
    generic Call object. Some calls have no chance at resolution (e.g. array[2](param))
    so we return nothing instead.

    :param func ast:
    :rtype: Call|None
    """
    callee = func['callee']
    if callee['type'] == 'MemberExpression':
        if callee['object']['type'] == 'ThisExpression':
            owner_token = 'this'
        else:
            owner_token = callee['object']['name']
        return Call(token=callee['property']['name'],
                    line_number=lineno(callee),
                    owner_token=owner_token)
    if callee['type'] == 'Identifier': # TODO
        return Call(token=callee['name'], line_number=lineno(callee))
    # if type(func) in (ast.Subscript, ast.Call):
    #     return None
    print('\a'); import ipdb; ipdb.set_trace()
    logging.warning("Unknown function type %r" % callee['type'])
    return None


def _make_calls(body):
    """
    Given a list of lines, find all calls in this list.

    :param list|dict body:
    :rtype: list[Call]
    """
    calls = []
    for element in walk(body):
        if element['type'] != 'CallExpression':
            continue
        call = _get_call_from_func_element(element)
        if call:
            calls.append(call)

        # if element['type'] != 'ExpressionStatement':
        #     continue
        # if element['expression']['type'] == 'CallExpression':
        #     call = _get_call_from_func_element(element['expression'])
        #     if call:
        #         calls.append(call)
        #     continue
        # if element['expression']['type'] == 'AssignmentExpression' \
        #    and element['expression']['right']['type'] == 'CallExpression':
        #     call = _get_call_from_func_element(element['expression']['right'])
        #     if call:
        #         calls.append(call)
    return calls


def _process_assign(element):
    """
    Given an element from the ast which is an assignment statement, return a
    Variable that points_to the type of object being assigned. For now, the
    points_to is a string but that is resolved later.

    :param element ast:
    :rtype: Variable
    """

    if len(element['declarations']) > 1:
        return
    target = element['declarations'][0]
    if target['type'] != 'VariableDeclarator':
        return
    token = target['id']['name']

    if target['init']['type'] != 'NewExpression':
        return
    call = _get_call_from_func_element(target['init'])
    return Variable(token, call, lineno(element))


def _make_variables(tree, parent):
    """
    Given an ast of all the lines in a function, generate a list of
    variables in that function. Variables are tokens and what they link to.
    In this case, what it links to is just a string. However, that is resolved
    later.

    :param tree list|dict:
    :param parent Group:
    :rtype: list[Variable]
    """
    variables = []
    for element in walk(tree):
        if element['type'] == 'VariableDeclaration':
            variables.append(_process_assign(element))
        # if type(element) in (ast.Import, ast.ImportFrom):  # TODO
        #     variables.append(_process_import(element))

    if parent.group_type == 'CLASS':
        variables.append(Variable('this', parent, lineno(tree)))  # TODO

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
    if tree.get('kind') == 'constructor':
        token = '(constructor)'  # TODO this should go for Python init too
    elif tree['type'] == 'FunctionDeclaration':
        token = tree['id']['name']
    elif tree['type'] == 'MethodDefinition':
        token = tree['key']['name']

    if tree['type'] == 'FunctionDeclaration':
        body = tree['body']
    else:
        body = tree['value']

    line_number = lineno(tree)
    calls = _make_calls(body)
    variables = _make_variables(body, parent)
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
    assert tree['type'] == 'ClassDeclaration'
    subgroup_trees, node_trees, body_trees = Javascript.separate_namespaces(tree)

    group_type = 'CLASS'
    token = tree['id']['name']
    line_number = lineno(tree)

    class_group = Group(token, line_number, group_type, parent=parent)

    for node_tree in node_trees:
        class_group.add_node(_make_node(node_tree, parent=class_group))

    for subgroup_tree in subgroup_trees:
        logging.warning("Code2flow does not support nested classes. Skipping %r in %r.",
                        subgroup_tree.name, parent.token)
    return class_group


class Javascript(BaseLanguage):
    # from https://www.w3schools.com/js/js_reserved.asp
    RESERVED_KEYWORDS = [
        'Array', 'Date', 'eval', 'function', 'hasOwnProperty', 'Infinity',
        'isFinite', 'isNaN', 'isPrototypeOf', 'length', 'Math', 'NaN', 'name',
        'Number', 'Object', 'prototype', 'String', 'toString', 'undefined',
        'valueOf', 'alert', 'all', 'anchor', 'anchors', 'area', 'assign',
        'blur', 'button', 'checkbox', 'clearInterval', 'clearTimeout',
        'clientInformation', 'close', 'closed', 'confirm', 'constructor',
        'crypto', 'decodeURI', 'decodeURIComponent', 'defaultStatus', 'document',
        'element', 'elements', 'embed', 'embeds', 'encodeURI',
        'encodeURIComponent', 'escape', 'event', 'fileUpload', 'focus', 'form',
        'forms', 'frame', 'innerHeight', 'innerWidth', 'layer', 'layers',
        'link', 'location', 'mimeTypes', 'navigate', 'navigator', 'frames',
        'frameRate', 'hidden', 'history', 'image', 'images', 'offscreenBuffering',
        'open', 'opener', 'option', 'outerHeight', 'outerWidth', 'packages',
        'pageXOffset', 'pageYOffset', 'parent', 'parseFloat', 'parseInt',
        'password', 'pkcs11', 'plugin', 'prompt', 'propertyIsEnum', 'radio',
        'reset', 'screenX', 'screenY', 'scroll', 'secure', 'select', 'self',
        'setInterval', 'setTimeout', 'status', 'submit', 'taint', 'text',
        'textarea', 'top', 'unescape', 'untaint', 'window']

    @staticmethod
    def assert_dependencies():
        if not is_installed('acorn'):
            raise AssertionError("Acorn is required to parse javascript files "
                                 "but was not found on the path. Install it from "
                                 "npm and try again.")

    @staticmethod
    def get_tree(filename):
        """
        Get the entire AST for this file

        :param filename str:
        :rtype: ast
        """
        # output = subprocess.check_output(["acorn", filename])#, '--location'])
        output = subprocess.check_output(["node", "lib/get_ast.js", filename])#, '--location'])
        tree = json.loads(output)
        assert isinstance(tree, dict)
        assert tree['type'] == 'Program'
        assert tree['sourceType'] == 'script'
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
        while isinstance(tree, dict):
            tree = tree['body']

        groups = []
        nodes = []
        body = []
        for el in tree:
            if el['type'] in ('MethodDefinition', 'FunctionDeclaration'):
                nodes.append(el)
            elif el['type'] == 'ClassDeclaration':
                groups.append(el)
            elif el.get('body'):
                tup = Javascript.separate_namespaces(el)
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

        # TODO js is callback hell so we really need to nest deep

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
                if call.token == node.token and node.parent.group_type == 'SCRIPT':
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

        subgroup_trees, node_trees, body_trees = Javascript.separate_namespaces(tree)
        group_type = 'SCRIPT'
        token = os.path.split(filename)[-1].rsplit('.js', 1)[0]
        line_number = 0

        file_group = Group(token, line_number, group_type, parent=None)

        for node_tree in node_trees:
            file_group.add_node(_make_node(node_tree, parent=file_group))

        file_group.add_node(_make_root_node(body_trees, parent=file_group), is_root=True)

        for subgroup_tree in subgroup_trees:
            file_group.add_subgroup(_make_class_group(subgroup_tree, parent=file_group))

        return file_group
