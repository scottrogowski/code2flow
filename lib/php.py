import json
import os
import subprocess

from .model import (Group, Node, Call, Variable, BaseLanguage,
                    OWNER_CONST, GROUP_TYPE, is_installed, flatten)


# def resolve_owner(owner_el):
#     """
#     Resolve who owns the call, if anyone.
#     So if the expression is i_ate.pie(). And i_ate is a Person, the callee is Person.
#     This is returned as a string and eventually set to the owner_token in the call

#     :param owner_el ast:
#     :rtype: str|None
#     """
#     if not owner_el or not isinstance(owner_el, list):
#         return None
#     if owner_el[0] == 'begin':
#         # skip complex ownership
#         return OWNER_CONST.UNKNOWN_VAR
#     if owner_el[0] == 'send':
#         # sends are complex too
#         return OWNER_CONST.UNKNOWN_VAR
#     if owner_el[0] == 'lvar':
#         # var.func()
#         return owner_el[1]
#     if owner_el[0] == 'ivar':
#         # @var.func()
#         return owner_el[1]
#     if owner_el[0] == 'self':
#         return 'self'
#     if owner_el[0] == 'const':
#         return owner_el[2]

#     return OWNER_CONST.UNKNOWN_VAR


def get_call_from_expr(func_expr):
    """
    Given an ast that represents a send call, clear and create our
    generic Call object. Some calls have no chance at resolution (e.g. array[2](param))
    so we return nothing instead.

    :param func_expr ast:
    :rtype: Call|None
    """
    try:
        if func_expr['nodeType'] == 'Expr_FuncCall':
            token = func_expr['name']['parts'][0]
            owner_token = None
        elif func_expr['nodeType'] == 'Expr_New' and func_expr['class'].get('parts'):
            token = '__construct'
            owner_token = func_expr['class']['parts'][0]
        elif func_expr['nodeType'] == 'Expr_MethodCall':
            token = func_expr['name']['name']
            if 'var' in func_expr['var']:
                owner_token = OWNER_CONST.UNKNOWN_VAR
            else:
                owner_token = func_expr['var']['name']
        elif func_expr['nodeType'] == 'Expr_BinaryOp_Concat':
            token = func_expr['right']['name']['parts'][0]
            owner_token = func_expr['left']['name']
        else:
            return None
    except:
        print('\a'); import ipdb; ipdb.set_trace()

    if owner_token and token == '__construct':
        # Taking out owner_token for constructors as a little hack to make it work
        return Call(token=owner_token)
    ret = Call(token=token,
               owner_token=owner_token)
    print("returning call", ret)
    # print(func_expr)
    return ret


def walk(tree):
    """
    Given an ast tree walk it to get every node

    :param tree_el ast:
    :rtype: list[ast]
    """
    ret = []
    if isinstance(tree, list):
        for el in tree:
            ret += walk(el)
        return ret

    assert isinstance(tree, dict)
    if 'expr' in tree:
        ret.append(tree['expr'])
        ret += walk(tree['expr'])
    if 'var' in tree:
        ret.append(tree['var'])
        ret += walk(tree['var'])

    # if 'nodeType' in tree:
    #     ret.append(tree)
    #     for el in tree.values():
    #         if isinstance(el, dict):
    #             ret += walk(el)
    return ret


def make_calls(body_el):
    """
    Given a list of lines, find all calls in this list.

    :param body_el ast:
    :rtype: list[Call]
    """
    calls = []
    # print('\a'); import ipdb; ipdb.set_trace()
    for expr in walk(body_el):
        # print("walk expre", expr)
        calls.append(get_call_from_expr(expr))
    # print('\a'); import ipdb; ipdb.set_trace()
    return list(filter(None, calls))


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
        return Variable(varname, call)
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
    # print('\a'); import ipdb; ipdb.set_trace()
    variables = []
    for el in walk(tree_el):
        if el['nodeType'] == 'Expr_Assign':
            variables.append(process_assign(el))

    # Make a 'this' variable for use anywhere we need it that points to the class
    if isinstance(parent, Group) and parent.group_type == GROUP_TYPE.CLASS:
        variables.append(Variable('this', parent))

    # TODO maybe a self variable too for class variables

    variables = list(filter(None, variables))
    return variables


# def as_lines(tree_el):
#     """
#     PHP ast bodies are structured differently depending on circumstances.
#     This ensures that they are structured as a list of statements

#     :param tree_el ast:
#     :rtype: list[tree_el]
#     """
#     if not tree_el:
#         return []
#     if isinstance(tree_el[0], list):
#         return tree_el
#     if tree_el[0] == 'begin':
#         return tree_el
#     return [tree_el]


# def get_tree_body(tree_el):
#     """
#     Depending on the type of element, get the body of that element

#     :param tree_el ast:
#     :rtype: list[tree_el]
#     """

#     if tree_el[0] == 'module':
#         body_struct = tree_el[2]
#     elif tree_el[0] == 'defs':
#         body_struct = tree_el[4]
#     else:
#         body_struct = tree_el[3]
#     return as_lines(body_struct)


# def get_inherits(tree, body_tree):
#     """
#     Get the various types of inheritances this class/module can have

#     :param tree ast:
#     :param body_tree list[ast]
#     :rtype: list[str]
#     """
#     inherits = []

#     # extends
#     if tree[0] == 'class' and tree[2]:
#         inherits.append(tree[2][2])

#     # module automatically extends same-named modules
#     if tree[0] == 'module':
#         inherits.append(tree[1][2])

#     # mixins
#     for el in body_tree:
#         if el[0] == 'send' and el[2] == 'include':
#             inherits.append(el[3][2])

#     return inherits


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
        groups = []
        nodes = []
        body = []
        for el in tree:
            if el['nodeType'] in ('Stmt_Function', 'Stmt_ClassMethod'):
                nodes.append(el)
            elif el['nodeType'] in ('Stmt_Class',):
                groups.append(el)
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
        assert tree['nodeType'] in ('Stmt_Function', 'Stmt_ClassMethod')

        token = tree['name']['name']
        print("processing node", token, parent)
        is_constructor = token == '__construct' and parent.group_type == GROUP_TYPE.CLASS

        tree_body = tree['stmts']
        subgroup_trees, subnode_trees, this_scope_body = PHP.separate_namespaces(tree_body)
        assert not subgroup_trees
        calls = make_calls(this_scope_body)
        variables = make_local_variables(this_scope_body, parent) # TODO
        node = Node(token, calls, variables, parent=parent,
                    is_constructor=is_constructor)

        # This is a little different from the other languages in that
        # the node is now on the parent
        # subnodes = flatten([PHP.make_nodes(t, parent) for t in subnode_trees])
        subnodes = []
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
        calls = make_calls(lines)
        variables = make_local_variables(lines, parent)
        root_node = Node(token, calls, variables, parent=parent)
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
        assert tree['nodeType'] in ('Stmt_Class',)
        subgroup_trees, node_trees, body_trees = PHP.separate_namespaces(tree['stmts'])

        token = tree['name']['name']

        # inherits = get_inherits(tree, body_trees)
        inherits = [] # TODO

        class_group = Group(token, GROUP_TYPE.CLASS, 'Class',
                            inherits=inherits, parent=parent)

        # TODO
        assert not subgroup_trees
        # for subgroup_tree in subgroup_trees:
        #     class_group.add_subgroup(PHP.make_class_group(subgroup_tree, class_group))

        for node_tree in node_trees:
            for new_node in PHP.make_nodes(node_tree, parent=class_group):
                class_group.add_node(new_node)

        # TODO
        # for node in class_group.nodes:
        #     node.variables += [Variable(n.token, n) for n in class_group.nodes]

        return class_group
