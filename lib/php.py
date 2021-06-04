import json
import os
import subprocess

from .model import (Group, Node, Call, Variable, BaseLanguage,
                    OWNER_CONST, GROUP_TYPE, is_installed, flatten)


def lineno(tree):
    return tree['attributes']['startLine']


def get_name(tree):
    try:
        return tree['name']['name']
    except KeyError:
        pass
    try:
        assert len(tree['name']['parts']) == 1
        return tree['name']['parts'][0]
    except KeyError:
        pass
    if tree['name']['nodeType'] == 'Expr_Closure':
        return None
    assert False


# STOP_TYPES = ('Expr_FuncCall', 'Expr_New', 'Expr_MethodCall', 'Expr_BinaryOp_Concat', 'Expr_StaticCall' )


def get_call_from_expr(func_expr):
    """
    Given an ast that represents a send call, clear and create our
    generic Call object. Some calls have no chance at resolution (e.g. array[2](param))
    so we return nothing instead.

    :param func_expr ast:
    :rtype: Call|None
    """
    if func_expr['nodeType'] == 'Expr_FuncCall':
        # token = func_expr['name']['parts'][0]
        token = get_name(func_expr)
        owner_token = None
    elif func_expr['nodeType'] == 'Expr_New' and func_expr['class'].get('parts'):
        token = '__construct'
        owner_token = func_expr['class']['parts'][0]
    elif func_expr['nodeType'] == 'Expr_MethodCall':
        # token = func_expr['name']['name']
        token = get_name(func_expr)
        if 'var' in func_expr['var']:
            owner_token = OWNER_CONST.UNKNOWN_VAR
        else:
            owner_token = func_expr['var']['name']
    elif func_expr['nodeType'] == 'Expr_BinaryOp_Concat' and func_expr['right']['nodeType'] == 'Expr_FuncCall':
        token = get_name(func_expr['right'])
        # token = func_expr['right']['name']['parts'][0]
        owner_token = func_expr['left']['name']
    elif func_expr['nodeType'] == 'Expr_StaticCall':
        token = get_name(func_expr)
        assert len(func_expr['class']['parts']) == 1
        owner_token = func_expr['class']['parts'][0]
    else:
        return None

    if owner_token and token == '__construct':
        # Taking out owner_token for constructors as a little hack to make it work
        return Call(token=owner_token,
                    line_number=lineno(func_expr))
    ret = Call(token=token,
               owner_token=owner_token,
               line_number=lineno(func_expr))
    return ret


def walk(tree):
    """
    Given an ast tree walk it to get every node

    :param tree_el ast:
    :rtype: list[ast]
    """

    if isinstance(tree, list):
        ret = []
        for el in tree:
            if isinstance(el, dict) and el.get('nodeType'):
                ret += walk(el)
        return ret

    assert isinstance(tree, dict)
    assert tree['nodeType']
    ret = [tree]

    if tree['nodeType'] == 'Expr_BinaryOp_Concat':
        return ret

    for v in tree.values():
        if isinstance(v, list) or (isinstance(v, dict) and v.get('nodeType')):
            ret += walk(v)
    return ret


def children(tree):
    """
    Given an ast tree get all children

    :param tree_el ast:
    :rtype: list[ast]
    """
    assert isinstance(tree, dict)
    ret = []
    for v in tree.values():
        if isinstance(v, list):
            for el in v:
                if isinstance(el, dict) and el.get('nodeType'):
                    ret.append(el)
        elif isinstance(v, dict) and v.get('nodeType'):
            ret.append(v)
    return ret


def make_calls(body_el):
    """
    Given a list of lines, find all calls in this list.

    :param body_el ast:
    :rtype: list[Call]
    """
    calls = []
    for expr in walk(body_el):
        calls.append(get_call_from_expr(expr))
    ret = list(filter(None, calls))

    return ret


def process_assign(assignment_el):
    """
    Given an assignment statement, return a
    Variable that points_to the type of object being assigned. The
    points_to is often a string but that is resolved later.

    :param assignment_el ast:
    :rtype: Variable
    """

    assert assignment_el['nodeType'] == 'Expr_Assign'
    varname = assignment_el['var']['name']
    call = get_call_from_expr(assignment_el['expr'])
    if call:
        return Variable(varname, call, line_number=lineno(assignment_el))
    # else is something like `varname = num`
    return None


def make_local_variables(tree_el, parent):
    """
    Given an ast of all the lines in a function, generate a list of
    variables in that function. Variables are tokens and what they link to.
    In this case, what it links to is just a string. However, that is resolved
    later.

    :param tree_el ast:
    :param parent Group:
    :rtype: list[Variable]
    """
    variables = []
    for el in walk(tree_el):
        if el['nodeType'] == 'Expr_Assign':
            variables.append(process_assign(el))

    # Make a 'this' variable for use anywhere we need it that points to the class
    if isinstance(parent, Group) and parent.group_type == GROUP_TYPE.CLASS:
        variables.append(Variable('this', parent, line_number=parent.line_number))
        variables.append(Variable('self', parent, line_number=parent.line_number))

    variables = list(filter(None, variables))
    return variables


def get_inherits(tree):
    """
    Get the various types of inheritances this class/module can have

    :param tree ast:
    :rtype: list[str]
    """
    ret = []

    if tree.get('extends', {}):
        assert len(tree['extends']['parts']) == 1
        ret.append(tree['extends']['parts'][0])

    for stmt in tree.get('stmts', []):
        if stmt['nodeType'] == 'Stmt_TraitUse':
            for trait in stmt['traits']:
                ret.append(trait['parts'][0])
    return ret


class PHP(BaseLanguage):

    @staticmethod
    def assert_dependencies():
        assert is_installed('php'), "No php installation could be found"

    @staticmethod
    def get_tree(filename, lang_params):
        """
        Get the entire AST for this file

        :param filename str:
        :param lang_params LanguageParams:
        :rtype: ast
        """
        script_loc = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                  "get_ast.php")

        cmd = ["php", script_loc, filename]
        output = subprocess.check_output(cmd, stderr=subprocess.PIPE)
        try:
            tree = json.loads(output)
        except json.decoder.JSONDecodeError:
            raise AssertionError(
                "Could not parse file %r. You may have a syntax error. "
                "For more detail, try running with `php %s`. " %
                (filename, filename)) from None
        assert isinstance(tree, list)

        if len(tree) == 1 and tree[0]['nodeType'] == 'Stmt_InlineHTML':
            raise AssertionError("Tried to parse a file that is not likely PHP")
        return tree

    @staticmethod
    def separate_namespaces(tree):
        """
        Given a tree element, recursively separate that AST into lists of ASTs for the
        subgroups, nodes, and body. This is an intermediate step to allow for
        clearner processing downstream

        :param tree ast:
        :returns: tuple of group, node, and body trees. These are processed
                  downstream into real Groups and Nodes.
        :rtype: (list[ast], list[ast], list[ast])
        """
        tree = tree or []  # if its abstract, it comes in with no body

        groups = []
        nodes = []
        body = []
        for el in tree:
            if el['nodeType'] in ('Stmt_Function', 'Stmt_ClassMethod', 'Expr_Closure'):
                nodes.append(el)
            elif el['nodeType'] in ('Stmt_Class', 'Stmt_Namespace', 'Stmt_Trait'):
                groups.append(el)
            else:
                tup = PHP.separate_namespaces(children(el))
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
        Given a tree element of all the lines in a function, create the node along
        with the calls and variables internal to it.
        Also make the nested subnodes

        :param tree ast:
        :param parent Group:
        :rtype: list[Node]
        """
        assert tree['nodeType'] in ('Stmt_Function', 'Stmt_ClassMethod', 'Expr_Closure')

        if tree['nodeType'] == 'Expr_Closure':
            token = '(Closure)'
        else:
            token = tree['name']['name']
        print("processing node", token, parent)
        is_constructor = token == '__construct' and parent.group_type == GROUP_TYPE.CLASS

        tree_body = tree['stmts']
        subgroup_trees, subnode_trees, this_scope_body = PHP.separate_namespaces(tree_body)
        assert not subgroup_trees
        calls = make_calls(this_scope_body)
        variables = make_local_variables(this_scope_body, parent)
        node = Node(token, calls, variables, parent=parent,
                    is_constructor=is_constructor, line_number=lineno(tree))

        subnodes = flatten([PHP.make_nodes(t, parent) for t in subnode_trees])
        return [node] + subnodes

    @staticmethod
    def make_root_node(lines, parent):
        """
        The "root_node" are is an implict node of lines which are executed in the global
        scope on the file itself and not otherwise part of any function.

        :param lines list[ast]:
        :param parent Group:
        :rtype: Node
        """
        token = "(global)"
        line_number = lines and lineno(lines[0]) or 0
        calls = make_calls(lines)
        variables = make_local_variables(lines, parent)
        root_node = Node(token, calls, variables, parent=parent,
                         line_number=line_number)
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
        assert tree['nodeType'] in ('Stmt_Class', 'Stmt_Namespace', 'Stmt_Trait')
        subgroup_trees, node_trees, body_trees = PHP.separate_namespaces(tree['stmts'])

        token = get_name(tree)
        display_name = tree['nodeType'][5:]

        inherits = get_inherits(tree)

        print("processing group", token)
        class_group = Group(token, GROUP_TYPE.CLASS, display_name,
                            inherits=inherits, parent=parent, line_number=lineno(tree))

        for subgroup_tree in subgroup_trees:
            class_group.add_subgroup(PHP.make_class_group(subgroup_tree, class_group))

        for node_tree in node_trees:
            for new_node in PHP.make_nodes(node_tree, parent=class_group):
                class_group.add_node(new_node)

        if tree['nodeType'] == 'Stmt_Namespace':
            class_group.add_node(PHP.make_root_node(body_trees, class_group))
            for node in class_group.nodes:
                node.variables += [Variable(n.token, n, line_number=n.line_number)
                                   for n in class_group.nodes]

        return class_group
