import logging
import os
import json
import subprocess

from .model import (Group, Node, Call, Variable, BaseLanguage,
                    OWNER_CONST, GROUP_TYPE, is_installed, djoin, flatten)


def lineno(el):
    """
    Get the first line number of ast element

    :param ast el:
    :rtype: int
    """
    if isinstance(el, list):
        el = el[0]
    ret = el['loc']['start']['line']
    assert type(ret) == int
    return ret


def walk(tree):
    """
    Walk through the ast tree and return all nodes
    :param ast tree:
    :rtype: list[ast]
    """
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


def resolve_owner(callee):
    """
    Resolve who owns the call object.
    So if the expression is i_ate.pie(). And i_ate is a Person, the callee is Person.
    This is returned as a string and eventually set to the owner_token in the call

    :param ast callee:
    :rtype: str
    """

    if callee['object']['type'] == 'ThisExpression':
        return 'this'
    if callee['object']['type'] == 'Identifier':
        return callee['object']['name']
    if callee['object']['type'] == 'MemberExpression':
        if 'object' in callee['object'] and 'name' in callee['object']['property']:
            return djoin((resolve_owner(callee['object']) or ''),
                         callee['object']['property']['name'])
        return OWNER_CONST.UNKNOWN_VAR
    if callee['object']['type'] == 'CallExpression':
        return OWNER_CONST.UNKNOWN_VAR

    if callee['object']['type'] == 'NewExpression':
        if 'name' in callee['object']['callee']:
            return callee['object']['callee']['name']
        return djoin(callee['object']['callee']['object']['name'],
                     callee['object']['callee']['property']['name'])

    return OWNER_CONST.UNKNOWN_VAR


def get_call_from_func_element(func):
    """
    Given a javascript ast that represents a function call, clear and create our
    generic Call object. Some calls have no chance at resolution (e.g. array[2](param))
    so we return nothing instead.

    :param func dict:
    :rtype: Call|None
    """
    callee = func['callee']
    if callee['type'] == 'MemberExpression' and 'name' in callee['property']:
        owner_token = resolve_owner(callee)
        return Call(token=callee['property']['name'],
                    line_number=lineno(callee),
                    owner_token=owner_token)
    if callee['type'] == 'Identifier':
        return Call(token=callee['name'], line_number=lineno(callee))
    return None


def make_calls(body):
    """
    Given a list of lines, find all calls in this list.

    :param list|dict body:
    :rtype: list[Call]
    """
    calls = []
    for element in walk(body):
        if element['type'] == 'CallExpression':
            call = get_call_from_func_element(element)
            if call:
                calls.append(call)
        elif element['type'] == 'NewExpression' and element['callee']['type'] == 'Identifier':
            calls.append(Call(token=element['callee']['name'],
                              line_number=lineno(element)))
    return calls


def process_assign(element):
    """
    Given an element from the ast which is an assignment statement, return a
    Variable that points_to the type of object being assigned. The
    points_to is often a string but that is resolved later.

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
        call = get_call_from_func_element(target['init'])
        if call:
            return [Variable(token, call, lineno(element))]

    # this block is for require (as in: import) expressions
    if target['init']['type'] == 'CallExpression' \
       and target['init']['callee'].get('name') == 'require':
        import_src_str = target['init']['arguments'][0]['value']
        if 'name' in target['id']:
            imported_name = target['id']['name']
            points_to_str = djoin(import_src_str, imported_name)
            return [Variable(imported_name, points_to_str, lineno(element))]
        ret = []
        for prop in target['id'].get('properties', []):
            imported_name = prop['key']['name']
            points_to_str = djoin(import_src_str, imported_name)
            ret.append(Variable(imported_name, points_to_str, lineno(element)))
        return ret

    # For the other type of import expressions
    if target['init']['type'] == 'ImportExpression':
        import_src_str = target['init']['source']['raw']
        imported_name = target['id']['name']
        points_to_str = djoin(import_src_str, imported_name)
        return [Variable(imported_name, points_to_str, lineno(element))]

    if target['init']['type'] == 'CallExpression':
        if 'name' not in target['id']:
            return []
        call = get_call_from_func_element(target['init'])
        if call:
            return [Variable(target['id']['name'], call, lineno(element))]

    if target['init']['type'] == 'ThisExpression':
        assert set(target['init'].keys()) == {'start', 'end', 'loc', 'type'}
        return []
    return []


def make_local_variables(tree, parent):
    """
    Given an ast of all the lines in a function, generate a list of
    variables in that function. Variables are tokens and what they link to.
    In this case, what it links to is just a string. However, that is resolved
    later.

    Also return variables for the outer scope parent

    :param tree list|dict:
    :param parent Group:
    :rtype: list[Variable]
    """
    if not tree:
        return []

    variables = []
    for element in walk(tree):
        if element['type'] == 'VariableDeclaration':
            variables += process_assign(element)

    # Make a 'this' variable for use anywhere we need it that points to the class
    if isinstance(parent, Group) and parent.group_type == GROUP_TYPE.CLASS:
        variables.append(Variable('this', parent, lineno(tree)))

    variables = list(filter(None, variables))
    return variables


def children(tree):
    """
    The acorn AST is tricky. This returns all the children of an element
    :param ast tree:
    :rtype: list[ast]
    """
    assert type(tree) == dict
    ret = []
    for k, v in tree.items():
        if type(v) == dict and v.get('type'):
            ret.append(v)
        if type(v) == list:
            ret += filter(None, v)
    return ret


def get_inherits(tree):
    """
    Gets the superclass of the class. In js, this will be max 1 element
    :param ast tree:
    :rtype: list[str]
    """
    if tree['superClass']:
        if 'name' in tree['superClass']:
            return [tree['superClass']['name']]
        return [djoin(tree['superClass']['object']['name'], tree['superClass']['property']['name'])]
    return []


def get_acorn_version():
    """
    Get the version of installed acorn
    :rtype: str
    """
    proc = subprocess.Popen(['node', '-p', 'require(\'acorn/package.json\').version'],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            cwd=os.path.dirname(os.path.realpath(__file__)))
    assert proc.wait() == 0, "Acorn is required to parse javascript files. " \
                             "It was found on the path but could not be imported " \
                             "in node.\n" + proc.stderr.read().decode()
    return proc.stdout.read().decode().strip()


class Javascript(BaseLanguage):
    @staticmethod
    def assert_dependencies():
        """Assert that acorn is installed and the correct version"""
        assert is_installed('acorn'), "Acorn is required to parse javascript files " \
                                      "but was not found on the path. Install it " \
                                      "from npm and try again."
        version = get_acorn_version()
        if not version.startswith('8.'):
            logging.warning("Acorn is required to parse javascript files. "
                            "Version %r was found but code2flow has only been "
                            "tested on 8.*", version)
        logging.info("Using Acorn %s" % version)

    @staticmethod
    def get_tree(filename, lang_params):
        """
        Get the entire AST for this file

        :param filename str:
        :param lang_params LanguageParams:
        :rtype: ast
        """
        script_loc = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                  "get_ast.js")
        cmd = ["node", script_loc, lang_params.source_type, filename]
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError:
            raise AssertionError(
                "Acorn could not parse file %r. You may have a JS syntax error or "
                "if this is an es6-style source, you may need to run code2flow "
                "with --source-type=module. "
                "For more detail, try running the command "
                "\n  acorn %s\n"
                "Warning: Acorn CANNOT parse all javascript files. See their docs. " %
                (filename, filename)) from None
        tree = json.loads(output)
        assert isinstance(tree, dict)
        assert tree['type'] == 'Program'
        return tree

    @staticmethod
    def separate_namespaces(tree):
        """
        Given an AST, recursively separate that AST into lists of ASTs for the
        subgroups, nodes, and body. This is an intermediate step to allow for
        cleaner processing downstream

        :param tree ast:
        :returns: tuple of group, node, and body trees. These are processed
                  downstream into real Groups and Nodes.
        :rtype: (list[ast], list[ast], list[ast])
        """

        groups = []
        nodes = []
        body = []
        for el in children(tree):
            if el['type'] in ('MethodDefinition', 'FunctionDeclaration'):
                nodes.append(el)
            elif el['type'] == 'ClassDeclaration':
                groups.append(el)
            else:
                tup = Javascript.separate_namespaces(el)
                if tup[0] or tup[1]:
                    groups += tup[0]
                    nodes += tup[1]
                    body += tup[2]
                else:
                    body.append(el)
        return groups, nodes, body

    @staticmethod
    def make_nodes(tree, parent):
        """
        Given an ast of all the lines in a function, create the node along with the
        calls and variables internal to it.
        Also make the nested subnodes

        :param tree ast:
        :param parent Group:
        :rtype: list[Node]
        """
        is_constructor = False
        if tree.get('kind') == 'constructor':
            token = '(constructor)'
            is_constructor = True
        elif tree['type'] == 'FunctionDeclaration':
            token = tree['id']['name']
        elif tree['type'] == 'MethodDefinition':
            token = tree['key']['name']

        if tree['type'] == 'FunctionDeclaration':
            full_node_body = tree['body']
        else:
            full_node_body = tree['value']

        subgroup_trees, subnode_trees, this_scope_body = Javascript.separate_namespaces(full_node_body)
        if subgroup_trees:
            # TODO - this is when a class is defined within a function
            # It's unusual but should probably be handled in the future.
            # Handling this use case would require some code reorganziation.
            # Take a look at class_in_function.js to better understand.
            logging.warning("Skipping class defined within a function!")

        line_number = lineno(tree)
        calls = make_calls(this_scope_body)
        variables = make_local_variables(this_scope_body, parent)
        node = Node(token, calls, variables, parent=parent, line_number=line_number,
                    is_constructor=is_constructor)
        subnodes = flatten([Javascript.make_nodes(t, node) for t in subnode_trees])

        return [node] + subnodes

    @staticmethod
    def make_root_node(lines, parent):
        """
        The "root_node" is an implict node of lines which are executed in the global
        scope on the file itself and not otherwise part of any function.

        :param lines list[ast]:
        :param parent Group:
        :rtype: Node
        """
        token = "(global)"
        calls = make_calls(lines)
        variables = make_local_variables(lines, parent)
        root_node = Node(token, calls, variables,
                         line_number=0, parent=parent)
        return root_node

    @staticmethod
    def make_class_group(tree, parent):
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
        assert not subgroup_trees

        group_type = GROUP_TYPE.CLASS
        token = tree['id']['name']
        display_name = 'Class'
        line_number = lineno(tree)
        inherits = get_inherits(tree)
        class_group = Group(token, group_type, display_name,
                            inherits=inherits, line_number=line_number, parent=parent)

        for node_tree in node_trees:
            for new_node in Javascript.make_nodes(node_tree, parent=class_group):
                class_group.add_node(new_node)

        return class_group

    @staticmethod
    def file_import_tokens(filename):
        """
        Returns the token(s) we would use if importing this file from another.

        :param filename str:
        :rtype: list[str]
        """
        return []
