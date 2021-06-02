import json
import subprocess

from .model import (Group, Node, Call, Variable, BaseLanguage,
                    OWNER_CONST, is_installed, djoin, flatten)


def resolve_owner(owner_struct):
    """
    Resolve who owns the call object.
    So if the expression is i_ate.pie(). And i_ate is a Person, the callee is Person.
    This is returned as a string and eventually set to the owner_token in the call

    :param ast callee:
    :rtype: str
    """
    try:
        if not owner_struct or not isinstance(owner_struct, list):
            return None
        if owner_struct[0] == 'begin':
            # skip complex ownership
            return "UNKNOWN_VAR"
        if owner_struct[0] == 'send':
            # sends are complex too
            return "UNKNOWN_VAR"
        if owner_struct[0] == 'lvar':
            # var.func()
            return owner_struct[1]
        if owner_struct[0] == 'ivar':
            # @var.func()
            return owner_struct[1]
        if owner_struct[0] == 'self':
            return 'self'
        if owner_struct[0] == 'const':
            return owner_struct[2]

        return "UNKNOWN_VAR"
        # if owner_struct[1]:
        #     return djoin(resolve_owner(owner_struct[1]), owner_struct[2])
        # return owner_struct[2]
    except:
        print('\a'); import ipdb; ipdb.set_trace()


def get_call_from_send_element(func):
    """
    Given a Ruby ast that represents a send call, clear and create our
    generic Call object. Some calls have no chance at resolution (e.g. array[2](param))
    so we return nothing instead.

    :param func dict:
    :rtype: Call|None
    # TODO filter out builtin methods???
    """
    owner_struct = func[1]
    token = func[2]
    owner = resolve_owner(owner_struct)
    if owner and token == 'new':
        return Call(token=owner)
        # TODO
        # owner_token=owner,
        # definite_constructor=True)
    return Call(token=token,
                owner_token=owner)


def walk(tree):
    if not tree:
        return []
    ret = [tree]
    for el in tree:
        if isinstance(el, list):
            ret += walk(el)
    return ret


def make_calls(body):
    """
    Given a list of lines, find all calls in this list.

    :param list|dict body:
    :rtype: list[Call]
    """
    calls = []
    for element in walk(body):
        if element[0] == 'send':
            call = get_call_from_send_element(element)
            if call:
                calls.append(call)
    return calls


def process_assign(element):
    """
    Given an element from the ast which is an assignment statement, return a
    Variable that points_to the type of object being assigned. The
    points_to is often a string but that is resolved later.

    :param element ast:
    :rtype: Variable
    """

    assert element[0] == 'lvasgn'
    varname = element[1]
    if element[2][0] == 'send':
        call = get_call_from_send_element(element[2])
        return Variable(varname, call)
    # else is something like `varname = num`
    return None


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
    variables = []
    for element in tree:
        if element[0] == 'lvasgn':
            variables.append(process_assign(element))

    # Make a 'self' variable for use anywhere we need it that points to the class
    if isinstance(parent, Group) and parent.group_type == 'CLASS':
        variables.append(Variable('self', parent))

    variables = list(filter(None, variables))
    return variables


def get_tree_body(tree):
    if tree[0] == 'module':
        body_struct = tree[2]
    elif tree[0] == 'defs':
        body_struct = tree[4]
    else:
        body_struct = tree[3]

    if not body_struct:
        return []
    if body_struct[0] == 'begin':
        return body_struct
    return [body_struct]


def get_mixins(body_tree):
    mixins = []
    for el in body_tree:
        if el[0] == 'send' and el[2] == 'include':
            mixins.append(el[3][2])
    return mixins


class Ruby(BaseLanguage):

    @staticmethod
    def assert_dependencies():
        assert is_installed('ruby-parse'), "The ruby-parse gem is requred to " \
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
                "Ruby-parse could not parse file %r. You may have a syntax error or "
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
        Given an AST body, recursively separate that AST into lists of ASTs for the
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
        Given an ast of all the lines in a function, create the node along with the
        calls and variables internal to it.
        Also make the nested subnodes

        :param tree ast:
        :param parent Group:
        :rtype: list[Node]
        """
        if tree[0] == 'defs':
            token = tree[2]
        else:
            token = tree[1]

        is_constructor = token == 'initialize'

        tree_body = get_tree_body(tree)
        subgroup_trees, subnode_trees, this_scope_body = Ruby.separate_namespaces(tree_body)
        assert not subgroup_trees
        calls = make_calls(this_scope_body)
        variables = make_local_variables(this_scope_body, parent)

        node = Node(token, calls, variables, parent=parent,
                    is_constructor=is_constructor)

        # This is a little different from the other languages in that
        # the node is now on the parent
        subnodes = flatten([Ruby.make_nodes(t, parent) for t in subnode_trees])
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
        assert tree[0] in ('class', 'module')
        tree_body = get_tree_body(tree)
        subgroup_trees, node_trees, body_trees = Ruby.separate_namespaces(tree_body)
        assert not subgroup_trees
        # print('\a'); import ipdb; ipdb.set_trace()

        group_type = 'CLASS'
        assert tree[1][0] == 'const'
        token = tree[1][2]

        mixins = get_mixins(body_trees)

        class_group = Group(token, group_type, inherits=mixins, parent=parent)

        for node_tree in node_trees:
            for new_node in Ruby.make_nodes(node_tree, parent=class_group):
                class_group.add_node(new_node)

        for node in class_group.nodes:
            node.variables += [Variable(n.token, n) for n in class_group.nodes]

        return class_group
