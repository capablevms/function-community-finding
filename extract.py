"""
Extracts the information from C files and
creates a call graph using igraph.
"""

import os
import re
import igraph

from igraph import Graph

from clang.cindex import Index, CursorKind, TypeKind
from clang import cindex

from collections import Counter, deque
from itertools import chain

"""
List all the headers from the folder.
And formats them to be inserted in the newly generated c files.
[ Works with lua only ]
"""
def get_headers(path): 
    headers = []

    for file in os.listdir(path):
        if file.endswith(".h"):
            if file == "ljumptab.h":
                continue
            if file == "ltests.h":
                continue
            headers.append(file)
            
    includes = """
#include <time.h>
#include <setjmp.h>
#include <ctype.h>
"""

    for header in headers:
        includes += "#include \"" + header + "\"\n"

    return includes    

"""
Use the libclang extents to read from a file opend with 'r'
"""
def file_read_extent(file, extent):
    file.seek(extent.start.offset)
    return file.read(extent.end.offset - extent.start.offset)
"""
Common printing information about a decl.
"""
def print_decl(decl):
    print(decl.displayname, decl.extent.start.line)


"""
Get the type declaration from things taht look like variables.
It works on variables and function parameters.
"""
def variable_to_type(variable):
    if variable.type.kind == TypeKind.POINTER:
        decl = variable.type.get_pointee().get_declaration()
        if decl.type.kind == TypeKind.TYPEDEF:
            if decl.extent.start.line == 0:
                print(variable.displayname, variable.extent.start.line)
            return decl
        else:
            return None
    elif variable.type.kind == TypeKind.TYPEDEF:
        decl = variable.type.get_declaration()
        if decl.extent.start.line == 0:
            print(variable.displayname, variable.extent.start.line)
        return decl
    elif variable.type.kind == TypeKind.RECORD:
        raise Exception("Error: " + str(variable.extent.start.line) + " " + variable )
    
"""
Extract all the declarations from a translation unit.
"""
def get_decl(tu, split_line, decl = CursorKind.FUNCTION_DECL):
    for child in tu.cursor.get_children():
        if child.kind == decl and child.extent.start.line > split_line:
            yield child.displayname, child

            
            
def traverse(child):
    nodes = deque(child.get_children())
    while len(nodes) > 0:
        node = nodes.pop()
        if node.displayname != "":
            yield node
        nodes.extend(node.get_children())
"""
Extracts all the call inside of a declaration.
"""
def get_calls(child, expr = CursorKind.CALL_EXPR):
    nodes = deque(child.get_children())
    while len(nodes) > 0:
        node = nodes.pop()
        if node.displayname != "" and node.kind == expr:
            yield node
        nodes.extend(node.get_children())

        
def get_decls(child):
    nodes = deque(child.get_children())
    while len(nodes) > 0:
        node = nodes.pop()
        if node.kind == CursorKind.VAR_DECL:
            yield node
        if node.kind == CursorKind.PARM_DECL:
            yield node
        nodes.extend(node.get_children())

"""
Get all the translation units out of the C files.
"""
def get_tus(index, path):
    for file in os.listdir(path):
        if file.endswith(".c"):
            split_line = 0
            # this works on the assumption that all includes are at the start of the file.
            # calculating the split line gives information about which things are defined in
            # headers and which are defined in in the c file.
            with open(os.path.join(path, file), "r") as f:
                for current_line_no, line in enumerate(f):
                    match = re.match("# [0-9]+ \"" + file + "\" 2", line)
                    if match:
                        split_line = current_line_no
            yield (split_line, index.parse(os.path.join(path, file)))
    
def generate_graph(path):
    definitions = {}
    graph = Graph()
    index = Index.create()
    
    # Use the function declarations to create the graph edges.
    for (sl, tu) in get_tus(index, path):
        print(tu.spelling)
        for (k, v) in get_decl(tu, sl):
            sub_children = list(map(lambda x: x.kind, v.get_children()))
            if not (len(sub_children) > 0 and sub_children[-1] == CursorKind.COMPOUND_STMT):
                continue 
                
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
