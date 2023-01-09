# -*- coding: utf-8 -*-

import networkx as nx
from logger import is_debug

if __name__ == "__main__":
    a = nx.MultiDiGraph([(0, 1, {"color": "red"}),(0,2, {"color": "red"}),(1,0, {"color": "red"}),(1,2, {"color": "red"}),(2,1, {"color": "red"}),(3,1, {"color": "blue"}),(3,2, {"color": "blue"}),(1,3, {"color": "blue"})])

def findpath(graph,vertex,color,direction="down",root=None):
    path=[vertex]
    i=0
    while i<len(path):
        if direction == "down":
            selected_edges = [(u,v) for u,v,e in graph.out_edges(path[i],data=True) if e["color"] == color]
            for edge in selected_edges:
                if edge[1] not in path:
                    path.append(edge[1])
            if root in path:
                break
        else:
            selected_edges = [(u,v) for u,v,e in graph.in_edges(path[i],data=True) if e["color"] == color]
            for edge in selected_edges:
                if edge[0] not in path:
                    path.append(edge[0])
        i+=1
    return(path)

# single path
def findpath_root(graph,vertex,color,root):
    #print(graph,vertex,color,root)
    path=[vertex]
    if vertex==root:
        return([],root)
    i=0
    ii=0
    root_reached=False
    last_node=None
    while i<len(path) and ii<len(graph.nodes)+1 :
        ii+=1
        selected_edges = [(u,v) for u,v,e in graph.out_edges(path[i],data=True) if e["color"] == color]
        for edge in selected_edges:
            if edge[1] not in path:
                path.append(edge[1])
                last_node=edge[1]
                i+=1
                break
        if root in path:
            root_reached=True
            break
    if i==len(graph.nodes)+1:
        log1('Warning! infinite loop at path',color,path)
        return path,last_node
    if root_reached:
        return path,root
    else:
        return path,last_node

def find_parents(graph,vertex,color):
    parent_nodes=[vertex]
    parent_edges=[]
    i=0
    while i<len(parent_nodes):
        selected_edges = [(u,v,i) for u,v,i,e in graph.in_edges(parent_nodes[i],keys=True,data=True) if e["color"] == color]
        for e in selected_edges:
            if e not in parent_edges:
                parent_nodes.append(e[0])
                parent_edges.append(e)
        i+=1
    return parent_nodes,parent_edges

# arc disjoint
def isoverlapping(path1,path2,disjoint='arc',root=None):
    if disjoint=='arc' or disjoint=='edge':
        path1arcs = [path1[i:i+2] for i in range(len(path1)-1)]
        path2arcs = [path2[i:i+2] for i in range(len(path2)-1)]
        for e1 in path1arcs:
            for e2 in path2arcs:
                #if e1[0] == e2[0] and e1[1] == e2[1]:
                #    return True
                if disjoint=='edge':
                    if e1[0] == e2[1] and e1[1] == e2[0]:
                        return True
    if disjoint=='node':
        #print('check',path1,path2)
        for n1 in path1[1:-1]:
            if n1==root: continue
            for n2 in path2:
                if n1==root: continue
                if n1 == n2:
                    return True
    return False

def hasoutedge(graph,vertex,hascolor):
    onecolor = nx.get_edge_attributes(graph, "color")
    for oneedge in graph.edges(vertex,keys=True):
        if onecolor[oneedge] == hascolor:
            return 1
    return 0

def hasinedge(graph,vertex,hascolor):
    onecolor = nx.get_edge_attributes(graph, "color")
    for oneedge in graph.in_edges(vertex,keys=True):
        if onecolor[oneedge] == hascolor:
            return 1
    return 0

"""if is_debug(2):
    print(findpath(a,1,"blue"))

if is_debug(2):
    print(isoverlapping([0,1,2,3,4,5],[5,3,1,4,0]))"""
