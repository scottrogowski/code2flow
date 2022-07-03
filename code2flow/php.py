import json
import os
import subprocess

from .model import (Group, Node, Call, Variable, BaseLanguage,
                    OWNER_CONST, GROUP_TYPE, is_installed, flatten, djoin)


def lineno(tree):
    """
    Return the line number of the AST
    :param tree ast:
    :rtype: int
    """
    return tree['attributes']['startLine']


def get_name(tree, from_='name'):
    """
    Get the name (token) of the AST node.
    :param tree ast:
    :rtype: str|None
    """
    # return tree['name']['name']
    if 'name' in tree and isinstance(tree['name'], str):
        return tree['name']

    if 'parts' in tree:
        return djoin(tree['parts'])

    if from_ in tree:
        return get_name(tree[from_])

    return None


def get_call_from_expr(func_expr):
    """
    Given an ast that represents a send call, clear and create our
    generic Call object. Some calls have no chance at resolution (e.g. array[2](param))
    so we return nothing instead.

    :param func_expr ast:
    :rtype: Call|None
    """
    if func_expr['nodeType'] == 'Expr_FuncCall':
        token = get_name(func_expr)
        owner_token = None
    elif func_expr['nodeType'] == 'Expr_New' and func_expr['class'].get('parts'):
        token = '__construct'
        owner_token = get_name(func_expr['class'])
    elif func_expr['nodeType'] == 'Expr_MethodCall':
        # token = func_expr['name']['name']
        token = get_name(func_expr)
        if 'var' in func_expr['var']:
            owner_token = OWNER_CONST.UNKNOWN_VAR
        else:
            owner_token = get_name(func_expr['var'])
    elif func_expr['nodeType'] == 'Expr_BinaryOp_Concat' and func_expr['right']['nodeType'] == 'Expr_FuncCall':
        token = get_name(func_expr['right'])
        if 'class' in func_expr['left']:
            owner_token = get_name(func_expr['left']['class'])
        else:
            owner_token = get_name(func_expr['left'])
    elif func_expr['nodeType'] == 'Expr_StaticCall':
        token = get_name(func_expr)
        owner_token = get_name(func_expr['class'])
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
    Given an ast tree walk it to get every node. For PHP, the exception
    is that we return Expr_BinaryOp_Concat which has internal nodes but
    is important to process as a whole.

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
    Given an ast tree get all children. For PHP, children are anything
    with a nodeType.

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
        call = get_call_from_expr(expr)
        calls.append(call)
    ret = list(filter(None, calls))

    return ret


def process_assign(assignment_el):
    """
    Given an assignment statement, return a
    Variable that points_to the type of object being assigned.

    :param assignment_el ast:
    :rtype: Variable
    """
    assert assignment_el['nodeType'] == 'Expr_Assign'
    if 'name' not in assignment_el['var']:
        return None

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

    :param tree_el ast:
    :param parent Group:
    :rtype: list[Variable]
    """
    variables = []
    for el in walk(tree_el):
        if el['nodeType'] == 'Expr_Assign':
            variables.append(process_assign(el))
        if el['nodeType'] == 'Stmt_Use':
            for use in el['uses']:
                owner_token = djoin(use['name']['parts'])
                token = use['alias']['name'] if use['alias'] else owner_token
                variables.append(Variable(token, points_to=owner_token,
                                          line_number=lineno(el)))

    # Make a 'this'/'self' variable for use anywhere we need it that points to the class
    if isinstance(parent, Group) and parent.group_type in GROUP_TYPE.CLASS:
        variables.append(Variable('this', parent, line_number=parent.line_number))
        variables.append(Variable('self', parent, line_number=parent.line_number))

    return list(filter(None, variables))


def get_inherits(tree):
    """
    Get the various types of inheritances this class/namespace/trait can have

    :param tree ast:
    :rtype: list[str]
    """
    ret = []

    if tree.get('extends', {}):
        ret.append(djoin(tree['extends']['parts']))

    for stmt in tree.get('stmts', []):
        if stmt['nodeType'] == 'Stmt_TraitUse':
            for trait in stmt['traits']:
                ret.append(djoin(trait['parts']))
    return ret


def run_ast_parser(filename):
    """
    Parse the php file and return the output + the returncode
    Separate function b/c unittesting and asserting php-parser installation.
    :param filename str:
    :type: str, int
    """

    script_loc = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                              "get_ast.php")
    cmd = ["php", script_loc, filename]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return proc.communicate()[0], proc.returncode


class PHP(BaseLanguage):
    @staticmethod
    def assert_dependencies():
        """Assert that php and php-parser are installed"""
        assert is_installed('php'), "No php installation could be found"
        self_ref = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                "get_ast.php")
        outp, returncode = run_ast_parser(self_ref)
        path = os.path.dirname(os.path.realpath(__file__))
        assert_msg = 'Error running the PHP parser. From the `%s` directory, run ' \
                     '`composer require nikic/php-parser "^4.10"`.' % path
        assert not returncode, assert_msg
        return outp

    @staticmethod
    def get_tree(filename, lang_params):
        """
        Get the entire AST for this file

        :param filename str:
        :param lang_params LanguageParams:
        :rtype: ast
        """

        outp, returncode = run_ast_parser(filename)
        if returncode:
            raise AssertionError(
                "Could not parse file %r. You may have a syntax error. "
                "For more detail, try running with `php %s`. " %
                (filename, filename))

        tree = json.loads(outp)
        assert isinstance(tree, list)
        if len(tree) == 1 and tree[0]['nodeType'] == 'Stmt_InlineHTML':
            raise AssertionError("Tried to parse a file that is not likely PHP")
        return tree

    @staticmethod
    def separate_namespaces(tree):
        """
        Given a tree element, recursively separate that AST into lists of ASTs for the
        subgroups, nodes, and body. This is an intermediate step to allow for
        cleaner processing downstream

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
        is_constructor = token == '__construct' and parent.group_type == GROUP_TYPE.CLASS

        tree_body = tree['stmts']
        subgroup_trees, subnode_trees, this_scope_body = PHP.separate_namespaces(tree_body)
        assert not subgroup_trees
        calls = make_calls(this_scope_body)
        variables = make_local_variables(this_scope_body, parent)

        if parent.group_type == GROUP_TYPE.CLASS and parent.parent.group_type == GROUP_TYPE.NAMESPACE:
            import_tokens = [djoin(parent.parent.token, parent.token, token)]
        if parent.group_type in (GROUP_TYPE.NAMESPACE, GROUP_TYPE.CLASS):
            import_tokens = [djoin(parent.token, token)]
        else:
            import_tokens = [token]

        node = Node(token, calls, variables, parent, import_tokens=import_tokens,
                    is_constructor=is_constructor, line_number=lineno(tree))

        subnodes = flatten([PHP.make_nodes(t, parent) for t in subnode_trees])
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
        line_number = lineno(lines[0]) if lines else 0
        calls = make_calls(lines)
        variables = make_local_variables(lines, parent)
        root_node = Node(token, calls, variables, parent,
                         line_number=line_number)
        return root_node

    @staticmethod
    def make_class_group(tree, parent):
        """
        Given an AST for the subgroup (a class), generate that subgroup.
        In this function, we will also need to generate all of the nodes internal
        to the group.

        Specific to PHP, this can also be a namespace or class.

        :param tree ast:
        :param parent Group:
        :rtype: Group
        """
        assert tree['nodeType'] in ('Stmt_Class', 'Stmt_Namespace', 'Stmt_Trait')
        subgroup_trees, node_trees, body_trees = PHP.separate_namespaces(tree['stmts'])

        token = get_name(tree['name'])
        display_type = tree['nodeType'][5:]

        inherits = get_inherits(tree)

        group_type = GROUP_TYPE.CLASS
        if display_type == 'Namespace':
            group_type = GROUP_TYPE.NAMESPACE

        import_tokens = [token]
        if display_type == 'Class' and parent.group_type == GROUP_TYPE.NAMESPACE:
            import_tokens = [djoin(parent.token, token)]

        class_group = Group(token, group_type, display_type, import_tokens=import_tokens,
                            parent=parent, inherits=inherits, line_number=lineno(tree))

        for subgroup_tree in subgroup_trees:
            class_group.add_subgroup(PHP.make_class_group(subgroup_tree, class_group))

        for node_tree in node_trees:
            for new_node in PHP.make_nodes(node_tree, parent=class_group):
                class_group.add_node(new_node)

        if group_type == GROUP_TYPE.NAMESPACE:
            class_group.add_node(PHP.make_root_node(body_trees, class_group))
            for node in class_group.nodes:
                node.variables += [Variable(n.token, n, line_number=n.line_number)
                                   for n in class_group.nodes]

        return class_group

    @staticmethod
    def file_import_tokens(filename):
        """
        Returns the token(s) we would use if importing this file from another.

        :param filename str:
        :rtype: list[str]
        """
        return []
