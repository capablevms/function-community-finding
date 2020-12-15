"""
Extracts the information from C files and
creates a call graph using igraph.
"""

import os
import igraph

from igraph import Graph

from clang.cindex import Index, CursorKind
from clang import cindex

from collections import Counter, deque
from itertools import chain

"""
Extract all the declarations from a translation unit.
"""
def get_decl(tu):
    for child in tu.cursor.get_children():
        if child.kind == CursorKind.FUNCTION_DECL:
            sub_children = list(map(lambda x: x.kind, child.get_children()))
            if len(sub_children) > 0 and sub_children[-1] == CursorKind.COMPOUND_STMT:
                yield child.displayname, child

"""
Extracts all the call inside of a declaration.
"""
def get_calls(child):
    nodes = deque(child.get_children())
    while len(nodes) > 0:
        node = nodes.pop()
        if node.displayname != "" and node.kind == CursorKind.CALL_EXPR:
            yield node
        nodes.extend(node.get_children())

"""
Get all the translation units out of the C files.
"""
def get_tus(index, path):
    for file in os.listdir(path):
        if file.endswith(".c"):
            yield index.parse(path + "/" + file)
    
def generate_graph(path):
    definitions = {}
    graph = Graph()
    index = Index.create()
    
    # Use the function declarations to create the graph edges.
    for tu in get_tus(index, path):
        print(tu.spelling)
        for (k, v) in get_decl(tu):
            if k in definitions:
                raise Exception("error: ", k)
            definitions[k] = v
            graph.add_vertex(k, label=k, short=v.spelling)

    print("Defined functions:", len(definitions))

    # Use the calls done inside each declaration to create the vertecies.
    for k, v in definitions.items():
        edges = {}

        for n in get_calls(v):
            ref = n.referenced
            if ref.displayname in definitions:
                edges[ref.displayname] = ref
        for _, ref in edges.items():
            graph.add_edge(k, ref.displayname)

    to_delete_ids = [v.index for v in graph.vs if v.degree() == 0]
    graph.delete_vertices(to_delete_ids)
    return graph
