from collections import defaultdict
from re import VERBOSE
from funcparserlib.lexer import make_tokenizer, Spec
from funcparserlib.parser import maybe, many, eof, skip, fwd, name_parser_vars
from funcparserlib.contrib.common import const, n, op, op_, sometok


ENCODING = 'utf-8'
regexps = {
    'escaped': ur'''
        \\                                  # Escape
          ((?P<standard>["\\/bfnrt])        # Standard escapes
        | (u(?P<unicode>[0-9A-Fa-f]{4})))   # uXXXX
        ''',
    'unescaped': ur'''
        [\x20-\x21\x23-\x5b\x5d-\uffff]     # Unescaped: avoid ["\\]
        ''',
}

specs = [
    Spec('eol', r'[\r\n]+'),
    Spec('space', r'\s+'),
    Spec('string', ur'"(%(unescaped)s | %(escaped)s)*"' % regexps, VERBOSE),
    Spec('name', r'[A-Za-z_][A-Za-z_0-9]*'),
    Spec('class', r'\.[A-Za-z_][A-Za-z_0-9]*'),
    Spec('id', r'#[A-Za-z_][A-Za-z_0-9]*'),
    Spec('eq', r'='),
    Spec('>', '>'),
    Spec('<', '<'),
]
tokenizer = make_tokenizer(specs)

test = """
div.big .orange
    form method="POST" #main_form
        table
            tr
                td.first "Hello World!"
                td.second "Hello World!"
                td.third "Hello World!"
"""
class Eof(object):
    def __init__(self, data):
        pass

class Spaces(object):
    def __init__(self, s):
        self.len = len(s)

class Tag(object):
    def __init__(self, data):
        self.name = data[0]
        self.data = defaultdict(list)
        for tok in data[1]:
            self.data[tok.__class__.__name__].append(tok)

    def render(self):
        def join_all(name):
            return ' '.join(t.render() for t in self.data[name])
        classes = join_all('Class')
        ids = join_all('Id')
        return '<{name} id="{ids}" class="{classes}" {attrs}>'.format(
            name=self.name,
            ids=ids, classes=classes, attrs=join_all('Attribute'))


class Class(object):
    def __init__(self, name):
        self.name = name.lstrip('.')

    def render(self):
        return self.name

class Id(object):
    def __init__(self, name):
        self.name = name.lstrip('#')

    def render(self):
        return self.name

class Attribute(object):
    def __init__(self, (name, value)):
        self.name = name
        self.value = value

    def render(self):
        return '{s.name}="{s.value}"'.format(s=self)

eol = sometok('eol') >> Eof
space = sometok('space') >> Spaces
string = sometok("string") >> (lambda s: s[1:-1])
name = sometok('name') >> (lambda s: s)
cls = sometok('class') >> Class
attr = name + skip(sometok('eq')) + string >> Attribute
identificator = sometok('id') >> Id
tag = name + many(cls|identificator|attr|skip(space)) >> Tag
complete = many(eol|tag|string|space) + eof

parsed = complete.parse(list(tokenizer(test)))[0]

for d in parsed:
    if hasattr(d, 'render'):
        print d.render()
