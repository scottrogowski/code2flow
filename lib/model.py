import collections
import random
import re

TRUNK_COLOR = '#966F33'
LEAF_COLOR = '#6db33f'
EDGE_COLOR = "#cf142b"


class Node():
    '''
    Nodes represent functions
    '''

    def __init__(self, name, long_name, source, parent,
                 character_pos=0, line_number=0, lang=None):
        # basic vars
        self.name = name
        self.long_name = long_name
        self.source = source
        self.parent = parent
        self.character_pos = character_pos
        self.line_number = line_number  # The line number the definition is on
        self.lang = lang

        # generate the name patterns for other nodes to search for this one
        # self.pattern is the name pattern which is found by others eg. node()
        self.pattern = re.compile(r"(?:\W|\A)(%s)\s*\(" % self.name, re.MULTILINE)

        # increment the identifier
        # Needed for the sake of a unique node name for graphviz
        self.uid = random.randbytes(4).hex()

        # Assume it is a leaf and a trunk until determined otherwise
        self.is_leaf = True  # it calls nothing else
        self.is_trunk = True  # nothing calls it

    def __repr__(self):
        return "<Node %s from %r:%d parent=%r>" % (
            self.name, self.source.filename, self.line_number, self.parent.name)

    def get_display_name(self, full):
        '''
        Return the name with the namespace
        '''
        name = self.long_name

        if not full or not self.parent:
            return name
        return self.parent.name + '.' + name

    def chained_name(self):
        names = [self.name]
        parent = self.parent
        while True:
            if not parent:
                break
            names.append(parent.name)
            parent = parent.parent
        names.reverse()
        return names[0] + ':' + '.'.join(names[1:])

    def links_to(self, other, all_nodes):
        return self.lang.links_to(self, other, all_nodes)

    def contains(self, other):
        return other.links_to(self)

    def get_UID(self):
        return 'node_' + str(self.uid)

    def get_file_group(self):
        return self.parent.get_file_group()

    def get_filename(self):
        return self.parent.get_filename()

    def to_dot(self, no_grouping=False):
        """
        Returns string format for embedding in a dotfile. Example output:
        node_uid_a [splines = "ortho" shape = "rect" ...]
        """
        attributes = {
            # 'splines': "ortho",
            'label': f"{self.line_number}: {self.get_display_name(full=no_grouping)}",
            'name': self.chained_name(),
            'shape': "rect",
            'style': 'rounded,filled',
        }
        if self.is_trunk:
            attributes['fillcolor'] = TRUNK_COLOR
        elif self.is_leaf:
            attributes['fillcolor'] = LEAF_COLOR

        ret = self.get_UID() + ' ['
        for k, v in attributes.items():
            ret += f'{k}="{v}" '
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
        Returns string format for embedding in a dotfile. Example output:
        node_uid_a -> node_uid_b [color='#aaa' penwidth='2']
        '''
        ret = self.node0.get_UID() + ' -> ' + self.node1.get_UID()
        ret += f' [color="{EDGE_COLOR}" penwidth="2"]'
        return ret

    def has_end_node(self, node1):
        return node1 == self.node1

    def has_start_node(self, node0):
        return node0 == self.node0


class Group():
    '''
    Groups represent namespaces
    '''

    def __init__(self, name, long_name, source_code,
                 parent=None, line_number=0, lang=None):
        self.name = name
        self.long_name = long_name
        self.source = source_code
        self.parent = parent
        self.line_number = line_number
        self.lang = lang

        self.nodes = []
        self.subgroups = []

        # Needed for the sake of a unique node name for graphviz
        self.uid = random.randbytes(4).hex()

    def __repr__(self):
        return "<Group %r from %r line=%d nodes=%d subgroups=%d>" % (
            self.name, self.source.filename, self.line_number,
            len(self.nodes), len(self.subgroups))

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

        ret = 'subgraph ' + self.get_UID() + ' {\n'
        if self.nodes:
            ret += '    '
            ret += ' '.join(node.get_UID() for node in self.nodes)
            ret += ';\n'
        attributes = {
            'label': self.get_dispay_name(),
            'name': self.name,
            'style': 'filled',
        }
        for k, v in attributes.items():
            ret += f'{k}="{v}" '
        ret += '    graph[style=dotted];\n'
        for subgroup in self.subgroups:
            ret += '    ' + ('\n'.join('    ' + ln for ln in
                                       subgroup.to_dot().split('\n'))).strip() + '\n'
        ret += '};\n'
        return ret

    def get_dispay_name(self):
        if not self.parent:
            return "file: " + self.long_name
        return "class: " + self.long_name

    def get_namespace(self):
        return self.lang.get_group_namespace(self)

    # def _pprint(self, printHere=True):
    #     '''
    #     Print the file structure
    #     Strictly for debugging right now
    #     '''
    #     tree = [(x.name, 'node') for x in self.nodes]
    #     tree += [(x.name, x._pprint(printHere=False)) for x in self.subgroups]
    #     if printHere:
    #         pprint.pprint(dict(tree))
    #     else:
    #         return dict(tree)

    def get_UID(self):
        '''
        '''
        return 'cluster_' + str(self.uid)

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


def _decode_source(string_data):
    return ''.join(t[0] for t in string_data)


def _remove_comments_and_strings(string_data, lang):
    """
    Remove all comments and strings from the sourcecode and
    adjust the char_to_line_map
    """
    while True:
        raw_source = _decode_source(string_data)
        matches = {
            token: regex.search(raw_source)
            for token, regex in lang.comments.items()
        }
        match_positions = {
            token: match.span()[0]
            for token, match in matches.items() if match
        }
        if not match_positions:
            break

        match_token_to_use = min(match_positions.items(), key=lambda m: m[1])[0]
        comment_re = lang.comments[match_token_to_use]

        match = comment_re.search(raw_source)
        span_start, span_end = match.span(2)
        string_data = string_data[:span_start] + string_data[span_end:]
    return string_data


def _print_source(string_data):
    lines = collections.defaultdict(str)
    for c, _, line_number in string_data:
        lines[line_number] += c.replace(' ', '◽')
    ret = ''
    for line_number, line in sorted(lines.items()):
        ret += f'{line_number}: {line.rstrip()}\n'
    return ret


def _encode_source(raw_source):
    char_list = []
    i = 0
    for line_number, row in enumerate(raw_source.split('\n')):
        for c in row:
            char_list.append((c, i, line_number + 1))
            i += 1
        char_list.append(('\n', i, line_number + 1))
        i += 1
    return char_list


class SourceCode():
    '''
    SourceCode is a convenient object object representing:
        source text (string_data)
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
        find(what,start) #run string_data.find()
        extract_between_delimiters(a,b,start_at) #return new sourcecode between the first pair of delimiters after start_at
        get_source_in_block(bracket_pos) #Return the source to the matching bracket
        matching_bracket_pos(bracket_pos) #Return the matching bracket position
        _end_delim_pos(start_at,a,b) #return the position of the nearest end bracket given a position in the block
        _open_delim_pos(start_at) #return the position of the nearest begin bracket given a position in the block
        _remove_comments_and_strings() #called on init. Does as it says changing the object

    '''
    __slots__ = [
        'string_data',
        'lang',
        'filename',
        'original_source',
    ]

    delim_a = '{'
    delim_b = '}'
    delim_len = 1

    def __init__(self, string_data, filename=None, lang=None, original_source=None):
        '''
        Remove the comments and build the line_number/file mapping while doing so
        '''
        if isinstance(string_data, str):
            string_data = _encode_source(string_data)
            string_data = _remove_comments_and_strings(string_data, lang)
        self.string_data = string_data
        self.lang = lang
        self.filename = filename
        self.original_source = original_source or self

    def __str__(self):
        '''
        For debugging. Print the source with line numbers
        '''
        return _print_source(self.string_data)

    def __repr__(self):
        ret = "<SourceCode %r from=%d to=%d>" % (
            self.filename, self.first_line_number(), self.last_line_number())
        return ret

    def __bool__(self):
        '''
        __bool__ is object evaluates to True or False
        string_data will be False when the string_data has nothing or nothing but whitespace
        '''
        return bool(self.string_data)

    def __len__(self):
        return len(self.string_data)

    def __getitem__(self, sl):
        '''
        If sliced, return a new object with the string_data and the char_to_line_map sliced by [firstChar:lastChar]

        1. Slice the source string in the obvious way.
        2. Slice the char_to_line_map
            a. Remove character mappings that are not in between where we are shifting to
            b. Take remaining char_positions and shift them over by start shift

        '''
        # if type(sl) == int:
        #     return StringData(self.string_data[sl],

        assert type(sl) == slice

        start = sl.start or 0

        if sl.stop is None:
            stop = len(self.string_data)
        elif sl.stop < 0:
            stop = len(self.string_data) + sl.stop
        else:
            stop = sl.stop

        if start == stop:
            return SourceCode("", self.filename, self.lang, self.original_source)
        assert start < stop

        new_source_code_obj = self.copy()
        new_source_code_obj.string_data = new_source_code_obj.string_data[start:stop]

        return new_source_code_obj

    def __add__(self, other):
        '''
        Add two pieces of sourcecode together shifting the character to line map appropriately
        '''
        assert False

    #     # If one operand is nothing, just return the value of this operand
    #     if not other:
    #         return self.copy()

    #     assert self.last_line_number() <= other.first_line_number()

    #     string_data = self.string_data + other.string_data

    #     shifted_char_to_line_map = {}
    #     char_positions = list(other.char_to_line_map.keys())
    #     for char_pos in char_positions:
    #         shifted_char_to_line_map[char_pos + len(self.string_data)] = other.char_to_line_map[char_pos]

    #     char_to_line_map = dict(list(self.char_to_line_map.items()) + list(shifted_char_to_line_map.items()))

    #     ret = SourceCode(string_data=string_data,
    #                      char_to_line_map=char_to_line_map,
    #                      filename=self.filename,
    #                      lang=self.lang)
    #     return ret

    def __sub__(self, other):
        assert self.filename == other.filename

        if not other:
            return self.copy()

        assert self.string_data[0][1] <= other.string_data[0][1]
        assert other.string_data[-1][1] <= self.string_data[-1][1]

        ret = self.copy()

        other_positions = [t[1] for t in other.string_data]
        ret.string_data = [t for t in self.string_data if t[1] not in other_positions]
        return ret

    @property
    def source_string(self):
        return _decode_source(self.string_data)

    def copy(self):
        ret = SourceCode(list(self.string_data),
                         filename=self.filename,
                         lang=self.lang,
                         original_source=self)
        return ret

    def first_line_number(self):
        '''
        First line number of the entire source
        '''
        return self.string_data[0][2]

    def last_line_number(self):
        '''
        Last line number of the entire source
        '''
        return self.string_data[-1][2]

    def search(self, regex):
        return re.search(regex, self.source_string)

    def finditer(self, regex):
        return re.finditer(regex, self.source_string)

    # def remove(self, string_to_remove):
    #     '''
    #     Remove a string. Does not alter object in place
    #     '''
    #     first_pos = self.string_data.find(string_to_remove)
    #     if first_pos == -1:
    #         raise Exception("String not found in source")
    #     last_pos = first_pos + len(string_to_remove)
    #     return self[:first_pos] + self[last_pos:]

    # def pop(self):
    #     '''
    #     Pop off the last line
    #     '''
    #     last_line_pos = self.string_data.rfind('\n')
    #     ret = self.string_data[last_line_pos:]
    #     self = self[:last_line_pos]

    #     return ret

    # def _get_position(self, line_number_request):
    #     '''
    #     From line_number, get the character position
    #     '''
    #     for pos, line_number in self.char_to_line_map.items():
    #         if line_number == line_number_request:
    #             return pos

    #     raise Exception("Could not find line number in source")

    def get_line_number(self, pos):
        '''
        Decrement until we find the first character of the line and can get the line_number
        '''
        return self.string_data[pos][2]

    # def extract_between_delimiters(self, start_at=0):
    #     '''
    #     Return the source between the first pair of delimiters after 'start_at'
    #     '''
    #     start = self.string_data.find(self.delim_a, start_at)
    #     if start == -1:
    #         return None
    #     start += self.delim_len

    #     end_pos = self._end_delim_pos(start, self.delim_a, self.delim_b)
    #     if end_pos != -1:
    #         return self[start:end_pos]
    #     else:
    #         return None

    # def matching_bracket_pos(self, bracket_pos):
    #     '''
    #     Find the matching bracket position
    #     '''

    #     delim = self[bracket_pos]
    #     if delim == self.delim_a:
    #         if self.string_data[bracket_pos + 1] == self.delim_b:
    #             return bracket_pos + 1
    #         else:
    #             return self._end_delim_pos(start_at=bracket_pos + 1)
    #     elif delim == self.delim_b:
    #         if self.string_data[bracket_pos - 1] == self.delim_a:
    #             return bracket_pos - 1
    #         else:
    #             return self._open_delim_pos(start_at=bracket_pos - 1)
    #     else:
    #         raise Exception('"%s" is not a known delimiter' % delim)

    # def _end_delim_pos(self, start_at):
    #     '''
    #     Find the nearest end delimiter assuming that 'start_at' is inside of a block
    #     '''

    #     count = 1
    #     i = start_at
    #     while i < len(self.string_data) and count > 0:
    #         tmp = self.string_data[i:i + self.delim_len]
    #         if tmp == self.delim_a:
    #             count += 1
    #             i += self.delim_len
    #         elif tmp == self.delim_b:
    #             count -= 1
    #             i += self.delim_len
    #         else:
    #             i += 1

    #     if count == 0:
    #         return i - self.delim_len
    #     else:
    #         return -1

    # def _open_delim_pos(self, pos):
    #     '''
    #     Find the nearest begin delimiter assuming that 'pos' is inside of a block
    #     TODO there is probably no reason why this also includes parenthesis
    #     TODO this should probably just be the same function as _end_delim_pos
    #     '''

    #     count = 0
    #     i = pos
    #     while i >= 0 and count >= 0:
    #         if self.string_data[i] in ('}', ')'):
    #             count += 1
    #         elif self.string_data[i] in ('{', '('):
    #             count -= 1
    #         i -= 1

    #     if count == -1:
    #         return i + 1
    #     return 0

    def get_source_in_block(self, end_indentifier_pos, start_pos):
        return self.lang.get_source_in_block(self, end_indentifier_pos, start_pos)
