from collections import defaultdict
from re import VERBOSE
from funcparserlib.lexer import make_tokenizer, Spec
from funcparserlib.parser import many, eof, skip
from funcparserlib.contrib.common import sometok


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

class Eol(object):
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

    def close(self):
        return '</{0}>'.format(self.name)


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

eol = sometok('eol') >> Eol
space = sometok('space') >> Spaces
string = sometok("string") >> (lambda s: s[1:-1])
name = sometok('name') >> (lambda s: s)
cls = sometok('class') >> Class
attr = name + skip(sometok('eq')) + string >> Attribute
identificator = sometok('id') >> Id
tag = name + many(cls|identificator|attr|skip(space)) >> Tag
complete = many(eol|tag|string|space) + eof


def compile(pyml_text, spaces=False):
    parsed = complete.parse(list(tokenizer(pyml_text)))[0]
    start = True
    lens = [0]
    tags = [[]]
    for d in parsed:
        if isinstance(d, Tag):
            yield d.render()
            tags[-1].append(d)
        elif isinstance(d, Spaces) and start:
            start = False
            if lens[-1] < d.len:
                tags.append([])
                lens.append(d.len)
            elif lens[-1] >= d.len:
                if spaces:
                    yield ' ' * lens[-1]
                for tag in tags[-1]:
                    yield tag.close()
                if spaces:
                    yield '\n'
                tags[-1] = []
                if lens[-1] > d.len:
                    tags.pop(-1)
                    lens.pop(-1)
            if spaces:
                yield ' ' * d.len
        elif isinstance(d, Eol):
            start = True
            if spaces:
                yield '\n'
        elif isinstance(d, basestring):
            yield d
    for tgs, l in reversed(zip(tags, lens)):
        if spaces:
            yield ' ' * l
        for tag in reversed(tgs):
            yield tag.close()
        if spaces:
            yield '\n'

if __name__ == '__main__':
    test = """
div.big .orange
    form method="POST" #main_form
        table tr
                td.first "Hello World!"
                td.second "Hello World!"
                td.third "Hello World!"
"""
    print ''.join(compile(test, True))
