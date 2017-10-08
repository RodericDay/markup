#!/usr/bin/env pypy3
import collections
import glob
import os
import re
import string
import sys


# slugifier translator
slugify = collections.defaultdict(str)
for c in '_- /':
    slugify[ord(c)] = '-'
for c in string.ascii_lowercase+string.digits:
    slugify[ord(c)] = c
    slugify[ord(c.upper())] = c


# simple replacements
code = r'<code>\1</code>'
strike = r'<del>\1</del>'
underline = r'<u>\1</u>'
italics = r'<i>\1</i>'
bold = r'<b>\1</b>'
thematic_break = '<hr/>'
quote = r'<blockquote>\1</blockquote>'
date = r'<span class="date">\1</span>'
em_dash = r'&mdash;'
anchor = r'<a href="\1">\1</a>'
reference = r'<a href="\2">\1</a>'
note_text = r'<a id="\1text" href="#\1foot">&#91;\1&#93;</a>'
note_foot = r'<a id="\1foot" href="#\1text">&#91;\1&#93;</a>'


def blockquote(match):
    before, text, after = match.groups()
    pre = '\n<blockquote>' if before == '\n' else ''
    post = '</blockquote>' if after == '\n' else '\n<br/>'
    return pre + text + post

def codearea(match):
    code = match.group(1).strip()
    n = len(code.splitlines())
    m = max(map(len, code.splitlines())) + 1
    tpl = '<textarea class="codearea" rows="%s" cols="%s" readonly>%s</textarea>'
    blob = tpl % (n, m, code)
    return preserve(blob)

def description(match):
    term, inner = match.groups()
    inner = inner.replace('\n    ', '\n')
    return f'<dt>{term}</dt>\n<dd>\n{inner}\n</dd>'

def inline(match):
    title, src = match.groups()
    if src.lower().endswith(("png","jpg","jpeg","gif","svg")):
        return f'<img src="{src}" title="{title}"/>'
    elif src.lower().endswith(("py","js")):
        return codearea(re.match(r"([\s\S]*)", open(src).read()))
    else:
        raise RuntimeError(f"Cannot inline <{src}>")

def heading(match):
    hashes, text = match.groups()
    slug = text.translate(slugify)
    n = len(hashes)
    return f'<h{n} id="{slug}">{text}</h{n}>'

def ordered_list_item(match):
    before, text, after = match.groups()
    ol = '\n<ol>\n' if before == '\n' else ''
    lo = '</ol>' if after == '\n' else ''
    return f'{ol}<li>{text}</li>\n{lo}'

def paragraph(match):
    line, = match.groups()
    if line.startswith(('<','{')):
        return line
    return f'<p>{line}</p>'

def unordered_list_item(match):
    before, text, after = match.groups()
    ul = '\n<ul>\n' if before == '\n' else ''
    lu = '</ul>' if after == '\n' else ''
    return f'{ul}<li>{text}</li>\n{lu}'

def verbatim(match):
    tag, content = match.groups()
    blob = f'<{tag}{content}</{tag}>'
    return preserve(blob)

preserved_blobs = []
def preserve(blob):
    preserved_blobs.append(blob)
    return "{%s}" % (len(preserved_blobs)-1)

rules = [
    (r'```([\S\s]+?)```', codearea),
    (r'<(svg)([\S\s]+?)</\1>', verbatim),  # I don't like not closing the tag
    (r'<(pre)([\S\s]+?)</\1>', verbatim),  #
    (r'<(style)([\S\s]+?)</\1>', verbatim),  #
    (r'<(script)([\S\s]+?)</\1>', verbatim),  #
    (r'(?<=\n)([^\n]+):\n    ([\s\S]+?)(?=\n\n)', description),
    (r'(?<=(\s|\S))\n {4,}(.+)(?=\n(\s|\S))', blockquote),
    (r'(?<=(\s|\S))\n[-*] (.+)(?=\n(\s|\S))', unordered_list_item),
    (r'(?<=(\s|\S))\n\d+[)] (.+)(?=\n(\s|\S))', ordered_list_item),
    (r'!\[([^\]]*)\]\(([^\)]+)\)', inline),
    (r'(?<=\n)> ([^\n]+)(?=\n)', quote),
    (r'(?<=\n)(#+) ([^\n]+)(?=\n)', heading),
    (r'(?<=\n)---(?=\n)', thematic_break),
    (r'\[(\d+)\]:', note_foot),
    (r'\[(\d+)\]', note_text),
    (r'(?<=\n)([^\n]+)(?=\n)', paragraph),
    (r'\*\*(.+?)\*\*', bold),
    (r'\*(.+?)\*', italics),
    (r'__(.+?)__', underline),
    (r'~~(.+?)~~', strike),
    (r'`(.+?)`', code),
    (r'(?<=[\s>])(\d{4}/\d{2}/\d{2})(?=\s)', date),
    (r'--', em_dash),
    (r'<(https?://[^>]+?)>', anchor),
    (r'\[([^\]]+?)\]\(([^\)]+?)\)', reference),
]

def markup(string):
    preserved_blobs.clear()
    _ = '\n' + string + '\n'
    for fragment, replacement in rules:
        _ = re.sub(fragment, replacement, _)
    return _.strip().format(*preserved_blobs) + '\n'

def to_html(tpath, mpath, hpath):
    assert tpath.endswith(".tpl"), "1st arg should be a template file"
    assert mpath.endswith(".md"), "2nd arg should be a markdown-ish file"
    assert hpath.endswith(".html"), "3rd arg should be HTML path output"
    with open(tpath) as tp, open(mpath) as mp, open(hpath, "w") as hp:
        _ = mp.read()
        _ = markup(_)
        _ = tp.read().format(_)
        hp.write(_)


if __name__ == '__main__':
    this_file, *arguments = sys.argv
    if arguments:
        to_html(*arguments)

    else:
        import unittest

        class Test(unittest.TestCase):

            def test_all(self):
                with open('test.html') as fph, open('test.txt') as fpt:
                    text, html = fpt.read(), fph.read()
                    self.assertEqual(markup(text), html)

        unittest.main()
