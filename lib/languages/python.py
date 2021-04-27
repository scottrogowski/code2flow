import ast as asst
import random
import os

TRUNK_COLOR = '#966F33'
LEAF_COLOR = '#6db33f'
EDGE_COLOR = "#cf142b"


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
        return self.label()

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
        self.subgroups = []
        self.parent = parent
        self.group_type = group_type

        self.uid = "cluster_" + random.randbytes(4).hex()

    def __repr__(self):
        return self.label()

    def label(self):
        return f"{self.group_type}: {self.token}"

    def filename(self):
        if self.group_type == 'MODULE':
            return self.token
        return self.parent.filename()

    def add_subgroup(self, sg):
        self.subgroups.append(sg)

    def add_node(self, node):
        self.nodes.append(node)

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

    def remove_from_parent(self):
        if self.parent:
            self.parent.nodes = [n for n in self.parent.nodes if n != self]

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
        owner = []
        val = func.value
        while True:
            try:
                owner.append(getattr(val, 'attr', val.id))
            except:
                pass
            val = getattr(val, 'value', None)
            if not val:
                break
        owner = '.'.join(reversed(owner))
        return {'token': func.attr,
                'owner': owner}
    if type(func) == asst.Name:
        return {'token': func.id}
    raise AssertionError("Unknown function type %r" % type(func))


def _make_calls(lines):
    calls = []
    for ast in lines:
        for element in asst.walk(ast):
            if type(element) != asst.Call:
                continue

            calls.append(_get_func(element.func))
    return calls


def _process_assign(element):
    if len(element.targets) > 1:
        return
    target = element.targets[0]
    if type(target) != asst.Name:
        return
    var_name = target.id

    if type(element.value) != asst.Call:
        return
    var_type = _get_func(element.value.func)
    return {'var_name': var_name, 'var_type': var_type, 'line_number': element.lineno, 'from': "ASSIGNMENT"}


def _process_import(element):
    if len(element.names) > 1:
        return None

    if not isinstance(element.names[0], asst.alias):
        return None

    alias = element.names[0]
    var_name = alias.asname or alias.name
    var_type = alias.name

    if hasattr(element, 'module'):
        var_type = element.module

    return {'var_name': var_name, 'var_type': var_type,
            'line_number': element.lineno, 'from': 'IMPORT'}


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

    for subgroup_ast in subgroup_asts:
        class_group.add_subgroup(_make_class_group(subgroup_ast, parent))
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
    def links(node_a, node_b):
        for call in node_a.calls:
            if call['token'] == node_b.token:
                return True
        return False

    @staticmethod
    def make_file_group(ast, filename):
        assert type(ast) == asst.Module
        subgroup_asts, node_asts, body_asts = Python.segregate_groups_nodes_body(ast)
        group_type = 'MODULE'
        token = os.path.split(filename)[-1]
        line_number = 0

        file_group = Group(token, line_number, group_type, parent=None)

        for node_ast in node_asts:
            file_group.add_node(_make_node(node_ast, parent=file_group))
        file_group.add_node(_make_root_node(body_asts, parent=file_group))

        for subgroup_ast in subgroup_asts:
            file_group.add_subgroup(_make_class_group(subgroup_ast, parent=file_group))

        return file_group
