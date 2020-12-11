import extract
import igraph
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", "-p", help="set the path to the c files")
    
    args = parser.parse_args()
    
    graph = extract.generate_graph(args.path)
    
    bc = graph.biconnected_components()
    igraph.plot(graph, target="bc.svg", bbox=(0, 0, 9200, 9200), vertex_label=graph.vs["short"], mark_groups=bc)
    
    ceb = graph.community_edge_betweenness(directed=False)
    igraph.plot(graph, target="ceb.svg", bbox=(0, 0, 9200, 9200), vertex_label=graph.vs["short"], mark_groups=ceb.as_clustering())
