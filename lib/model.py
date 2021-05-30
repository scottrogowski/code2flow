import abc
import os


TRUNK_COLOR = '#966F33'
LEAF_COLOR = '#6db33f'
EDGE_COLOR = "#cf142b"
NODE_COLOR = "#cccccc"


def is_installed(executable_cmd):
    """
    Determine whether a command can be run or not

    :param list[str] individual_files:
    :rtype: str
    """
    for path in os.environ["PATH"].split(os.pathsep):
        path = path.strip('"')
        exe_file = os.path.join(path, executable_cmd)
        if os.path.isfile(exe_file) and os.access(exe_file, os.X_OK):
            return True
    return False


class BaseLanguage(abc.ABC):
    """
    Languages are individual implementations for different dynamic languages.
    This will eventually be the superclass of Python, Javascript, PHP, and Ruby.
    Every implementation must implement all of these methods.
    For more detail, see the individual implementations.
    (Note that the 'Tree' parameter / rtype is generic and will be a different
     type for different languages. In Python, it is an ast)
    """

    @property
    @abc.abstractmethod
    def RESERVED_KEYWORDS(self):
        """
        :rtype: list[str]
        """

    @staticmethod
    @abc.abstractmethod
    def get_tree(filename):
        """
        :param filename str:
        :rtype: Tree
        """

    @staticmethod
    @abc.abstractmethod
    def separate_namespaces(tree):
        """
        :param tree Tree:
        :returns: tuple of group, node, and body trees. These are processed
                  downstream into real Groups and Nodes.
        :rtype: (list[Tree], list[Tree], list[Tree])
        """

    @staticmethod
    @abc.abstractmethod
    def find_link_for_call(call, node_a, all_nodes):
        """
        :param call Call:
        :param node_a Node:
        :param all_nodes list[Node]:

        :returns: The node it links to and the call if >1 node matched.
        :rtype: (Node|None, Call|None)
        """

    @staticmethod
    @abc.abstractmethod
    def make_file_group(tree, filename):
        """
        :param tree Tree:
        :param filename Str:

        :rtype: (Group)
        """


class Variable():
    """
    Variables represent named tokens that are accessible to their scope.
    They may either point to a string or, once resolved, a Group/Node.
    Not all variables can be resolved
    """
    def __init__(self, token, points_to, line_number):
        self.token = token
        self.points_to = points_to
        self.line_number = line_number

    def __repr__(self):
        return f"<Variable token={self.token} points_to={self.points_to}"


class Call():
    """
    Calls represent function call expressions.
    They can be an attribute call like
        object.do_something()
    Or a "naked" call like
        do_something()

    """
    def __init__(self, token, line_number, owner_token=None):
        self.token = token
        self.owner_token = owner_token
        self.line_number = line_number

    def __repr__(self):
        return f"<Call owner_token={self.owner_token} token={self.token}>"

    def to_string(self):
        """
        Returns a representation of this call to be printed by the engine
        in logging.
        """
        if self.owner_token:
            return f"{self.owner_token}.{self.token}()"
        return f"{self.token}()"

    def is_attr(self):
        """
        Attribute calls are like `a.do_something()` rather than `do_something()`
        """
        return bool(self.owner_token)

    def matches_variable(self, variable):
        """
        Check whether this variable is what the call is acting on.
        For example, if we had 'obj' from
            obj = Obj()
        as a variable and a call of
            obj.do_something()
        Those would match and we would return the "do_something" node from obj.

        :param variable Variable:
        :rtype: Node
        """
        if self.is_attr():
            if self.owner_token == variable.token:
                # print('\a'); from icecream import ic; ic(self, variable)
                # print('\a'); import ipdb; ipdb.set_trace()
                for node in getattr(variable.points_to, 'nodes', []):
                    if self.token == node.token:
                        return node
                if variable.points_to == 'UNKNOWN_MODULE':
                    return 'UNKNOWN_MODULE' # TODO
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

        self.uid = "node_" + os.urandom(4).hex()

        # Assume it is a leaf and a trunk. These are modified later
        self.is_leaf = True  # it calls nothing else
        self.is_trunk = True  # nothing calls it

    def __repr__(self):
        return f"<Node token={self.token} parent={self.parent}>"

    def name(self):
        """
        Names exist largely for unit tests
        """
        return f"{self.parent.filename()}::{self.token_with_ownership()}"

    def root_parent(self):
        parent = self.parent
        while parent.parent:
            parent = parent.parent
        return parent

    def is_method(self):
        return self.parent and self.parent.group_type == 'CLASS'

    def token_with_ownership(self):
        """
        Token which includes what group this is a part of
        """
        if self.is_method():
            return self.parent.token + '.' + self.token
        return self.token

    def label(self):
        """
        Labels are what you see on the graph
        """
        return f"{self.line_number}: {self.token}()"

    def remove_from_parent(self):
        """
        Remove this node from it's parent. This effectively deletes the node.
        """
        self.parent.nodes = [n for n in self.parent.nodes if n != self]

    def get_variables(self, line_number):
        """
        Get variables in-scope on the line number.
        This includes all local variables as-well-as outer-scope variables
        """
        ret = []
        ret += list([v for v in self.variables if v.line_number <= line_number])
        ret.sort(key=lambda v: v.line_number, reverse=True)

        parent = self.parent
        while parent:
            ret += parent.get_variables()
            parent = parent.parent
        return ret

    def resolve_variables(self, file_groups):
        """
        For all variables, attempt to resolve the Node/Group type.
        There is a good chance this will be unsuccessful.
        points to.

        :param list[Group] file_groups:
        :rtype: None
        """
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

    def to_dot(self):
        """
        Output for graphviz (.dot) files
        """
        attributes = {
            'label': self.label(),
            'name': self.name(),
            'shape': "rect",
            'style': 'rounded,filled',
            'fillcolor': NODE_COLOR,
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
        """
        Output for json files (json graph specification)
        """
        return {
            'uid': self.uid,
            'label': self.label(),
            'name': self.name(),
        }


def _wrap_as_variables(sequence):
    """
    Given a list of either Nodes or Groups, wrap them in variables
    :param list[Group|Node] sequence:
    :rtype: list[Variable]
    """
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
    """
    Groups represent namespaces (classes and modules/files)
    """
    def __init__(self, token, line_number, group_type, parent=None):
        self.token = token
        self.line_number = line_number
        self.nodes = []
        self.root_node = None
        self.subgroups = []
        self.parent = parent
        self.group_type = group_type
        assert group_type in ('MODULE', 'SCRIPT', 'CLASS')

        self.uid = "cluster_" + os.urandom(4).hex()  # group doesn't work by syntax rules

    def __repr__(self):
        return f"<Group token={self.token} type={self.group_type}>"

    def label(self):
        """
        Labels are what you see on the graph
        """
        return f"{self.group_type}: {self.token}"

    def filename(self):
        """
        The ultimate filename of this group.
        """
        if self.group_type in ('MODULE', 'SCRIPT'):
            return self.token
        return self.parent.filename()

    def add_subgroup(self, sg):
        """
        Subgroups are found after initialization. This is how they are added.
        :param sg Group:
        """
        self.subgroups.append(sg)

    def add_node(self, node, is_root=False):
        """
        Nodes are found after initialization. This is how they are added.
        :param node Node:
        :param is_root bool:
        """
        self.nodes.append(node)
        if is_root:
            self.root_node = node

    def all_nodes(self):
        """
        List of nodes that are part of this group + all subgroups
        :rtype: list[Node]
        """
        ret = list(self.nodes)
        for subgroup in self.subgroups:
            ret += subgroup.all_nodes()
        return ret

    def all_groups(self):
        """
        List of groups that are part of this group + all subgroups
        :rtype: list[Group]
        """
        ret = [self]
        for subgroup in self.subgroups:
            ret += subgroup.all_groups()
        return ret

    def get_variables(self):
        """
        Get in-scope variables from this group.
        This assumes every variable will be in-scope in nested functions

        :rtype: list[Variable]
        """
        if self.root_node:
            variables = (self.root_node.variables
                         + _wrap_as_variables(self.subgroups)
                         + _wrap_as_variables(n for n in self.nodes if n != self.root_node))
            return sorted(variables, key=lambda v: v.line_number, reverse=True)
        else:
            return []

    def remove_from_parent(self):
        """
        Remove this group from it's parent. This is effectively a deletion
        """
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
