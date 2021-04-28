import ast as asst
import os

from .model import Group, Node, Call, Variable


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
    return Variable(token, call, element.lineno)


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
        # TODO this is a string. Need to do a lookup maybe

    return Variable(token, rhs, element.lineno)


def _make_variables(lines, parent):
    variables = []
    for ast in lines:
        for element in asst.walk(ast):
            if type(element) == asst.Assign:
                variables.append(_process_assign(element))
            if type(element) in (asst.Import, asst.ImportFrom):
                variables.append(_process_import(element))
    if parent.group_type == 'CLASS':
        variables.append(Variable('self', parent, lines[0].lineno))

    variables = list(filter(None, variables))
    return variables


def _make_node(ast, parent):
    token = ast.name
    line_number = ast.lineno
    calls = _make_calls(ast.body)
    variables = _make_variables(ast.body, parent)
    return Node(token, line_number, calls, variables, parent=parent)


def _make_root_node(lines, parent):
    token = "(global)"
    line_number = 0
    calls = _make_calls(lines)
    variables = _make_variables(lines, parent)
    return Node(token, line_number, calls, variables, parent=parent)


def _make_class_group(ast, parent):
    assert type(ast) == asst.ClassDef
    subgroup_asts, node_asts, body_asts = Python.separate_namespaces(ast)

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
    def separate_namespaces(ast):
        groups = []
        nodes = []
        body = []
        for el in ast.body:
            if type(el) == asst.FunctionDef:
                nodes.append(el)
            elif type(el) == asst.ClassDef:
                groups.append(el)
            elif getattr(el, 'body', None):
                tup = Python.separate_namespaces(el)
                groups += tup[0]
                nodes += tup[1]
                body += tup[2]
            else:
                body.append(el)
        return groups, nodes, body

    @staticmethod
    def find_link_for_call(call, node_a, all_nodes):

        all_vars = node_a.get_variables(call.line_number)

        for var in all_vars:
            var_match = call.matches_variable(var)
            if var_match:
                if var_match == 'UNKNOWN_MODULE':
                    return None, None
                assert isinstance(var_match, Node)
                return var_match, None

        possible_nodes = []
        if call.is_attr():
            for node in all_nodes:
                if call.token != node.token:
                    continue
                possible_nodes.append(node)
        else:
            for node in all_nodes:
                if call.token == node.token and node.parent.group_type == 'MODULE':
                    possible_nodes.append(node)

        if len(possible_nodes) == 1:
            return possible_nodes[0], None
        return None, call

    @staticmethod
    def find_links(node_a, all_nodes):
        links = []
        for call in node_a.calls:
            lfc = Python.find_link_for_call(call, node_a, all_nodes)
            if isinstance(lfc, Group):
                assert False
            links.append(lfc)
        return list(filter(None, links))

    @staticmethod
    def make_file_group(ast, filename):
        assert type(ast) == asst.Module
        subgroup_asts, node_asts, body_asts = Python.separate_namespaces(ast)
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
