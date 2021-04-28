import random


TRUNK_COLOR = '#966F33'
LEAF_COLOR = '#6db33f'
EDGE_COLOR = "#cf142b"


class Variable():
    def __init__(self, token, points_to, line_number):
        self.token = token
        self.points_to = points_to
        self.line_number = line_number

    def __repr__(self):
        return f"<Variable token={self.token} points_to={self.points_to}"


class Call():
    def __init__(self, token, line_number, owner_token=None):
        self.token = token
        self.owner_token = owner_token
        self.line_number = line_number

    def __repr__(self):
        return f"<Call owner_token={self.owner_token} token={self.token}>"

    def to_string(self):
        if self.owner_token:
            return f"{self.owner_token}.{self.token}"
        return f"{self.token}"

    def is_attr(self):
        return bool(self.owner_token)

    def matches_variable(self, variable):
        if self.is_attr():
            if self.owner_token == variable.token:
                for node in getattr(variable.points_to, 'nodes', []):
                    if self.token == node.token:
                        return node
                return 'UNKNOWN_MODULE'
            return None
        if self.token == variable.token and isinstance(variable.points_to, Node):
            return variable.points_to
        return None


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
        return f"{self.line_number}: {self.token}()"

    def remove_from_parent(self):
        self.parent.nodes = [n for n in self.parent.nodes if n != self]

    def get_variables(self, line_number):
        ret = []
        ret += list([v for v in self.variables if v.line_number <= line_number])

        parent = self.parent
        while parent:
            ret += parent.get_variables()
            parent = parent.parent
        return ret

    def polish_variables(self, file_groups):
        for variable in self.variables:
            if isinstance(variable.points_to, str):
                for file_group in file_groups:
                    if file_group.token == variable.points_to:
                        variable.points_to = file_group
                        break
                else:
                    variable.points_to = "UNKNOWN_MODULE"  # Indicates we must skip
            elif isinstance(variable.points_to, Call):
                if variable.points_to.is_attr():
                    # Only process Class(); Not a.Class()
                    continue
                for file_group in file_groups:
                    for group in file_group.all_groups():
                        if group.token == variable.points_to.token:
                            variable.points_to = group

    def to_dot(self, no_grouping):
        attributes = {
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

    def to_dict(self):
        return {
            'uid': self.uid,
            'label': self.label(),
            'name': self.name(),
        }


def _wrap_as_variables(sequence):
    return [Variable(el.token, el, el.line_number) for el in sequence]


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

    def to_dict(self):
        return {
            'source': self.node0.uid,
            'target': self.node1.uid,
            'directed': True,
        }


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
            variables = (self.root_node.variables
                         + _wrap_as_variables(self.subgroups)
                         + _wrap_as_variables(n for n in self.nodes if n != self.root_node))
            return sorted(variables, key=lambda v: v.line_number, reverse=True)
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

