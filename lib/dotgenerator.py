from .model import TRUNK_COLOR, LEAF_COLOR, EDGE_COLOR

LEGEND = """subgraph legend{
    rank = min;
    label = "legend";
    Legend [shape=none, margin=0, label = <
        <table cellspacing="0" cellpadding="0" border="1"><tr><td>Code2flow Legend</td></tr><tr><td>
        <table cellspacing="0">
        <tr><td>Regular function</td><td width="50px"></td></tr>
        <tr><td>Trunk function (nothing calls this)</td><td bgcolor='%s'></td></tr>
        <tr><td>Leaf function (this calls nothing else)</td><td bgcolor='%s'></td></tr>
        <tr><td>Function call</td><td><font color='%s'>&#8594;</font></td></tr>
        </table></td></tr></table>
        >];
}""" % (TRUNK_COLOR, LEAF_COLOR, EDGE_COLOR)


def write_dot_file(filename, nodes, edges, groups, hide_legend=False,
                   no_grouping=False):
    '''
    Write a dot file that can be read by graphviz

    :param filename str:
    :param nodes list[Node]: functions
    :param edges list[Edge]: function calls
    :param groups list[Group]: classes and files
    :param hide_legend bool:
    :rtype: None
    '''

    content = "digraph G {\n"
    content += "concentrate=true;\n"
    content += 'splines="ortho";\n'
    content += 'rankdir="LR";\n'
    if not hide_legend:
        content += LEGEND
    for node in nodes:
        content += node.to_dot(no_grouping) + ';\n'
    for edge in edges:
        content += edge.to_dot() + ';\n'
    if not no_grouping:
        for group in groups:
            content += group.to_dot()
    content += '}'

    with open(filename, 'w') as outfile:
        outfile.write(content)
