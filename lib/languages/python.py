import ast as asst
import random
import os

TRUNK_COLOR = '#966F33'
LEAF_COLOR = '#6db33f'
EDGE_COLOR = "#cf142b"


"""
I think I need to spend some time sitting down and drawing out
the detailed relationships between Variable, Call, Node, Group, etc.

I think doing so would go a long way.

Variable including defined functions and classes makes a lot of sense actually.
Functions themselves are tokens.
So then, when we say variables, we are looking at everything in scope.
Then, matching them makes a whole lot more sense

"""


class Variable():
    def __init__(self, token, rhs, line_number, var_type):
        self.token = token
        self.rhs = rhs
        self.line_number = line_number
        self.var_type = var_type
        self.parent = None

    def __repr__(self):
        return f"<Variable type={self.var_type} token={self.token} rhs={self.rhs}"


class Call():
    def __init__(self, token, line_number, owner_token=None):
        self.token = token
        self.owner_token = owner_token
        self.line_number = line_number
        self.owner_var = None

    def __repr__(self):
        return f"<Call owner_token={self.owner_token} token={self.token}>"


class Node():
    def __init__(self, token, line_number, calls, variables, parent):
        self.token = token
        self.line_number = line_number
        self.calls = calls
        self.variables = variables
        self.parent = parent

        self.uid = "node_" + random.randbytes(4).hex()

        # Assume it is a leaf and a trunk until determined otherwise
        self.is_leaf = True  # it calls nothing else
        self.is_trunk = True  # nothing calls it

    def __repr__(self):
        return f"<Node token={self.token} parent={self.parent}>"

    def name(self):
        return f"{self.parent.filename()}:{self.token_with_ownership()}"

    def token_with_ownership(self):
        if self.parent and self.parent.group_type == 'CLASS':
            return self.parent.token + '.' + self.token
        return self.token

    def label(self):
        return f"{self.line_number}: {self.token}"

    def remove_from_parent(self):
        self.parent.nodes = [n for n in self.parent.nodes if n != self]

    def resolve_variables(self, file_groups):
        if self.variables:
            print('\a'); from icecream import ic; ic("resolve_variables", self, self.variables)

        for variable in self.variables:
            if variable.var_type == 'IMPORT':
                for file_group in file_groups:
                    for group in file_group.all_groups():
                        print('\a'); from icecream import ic; ic("check if match", group, variable)
                        if group.token == variable.rhs: # variable.module maybe
                            ic("match")
                            variable.parent = group
                        else:
                            ic("not match")

            elif variable.var_type == 'ASSIGNMENT':
                if variable.rhs.owner_token:
                    # Only process Class(); Not a.Class()
                    continue
                for file_group in file_groups:
                    for group in file_group.all_groups():
                        if group.token == variable.rhs.token:
                            variable.parent = group

    def resolve_call_owners(self):
        in_scope_variables = []
        parent = self.parent
        while parent:
            in_scope_variables += parent.get_variables()
            parent = parent.parent

        print('\a'); from icecream import ic; ic("resolve_call_owners", self, in_scope_variables)

        for call in self.calls:
            ic("call", call)

            if not call.owner_token:
                continue
            if call.owner_token == 'self':
                # TODO this is weird
                call.owner_var = self
                continue

            local_variables = [v for v in self.variables
                               if v.line_number < call.line_number]
            local_variables.sort(key=lambda v: v.line_number, reverse=True)
            variables = local_variables + in_scope_variables

            for var in variables:
                if var.token == call.owner_token:
                    call.owner_var = var
                    break

            print('\a'); from icecream import ic; ic(call)
            # print('\a'); from icecream import ic; ic(variables)

    def to_dot(self, no_grouping):
        attributes = {
            # 'splines': "ortho",
            'label': self.label(),
            'name': self.name(),
            'shape': "rect",
            'style': 'rounded,filled',
        }
        if self.is_trunk:
            attributes['fillcolor'] = TRUNK_COLOR
        elif self.is_leaf:
            attributes['fillcolor'] = LEAF_COLOR

        ret = self.uid + ' ['
        for k, v in attributes.items():
            ret += f'{k}="{v}" '
        ret += ']'

        return ret


class Edge():
    def __init__(self, node0, node1):
        self.node0 = node0
        self.node1 = node1

        # When we draw the edge, we know the calling function is definitely not a leaf...
        # and the called function is definitely not a trunk
        node0.is_leaf = False
        node1.is_trunk = False

    def __repr__(self):
        return f"<Edge {self.node0} -> {self.node1}"

    def to_dot(self):
        '''
        Returns string format for embedding in a dotfile. Example output:
        node_uid_a -> node_uid_b [color='#aaa' penwidth='2']
        '''
        ret = self.node0.uid + ' -> ' + self.node1.uid
        ret += f' [color="{EDGE_COLOR}" penwidth="2"]'
        return ret


class Group():
    def __init__(self, token, line_number, group_type, parent=None):
        self.token = token
        self.line_number = line_number
        self.nodes = []
        self.root_node = None
        self.subgroups = []
        self.parent = parent
        self.group_type = group_type

        self.uid = "cluster_" + random.randbytes(4).hex()  # group doesn't work by syntax rules

    def __repr__(self):
        return f"<Group token={self.token} type={self.group_type}>"

    def label(self):
        return f"{self.group_type}: {self.token}"

    def filename(self):
        if self.group_type == 'MODULE':
            return self.token + '.py'
        return self.parent.filename()

    def add_subgroup(self, sg):
        self.subgroups.append(sg)

    def add_node(self, node, is_root=False):
        self.nodes.append(node)
        if is_root:
            self.root_node = node

    def all_nodes(self):
        ret = list(self.nodes)
        for subgroup in self.subgroups:
            ret += subgroup.all_nodes()
        return ret

    def all_groups(self):
        ret = [self]
        for subgroup in self.subgroups:
            ret += subgroup.all_groups()
        return ret

    def get_variables(self):
        if self.root_node:
            return sorted(self.root_node.variables, key=lambda v: v.line_number, reverse=True)
        else:
            return []

    def remove_from_parent(self):
        if self.parent:
            self.parent.subgroups = [g for g in self.parent.subgroups if g != self]

    def to_dot(self):
        """
        Returns string format for embedding in a dotfile. Example output:
        subgraph group_uid_a {
            node_uid_b node_uid_c;
            label='class_name';
            ...
            subgraph group_uid_z {
                ...
            }
            ...
        }
        """

        ret = 'subgraph ' + self.uid + ' {\n'
        if self.nodes:
            ret += '    '
            ret += ' '.join(node.uid for node in self.nodes)
            ret += ';\n'
        attributes = {
            'label': self.label(),
            'name': self.token,
            'style': 'filled',
        }
        for k, v in attributes.items():
            ret += f'    {k}="{v}";\n'
        ret += '    graph[style=dotted];\n'
        for subgroup in self.subgroups:
            ret += '    ' + ('\n'.join('    ' + ln for ln in
                                       subgroup.to_dot().split('\n'))).strip() + '\n'
        ret += '};\n'
        return ret


def _get_func(func):
    if type(func) == asst.Attribute:
        owner_token = []
        val = func.value
        while True:
            try:
                owner_token.append(getattr(val, 'attr', val.id))
            except:
                pass
            val = getattr(val, 'value', None)
            if not val:
                break
        owner_token = '.'.join(reversed(owner_token))
        return Call(token=func.attr, line_number=func.lineno, owner_token=owner_token)
    if type(func) == asst.Name:
        return Call(token=func.id, line_number=func.lineno)
    raise AssertionError("Unknown function type %r" % type(func))


def _make_calls(lines):
    calls = []
    for ast in lines:
        for element in asst.walk(ast):
            if type(element) != asst.Call:
                continue
            call = _get_func(element.func)
            calls.append(call)
    return calls


def _process_assign(element):
    if len(element.targets) > 1:
        return
    target = element.targets[0]
    if type(target) != asst.Name:
        return
    token = target.id

    if type(element.value) != asst.Call:
        return
    call = _get_func(element.value.func)
    return Variable(token, call, element.lineno, 'ASSIGNMENT')


def _process_import(element):
    if len(element.names) > 1:
        return None

    if not isinstance(element.names[0], asst.alias):
        return None

    alias = element.names[0]
    token = alias.asname or alias.name
    rhs = alias.name

    if hasattr(element, 'module'):
        rhs = element.module

    return Variable(token, rhs, element.lineno, 'IMPORT')


def _make_variables(lines):
    variables = []
    for ast in lines:
        for element in asst.walk(ast):
            if type(element) == asst.Assign:
                variables.append(_process_assign(element))
            if type(element) in (asst.Import, asst.ImportFrom):
                variables.append(_process_import(element))

    variables = list(filter(None, variables))
    return variables


def _make_node(ast, parent):
    token = ast.name
    line_number = ast.lineno
    calls = _make_calls(ast.body)
    variables = _make_variables(ast.body)
    return Node(token, line_number, calls, variables, parent=parent)


def _make_root_node(lines, parent):
    token = "(global)"
    line_number = 0
    calls = _make_calls(lines)
    variables = _make_variables(lines)
    return Node(token, line_number, calls, variables, parent=parent)


def _make_class_group(ast, parent):
    assert type(ast) == asst.ClassDef
    subgroup_asts, node_asts, body_asts = Python.segregate_groups_nodes_body(ast)

    group_type = 'CLASS'
    token = ast.name
    line_number = ast.lineno

    class_group = Group(token, line_number, group_type, parent=parent)

    for node_ast in node_asts:
        class_group.add_node(_make_node(node_ast, parent=class_group))

    assert not subgroup_asts
    return class_group


class Python():
    @staticmethod
    def get_ast(filename):
        with open(filename) as f:
            src = f.read()
            return asst.parse(src)
            # return ast2json.ast2json(ast_parse(src))

    @staticmethod
    def segregate_groups_nodes_body(ast):
        groups = []
        nodes = []
        body = []
        for el in ast.body:
            if type(el) == asst.FunctionDef:
                nodes.append(el)
            elif type(el) == asst.ClassDef:
                groups.append(el)
            elif getattr(el, 'body', None):
                tup = Python.segregate_groups_nodes_body(el)
                groups += tup[0]
                nodes += tup[1]
                body += tup[2]
            else:
                body.append(el)
        return groups, nodes, body

    @staticmethod
    def find_links(node_a, all_nodes):
        links = []
        for call in node_a.calls:
            possible_nodes_for_call = []
            for node_b in all_nodes:
                if call.token == node_b.token:
                    if not call.owner_var or call.owner_var.parent == node_b.parent:
                        possible_nodes_for_call.append(node_b)
            try:
                assert len(possible_nodes_for_call) <= 1
            except AssertionError as ex:
                print('\a'); from icecream import ic; ic("multiple NODES")
                print('\a'); from icecream import ic; ic(call)
                print('\a'); from icecream import ic; ic(possible_nodes_for_call)
                raise ex
            links += possible_nodes_for_call
        return links

    @staticmethod
    def make_file_group(ast, filename):
        assert type(ast) == asst.Module
        subgroup_asts, node_asts, body_asts = Python.segregate_groups_nodes_body(ast)
        group_type = 'MODULE'
        token = os.path.split(filename)[-1].rsplit('.py', 1)[0]
        line_number = 0

        file_group = Group(token, line_number, group_type, parent=None)

        for node_ast in node_asts:
            file_group.add_node(_make_node(node_ast, parent=file_group))
        file_group.add_node(_make_root_node(body_asts, parent=file_group), is_root=True)

        for subgroup_ast in subgroup_asts:
            file_group.add_subgroup(_make_class_group(subgroup_ast, parent=file_group))

        return file_group
