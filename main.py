import extract
import igraph
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", "-p", help="set the path to the c files")
    parser.add_argument("--graph", action='store_const', const=True, default=False, help="generate a graph image")
    parser.add_argument("--output", "-o", help="the file where c files will be genreated")
    
    args = parser.parse_args()
    if args.graph:
        graph = extract.generate_graph(args.path)

        bc = graph.biconnected_components()
        igraph.plot(graph, target="bc.svg", bbox=(0, 0, 9200, 9200), vertex_label=graph.vs["short"], mark_groups=bc)

        ceb = graph.community_edge_betweenness(directed=False)
        igraph.plot(graph, target="ceb.svg", bbox=(0, 0, 9200, 9200), vertex_label=graph.vs["short"], mark_groups=ceb.as_clustering())
    else:
        # TODO: remove
        #    I intend to move this code in a separate function and keep the main only
        #    for parsing arguments, but I will keep it here for convenience.
        
        from clang.cindex import Index, CursorKind, TypeKind   
        index = Index.create()
        
        includes = extract.get_headers(args.path)
        
        for split_line, tu in extract.get_tus(index, args.path):
            print(tu.spelling, split_line)
            cache = {}
            file = open(tu.spelling, "r+")
            for (k, v) in extract.get_decl(tu, split_line, CursorKind.VAR_DECL):
                calls = ""

                for call in extract.get_calls(v, CursorKind.DECL_REF_EXPR):
                    calls += "extern " + call.referenced.result_type.spelling + " " + call.referenced.displayname + ";\n"

                var_text = extract.file_read_extent(file, v.extent)

                res_file = open(os.path.join(args.output, v.spelling + ".c"), "w")
                res_file.write(includes + "\n" + calls + "\n" + var_text + ";\n")
                res_file.flush()
                res_file.close()

            for (k, v) in extract.get_decl(tu, split_line):
                sub_children = list(map(lambda x: x.kind, v.get_children()))
                if not (len(sub_children) > 0 and sub_children[-1] == CursorKind.COMPOUND_STMT):
                    continue 
                
                calls = ""
                needed_decls = {}

                for variable in extract.get_decls(v):
                    if decl := extract.variable_to_type(variable):
                        if decl.extent.start.line < split_line:
                            continue

                        extract.print_decl(decl)
                        if not decl.displayname in cache:
                            cache[decl.displayname] = extract.file_read_extent(file, decl.extent)
                        needed_decls[decl.displayname] = cache[decl.displayname]

                for call in extract.get_calls(v):
                    calls += "extern " + call.referenced.result_type.spelling + " " + call.referenced.displayname + ";\n"
                    for variable in extract.get_decls(call.referenced):
                        if decl := extract.variable_to_type(variable):
                            if decl.extent.start.line < split_line:
                                continue

                            if not decl.displayname in cache:
                                cache[decl.displayname] = extract.file_read_extent(file, decl.extent)
                            needed_decls[decl.displayname] = cache[decl.displayname]
                defs = "".join(str(decl) + ";\n" for decl in needed_decls.values()) + "\n"  

                func_text = extract.file_read_extent(file, v.extent)
                print(v.spelling, defs)
                res_file = open(os.path.join(args.output, v.spelling + ".c"), "w")
                res_file.write(includes + "\n" + defs + "\n" + calls + "\n" + func_text)
                res_file.flush()
                res_file.close()
            file.close()