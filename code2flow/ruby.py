import json
import subprocess

from .model import (Group, Node, Call, Variable, BaseLanguage,
                    OWNER_CONST, GROUP_TYPE, is_installed, flatten)


def resolve_owner(owner_el):
    """
    Resolve who owns the call, if anyone.
    So if the expression is i_ate.pie(). And i_ate is a Person, the callee is Person.
    This is returned as a string and eventually set to the owner_token in the call

    :param owner_el ast:
    :rtype: str|None
    """
    if not owner_el or not isinstance(owner_el, list):
        return None
    if owner_el[0] == 'begin':
        # skip complex ownership
        return OWNER_CONST.UNKNOWN_VAR
    if owner_el[0] == 'send':
        # sends are complex too
        return OWNER_CONST.UNKNOWN_VAR
    if owner_el[0] == 'lvar':
        # var.func()
        return owner_el[1]
    if owner_el[0] == 'ivar':
        # @var.func()
        return owner_el[1]
    if owner_el[0] == 'self':
        return 'self'
    if owner_el[0] == 'const':
        return owner_el[2]

    return OWNER_CONST.UNKNOWN_VAR


def get_call_from_send_el(func_el):
    """
    Given an ast that represents a send call, clear and create our
    generic Call object. Some calls have no chance at resolution (e.g. array[2](param))
    so we return nothing instead.

    :param func_el ast:
    :rtype: Call|None
    """
    owner_el = func_el[1]
    token = func_el[2]
    owner = resolve_owner(owner_el)
    if owner and token == 'new':
        # Taking out owner_token for constructors as a little hack to make it work
        return Call(token=owner)
    return Call(token=token,
                owner_token=owner)


def walk(tree_el):
    """
    Given an ast element (list), walk it in a dfs to get every el (list) out of it

    :param tree_el ast:
    :rtype: list[ast]
    """

    if not tree_el:
        return []
    ret = [tree_el]
    for el in tree_el:
        if isinstance(el, list):
            ret += walk(el)
    return ret


def make_calls(body_el):
    """
    Given a list of lines, find all calls in this list.

    :param body_el ast:
    :rtype: list[Call]
    """
    calls = []
    for el in walk(body_el):
        if el[0] == 'send':
            calls.append(get_call_from_send_el(el))
    return calls


def process_assign(assignment_el):
    """
    Given an assignment statement, return a
    Variable that points_to the type of object being assigned. The
    points_to is often a string but that is resolved later.

    :param assignment_el ast:
    :rtype: Variable
    """

    assert assignment_el[0] == 'lvasgn'
    varname = assignment_el[1]
    if assignment_el[2][0] == 'send':
        call = get_call_from_send_el(assignment_el[2])
        return Variable(varname, call)
    # else is something like `varname = num`
    return None


def make_local_variables(tree_el, parent):
    """
    Given an ast of all the lines in a function, generate a list of
    variables in that function. Variables are tokens and what they link to.
    In this case, what it links to is just a string. However, that is resolved
    later.

    Also return variables for the outer scope parent

    :param tree_el ast:
    :param parent Group:
    :rtype: list[Variable]
    """
    variables = []
    for el in tree_el:
        if el[0] == 'lvasgn':
            variables.append(process_assign(el))

    # Make a 'self' variable for use anywhere we need it that points to the class
    if isinstance(parent, Group) and parent.group_type == GROUP_TYPE.CLASS:
        variables.append(Variable('self', parent))

    variables = list(filter(None, variables))
    return variables


def as_lines(tree_el):
    """
    Ruby ast bodies are structured differently depending on circumstances.
    This ensures that they are structured as a list of statements

    :param tree_el ast:
    :rtype: list[tree_el]
    """
    if not tree_el:
        return []
    if isinstance(tree_el[0], list):
        return tree_el
    if tree_el[0] == 'begin':
        return tree_el
    return [tree_el]


def get_tree_body(tree_el):
    """
    Depending on the type of element, get the body of that element

    :param tree_el ast:
    :rtype: list[tree_el]
    """

    if tree_el[0] == 'module':
        body_struct = tree_el[2]
    elif tree_el[0] == 'defs':
        body_struct = tree_el[4]
    else:
        body_struct = tree_el[3]
    return as_lines(body_struct)


def get_inherits(tree, body_tree):
    """
    Get the various types of inheritances this class/module can have

    :param tree ast:
    :param body_tree list[ast]
    :rtype: list[str]
    """
    inherits = []

    # extends
    if tree[0] == 'class' and tree[2]:
        inherits.append(tree[2][2])

    # module automatically extends same-named modules
    if tree[0] == 'module':
        inherits.append(tree[1][2])

    # mixins
    for el in body_tree:
        if el[0] == 'send' and el[2] == 'include':
            inherits.append(el[3][2])

    return inherits


class Ruby(BaseLanguage):
    @staticmethod
    def assert_dependencies():
        """Assert that ruby-parse is installed"""
        assert is_installed('ruby-parse'), "The 'parser' gem is requred to " \
                                           "parse ruby files but was not found " \
                                           "on the path. Install it from gem " \
                                           "and try again."

    @staticmethod
    def get_tree(filename, lang_params):
        """
        Get the entire AST for this file

        :param filename str:
        :param lang_params LanguageParams:
        :rtype: ast
        """
        version_flag = "--" + lang_params.ruby_version
        cmd = ["ruby-parse", "--emit-json", version_flag, filename]
        output = subprocess.check_output(cmd, stderr=subprocess.PIPE)
        try:
            tree = json.loads(output)
        except json.decoder.JSONDecodeError:
            raise AssertionError(
                "Ruby-parse could not parse file %r. You may have a syntax error. "
                "For more detail, try running the command `ruby-parse %s`. " %
                (filename, filename)) from None
        assert isinstance(tree, list)

        if tree[0] not in ('module', 'begin'):
            # one-line files
            tree = [tree]
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
        groups = []
        nodes = []
        body = []
        for el in as_lines(tree):
            if el[0] in ('def', 'defs'):
                nodes.append(el)
            elif el[0] in ('class', 'module'):
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
        if tree[0] == 'defs':
            token = tree[2]  # def self.func
        else:
            token = tree[1]  # def func

        is_constructor = token == 'initialize' and parent.group_type == GROUP_TYPE.CLASS

        tree_body = get_tree_body(tree)
        subgroup_trees, subnode_trees, this_scope_body = Ruby.separate_namespaces(tree_body)
        assert not subgroup_trees
        calls = make_calls(this_scope_body)
        variables = make_local_variables(this_scope_body, parent)
        node = Node(token, calls, variables,
                    parent=parent, is_constructor=is_constructor)

        # This is a little different from the other languages in that
        # the node is now on the parent
        subnodes = flatten([Ruby.make_nodes(t, parent) for t in subnode_trees])
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
        assert tree[0] in ('class', 'module')
        tree_body = get_tree_body(tree)
        subgroup_trees, node_trees, body_trees = Ruby.separate_namespaces(tree_body)

        group_type = GROUP_TYPE.CLASS
        if tree[0] == 'module':
            group_type = GROUP_TYPE.NAMESPACE
        display_type = tree[0].capitalize()
        assert tree[1][0] == 'const'
        token = tree[1][2]

        inherits = get_inherits(tree, body_trees)
        class_group = Group(token, group_type, display_type,
                            inherits=inherits, parent=parent)

        for subgroup_tree in subgroup_trees:
            class_group.add_subgroup(Ruby.make_class_group(subgroup_tree, class_group))

        for node_tree in node_trees:
            for new_node in Ruby.make_nodes(node_tree, parent=class_group):
                class_group.add_node(new_node)
        for node in class_group.nodes:
            node.variables += [Variable(n.token, n) for n in class_group.nodes]

        return class_group

    @staticmethod
    def file_import_tokens(filename):
        """
        Returns the token(s) we would use if importing this file from another.

        :param filename str:
        :rtype: list[str]
        """
        return []
