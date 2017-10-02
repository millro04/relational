# Relational
# Copyright (C) 2008-2017  Salvo "LtWorf" Tomaselli
#
# Relational is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# author Salvo "LtWorf" Tomaselli <tiposchi@tiscali.it>
#
#
#
# This module implements a parser for relational algebra, and can be used
# to convert expressions into python expressions and to get the parse-tree
# of the expression.
#
# Language definition here:
# http://ltworf.github.io/relational/grammar.html
from typing import Optional, Union, List, Any

from relational import rtypes

RELATION = 0
UNARY = 1
BINARY = 2

PRODUCT = '*'
DIFFERENCE = '-'
UNION = '∪'
INTERSECTION = '∩'
DIVISION = '÷'
JOIN = '⋈'
JOIN_LEFT = '⧑'
JOIN_RIGHT = '⧒'
JOIN_FULL = '⧓'
PROJECTION = 'π'
SELECTION = 'σ'
RENAME = 'ρ'
ARROW = '➡'
SEMIJOIN = 'semijoin'

b_operators = (PRODUCT, DIFFERENCE, UNION, INTERSECTION, DIVISION,
               JOIN, JOIN_LEFT, JOIN_RIGHT, JOIN_FULL, SEMIJOIN)  # List of binary operators
u_operators = (PROJECTION, SELECTION, RENAME)  # List of unary operators

# Associates operator with python method
op_functions = {
    PRODUCT: 'product', DIFFERENCE: 'difference', UNION: 'union', INTERSECTION: 'intersection', DIVISION: 'division', JOIN: 'join',
    JOIN_LEFT: 'outer_left', JOIN_RIGHT: 'outer_right', JOIN_FULL: 'outer', SEMIJOIN: 'semijoin', PROJECTION: 'projection', SELECTION: 'selection', RENAME: 'rename'}


class TokenizerException (Exception):
    pass


class ParserException (Exception):
    pass


class CallableString(str):

    '''
    This is a string. However it is also callable.

    For example:
    CallableString('1+1')()
    returns 2

    It is used to contain Python expressions and print
    or execute them.
    '''

    def __call__(self, context=None):
        '''
        context is a dictionary where to
        each name is associated the relative relation
        '''
        return eval(self, context)


class Node:

    '''This class is a node of a relational expression. Leaves are relations
    and internal nodes are operations.

    The 'kind' property indicates whether the node is a binary operator, unary
    operator or relation.
    Since relations are leaves, a relation node will have no attribute for
    children.

    If the node is a binary operator, it will have left and right properties.

    If the node is a unary operator, it will have a child, pointing to the
    child node and a property containing the string with the props of the
    operation.

    This class is used to convert an expression into python code.'''
    kind = None #  type: Optional[int]
    __hash__ = None #  type: None

    def __init__(self, expression: Optional[list] = None) -> None:
        '''Generates the tree from the tokenized expression
        If no expression is specified then it will create an empty node'''
        if expression is None or len(expression) == 0:
            return

        # If the list contains only a list, it will consider the lower level list.
        # This will allow things like ((((((a))))) to work
        while len(expression) == 1 and isinstance(expression[0], list):
            expression = expression[0]

        # The list contains only 1 string. Means it is the name of a relation
        if len(expression) == 1:
            self.kind = RELATION
            self.name = expression[0]
            if not rtypes.is_valid_relation_name(self.name):
                raise ParserException(
                    u"'%s' is not a valid relation name" % self.name)
            return

        '''


        people semijoin skills (id=skill_id)

        if semijoin in str:
            #parse the input up in 2 parts:
                1) "people semijoin skills"
                2) fieldStr = id=skills_id


            1) Build the node from part 1
            2) Keep as is
            3) Call relation.semijoin(node.left, node.right, fieldStr)


        [x, semijoin, y]
        '''
        # Expression from right to left, searching for binary operators
        # this means that binary operators have lesser priority than
        # unary operators.
        # It finds the operator with lesser priority, uses it as root of this
        # (sub)tree using everything on its left as left parameter (so building
        # a left subtree with the part of the list located on left) and doing
        # the same on right.
        # Since it searches for strings, and expressions into parenthesis are
        # within sub-lists, they won't be found here, ensuring that they will
        # have highest priority.
        for i in range(len(expression) - 1, -1, -1):
            if expression[i] in b_operators:  # Binary operator
                self.kind = BINARY
                self.name = expression[i]
                #At this point, i should be 0
                #len(epression[0:0]
                if len(expression[:i]) == 0:

                    raise ParserException(
                        u"Expected left operand for '%s'" % self.name)

                if len(expression[i + 1:]) == 0:
                    raise ParserException(
                        u"Expected right operand for '%s'" % self.name)

                self.left = node(expression[:i])
                self.right = node(expression[i + 1:])
                return
        '''Searches for unary operators, parsing from right to left'''
        for i in range(len(expression) - 1, -1, -1):
            if expression[i] in u_operators:  # Unary operator
                self.kind = UNARY
                self.name = expression[i]

                if len(expression) <= i + 2:
                    raise ParserException(
                        u"Expected more tokens in '%s'" % self.name)

                self.prop = expression[1 + i].strip()
                self.child = node(expression[2 + i])

                return
        raise ParserException("Expected operator in '%s'" % expression)

    def toCode(self):
        '''This method converts the AST into a python code object'''
        code = self._toPython()
        return compile(code, '<relational_expression>', 'eval')

    def toPython(self) -> CallableString:
        '''This method converts the AST into a python code string, which
        will require the relation module to be executed.

        The return value is a CallableString, which means that it can be
        directly called.'''
        return CallableString(self._toPython())

    def _toPython(self) -> str:
        '''
        Same as toPython but returns a regular string
        '''
        if self.name in b_operators:
            return '%s.%s(%s)' % (self.left.toPython(), op_functions[self.name], self.right.toPython())
        elif self.name in u_operators:
            prop = self.prop

            # Converting parameters
            if self.name == PROJECTION:
                prop = '\"%s\"' % prop.replace(' ', '').replace(',', '\",\"')
            elif self.name == RENAME:
                prop = '{\"%s\"}' % prop.replace(
                    ',', '\",\"').replace(ARROW, '\":\"').replace(' ', '')
            else:  # Selection
                prop = repr(prop)

            return '%s.%s(%s)' % (self.child.toPython(), op_functions[self.name], prop)
        return self.name

    def printtree(self, level: int = 0) -> str:
        '''returns a representation of the tree using indentation'''
        r = ''
        for i in range(level):
            r += '  '
        r += self.name
        if self.name in b_operators:
            r += self.left.printtree(level + 1)
            r += self.right.printtree(level + 1)
        elif self.name in u_operators:
            r += '\t%s\n' % self.prop
            r += self.child.printtree(level + 1)
        return '\n' + r

    def get_left_leaf(self) -> 'Node':
        '''This function returns the leftmost leaf in the tree.'''
        if self.kind == RELATION:
            return self
        elif self.kind == UNARY:
            return self.child.get_left_leaf()
        elif self.kind == BINARY:
            return self.left.get_left_leaf()
        raise ValueError('What kind of alien object is this?')

    def result_format(self, rels: dict) -> list:
        '''This function returns a list containing the fields that the resulting relation will have.
        It requires a dictionary where keys are the names of the relations and the values are
        the relation objects.'''
        if not isinstance(rels, dict):
            raise TypeError('Can\'t be of None type')

        if self.kind == RELATION:
            return list(rels[self.name].header)
        elif self.kind == BINARY and self.name in (DIFFERENCE, UNION, INTERSECTION):
            return self.left.result_format(rels)
        elif self.kind == BINARY and self.name == DIVISION:
            return list(set(self.left.result_format(rels)) - set(self.right.result_format(rels)))
        elif self.name == PROJECTION:
            return [i.strip() for i in self.prop.split(',')]
        elif self.name == PRODUCT:
            return self.left.result_format(rels) + self.right.result_format(rels)
        elif self.name == SELECTION:
            return self.child.result_format(rels)
        elif self.name == RENAME:
            _vars = {}
            for i in self.prop.split(','):
                q = i.split(ARROW)
                _vars[q[0].strip()] = q[1].strip()

            _fields = self.child.result_format(rels)
            for i in range(len(_fields)):
                if _fields[i] in _vars:
                    _fields[i] = _vars[_fields[i]]
            return _fields
        elif self.name in (JOIN, JOIN_LEFT, JOIN_RIGHT, JOIN_FULL):
            return list(set(self.left.result_format(rels)).union(set(self.right.result_format(rels))))
        raise ValueError('What kind of alien object is this?')

    def __eq__(self, other):
        if not (isinstance(other, node) and self.name == other.name and self.kind == other.kind):
            return False

        if self.kind == UNARY:
            if other.prop != self.prop:
                return False
            return self.child == other.child
        if self.kind == BINARY:
            return self.left == other.left and self.right == other.right
        return True

    def __str__(self):
        if (self.kind == RELATION):
            return self.name
        elif (self.kind == UNARY):
            return self.name + " " + self.prop + " (" + self.child.__str__() + ")"
        elif (self.kind == BINARY):
            le = self.left.__str__()
            if self.right.kind != BINARY:
                re = self.right.__str__()
            else:
                re = "(" + self.right.__str__() + ")"
            return (le + self.name + re)
        raise ValueError('What kind of alien object is this?')


def _find_matching_parenthesis(expression: str, start=0, openpar=u'(', closepar=u')') -> Optional[int]:
    '''This function returns the position of the matching
    close parenthesis to the 1st open parenthesis found
    starting from start (0 by default)'''
    par_count = 0  # Count of parenthesis

    string = False
    escape = False

    for i in range(start, len(expression)):
        if expression[i] == '\'' and not escape:
            string = not string
        if expression[i] == '\\' and not escape:
            escape = True
        else:
            escape = False
        if string:
            continue

        if expression[i] == openpar:
            par_count += 1
        elif expression[i] == closepar:
            par_count -= 1
            if par_count == 0:
                return i  # Closing parenthesis of the parameter
    return None

def _find_token(haystack: str, needle: str) -> int:
    '''
    Like the string function find, but
    ignores tokens that are within a string
    literal.
    '''
    r = -1
    string = False
    escape = False

    for i in range(len(haystack)):
        if haystack[i] == '\'' and not escape:
            string = not string
        if haystack[i] == '\\' and not escape:
            escape = True
        else:
            escape = False
        if string:
            continue

        if haystack[i:].startswith(needle):
            return i
    return r


def tokenize(expression: str) -> list:
    '''This function converts a relational expression into a list where
    every token of the expression is an item of a list. Expressions into
    parenthesis will be converted into sublists.'''

    # List for the tokens
    items = [] #  type: List[Union[str,list]]

    expression = expression.strip()  # Removes initial and ending spaces

    while len(expression) > 0:
        if expression.startswith('('):  # Parenthesis state
            end = _find_matching_parenthesis(expression)
            if end is None:
                raise TokenizerException(
                    "Missing matching ')' in '%s'" % expression)
            # Appends the tokenization of the content of the parenthesis
            items.append(tokenize(expression[1:end]))
            # Removes the entire parentesis and content from the expression
            expression = expression[end + 1:].strip()

        elif expression.startswith((SELECTION, RENAME, PROJECTION)):  # Unary operators
            items.append(expression[0:1])
                         # Adding operator in the top of the list
            expression = expression[
                1:].strip()  # Removing operator from the expression

            if expression.startswith('('):  # Expression with parenthesis, so adding what's between open and close without tokenization
                par = expression.find(
                    '(', _find_matching_parenthesis(expression))
            else:  # Expression without parenthesis, so adding what's between start and parenthesis as whole
                par = _find_token(expression, '(')

            items.append(expression[:par].strip())
                         # Inserting parameter of the operator
            expression = expression[
                par:].strip()  # Removing parameter from the expression
        else:  # Relation (hopefully)
            expression += ' '  # To avoid the special case of the ending

            # Initial part is a relation, stop when the name of the relation is
            # over
            for r in range(1, len(expression)):
                if rtypes.RELATION_NAME_REGEXP.match(expression[:r + 1]) is None:
                    break
            items.append(expression[:r])
            expression = expression[r:].strip()
    return items


def tree(expression: str) -> Node:
    '''This function parses a relational algebra expression into a AST and returns
    the root node using the Node class.'''
    return Node(tokenize(expression))


def parse(expr: str) -> CallableString:
    '''This function parses a relational algebra expression, and returns a
    CallableString (a string that can be called) whith the corresponding
    Python expression.
    '''
    print("Tree", (tree(expr)))
    return tree(expr).toPython()

if __name__ == "__main__":
    while True:
        e = input("Expression: ")
        print (parse(e))

# Backwards compatibility
node = Node
