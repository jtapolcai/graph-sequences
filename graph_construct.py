# -*- coding: utf-8 -*-
import networkx as nx
from itertools import combinations, groupby
from networkx.readwrite import json_graph
import json
import graph_draw as ddraw
import DrawGraph as dg
from logger import log1,log2,log3,log4,log5,log6,is_debug,set_debug
import matplotlib.pyplot as plt
import sys
import argparse
from math import sqrt
import time
import random

aparser = argparse.ArgumentParser()
aparser.add_argument("-fig", help="Show graphs with Matplotlib", action='store_true')
aparser.add_argument("-tikz", help="Export graphs in tikz", action='store_true')
aparser.add_argument("-mirror", help="Show the graph upside down", action='store_true')
aparser.add_argument("-tikz_scale", type=float, help="Scale tikz figures", default=200)
aparser.add_argument("-root", type=int, help="The root node", default=0)
aparser.add_argument("-log", type=int, help="The logging level: 1- main info, 3- detailed  ", default=3)
aparser.add_argument("-file", type=str, help="The input .json network file", default='22_optic_eu.lgf.json')
aparser.add_argument("-xml_outfile", type=str, help="The xml file where the results are stored", default='result.xml')
aparser.add_argument("-test", help="Run tests", action='store_true')
aparser.add_argument("-alpha", type=float, help="Punishing parallel edges", default=0.1)
aparser.add_argument("-beta", type=float, help="Rewarding loop edges edges", default=10)
aparser.add_argument("-obj", type=str, help="Use special objective in deconstruction: grow, even_nodes_first, even_nodes_first_chi, random", default='')

args = aparser.parse_args()
set_debug(args.log)

xml_file = None

def log_xml(string):
    global xml_file
    xml_file.write(string+"\n")
def log_xmltag(tag,value):
    global xml_file
    xml_file.write("<"+tag+">"+str(value)+"</"+tag+">\n")


def multifactoring_(end_nodes, avoid=[]):
    #remove duplicates
    list = []
    for n in end_nodes:
        if n not in list:
            list.append(n)

    if len(list)<2:
        yield []
        return
    element_0 = list[0]
    for i in range(1,len(list)):
        first = (element_0,list[i])
        if first in avoid:
            continue
        for next in multifactoring(list[1:i]+list[i+1:], avoid):
            yield [first] + next

def intersection_count(candidate,avoid):
    if len(avoid)==0:
        return 0
    ret=0
    for u1,v1 in candidate:
        if u1==None:
            continue
        for u2,v2 in avoid:
             if (u1==u2 and v1==v2) or (u1==v2 and v1==u2):
                 ret+=1
    return ret

average_edge_length=1
def edge_physical_length(G,u,v):
    return sqrt((G.nodes[u]['pos'][0]-G.nodes[v]['pos'][0])**2+(G.nodes[u]['pos'][1]-G.nodes[v]['pos'][1])**2)

# the smaller the better, 0 is the best quality
def quality_of_a_candidate(G,candidate,border_edges):
    global average_edge_length
    quality=args.alpha+intersection_count(candidate,border_edges)
    physical_length=0
    for u,v in candidate:
        physical_length+=edge_physical_length(G,u,v)/average_edge_length
        if u==v:
            quality-=args.beta
    return quality

def is_already_listed(already_listed,candidate):
    candidate_list=[]
    for u,v in candidate:
        if u>v:
            candidate_list.append(str((v,u)))
        else:
            candidate_list.append(str((u,v)))
    candidate_list.sort()
    log4('candidate:',str(candidate_list))
    if str(candidate_list) in already_listed:
        return True
    already_listed.add(str(candidate_list))
    return False

def multifactoring(G, item_list,border_edges=[], allow_loops=False):
    candidates=[]
    already_listed=set()
    ignored=[]
    if len(set(item_list))==len(item_list):
        log3('all distinct items',item_list)
        possible_pairs=list(combinations(item_list, 2))
        log4('edge option:',possible_pairs)
        for candidate in combinations(possible_pairs, len(item_list)//2):
            if len(candidate)==1:
                candidate=[(candidate[0][0],candidate[0][1])]
            log4('candidate:',candidate,len(candidate))
            #check if not disjoint
            item_set=set()
            for u,v in candidate:
                item_set.add(u)
                item_set.add(v)
            if len(item_set)==len(item_list):
                if is_already_listed(already_listed,candidate):
                    continue
                log3('We try', candidate)
                quality=quality_of_a_candidate(G,candidate,border_edges)
                if quality==0:
                    yield list(candidate)
                else:
                    candidates.append((candidate,quality))
    else:
        log3('There is some repetition among items',item_list)
        possible_pairs=list(combinations(range(len(item_list)), 2))
        hist={}
        for i in item_list:
            if i in hist:
                hist[i]+=1
            else:
                hist[i]=1
        allow_loop_edge=allow_loops
        if max(hist.values())>len(item_list)//2:
            log3('Allow loop edges because',hist)
            allow_loop_edge=True
        for candidate in combinations(possible_pairs, len(item_list)//2):
            #check if not disjoint
            item_set=set()
            for u,v in candidate:
                item_set.add(u)
                item_set.add(v)
            if len(item_set)==len(item_list):
                log3('indices', candidate)
                ignore=False
                candidate_list=[]
                for u,v in list(candidate):
                    candidate_list.append((item_list[u],item_list[v]))
                    if item_list[v]==item_list[u] and not allow_loop_edge:
                        ignore=True
                if is_already_listed(already_listed,candidate_list):
                    continue
                if not ignore:
                    log3('WWe try', candidate_list)
                    quality=quality_of_a_candidate(G, candidate_list,border_edges)
                    if quality==0:
                        yield candidate_list
                    else:
                        candidates.append((candidate_list,quality))
                else:
                    ignored.append(candidate_list)
    # sort by the number of parallel edges
    candidates.sort(key=lambda x: x[1])
    log2('Rest of candidates (multifactoring):',candidates)
    for candidate,count in candidates:
        yield list(candidate)
    if allow_loops:
        for candidate in ignored:
            quality=quality_of_a_candidate(G, candidate_list,border_edges)
            if quality==0:
                yield list(candidate_list)
            else:
                candidates.append((candidate_list,quality))
        candidates.sort(key=lambda x: x[1])
        log2('Candidates:',candidates)
        for candidate,count in candidates:
            yield list(candidate)

def pair_multifactoring(G, item_list1,item_list2,degree_between, border_edges=[], allow_tear_off=True):
    log2('pair_multifactoring(',item_list1,'and',item_list2,'border edges:',border_edges)
    already_listed=set()
    candidates=[]
    # first without the H link
    if len(item_list1)%2==0 and len(item_list2)%2==0:
        log3('first without the H link')
        for candidate1 in multifactoring(G, item_list1):
            log2('candidate1',candidate1)
            for candidate2 in multifactoring(G, item_list2):
                log2('candidate1 and candidate2',candidate1,candidate2)
                candidate=candidate1+candidate2
                if is_already_listed(already_listed,candidate):
                    continue
                quality=quality_of_a_candidate(G,candidate,border_edges)
                if quality==0:
                    yield candidate
                else:
                    candidates.append((candidate,quality))
        candidates.sort(key=lambda x: x[1])
        log2('Rest of candidates (pair0):',candidates)
        for candidate,count in candidates:
            yield candidate
    # now allow single H link:
    if len(item_list1)%2==1 and len(item_list2)%2==1:
        log3('now allow single H link')
        for c1, item1  in enumerate(item_list1):
            item_list1_=item_list1[:c1]+item_list1[c1+1:]
            for candidate1 in multifactoring(G, item_list1_):
                for candidate2 in multifactoring(G, [item1]+item_list2):
                    candidate=candidate1+candidate2
                    if is_already_listed(already_listed,candidate):
                        continue
                    quality=quality_of_a_candidate(G,candidate,border_edges)
                    if quality==0:
                        yield candidate
                    else:
                        candidates.append((candidate,quality))
        candidates.sort(key=lambda x: x[1])
        log2('Rest of candidates (pair1):',candidates)
        for candidate,count in candidates:
            yield candidate
    # now allow two H links:
    if len(item_list1)%2==0 and len(item_list2)%2==0 and not (degree_between==1 and not allow_tear_off):
        log3('now allow two H links')
        for c1, item1  in enumerate(item_list1):
            for c2,item2  in enumerate(item_list2):
                if item1==item2:
                    continue
                item_list1_=item_list1.copy()
                item_list1_[c1]=item2
                item_list2_=item_list2.copy()
                item_list2_[c2]=item1
                log3('We swap items',item1,item2,'remaining',item_list1_,item_list2_)
                for candidate1 in multifactoring(G, item_list1_):
                    for candidate2 in multifactoring(G, item_list2_):
                        candidate=candidate1+candidate2
                        if is_already_listed(already_listed,candidate):
                            continue
                        quality=quality_of_a_candidate(G, candidate,border_edges)
                        if quality==0:
                            yield candidate
                        else:
                            candidates.append((candidate,quality))
        candidates.sort(key=lambda x: x[1])
        log2('Rest of candidates (pair2):',candidates)
        for candidate,count in candidates:
            yield candidate
        if degree_between!=1:
            log2('degree between is',degree_between,'we call regular multifactoring')
            multifactoring(G, item_list1+item_list2,border_edges, True)

def show_graph(G,force=False):
    global argparse
    if not args.fig and not force:
        return
    #log3(G.nodes())
    pos = nx.get_node_attributes(G, 'pos')
    nx.draw(G, pos, with_labels = True)
    nx.draw_networkx_edge_labels(G, pos, nx.get_edge_attributes(G,'capacity'))
    plt.show()

# if removing a single node
def list_critical_cuts(G,n):
    cuts_to_check=[]
    T = nx.gomory_hu_tree(G)
    for u,v in T.edges():
        if u==n or v==n:
            continue
        cut=T[u][v]["weight"]
        log3('Check',u,v,'cut:',cut)
        cuts_to_check.append((u,v,cut))
    for u1,v1 in T.edges(n):
        cut1=T[u1][v1]["weight"]
        if u1==n:
            u=v1
        else:
            u=u1
        for u2,v2 in T.edges(n):
            if u1==u2 and v1==v2:
                continue
            cut=min(cut1,T[u2][v2]["weight"])
            if u2==n:
                v=v2
            else:
                v=u2
            log3('Check',u,v,'cut',cut,'Neighbors cut1',cut1,'nodes',u1,v1,u2,v2)
            cuts_to_check.append((u,v,cut))
    return cuts_to_check

def remove_single_node(G, root, n):
    if is_debug(3): show_graph(G)
    copygraph = nx.Graph()
    removed_edges=[]
    degree=0
    loop_edge=0
    for v in G.nodes:
        if v!=n:
            copygraph.add_node(v,pos=G.nodes[v]["pos"])
    for u,v in G.edges():
        if u==v:
            loop_edge+=1
            continue
        if u==n or v==n:
            if u==n:
                vv=v
            else:
                vv=u
            for i in range(G[u][v]["capacity"]):
                removed_edges.append(vv)
            degree=degree+G[u][v]["capacity"]
        elif u!=v:
            copygraph.add_edge(u,v)
            copygraph[u][v]["capacity"]=G[u][v]["capacity"]
            log3(u,v)
    if degree+loop_edge % 2==1:
        log1('Warning! Not possible to remove node',n,'because it has odd degree, as adjacent with',removed_edges)
        return False
    log2('we remove node',n,', it has even nodal degree',degree, 'adjacent with nodes',removed_edges)
    for v in copygraph.nodes:
        copygraph.nodes[v]["pos"]=G.nodes[v]["pos"]
    border_edges=[]
    for u,v in G.edges():
        if u in removed_edges and v in removed_edges:
            border_edges.append((u,v))
    log_xml('<graph>')
    log_xmltag('removed_nodenum',1)
    log_xmltag('node_num_at',len(copygraph.nodes))
    log_xmltag('borders',len(removed_edges))
    log_xml('</graph>')
    # generate a list of cuts to check
    cuts_to_check=list_critical_cuts(G,n)
    for candidate in multifactoring(G, removed_edges,border_edges):
        log2('We try', candidate)
        #candidate=[(11, 10), (8, 3), (1, 0)]
        for u,v in list(candidate):
            if copygraph.has_edge(u, v):
                copygraph[u][v]["capacity"]+=1
            elif u!=v:
                copygraph.add_edge(u,v)
                copygraph[u][v]["capacity"]=1
        if is_debug(3): show_graph(copygraph)
        OK=True
        for u,v,cutvalue in cuts_to_check:
            log3('Now checking',u,v,'cut:',cutvalue)
            real=nx.maximum_flow_value(copygraph, u, v, capacity="capacity")
            if real<cutvalue:
                log2('Connectivity has changed between nodes',u,v,':',cutvalue,'->',real)
                OK=False
                break
        if OK:
            log2('succeed removing singe node',n)
            return copygraph,candidate, [n]
        else:
            log2('failed')
        for u,v in list(candidate):
            if u==v and copygraph.has_edge(u,v)==False:
                continue
            if copygraph[u][v]["capacity"]==1:
                copygraph.remove_edge(u,v)
            else:
                copygraph[u][v]["capacity"]-=1
    log1('Failed!!!!!!!!')
    #sys.exit(-1)
    return None,None,None

#if removing two nodes
def list_critical_cuts2(G,n1,n2):
    T = nx.gomory_hu_tree(G)
    cuts_to_check=[]
    for u,v in T.edges():
        if u==n1 or v==n1 or u==n2 or v==n2:
            continue
        log3('Check',u,v)
        cuts_to_check.append((u,v,T[u][v]["weight"]))
    cut_n1_n2=-1
    for u1,v1 in T.edges(n1):
        if v1==n2:
            cut_n1_n2=T[u1][v1]["weight"]
            continue
        cut1=T[u1][v1]["weight"]
        for u2,v2 in T.edges(n1):
            if v1==v2:
                continue
            if v2==n2 :
                continue
            cut=min(cut1,T[u2][v2]["weight"])
            log2('Check',v1,v2,'cut',cut,'a Neighbors n1 cut1',cut1,u1,v1,u2,v2)
            cuts_to_check.append((v1,v2,cut))
    for u1,v1 in T.edges(n2):
        if v1==n1:
            continue
        cut1=T[u1][v1]["weight"]
        for u2,v2 in T.edges(n2):
            if v1==v2:
                continue
            if v2==n1:
                continue
            cut=min(cut1,T[u2][v2]["weight"])
            log2('Check',v1,v2,'cut',cut,'b Neighbors n2 cut1',cut1,u1,v1,u2,v2)
            cuts_to_check.append((v1,v2,cut))
    if cut_n1_n2==-1:
        path = nx.shortest_path(T, n1, n2, weight="weight")
        cut_n1_n2=min( T[u][v]["weight"] for (u, v) in zip(path, path[1:]))
        log3('cut betwenn n1 and n2 is ',cut_n1_n2)
    for u1,v1 in T.edges(n1):
        if v1==n2 or v1==n1:
            continue
        cut1=min(cut_n1_n2,T[u1][v1]["weight"])
        for u2,v2 in T.edges(n2):
            if v1==v2:
                continue
            if v2==n1:
                continue
            cut=min(cut1,T[u2][v2]["weight"])
            log2('Check',v1,v2,'cut',cut,'c Neighbors n1 cut1',cut1,u1,v1,u2,v2)
            cuts_to_check.append((v1,v2,cut))
    return cuts_to_check

def remove_two_nodes(G, root, n1, n2, allow_tear_off=True):
    if is_debug(3): show_graph(G)
    if not G.has_edge(n1, n2):
        log1('Not possible to remove the nodes',n1,'and',n2,'because there is no edge between them')
        return False
    log2('we remove nodes',n1,n2)
    copygraph = nx.Graph()
    removed_edges1=[]
    removed_edges2=[]
    degree_n1=0
    degree_n2=0
    degree_between=0
    for v in G.nodes:
        if v!=n1 and v!=n2:
            copygraph.add_node(v,pos=G.nodes[v]["pos"])
    for u,v in G.edges():
        if (u==n1 and v==n2) or (u==n2 and v==n1):
            degree_between=degree_between+G[u][v]["capacity"]
            continue
        if u==n1 or v==n1:
            if u==n1:
                vv=v
            else:
                vv=u
            for i in range(G[u][v]["capacity"]):
                removed_edges1.append(vv)
            degree_n1=degree_n1+G[u][v]["capacity"]
        elif u==n2 or v==n2:
            if u==n2:
                vv=v
            else:
                vv=u
            for i in range(G[u][v]["capacity"]):
                removed_edges2.append(vv)
            degree_n2=degree_n2+G[u][v]["capacity"]
        elif u!=v:
            copygraph.add_edge(u,v)
            copygraph[u][v]["capacity"]=G[u][v]["capacity"]
            log3('Edge:',u,v)
    for v in copygraph.nodes:
        copygraph.nodes[v]["pos"]=G.nodes[v]["pos"]
    #if degree_n1 % 2==1 or degree_n2 % 2==1:
    if degree_n1 + degree_n2 % 2==1:
        log1('Warning! Not possible to remove the nodes',n1,'and',n2,'because their nodal degree is not odd')
        log1('Node',n1,'has even nodal degree',degree_n1)
        log1('Node',n2,'has even nodal degree',degree_n2, removed_edges1,removed_edges2)
        return False
    log2('Adjacent to',removed_edges1,'and',removed_edges2)
    for v in copygraph.nodes:
        copygraph.nodes[v]["pos"]=G.nodes[v]["pos"]
    removed_edges=removed_edges1+removed_edges2
    border_edges=[]
    for u,v in G.edges():
        if u in removed_edges and v in removed_edges:
            border_edges.append((u,v))
    log_xml('<graph>')
    log_xmltag('removed_nodenum',2)
    log_xmltag('node_num_at',len(copygraph.nodes))
    log_xmltag('borders',len(removed_edges))
    log_xml('</graph>')
    # generate a list of cuts to check
    cuts_to_check=list_critical_cuts2(G,n1,n2)
    for candidate in pair_multifactoring(G, removed_edges1,removed_edges2,degree_between,border_edges, allow_tear_off):
    #for candidate in multifactoring(removed_edges,border_edges):
        log2('We try', candidate)
        for u,v in list(candidate):
            if copygraph.has_edge(u, v):
                copygraph[u][v]["capacity"]+=1
            elif u!=v:
                copygraph.add_edge(u,v)
                copygraph[u][v]["capacity"]=1
        if is_debug(3): show_graph(copygraph)
        OK=True
        for u,v,cutvalue in cuts_to_check:
            log3('Check',u,v)
            real=nx.maximum_flow_value(copygraph, u, v, capacity="capacity")
            if real<cutvalue:
                log2('Connectivity has changed between nodes',u,v,':',cutvalue,'->',real,'min cut:',nx.minimum_cut(copygraph, u, v, capacity="capacity"))
                OK=False
                break
        if OK:
            log2('succeed removing node pair',n1,n2)
            return copygraph,candidate,[n1,n2]
        else:
            log2('failed')
        for u,v in list(candidate):
            if u==v:
                continue
            if copygraph[u][v]["capacity"]==1:
                copygraph.remove_edge(u,v)
            else:
                copygraph[u][v]["capacity"]-=1
    log1('Failed!!!!!!!!')
    #sys.exit(-1)
    return None,None,None

def leveler_degree(G, root):
    """
    Parameters
    ----------
    graph : networkx graph
        Input graph.
    root : node label, optional
        Label of the root node. The default is 0.

    Gives the nodes a 'level' attribute depending on how far they are from the root.
    Gives the edges a 'level' attribute which is the average of their endpoints' levels.
    Gives the nodes a 'sameneighbour' attribute as the number of neighbours with the same level.
    Gives the nodes an 'allneighbour' attribute as the number of neighbours with the same or at most 1 less level.
    ----------

    Returns: None
    """
    global args
    nx.set_node_attributes(G,True,"odd")
    for n in G.nodes:
        degree=0
        for u,v in G.edges(n):
            if u!=v:
                degree=degree+G[u][v]["capacity"]
        G.nodes[n]["odd"]=degree%2
    if args.fig:
        pos = nx.get_node_attributes(G, 'pos')
        color_map = {}
        for n in G.nodes:
            if G.nodes[n]["odd"]:
                color_map[n]='yellow'
            else:
                color_map[n]='green'
        nx.draw(G, pos, with_labels = True,  node_color=list(color_map.values()),nodelist=color_map.keys())
        nx.draw_networkx_edge_labels(G, pos, nx.get_edge_attributes(G,'capacity'))
        plt.show()

    nx.set_node_attributes(G,-1,"level")
    nx.set_node_attributes(G,0,"sameneighbour")
    nx.set_node_attributes(G,0,"allneighbour")
    attrs = {root: {"level":0}}
    nx.set_node_attributes(G, attrs)
    leveled = {root}
    currentlytolevel = [root]
    while len(leveled) < len(G):
        nexttolevel = []
        for node in currentlytolevel:
            for neighbour in G.neighbors(node):
                if G.nodes[neighbour]["level"] == -1:
                    G.nodes[neighbour]["level"] = G.nodes[node]["level"]+1
                    leveled.add(neighbour)
                    nexttolevel.append(neighbour)
        currentlytolevel = nexttolevel

def select_node_to_remove_random(graph, root):
    r = list(graph.nodes)
    random.shuffle(r)
    for node in r:
        if node==root:
            continue
        if not graph.nodes[node]["odd"]:
            return remove_single_node(graph,root,node)
        for u,n in graph.edges(node):
            if n==root:
                continue
            if graph.nodes[n]["odd"]:
                return remove_two_nodes(graph, root, node, n)

def st_connectivity(graph,s,t):
    return nx.maximum_flow_value(graph, s, t, capacity="capacity")

def compute_local_connectivty(graph,root):
    if 'loc_con' in graph.graph:
        return
    graph.graph['loc_con'] = True
    for node in graph.nodes:
        if node==root:
            continue
        graph.nodes[node]['loc_con']=st_connectivity(graph,node,root)

def select_node_to_remove_con(graph, root):
    compute_local_connectivty(graph,root)
    min_con=-1
    max_con=-1
    min_con_nodes=[]
    for node in graph.nodes:
        if node!=root:
            loc_con=graph.nodes[node]['loc_con']
            if min_con==-1 or min_con>loc_con:
                 min_con_nodes=[node]
                 min_con=loc_con
            elif min_con==loc_con:
                min_con_nodes.append(node)
            if max_con==-1 or max_con<loc_con:
                 max_con=loc_con
    log2('local connnectivity: min=',min_con,' max=',max_con,' min con nodes:', min_con_nodes)
    max_hop_even=[-1]*(max_con+1)
    max_hop_even_dist=[-1]*(max_con+1)
    max_hop_odd_dist=[-1]*(max_con+1)
    # 2: Most már csak páratlan fokú pontod van $l$ távolságra. Ha van $l+1$ távolságú pontod (az első iterációban ilyen még nem lesz), akkor ezek szomszédja csak $l$ távolságú lehet, amelyek között már csak páratlan fokú pont maradt. Ezeket a páratlan fokú a szomszédokat leemeled a Fig 1b alapján, amíg el nem fogynak.
    max_hop_odd_with_max_hop_odd_neighbour1=[-1]*(max_con+1)
    max_hop_odd_with_max_hop_odd_neighbour2=[-1]*(max_con+1)
    max_hop_odd_with_max_hop_odd_neighbour_dist=[-1]*(max_con+1)
    # 3: Most már csak páratlan fokú pontod van $l$ távolságra, és nincs $l+1$ távolságú pontod. Ekkor megnézed, hogy az $l$ távolságú pontok között van-e olyan, amelyek szomszédosak. Ha igen, leemeled a Fig 1b alapján, amíg el nem fogynak.
    max_hop_odd_with_odd_neighbour1=[-1]*(max_con+1)
    max_hop_odd_with_odd_neighbour2=[-1]*(max_con+1)
    max_hop_odd_with_odd_neighbour_dist=[-1]*(max_con+1)
    # 4: Most már $l$ távolságra is csak olyan páratlan fokú pontod van, amelyek csak $l-1$ ugrásnyi távolságra lévő pontokhoz kapcsolódnak. Ha ezek között van olyan amelyiknek páratlan fokú a szomszédja, akkor leemeled a Fig 1b alapján, amíg el nem fogynak.
    # 5: Most már csak olyan páratlan fokú pontod van, amelyek csak $l-1$ ugrásnyi távolságra lévő páros fokú pontokhoz kapcsolódnak. Ekkor l:=l-1 és visszalépsz 1-re.
    for node in graph.nodes:
        if node==root:
            continue
        loc_con=graph.nodes[node]['loc_con']
        if graph.nodes[node]["odd"]:
            if graph.nodes[node]["level"] >= max_hop_odd_dist[loc_con]:
                max_hop_odd_dist[loc_con]=graph.nodes[node]["level"]
                # check if it has an odd neighbour
                for u,n in graph.edges(node):
                    if n==root:
                        continue
                    #if graph[u][n]["capacity"]!=1:
                    #    continue
                    log3('check node',u,n)
                    if graph.nodes[n]["odd"]:
                        if graph.nodes[n]["level"]==max_hop_odd_dist[loc_con]:
                            max_hop_odd_with_max_hop_odd_neighbour1[loc_con]=node
                            max_hop_odd_with_max_hop_odd_neighbour2[loc_con]=n
                            max_hop_odd_with_max_hop_odd_neighbour_dist[loc_con]=max_hop_odd_dist[loc_con]
                        else:
                            max_hop_odd_with_odd_neighbour1[loc_con]=node
                            max_hop_odd_with_odd_neighbour2[loc_con]=n
                            max_hop_odd_with_odd_neighbour_dist[loc_con]=max_hop_odd_dist[loc_con]
        else:
            if graph.nodes[node]["level"] > max_hop_even_dist[loc_con]:
                max_hop_even_dist[loc_con]=graph.nodes[node]["level"]
                max_hop_even[loc_con]=node
    log2('root:',root)
    log2('Node',max_hop_even,'has even degree with max hop distance',max_hop_even_dist)
    log2('There is a node with odd degree of max hop distance',max_hop_odd_dist)
    log2('Adjacent nodes have odd degree both with',max_hop_odd_with_max_hop_odd_neighbour_dist,'hop distance:, nodes',max_hop_odd_with_max_hop_odd_neighbour1,max_hop_odd_with_max_hop_odd_neighbour2)
    log2('Adjacent nodes have odd degree the first with',max_hop_odd_with_odd_neighbour_dist,'hop distance, nodes:',max_hop_odd_with_odd_neighbour1,max_hop_odd_with_odd_neighbour2)
    for con in range(min_con,max_con+1):
        if max_hop_even_dist[con]>=0 and (max_hop_even_dist[con]>=max_hop_odd_dist[con] or 'even_nodes_first' in args.obj):
            return remove_single_node(graph,root,max_hop_even[con])
        else:
            if max_hop_odd_with_max_hop_odd_neighbour_dist[con]!=0 and max_hop_odd_with_max_hop_odd_neighbour_dist[con]==max_hop_odd_dist[con] and max_hop_odd_dist[con]>=0:
                if '_chi' in args.obj:
                    return select_proper_two_node_to_remove(graph, root, max_hop_odd_with_max_hop_odd_neighbour1[con], max_hop_odd_with_max_hop_odd_neighbour2[con])
                return remove_two_nodes(graph, root, max_hop_odd_with_max_hop_odd_neighbour1[con], max_hop_odd_with_max_hop_odd_neighbour2[con])
            elif max_hop_odd_with_odd_neighbour_dist[con]!=0 and max_hop_odd_with_odd_neighbour_dist[con]>=0:
                if '_chi' in args.obj:
                    return select_proper_two_node_to_remove(graph, root, max_hop_odd_with_odd_neighbour1[con], max_hop_odd_with_odd_neighbour2[con])
                return remove_two_nodes(graph, root, max_hop_odd_with_odd_neighbour1[con], max_hop_odd_with_odd_neighbour2[con])
            elif max_hop_even[con]>=0:
                log2('itt')
                return remove_single_node(graph,root,max_hop_even[con])

def select_node_to_remove(graph, root):
    """
    Parameters
    ----------
    graph : input graph in networkx graph format
    root : label of the root node, optional
        The default is 0.
    -------
    Returns:
    A list of nodes with maximal distance from the root in order. Primary ordering parameter is the number of neighbours on the same level (same distance from the root), secondary ordering parameter is the total number of neighbours of the node
    """
    # 1: Veszed az $l$ távolságú páros fokú pontokat. Leemeled őket Fig 1a alapján, amíg el nem fogynak.
    max_hop_even=-1
    max_hop_even_dist=-1
    max_hop_odd_dist=-1
    # 2: Most már csak páratlan fokú pontod van $l$ távolságra. Ha van $l+1$ távolságú pontod (az első iterációban ilyen még nem lesz), akkor ezek szomszédja csak $l$ távolságú lehet, amelyek között már csak páratlan fokú pont maradt. Ezeket a páratlan fokú a szomszédokat leemeled a Fig 1b alapján, amíg el nem fogynak.
    max_hop_odd_with_max_hop_odd_neighbour1=-1
    max_hop_odd_with_max_hop_odd_neighbour2=-1
    max_hop_odd_with_max_hop_odd_neighbour_dist=-1
    # 3: Most már csak páratlan fokú pontod van $l$ távolságra, és nincs $l+1$ távolságú pontod. Ekkor megnézed, hogy az $l$ távolságú pontok között van-e olyan, amelyek szomszédosak. Ha igen, leemeled a Fig 1b alapján, amíg el nem fogynak.
    max_hop_odd_with_odd_neighbour1=-1
    max_hop_odd_with_odd_neighbour2=-1
    max_hop_odd_with_odd_neighbour_dist=-1
    # 4: Most már $l$ távolságra is csak olyan páratlan fokú pontod van, amelyek csak $l-1$ ugrásnyi távolságra lévő pontokhoz kapcsolódnak. Ha ezek között van olyan amelyiknek páratlan fokú a szomszédja, akkor leemeled a Fig 1b alapján, amíg el nem fogynak.
    # 5: Most már csak olyan páratlan fokú pontod van, amelyek csak $l-1$ ugrásnyi távolságra lévő páros fokú pontokhoz kapcsolódnak. Ekkor l:=l-1 és visszalépsz 1-re.
    for node in graph.nodes:
        if node==root:
            continue
        if graph.nodes[node]["odd"]:
            log3('check odd node',node)
            if graph.nodes[node]["level"] >= max_hop_odd_dist:
                log3('check its neighbours')
                max_hop_odd_dist=graph.nodes[node]["level"]
                # check if it has an odd neighbour
                for u,n in graph.edges(node):
                    if n==root:
                        continue
                    #if graph[u][n]["capacity"]!=1:
                    #    continue
                    log3('check neighbour odd node',n)
                    if graph.nodes[n]["odd"]:
                        if graph.nodes[n]["level"]==max_hop_odd_dist:
                            max_hop_odd_with_max_hop_odd_neighbour1=node
                            max_hop_odd_with_max_hop_odd_neighbour2=n
                            max_hop_odd_with_max_hop_odd_neighbour_dist=max_hop_odd_dist
                        else:
                            max_hop_odd_with_odd_neighbour1=node
                            max_hop_odd_with_odd_neighbour2=n
                            max_hop_odd_with_odd_neighbour_dist=max_hop_odd_dist
        else:
            if graph.nodes[node]["level"] > max_hop_even_dist:
                max_hop_even_dist=graph.nodes[node]["level"]
                max_hop_even=node
    log2('root:',root)
    log2('Node',max_hop_even,'has even degree with max hop distance',max_hop_even_dist)
    log2('There is a node with odd degree of max hop distance',max_hop_odd_dist)
    log2('Adjacent nodes have odd degree both with',max_hop_odd_with_max_hop_odd_neighbour_dist,'hop distance:, nodes',max_hop_odd_with_max_hop_odd_neighbour1,max_hop_odd_with_max_hop_odd_neighbour2)
    log2('Adjacent nodes have odd degree the first with',max_hop_odd_with_odd_neighbour_dist,'hop distance, nodes:',max_hop_odd_with_odd_neighbour1,max_hop_odd_with_odd_neighbour2)
    if max_hop_even_dist>=0 and (max_hop_even_dist>=max_hop_odd_dist or args.obj=='even_nodes_first' or args.obj=='even_nodes_first_chi'):
        return remove_single_node(graph,root,max_hop_even)
    else:
        if max_hop_odd_with_max_hop_odd_neighbour_dist!=0 and max_hop_odd_with_max_hop_odd_neighbour_dist==max_hop_odd_dist and max_hop_odd_dist>=0:
            if args.obj=='even_nodes_first_chi':
                return select_proper_two_node_to_remove(graph, root, max_hop_odd_with_max_hop_odd_neighbour1, max_hop_odd_with_max_hop_odd_neighbour2)
            log2('We give up 1')
            return remove_two_nodes(graph, root, max_hop_odd_with_max_hop_odd_neighbour1, max_hop_odd_with_max_hop_odd_neighbour2)
        elif max_hop_odd_with_odd_neighbour_dist!=0 and max_hop_odd_with_odd_neighbour_dist>=0:
            if args.obj=='even_nodes_first_chi':
                return select_proper_two_node_to_remove(graph, root, max_hop_odd_with_odd_neighbour1, max_hop_odd_with_odd_neighbour2)
            log2('We give up 2')
            return remove_two_nodes(graph, root, max_hop_odd_with_odd_neighbour1, max_hop_odd_with_odd_neighbour2)
        else:
            log2('itt')
            return remove_single_node(graph,root,max_hop_even)

def select_proper_two_node_to_remove(graph, root, n1, n2, ignore=[]):
    log2('Call remove two nodes without allowing tear-off')
    ret=remove_two_nodes(graph, root, n1, n2, False)
    even_nodes=[]
    if ret[0]==None:
        ignore.append((n1, n2))
        log2('Try removing other nodes',ignore)
        show_graph(graph)
        nn1=None
        for node in graph.nodes:
            if node==root:
                continue
            if not graph.nodes[node]["odd"]:
                log2('Node', node,'is even')
                if node not in even_nodes:
                    even_nodes.append(node)
                continue
            for u,n in graph.edges(node):
                if n==root:
                    continue
                if not graph.nodes[n]["odd"]:
                    log2('Neighbour node ',n,'is odd')
                    if n not in even_nodes:
                        even_nodes.append(n)
                    continue
                log2('check nodes',node,n)
                if not ((node,n) in ignore) and not ((n,node) in ignore):
                    log2('A new node pair to remove:',node,n)
                    nn1=node
                    nn2=n
                    break
            if nn1!=None:
                break
        if len(ignore)<=10 and nn1!=None:
            log2('recursive call',nn1,nn2)
            return select_proper_two_node_to_remove(graph, root, nn1, nn2, ignore)
        else:
            if len(even_nodes)>0:
                min_con=-1
                nn=even_nodes[0]
                if 'loc_con' in graph.graph:
                    for n in even_nodes:
                        if min_con==-1 or graph.nodes[n]['loc_con']<min_con:
                            min_con=graph.nodes[n]['loc_con']
                            nn=n
                return remove_single_node(graph,root,nn)
            log1('Warning! finding proper odd node pair is failed')
            global warnings
            warnings+=1
            return remove_two_nodes(graph, root, n1, n2)
    else:
        log2('erase ignore')
        ignore.clear()
        return ret




def decompose(G,root,prev_new_edges=[]):
    ID=str(len(G.nodes))
    if args.fig:
        dg.showGraphJS(G,'figures/graph'+ID+'.json','figures/graph'+ID+'.html')
    #if len(G.nodes)<=2:
    if len(G.nodes)<=3:
        log2('The graph has 2 nodes. edges:',G.edges)
        if args.tikz:
            ddraw.showGraphTex(G, 'graph'+ID+'.tex', root,args.tikz_scale,[],[],prev_new_edges)
        node_pos=[]
        for n in G.nodes:
            node_pos.append(G.nodes[n]['pos'])
        edge_list=[]
        for u,v in G.edges:
            for i in range(G[u][v]["capacity"]):
                edge_list.append((u,v))
        ret=(edge_list,list(G.nodes),node_pos,root)
        return [ret]
    # pick the nodes to remove
    leveler_degree(G, root)
    if 'random' in args.obj:
        GG,new_edges,removed_nodes=select_node_to_remove_random(G,root)
    elif '_con' in args.obj:
        GG,new_edges,removed_nodes=select_node_to_remove_con(G,root)
    else:
        GG,new_edges,removed_nodes=select_node_to_remove(G,root)
    log1('new_edges', new_edges,'removed nodes', removed_nodes,'the new graph has', list(GG.nodes))
    ret=None
    if GG:
        if args.tikz:
            highlight_edges=[]
            if len(removed_nodes)==2:
                highlight_edges=[(removed_nodes[0],removed_nodes[1])]
            for u,v in G.edges:
                if u in removed_nodes or v in removed_nodes:
                    highlight_edges.append((u,v))
            ddraw.showGraphTex(G, 'graph'+ID+'.tex', root,args.tikz_scale,args.mirror, removed_nodes,highlight_edges,prev_new_edges)
        for n in GG.nodes:
            GG.nodes[n]["pos"] = G.nodes[n]["pos"]
        # recursive call
        ret=[new_edges]
        for n in removed_nodes:
            neighbors=[]
            for u,v in G.edges(n):
                for i in range(G[u][v]["capacity"]):
                    neighbors.append(v)
            ret.append([neighbors,n,G.nodes[n]['pos']])
        ret=decompose(GG,root,new_edges)+[ret]
    return ret

def read_json_file(filename):
    with open(filename) as f:
        js_graph = json.load(f)
    G=(json_graph.node_link_graph(js_graph))
    for n in G.nodes:
        G.nodes[n]["pos"] = (nx.get_node_attributes(G,'x')[n],nx.get_node_attributes(G,'y')[n])
    global average_edge_length
    average_edge_length=0
    for u,v  in G.edges:
        average_edge_length+=edge_physical_length(G,u,v)
    average_edge_length=average_edge_length/len(G.edges)
    nx.set_edge_attributes(G, 1, "capacity")
    return G



if __name__ == "__main__":
    input_topology = read_json_file(args.file)
    warnings=0
    if args.root>=0:
        root=args.root
        out_file_name=args.file.replace('net/','res/')+'.root'+str(root)+'_'+args.obj+'.dgh'
        xml_file_name=out_file_name[:-4]+'run.xml'
        xml_file = open(xml_file_name, "w") # used to be "a"
        log_xml('<?xml version="1.0" encoding="UTF-8"?>')
        log_xml('<simulation>')
        log_xmltag("node_num",len(input_topology.nodes))
        log_xmltag("edge_num",len(input_topology.edges))
        log_xmltag("root",root)
        log_xmltag("obj",args.obj)
        start = time.time()
        decompose_list=decompose(input_topology,root)
        end = time.time()
        log_xmltag("runtime",end - start)
        log_xmltag("warnings",warnings)
        log_xml('</simulation>')
        xml_file.close()
        with open(args.file.replace('net/','res/')+'.root'+str(root)+'-'+args.obj+'.dgh', 'w') as fp:
            json.dump(decompose_list, fp)
        log1('Number of warnings',warnings)
        log1(decompose_list)
    else:
        counter=-args.root
        for root in input_topology.nodes:
            if counter<0:
                break
            counter-=1
            log1('Decompose for root',root)
            decompose_list=decompose(input_topology,root)
            with open(args.file.replace('net/','res/')+'.root'+str(root)+'-'+args.obj+'.dgh', 'w') as fp:
                json.dump(decompose_list, fp)
            log1(decompose_list)

if args.test:
    if args.fig:
        dg.showGraphJS('22_optic_eu.lgf.json','graph.json','graph.html')
    remove_two_nodes(input_topology, 0, 1, 7)
    #decompose(G,0)
