'''
This is the base module which is then subclassed by the language chosen

There are three basic graph elements defined:
Graph:         Which represents namespaces or classes
Node:          Which represents functions
Edge:          Which represents function calls

Then, there are two other classes:
Sourcecode: An object to hold and manipulate the sourcecode
Mapper:         Runs the show

The implementation files (javascript.py and python.py) subclass every one of these
classes sometimes replacing functions and sometimes adding completely new functions

This way, we can share a lot of code between languages while still preserving full language flexibility

Functions that begin with an "_" are not replaced by any implementation
'''

import collections
import copy
import logging
import pprint
import re
import secrets

# from .mutablestring import MString

# for generating UIDs for groups and nodes
currentUID = 0


def _generate_edges(nodes):
    '''
    When a function calls another function, that is an edge
    This is in the global scope because edges can exist between any node and not just between groups
    '''
    edges = []
    for node0 in nodes:
        for node1 in nodes:
            # logging.info(f'"{node0.name}" links to "{node1.name}"?')
            if node0.links_to(node1, nodes):
                # logging.info("Yes. Edge created")
                edges.append(Edge(node0, node1))
    return edges


def _get_char_to_line_map(source_string):
    line_number = 1
    char_to_line_map = {}
    for i, c in enumerate(source_string):
        char_to_line_map[i] = line_number
        if c == '\n':
            line_number += 1
    return char_to_line_map


class Node():
    '''
    Nodes represent functions
    '''

    # How we know if a function returns
    return_pattern = re.compile(r"\Wreturn\W", re.MULTILINE)

    def __init__(self, name, source, parent,
                 character_pos=0, line_number=0, is_file_root=False, lang=None):
        # basic vars
        self.name = name
        self.source = source
        self.parent = parent
        self.character_pos = character_pos
        self.line_number = line_number  # The line number the definition is on
        self.is_file_root = is_file_root
        self.lang = lang

        # generate the name patterns for other nodes to search for this one
        # self.pattern is the name pattern which is found by others eg. node()
        self.pattern = re.compile(r"(?:\W|\A)(%s)\s*\(" % self.name, re.MULTILINE)

        self.is_init_node = self.lang.is_init_node(name)  # Init node, etc.

        # The pattern to search for when the other node is in the same scope e.g. self.node()
        # self.same_scope_patterns = self.lang.generate_same_scope_patterns(name)

        # The pattern to search for with the namespace eg. Node.node()
        # self.namespace_patterns = self.lang.generate_scope_patterns(self.get_full_name())

        # determine whether there are return statements or not
        self.returns = self.return_pattern.search(self.source.source_string)

        # increment the identifier
        # Needed for the sake of a unique node name for graphviz
        self.uid = secrets.token_hex()

        # Assume it is a leaf and a trunk until determined otherwise
        self.is_leaf = True  # it calls nothing else
        self.is_trunk = True  # nothing calls it

    def __repr__(self):
        return "<Node %s from %r:%d parent=%r>" % (
            self.name, self.source.filename, self.line_number, self.parent.name)

    def get_full_name(self):
        '''
        Return the name with the namespace
        '''
        namespace = self.lang.get_node_namespace(self.parent, self.name)
        if '/' in namespace:
            namespace = namespace.rsplit('/', 1)[1]

        return namespace + '.' + self.name if namespace else self.name

    def links_to(self, other, all_nodes):
        return self.lang.links_to(self, other, all_nodes)

    def contains(self, other):
        return other.links_to(self)

    def get_UID(self):
        return 'node' + str(self.uid)

    def get_file_group(self):
        return self.parent.get_file_group()

    def get_filename(self):
        return self.parent.get_filename()

    def to_dot(self):
        '''
        For printing to the DOT file
        '''
        attributes = {}

        attributes['label'] = "%d: %s" % (self.line_number, self.get_full_name())
        attributes['shape'] = "rect"
        attributes['style'] = "rounded"
        # attributes['splines']='ortho'
        if self.is_trunk:
            attributes['style'] += ',filled'
            attributes['fillcolor'] = 'coral'
        elif self.is_leaf:
            attributes['style'] += ',filled'
            attributes['fillcolor'] = 'green'

        ret = self.get_UID()
        if attributes:
            ret += ' [splines=ortho '
            for a in attributes:
                ret += '%s = "%s" ' % (a, attributes[a])
            ret += ']'

        return ret


class Edge():
    '''
    Edges represent function calls
    '''
    def __init__(self, node0, node1):
        self.node0 = node0
        self.node1 = node1

        # When we draw the edge, we know the calling function is definitely not a leaf...
        # and the called function is definitely not a trunk
        node0.is_leaf = False
        node1.is_trunk = False

    def to_dot(self):
        '''
        For printing to the DOT file
        '''
        ret = self.node0.get_UID() + ' -> ' + self.node1.get_UID()
        if self.node1.returns:
            ret += ' [color="blue" penwidth="2"]'
        return ret

    def has_end_node(self, node1):
        return node1 == self.node1

    def has_start_node(self, node0):
        return node0 == self.node0


class Group():
    '''
    Groups represent namespaces
    '''

    def __init__(self, name, source_code,
                 parent=None, line_number=0, lang=None):
        self.name = name
        self.source = source_code
        self.parent = parent
        self.line_number = line_number
        self.lang = lang

        self.nodes = []
        self.subgroups = []

        # So that we can track object calls as well like:
        # a = Obj()
        # a.b()
        # TODO2021 OOOOF this might be bad... These objects can be passed everywhere
        # and change names all the time. Let's see how we can handle this...
        self.new_object_pattern = self.lang.generate_new_object_pattern(name)
        self.new_object_assigned_pattern = self.lang.generate_new_object_assigned_pattern(name)

        # Needed for the sake of a unique node name for graphviz
        self.uid = secrets.token_hex()

    def __repr__(self):
        return "<Group %r from %r line=%d nodes=%d subgroups=%d>" % (
            self.name, self.source.filename, self.line_number,
            len(self.nodes), len(self.subgroups))

    def to_dot(self):
        '''
        for printing to the DOT file
        '''
        ret = 'subgraph ' + self.get_UID()
        ret += '{\n'
        if self.nodes:
            for node in self.nodes:
                ret += node.get_UID() + ' '
                # if node.is_file_root:
                #    ret += ";{rank=source; %s}"%node.get_UID()

            ret += ';\n'
        ret += 'label="%s";\n' % self.name
        ret += 'style=filled;\n'
        ret += 'color=black;\n'
        ret += 'graph[style=dotted];\n'
        for subgroup in self.subgroups:
            ret += str(subgroup)
        ret += '}'
        return ret

    def get_namespace(self):
        return self.lang.get_group_namespace(self.parent, self.name)

    def root_node_name(self, name=''):
        name = name or self.name
        return "(%s (global scope))" % (name)

    def _pprint(self, printHere=True):
        '''
        Print the file structure
        Strictly for debugging right now
        '''
        tree = [(x.name, 'node') for x in self.nodes]
        tree += [(x.name, x._pprint(printHere=False)) for x in self.subgroups]
        if printHere:
            pprint.pprint(dict(tree))
        else:
            return dict(tree)

    def get_UID(self):
        '''
        Something
        '''
        try:
            if self.isAnon:
                return 'clusterANON' + str(self.uid)
            else:
                raise Exception()
        except Exception:
            return 'cluster' + re.sub(r"[/\.\-\(\)=\s]", '', self.name) + str(self.uid)

    def all_nodes(self):
        '''
        Every node in this namespace and all descendent namespaces
        '''
        nodes = list(self.nodes)
        for subgroup in self.subgroups:
            nodes += subgroup.all_nodes()
        return nodes

    def get_file_group(self):
        if self.parent:
            return self.parent.get_file_group()
        else:
            return self

    def get_filename(self):
        return self.get_file_group().name


def _remove_comments_and_strings(source_string, lang):
    """
    Remove all comments and strings from the sourcecode and
    adjust the char_to_line_map
    """
    char_to_line_map = _get_char_to_line_map(source_string)

    for comment_group in lang.comments:
        while True:
            matches = {
                token: regex.search(source_string)
                for token, regex in comment_group.items()
            }
            match_positions = {
                token: match.span()[0]
                for token, match in matches.items() if match
            }
            if not match_positions:
                break

            match_token_to_use = min(match_positions.items(), key=lambda m: m[1])[0]
            comment_re = comment_group[match_token_to_use]

            match = comment_re.search(source_string)
            new_source_string = comment_re.sub(r'\1\3', source_string, count=1)
            new_char_to_line_map = {}
            span_start, span_end = match.span(2)
            match_len = span_end - span_start
            for char_pos, line_number in char_to_line_map.items():
                if char_pos < span_start:
                    new_char_to_line_map[char_pos] = line_number
                    continue
                if char_pos < span_end:
                    continue
                new_char_to_line_map[char_pos - match_len] = line_number
            source_string = new_source_string
            char_to_line_map = new_char_to_line_map
    return source_string, char_to_line_map


def _print_source(source_string, char_to_line_map):
    lines = collections.defaultdict(str)
    for char_pos, line_number in char_to_line_map.items():
        lines[line_number] += source_string[char_pos]
    ret = ''
    for line_number, char in sorted(lines.items()):
        ret += f'{line_number}: {char}'
    return ret


class SourceCode():
    '''
    SourceCode is a convenient object object representing:
        source text (source_string)
        a line number array (char_to_line_map)

    A sourcecode object is maintained internally in both Group and Node objects

    # Implementations will probably only have to overwrite the two properties:
    #     block_comments
    #     strings
    # Although Python does overwrite more because of it's indent system

    The sourcecode object supports the following primitive operations
        sc = SourceCode()
        len(sc) #characters
        sc[a:b] #betweenCharacters
        sc[a] #character
        scA + scB #addition as long as line numbers do not overlap
        scA - scB #subtraction as long as scB is completely inside scA
        sc == True #truth testing (empty string)
        str(sc) print with line numbers

    And these are the methods
        copy() #deepcopy
        first_line_number() #of the entire object
        last_line_number()  #of the entire object
        remove(string) #and return new sourcecode
        pop() #return last line
        _get_position(line_number) #get character index at line_number
        get_line_number(character_pos) #get line number of character
        find(what,start) #run source_string.find()
        extract_between_delimiters(a,b,start_at) #return new sourcecode between the first pair of delimiters after start_at
        get_source_in_block(bracket_pos) #Return the source to the matching bracket
        matching_bracket_pos(bracket_pos) #Return the matching bracket position
        _end_delim_pos(start_at,a,b) #return the position of the nearest end bracket given a position in the block
        _open_delim_pos(start_at) #return the position of the nearest begin bracket given a position in the block
        _remove_comments_and_strings() #called on init. Does as it says changing the object

    '''
    __slots__ = [
        'source_string',
        'char_to_line_map',
        'lang',
        'filename'
    ]

    delim_a = '{'
    delim_b = '}'
    delim_len = 1

    def __init__(self, source_string, char_to_line_map=None, filename=None, lang=None):
        '''
        Remove the comments and build the line_number/file mapping while doing so
        '''
        self.source_string = source_string
        self.lang = lang
        self.filename = filename

        if char_to_line_map:
            self.char_to_line_map = char_to_line_map
            return
        self.char_to_line_map = _get_char_to_line_map(source_string)
        self.source_string, self.char_to_line_map = _remove_comments_and_strings(source_string, lang)

    def __str__(self):
        '''
        For debugging. Print the source with line numbers
        '''
        return _print_source(self.source_string, self.char_to_line_map)

    def __repr__(self):
        ret = "<SourceCode %r from=%d to=%d>" % (
            self.filename, self.first_line_number(), self.last_line_number())
        return ret

    def __bool__(self):
        '''
        __bool__ is object evaluates to True or False
        source_string will be False when the source_string has nothing or nothing but whitespace
        '''
        return self.source_string.strip() != ''

    def __len__(self):
        return len(self.source_string)

    def __getitem__(self, sl):
        '''
        If sliced, return a new object with the source_string and the char_to_line_map sliced by [firstChar:lastChar]

        1. Slice the source string in the obvious way.
        2. Slice the char_to_line_map
            a. Remove character mappings that are not in between where we are shifting to
            b. Take remaining char_positions and shift them over by start shift

        '''
        if type(sl) == int:
            return self.source_string[sl]

        assert type(sl) == slice

        start = sl.start or 0

        if sl.stop is None:
            stop = len(self.source_string)
        elif sl.stop < 0:
            stop = len(self.source_string) + sl.stop
        else:
            stop = sl.stop

        if start > stop:
            raise Exception("Begin slice > end slice. You passed SourceCode[%d:%d]" % (sl.start, sl.stop))

        if start == stop:
            return None

        new_source_code_obj = self.copy()

        new_source_code_obj.source_string = new_source_code_obj.source_string[start:stop]

        # filter out character mapping we won't be using
        shifted_char_to_line_map = {}
        char_positions = list(new_source_code_obj.char_to_line_map.keys())
        char_positions = list(p for p in char_positions if start <= p < stop)

        # shift existing character mappings to reflect the new start position
        # If we start with 0, no shifting will take place
        for char_pos in char_positions:
            shifted_char_to_line_map[char_pos - start] = new_source_code_obj.char_to_line_map[char_pos]

        # we need this to be sure that we can always get the line number no matter where we splice
        shifted_char_to_line_map[0] = self.get_line_number(start)

        new_source_code_obj.char_to_line_map = shifted_char_to_line_map

        return new_source_code_obj

    def __add__(self, other):
        '''
        Add two pieces of sourcecode together shifting the character to line map appropriately
        '''

        # If one operand is nothing, just return the value of this operand
        if not other:
            return self.copy()

        assert self.last_line_number() <= other.first_line_number()

        source_string = self.source_string + other.source_string

        shifted_char_to_line_map = {}
        char_positions = list(other.char_to_line_map.keys())
        for char_pos in char_positions:
            shifted_char_to_line_map[char_pos + len(self.source_string)] = other.char_to_line_map[char_pos]

        char_to_line_map = dict(list(self.char_to_line_map.items()) + list(shifted_char_to_line_map.items()))

        ret = SourceCode(source_string=source_string,
                         char_to_line_map=char_to_line_map,
                         filename=self.filename,
                         lang=self.lang)
        return ret

    def __sub__(self, other):
        if not other:
            return self.copy()

        try:
            assert self.first_line_number() <= other.first_line_number()
            assert other.last_line_number() <= self.last_line_number()
        except:
            print('\a'); import ipdb; ipdb.set_trace()

        first_pos = self.source_string.find(other.source_string)
        assert first_pos != -1

        last_pos = first_pos + len(other.source_string)

        ret = self[:first_pos] + self[last_pos:]
        return ret

    def copy(self):
        ret = SourceCode(copy.deepcopy(self.source_string),
                         copy.deepcopy(self.char_to_line_map),
                         filename=self.filename,
                         lang=self.lang)
        return ret

    def first_line_number(self):
        '''
        First line number of the entire source
        '''
        return min(self.char_to_line_map.values())

    def last_line_number(self):
        '''
        Last line number of the entire source
        '''
        return max(self.char_to_line_map.values())

    def remove(self, string_to_remove):
        '''
        Remove a string. Does not alter object in place
        '''
        first_pos = self.source_string.find(string_to_remove)
        if first_pos == -1:
            raise Exception("String not found in source")
        last_pos = first_pos + len(string_to_remove)
        return self[:first_pos] + self[last_pos:]

    def pop(self):
        '''
        Pop off the last line
        '''
        last_line_pos = self.source_string.rfind('\n')
        ret = self.source_string[last_line_pos:]
        self = self[:last_line_pos]

        return ret

    def _get_position(self, line_number_request):
        '''
        From line_number, get the character position
        '''
        for pos, line_number in self.char_to_line_map.items():
            if line_number == line_number_request:
                return pos

        raise Exception("Could not find line number in source")

    def get_line_number(self, pos):
        '''
        Decrement until we find the first character of the line and can get the line_number
        '''
        while True:
            try:
                return self.char_to_line_map[pos]
            except Exception:
                pos -= 1
                if pos < 0:
                    raise Exception("could not get line number for position %d" % pos)

    def find(self, what, start=0):
        '''
        Pass through 'find' makes implementations cleaner
        '''
        return self.source_string.find(what, start)

    def extract_between_delimiters(self, start_at=0):
        '''
        Return the source between the first pair of delimiters after 'start_at'
        '''
        start = self.source_string.find(self.delim_a, start_at)
        if start == -1:
            return None
        start += self.delim_len

        end_pos = self._end_delim_pos(start, self.delim_a, self.delim_b)
        if end_pos != -1:
            return self[start:end_pos]
        else:
            return None

    def matching_bracket_pos(self, bracket_pos):
        '''
        Find the matching bracket position
        '''

        delim = self[bracket_pos]
        if delim == self.delim_a:
            if self.source_string[bracket_pos + 1] == self.delim_b:
                return bracket_pos + 1
            else:
                return self._end_delim_pos(start_at=bracket_pos + 1)
        elif delim == self.delim_b:
            if self.source_string[bracket_pos - 1] == self.delim_a:
                return bracket_pos - 1
            else:
                return self._open_delim_pos(start_at=bracket_pos - 1)
        else:
            raise Exception('"%s" is not a known delimiter' % delim)

    def _end_delim_pos(self, start_at):
        '''
        Find the nearest end delimiter assuming that 'start_at' is inside of a block
        '''

        count = 1
        i = start_at
        while i < len(self.source_string) and count > 0:
            tmp = self.source_string[i:i + self.delim_len]
            if tmp == self.delim_a:
                count += 1
                i += self.delim_len
            elif tmp == self.delim_b:
                count -= 1
                i += self.delim_len
            else:
                i += 1

        if count == 0:
            return i - self.delim_len
        else:
            return -1

    def _open_delim_pos(self, pos):
        '''
        Find the nearest begin delimiter assuming that 'pos' is inside of a block
        TODO there is probably no reason why this also includes parenthesis
        TODO this should probably just be the same function as _end_delim_pos
        '''

        count = 0
        i = pos
        while i >= 0 and count >= 0:
            if self.source_string[i] in ('}', ')'):
                count += 1
            elif self.source_string[i] in ('{', '('):
                count -= 1
            i -= 1

        if count == -1:
            return i + 1
        return 0

    def get_source_in_block(self, start_pos):
        return self.lang.get_source_in_block(self, start_pos)


def _get_nodes_and_groups(raw_source_by_filename, lang):
    nodes = []
    file_groups = []
    for filename, raw_source in raw_source_by_filename.items():
        # remove .py from filename
        logging.info(f"Getting source for {filename}...")

        # generate sourcecode (remove comments and add line numbers)
        source_code = SourceCode(raw_source, filename=filename, lang=lang)

        # Create all of the subgroups (classes) and nodes (functions) for this file
        logging.info("Generating groups and nodes...")
        file_group = lang.generate_file_group(name=filename,
                                              source_code=source_code,
                                              lang=lang)
        file_groups.append(file_group)

        # Append nodes generated to all nodes
        nodes += file_group.all_nodes()
    return nodes, file_groups


def map_it(lang, filenames):
    '''
    I. For each file passed,
        1. Generate the sourcecode for that file
        2. Generate a group from that file's sourcecode
            a. The group init will recursively generate all of the subgroups and function nodes for that file
    II.  Trim the groups bascially removing those which have no function nodes
    III. Generate the edges
    IV.  Return the file groups, function nodes, and edges
    '''

    # get the filename and the file_raw_source
    # only first file for now

    raw_source_by_filename = {}
    for filename in filenames:
        with open(filename) as f:
            raw_source_by_filename[filename] = f.read()

    nodes, file_groups = _get_nodes_and_groups(raw_source_by_filename, lang)

    # Trimming the groups mostly removes those groups with no function nodes
    # TODO in Python we don't remove shit
    for group in file_groups:
        lang.trim_groups(group)
        logging.info(f"Post trim, {group.name}...")
        group._pprint()

    # Figure out what functions map to what
    logging.info("Generating edges...")
    edges = _generate_edges(nodes)

    # Trim off the nodes (mostly global-frame nodes that don't do anything)
    final_nodes = []
    for node in nodes:
        if not lang.is_extraneous(node, edges):
            final_nodes.append(node)
        else:
            node.parent.nodes.remove(node)
            del node  # TODO

    # return everything we have done
    return file_groups, final_nodes, edges
