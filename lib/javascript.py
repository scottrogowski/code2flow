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


# TODO test chained().calls().on().python()

def _resolve_owner(callee):
    if callee['object']['type'] == 'ThisExpression':
        return 'this'
    if callee['object']['type'] == 'Identifier':
        return callee['object']['name']
    if callee['object']['type'] == 'MemberExpression':
        if 'object' in callee['object'] and 'name' in callee['object']['property']:
            return (_resolve_owner(callee['object']) or '') + '.' + callee['object']['property']['name']
        # else, probablys a []
        return 'UNKNOWN_MODULE'
    if callee['object']['type'] == 'CallExpression':
        return 'UNKNOWN_MODULE' # TODO we don't know so no point?
        # TODO not sure on this... Might need to return two things when this happens... it's like a().b()
        # return _resolve_owner(callee['object']['callee'])

    if callee['object']['type'] == 'NewExpression':
        return callee['object']['callee']['name']

    # TODO Keep below for a while
    # if callee['object']['type'] in ('ConditionalExpression', 'ArrayExpression',
    # 'Literal', 'BinaryExpression', 'TemplateLiteral', 'LogicalExpression',
    # 'FunctionExpression'):
    #     return None

    return 'UNKNOWN_MODULE'


def _get_call_from_func_element(func):
    """
    Given a javascript ast that represents a function call, clear and create our
    generic Call object. Some calls have no chance at resolution (e.g. array[2](param))
    so we return nothing instead.

    :param func dict:
    :rtype: Call|None
    """
    callee = func['callee']
    if callee['type'] == 'MemberExpression' and 'name' in callee['property']:
        owner_token = _resolve_owner(callee)
        return Call(token=callee['property']['name'],
                    line_number=lineno(callee),
                    owner_token=owner_token)
    if callee['type'] == 'Identifier':
        return Call(token=callee['name'], line_number=lineno(callee))
    # if type(func) in (ast.Subscript, ast.Call):
    #     return None
    # logging.warning("Unknown function type %r" % callee['type'])
    return None


def _make_calls(body):
    """
    Given a list of lines, find all calls in this list.

    :param list|dict body:
    :rtype: list[Call]
    """
    calls = []
    for element in walk(body):
        if element['type'] == 'CallExpression':
            call = _get_call_from_func_element(element)
            if call:
                calls.append(call)
        elif element['type'] == 'NewExpression':
            calls.append(Call(token='(constructor)',
                              owner_token=element['callee']['name'],
                              line_number=lineno(element)))
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
        return []
    target = element['declarations'][0]
    assert target['type'] == 'VariableDeclarator'
    if target['init'] is None:
        return []

    if target['init']['type'] == 'NewExpression':
        token = target['id']['name']
        call = _get_call_from_func_element(target['init'])
        return [Variable(token, call, lineno(element))]

    if target['init']['type'] == 'CallExpression' \
       and target['init']['callee'].get('name') == 'require':
        call = target['init']['arguments'][0]['value']
        if 'name' in target['id']:
            return [Variable(target['id']['name'], call, lineno(element))]
        ret = []
        for prop in target['id'].get('properties', []):
            ret.append(Variable(prop['key']['name'], call, lineno(element)))
        return ret
    if target['init']['type'] == 'ImportExpression':
        return [Variable(target['id']['name'], target['init']['source']['raw'], lineno(element))]

    if target['init']['type'] == 'CallExpression':
        if 'name' not in target['id']:
            return []
        return [Variable(target['id']['name'], _get_call_from_func_element(target['init']),
                         lineno(element))]

    if target['init']['type'] == 'ThisExpression':
        assert set(target['init'].keys()) == {'start', 'end', 'loc', 'type'}
        return []
        # return [Variable(target['id']['name'], _get_call_from_func_element(target['init']),
        #                  lineno(element))]
    return []
    # TODO keep those for a while maybe...
    # if target['init']['type'] in ('Literal', 'BinaryExpression', 'MemberExpression',
    #                               'Identifier', 'LogicalExpression', 'TemplateLiteral',
    #                               'ArrayExpression', 'ConditionalExpression',
    #                               'ObjectExpression', 'FunctionExpression'):
    #     # TODO on binary expression (= a + b) and memberexpression ( = a.b)
    #     return []


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
            variables += _process_assign(element)
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
    node = Node(token, line_number, calls, variables, parent=parent)
    return node


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
    root_node = Node(token, line_number, calls, variables, parent=parent)
    return root_node


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

    assert not subgroup_trees
    return class_group


def _dive(tree):
    assert type(tree) == dict
    ret = []
    for k, v in tree.items():
        if type(v) == dict and v.get('type'):
            ret.append(v)
        if type(v) == list:
            ret += v
    return ret


def _get_acorn_version():
    return subprocess.check_output(['npm', '-v', 'acorn'])


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
        assert is_installed('acorn'), "Acorn is required to parse javascript files " \
                                      "but was not found on the path. Install it " \
                                      "from npm and try again."

        if not _get_acorn_version().startswith(b'7.7.'):
            logging.warning("Acorn is required to parse javascript files. "
                            "Version %r was found but code2flow has only been "
                            "tested on 7.7.", _get_acorn_version())

    @staticmethod
    def get_tree(filename, source_type):
        """
        Get the entire AST for this file

        :param filename str:
        :rtype: ast
        """
        # output = subprocess.check_output(["acorn", filename])#, '--location'])
        script_loc = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                  "get_ast.js")
        cmd = ["node", script_loc, source_type, filename]
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as ex:
            raise AssertionError(
                "Acorn could not parse file %r. You may have a JS syntax error or "
                "you may need to run code2flow with --source-type. "
                "For more detail, try running the command `acorn %s`. "
                "Warning: Acorn CANNOT parse all javascript files. See their docs. " % \
                (filename, filename)) from None
        tree = json.loads(output)
        assert isinstance(tree, dict)
        assert tree['type'] == 'Program'
        # assert tree['sourceType'] == 'script'
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
        # while isinstance(tree, dict):
        #     tree = tree['body']


        # TODO body elements really need to just be all the leftover.
        # We really need to capture ALL method definitions and functiondeclarations
        # in a walk

        groups = []
        nodes = []
        body = []
        for el in _dive(tree):
            if type(el) == dict and el['type'] in ('MethodDefinition', 'FunctionDeclaration'):
                nodes.append(el)
            elif type(el) == dict and el['type'] == 'ClassDeclaration':
                groups.append(el)
            else:
                body.append(el)
                tup = Javascript.separate_namespaces(el)
                groups += tup[0]
                nodes += tup[1]

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

        # TODO js is callback hell so we really need to check nesting deep
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
                if call.token == '(constructor)' and call.owner_token != node.parent.token:
                    continue
                possible_nodes.append(node)
        else:
            for node in all_nodes:
                if call.token == node.token and node.parent.group_type in ('SCRIPT', 'MODULE'):
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
