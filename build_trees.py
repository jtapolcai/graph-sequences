# -*- coding: utf-8 -*-
import networkx as nx
from itertools import combinations, groupby
import DrawGraph as dg
import json
import graph_draw as ddraw
from logger import log1,log2,log3,log4,log5,log6,is_debug,set_debug
import matplotlib.pyplot as plt
import sys,os
import argparse
from Graphhandler import findpath,isoverlapping,hasoutedge,hasinedge,findpath_root, find_parents
from analyze_trees import verifyRouting, analyzeRouting
import time
from mip import Model, xsum, maximize, BINARY, CONTINUOUS,OptimizationStatus
#import graph_construct *

aparser = argparse.ArgumentParser()
aparser.add_argument("-fig", help="Show graphs with Matplotlib", action='store_true')
aparser.add_argument("-tikz", help="Export graphs in tikz", action='store_true')
aparser.add_argument("-tikz_scale", type=float, help="Scale tikz figures", default=200)
aparser.add_argument("-mirror", help="Show the graph upside down", action='store_true')
aparser.add_argument("-log", type=int, help="The logging level: 1- main info, 3- detailed  ", default=3)
aparser.add_argument("-wa", type=int, help="The weight in ILP for variable a", default=1000)
aparser.add_argument("-wl", type=int, help="The weight in ILP for variable l", default=100)
aparser.add_argument("-file", type=str, help="The input .json network file", default='net/16_test_torus_4x4.lgf.json.dgh')#'22_optic_eu.lgf.json')
#aparser.add_argument("-xml_outfile", type=str, help="The xml file where the results are stored", default='result.xml')
aparser.add_argument("-test", help="Run tests", action='store_true')
aparser.add_argument("-debug", help="Show figures for debuging", action='store_true')
aparser.add_argument("-id", type=str, help="An id added to the result files", default='0')
aparser.add_argument("-dis", type=str, help="Disjointness arc, edge, node", default='arc')
aparser.add_argument("-obj", type=str, help="The objective of the path lenght in the optimization: avg, longest, shortest", default='avg')
aparser.add_argument("-nopostprocess", help="Disable post processing", action='store_true')
aparser.add_argument("-dat", help="Write coverage in dat file", action='store_true')

args = aparser.parse_args()
set_debug(args.log)

all_colors=["red", "green", "blue",'orange','purple',"pink","grey"]
# the final graph is used to efficiently compute cuts
final_graph=nx.DiGraph()

def st_connectivity(G,s,t):
    global final_graph
    return nx.maximum_flow_value(final_graph, s, t, capacity="capacity")

row_counter=0
def rowId():
    global row_counter
    row_counter+=1
    return 'r'+str(row_counter)

def show_graph(G, force=False):
    global argparse
    if not args.fig and not force:
        return
    #log3(G.nodes())
    pos = nx.get_node_attributes(G, 'pos')
    #log2(nx.get_edge_attributes(G,'color'))
    nx.draw(G, pos, with_labels = True,edge_color='white')
    ax = plt.gca()
    for u,v,i in G.edges:
        arc_color=G[u][v][i]['color']
        log3('draw graph:',u,v,i,arc_color)
        if u!=v:
            ax.annotate("",
                xy=pos[u], xycoords='data',
                xytext=pos[v], textcoords='data',
                arrowprops=dict(arrowstyle="<-", color=arc_color,
                                shrinkA=10, shrinkB=10,
                                patchA=None, patchB=None,
                                connectionstyle="arc3,rad=rrr".replace('rrr',str(0.1*i+0.06)),),)
        else:
            pu=(pos[v][0]+2,pos[v][1]+3)
            pv=(pos[v][0]+2,pos[v][1]-3)
            ax.annotate("",
                xy=pu, xycoords='data',
                xytext=pv, textcoords='data',
                arrowprops=dict(arrowstyle="<-", color=arc_color,
                                shrinkA=10, shrinkB=10,
                                patchA=None, patchB=None,
                                connectionstyle="arc3,rad=rrr".replace('rrr',str(0.3*i+0.1)),),)
    plt.savefig('figures/net'+str(len(G.nodes))+'.png')
    log2('saved as figures/net'+str(len(G.nodes))+'.png')
    plt.show()

def ReBuildTreesGreedy(G, colors, root):
    nodes=[n for n in G.nodes if n!=root]
    for c in colors:
        BuildTreeGreedy(G, c, root,nodes)

def BuildTreeGreedy(G, c, root,parent_nodes):
    log2('BuildTreeGreedy for color', c)
    residual_graph = nx.DiGraph()
    for u,v,i in G.edges(keys=True):
        edge_color=G[u][v][i]['color']
        if edge_color=='black':
            residual_graph.add_edge(u,v,weight=1)
        if edge_color==c:
            residual_graph.add_edge(u,v,weight=0.1)
    # compute a tree
    tree_dict = nx.shortest_path(residual_graph, target=root)
    #log1(tree_dict)
    for u,path in tree_dict.items():
        if u in parent_nodes:
            log2(u,path,'is in the shortest path')
            for i,uu in enumerate(path[:-1]):
                vv=path[i+1]
                log2('first edge',uu,vv)
                fixed=False
                for ii in G[uu][vv]:
                    cc=G[uu][vv][ii]['color']
                    log2('has color',cc)
                    if cc==c:
                        fixed=True
                        break
                if not fixed:
                    for ii in G[uu][vv]:
                        cc=G[uu][vv][ii]['color']
                        log2('has color',cc)
                        if cc=='black':
                            fixed=True
                            log2('We set it to',c)
                            G[uu][vv][ii]['color']=c
                            break
    #sys.exit(-1)

# from the paper Grafting Arborescences for Extra Resilience of Fast Rerouting Schemes
def convertGraph(G, c, root, color):
    color_id={}
    for i,cc in enumerate(color):
        color_id[cc]=i
    for e,cc in G.edges(key=True):
        G[e]['arb']=color_id[cc['color']]
    G.graph['root']=root
    #GreedyMaximalDAG(g)
    #FindTreeNoContinue(G, color_id[cc])

def solve_two_node_graph(G,root,colors):
    if len(G.nodes)!=2:
        log1('Error the first graph must have two nodes, instead of',len(G.nodes))
        return
    for n in G.nodes:
        if n!=root:
            other=n
    log3('root=',root,'other',other)
    count1=0
    #count2=0
    for u,v,i in G.edges:
        log2('graph edge',u,v,i)
        if u==other and v==root:
            G[u][v][i]['color']=colors[count1]
            count1+=1
    return colors[:count1]

def solve_three_node_graph(G,root,colors):
    if len(G.nodes)!=3:
        log1('Error the first graph must have two nodes, instead of',len(G.nodes))
        return
    node_list=list(G.nodes)
    if node_list[0]==root:
        n1=node_list[1]
        n2=node_list[2]
    elif node_list[1]==root:
        n1=node_list[0]
        n2=node_list[2]
    elif node_list[2]==root:
        n1=node_list[0]
        n2=node_list[1]
    else:
        log1('Error root node not found')
        return
    log3('root=',root,'n1',n1,'n2',n2)
    count1=0
    count2=0
    for u,v,i in G.edges:
        #print(u,v,i)
        if u==n1 and v==root:
            G[u][v][i]['color']=colors[count1]
            count1+=1
    count2=count1
    for u,v,i in G.edges:
        if u==n2 and v==root:
            G[u][v][i]['color']=colors[count2]
            count2+=1
    count=count2
    count1_=0
    count2_=count1
    for u,v,i in G.edges:
        #print(u,v,i)
        if u==n2 and v==n1 and count1_<count1:
            G[u][v][i]['color']=colors[count1_]
            count1_+=1
        if u==n1 and v==n2 and count2_<count2:
            G[u][v][i]['color']=colors[count2_]
            count2_+=1
    return colors[:count]

def compute_paths(G,new_edges,colors,root):
    path={}
    term={}
    for c in colors:
        path[c]={}
        term[c]={}
        for u,v,i in new_edges:
            log3('new edge:',u,v,i)
            if v not in path[c]:
                P,dest=findpath_root(G,v,c,root)
                log3('Path from',v,'in color',c,'is',P,'dest',dest)
                if dest==root:
                    path[c][v]=P
                    log3('saved',v,'color',c,'Path',P)
                else:
                    term[c][v]=dest
    return path, term

def identify_nondisjoint_pairs(new_edges,path,colors,disjointness):
    avoid_pairs=[]
    for c1,c2 in combinations(colors,2):
        for (u1,v1,i1),(u2,v2,i2) in combinations(new_edges,2):
            if v1==v2:
                continue
            if v1 in path[c1] and v2 in path[c2]:
                log3('check pairs',v1,v2,c1,c2,'paths',path[c1][v1],path[c2][v2])
                if isoverlapping(path[c1][v1],path[c2][v2],disjointness,root):
                    avoid_pairs.append((c1,v1,c2,v2))
                else:
                    log3('Paths are fine:',c1,v1,c2,v2)
    return avoid_pairs

def identify_upstream_nondisjoint_edges(c1,parent_nodes,new_edges,path,colors,disjointness,G):
    avoid_edges=[]
    for v1 in parent_nodes:
        for c2 in colors:
            for u2,v2,i2 in new_edges:
                if v1==v2 or c1==c2:
                    continue
                P1,dest1=findpath_root(G,v1,c1,root)
                if v2 in path[c2]:
                    log3('check pairs',v1,v2,c1,c2,'paths',P1,path[c2][v2])
                    if isoverlapping(P1,path[c2][v2],disjointness,root):
                        avoid_edges.append((c2,v2))
                    else:
                        log3('Paths are fine:',c2,v2)
    return avoid_edges

def define_variable_cost(x,path,term, l, m):
    obj=args.obj
    cost={}
    hop={}
    #the path lenghts
    links_of_shortest_paths=[]
    min_hop=-1
    for c,xx in x.items():
        cost[c]={}
        hop[c]={}
        for e,var in xx.items():
            cost[c][e]=1
            hop_count=10
            if e[1] in path[c]:
                # shorter path have smaller cost
                hop_count=len(path[c][e[1]])
            hop[c][e]=hop_count
            # for average path length
            cost[c][e]=10+4.0/(1+hop_count)
            if obj=='longest':
                m += x[c][e]*hop_count <= l
            elif obj=='shortest':
    #            m += x[c][e]*hop_count*hop_count <= l
                if min_hop==-1 or hop_count<min_hop:
                     links_of_shortest_paths=[]
                     min_hop=hop_count
                if hop_count<=min_hop:
                     links_of_shortest_paths.append((c,e))
    if obj=='shortest':
        for c,xx in x.items():
            for e,var in xx.items():
                if (c,e) not in links_of_shortest_paths:
                     m += -x[c][e]*hop[c][e] <= l
    return cost

def in_edge_colors(G,n):
    in_colors=set()
    for v,u,i in G.in_edges(n,keys=True):
        log4('in edge',v,u,i)
        in_edge_color=G[v][u][i]['color']
        log4('in edge color',in_edge_color)
        if in_edge_color!='black':
             in_colors.add(in_edge_color)
    return in_colors

def out_edge_colors(G,n):
    out_colors=set()
    for v,u,i in G.out_edges(n,keys=True):
        log4('out edge',v,u,i)
        out_edge_color=G[v][u][i]['color']
        log4('out edge color',out_edge_color)
        if out_edge_color!='black':
             out_colors.add(out_edge_color)
    return out_colors

def border_colors(G,n,root,colors):
    ret=set()
    for v1,u1,i1 in G.in_edges(n,keys=True):
        if v1==root:
            return set(colors)
        for v,u,i in G.out_edges(v1,keys=True):
            out_edge_color=G[v][u][i]['color']
            log4('out edge',v,'-',u,' color',out_edge_color)
            if out_edge_color!='black':
                 ret.add(out_edge_color)
    return ret

def solve_add_node_graph(G,root,n, new_edges,colors,disjointness,no_gap=False):
    log2('We need to assign colors to these edges:',new_edges)
    tree_num=st_connectivity(G,root,n)
    must_colors=colors #in_edge_colors(G,n)
    #colors=must_colors.union(border_colors(G,n,root,colors))
    log2('colors',colors)
    if len(colors)==0:
        return True
    path,term=compute_paths(G,new_edges,colors,root)
    log2('Paths from neighbours',path)
    avoid_pairs=[]
    if disjointness!='arc':
        avoid_pairs=identify_nondisjoint_pairs(new_edges,path,colors,disjointness)
        log2('Avoid pairs:',avoid_pairs)
    number_of_upstreams={}
    avoid_edges=[]
    for c in colors:
        if c in must_colors:
            parent_nodes=find_parents(G,n,c)[0]
            number_of_upstreams[c]=len(parent_nodes)
            if disjointness!='arc':
                avoid_edges+=identify_upstream_nondisjoint_edges(c,parent_nodes,new_edges,path,colors,disjointness,G)
        else:
            number_of_upstreams[c]=1
    log2('Avoid edges:',avoid_edges)
    m = Model("network")
    if not is_debug(3): m.verbose = 0
    x={}
    for c in colors:
        x[c]={}
        for e in new_edges:
            x[c][e] = m.add_var(name='x_{}{}to{}id{}'.format(c,e[0],e[1],e[2]), var_type=BINARY)
    k={}
    for c in colors:
        k[c] = m.add_var(name='k_{}'.format(c), var_type=BINARY)

    # penalty variables
    a = m.add_var(name='a', var_type=BINARY)
    l= m.add_var(name='l', lb=0.0, var_type=CONTINUOUS)

    cost=define_variable_cost(x,path,term, l, m)
    wl=args.wl
    if args.obj=='longest':
        wl=wl*0.7
    m.objective = maximize(xsum(cost[c][e]*x[c][e] for c in colors for e in new_edges)\
        +xsum(1000*number_of_upstreams[c]*k[c] for c in colors) -args.wa*a -wl*l)

    if no_gap:
        m += xsum(k[c] for c in colors) >= tree_num,"local_connectivity"+rowId()

    #every edge has at most one color eq(3)
    for e in new_edges:
        m += xsum(x[c][e] for c in colors) <= 1,"one_edge_one_color"+rowId()

    #no loop edges eq (5)
    for c in colors:
        for e in new_edges:
            for rev_e in G[e[1]][e[0]]:
                if G[e[1]][e[0]][rev_e]['color']==c:
                    m += x[c][e] == 0,"no_loopback"+rowId()
                    break
    # no loops eq(6)
    for e in new_edges:
        for c in colors:
            #out_edge_colors_e=out_edge_colors(G,e[1])
            if e[1] not in path[c]:
                log2('avoid loops',c,e[1])
                m += x[c][e] == 0,"avoid_loops"+rowId()
            #if e[1]!=root and c not in out_edge_colors_e:
            #    m += x[c][e] == 0,"falling_tree"+rowId()
    #there are no two same colored out edge eq(4)
    for c in colors:
        m += xsum(x[c][e] for e in new_edges) == k[c],"one_color_one_outedge"+rowId()

    if no_gap:
        for c in must_colors: #must_colors
            m += k[c] == 1,"must_colors"+rowId()


    for c1,v1,c2,v2 in avoid_pairs:
        for e1 in new_edges:
            if e1[1]==v1:
                for e2 in new_edges:
                    if e2[1]==v2:
                        log2('pair:',e1,e2,v1,v2)
                        m += x[c1][e1]+x[c2][e2] <= 1 + a,"no_cross_downstream"+rowId()
    for c,v in avoid_edges:
        for e in new_edges:
            if e[1]==v:
                log2('edge:',e,v)
                m += x[c][e] == 0 + a,"no_cross_upstream"+rowId()

    if is_debug(2):
        m.write('model.lp')
    status = m.optimize()
    if status == OptimizationStatus.OPTIMAL or status == OptimizationStatus.FEASIBLE:
        selected = [(c,e) for c in colors for e in new_edges if x[c][e].x >= 0.99]
        for c,e in selected:
            log2('Edge',e,'has color',c)
            nx.set_edge_attributes(G, {e: {"color": c}})
        trees=0
        for c in colors:
            if k[c].x >= 0.5:
                trees+=1
        if tree_num>trees:
            for c in colors:
                trees=0
                if k[c].x <= 0.5:
                    parent_nodes,parent_arcs=find_parents(G,n,c)
                    log1('We lost subtree of color',c,'from',n,'parent links',parent_nodes,parent_arcs)
                    for e in parent_arcs:
                        nx.set_edge_attributes(G, {e: {"color": 'black'}})
                    if disjointness=='arc' and not args.nopostprocess:
                        BuildTreeGreedy(G, c, root,parent_nodes)
        return True
    if args.debug:
        log1('adding node',n,'is failed.')
        show_graph(G,True)
    return False

def solve_add_two_nodes_graph(G,root,n1, n2, new_edges1, new_edges2, new_edges_between1,new_edges_between2, colors, disjointness, no_gap=False):
    log2('We need to assign colors to these edges:',new_edges1,new_edges2, new_edges_between1,new_edges_between2)
    new_edges=new_edges1+new_edges2+new_edges_between1+new_edges_between2
    # what is the root-n1 connectivity:
    tree_num1=st_connectivity(G,root,n1)
    must_colors1=in_edge_colors(G,n1)
    #colors1=must_colors1.union(border_colors(G,n1,root,colors))
    tree_num2=st_connectivity(G,root,n2)
    must_colors2=in_edge_colors(G,n2)
    #colors2=must_colors2.union(border_colors(G,n2,root,colors))
    #common_colors=list(colors1.intersection(colors2))
    #colors1=list(colors1)
    #colors2=list(colors2)
    colors1=colors
    colors2=colors
    common_colors=colors
    log2('colors:',colors1,colors2,'intersect',common_colors,'tree nums',tree_num1,tree_num2)
    if len(colors1)==0 and len(colors2)==0:
        return True
    path,term=compute_paths(G,new_edges1+new_edges2,colors,root)
    log2('Paths from neighbours',path)
    avoid_pairs1=[]
    avoid_pairs2=[]
    if disjointness!='arc':
        avoid_pairs1=identify_nondisjoint_pairs(new_edges1,path,colors,disjointness)
        avoid_pairs2=identify_nondisjoint_pairs(new_edges2,path,colors,disjointness)
        log2('avoid pairs:',avoid_pairs1,avoid_pairs2)
    avoid_edges1=[]
    avoid_edges2=[]
    number_of_upstreams1={}
    for c in colors1:
        if c in colors1:
            parent_nodes=find_parents(G,n1,c)[0]
            number_of_upstreams1[c]=len(parent_nodes)
            if disjointness!='arc':
                avoid_edges1+=identify_upstream_nondisjoint_edges(c,parent_nodes,new_edges1,path,colors,disjointness,G)
        else:
            number_of_upstreams1[c]=1
    number_of_upstreams2={}
    for c in colors2:
        if c in colors2:
            parent_nodes=find_parents(G,n2,c)[0]
            number_of_upstreams2[c]=len(parent_nodes)
            if disjointness!='arc':
                avoid_edges2+=identify_upstream_nondisjoint_edges(c,parent_nodes,new_edges2,path,colors,disjointness,G)
        else:
            number_of_upstreams2[c]=1
    log2('avoid edges:',avoid_edges1,avoid_edges2)
    m = Model("network")
    if not is_debug(3): m.verbose = 0
    x={}
    for c in colors1:
        x[c]={}
        for e in new_edges1:
            x[c][e] = m.add_var(name='x_{}{}to{}id{}'.format(c,e[0],e[1],e[2]), var_type=BINARY)
    for c in common_colors:
        for e in new_edges_between1:
            x[c][e] = m.add_var(name='z_{}{}to{}id{}'.format(c,e[0],e[1],e[2]), var_type=BINARY)

    for c in colors2:
        if c not in x:
            x[c]={}
        for e in new_edges2:
            x[c][e] = m.add_var(name='y_{}{}to{}id{}'.format(c,e[0],e[1],e[2]), var_type=BINARY)
    for c in common_colors:
        for e in new_edges_between2:
            x[c][e] = m.add_var(name='z_{}{}to{}id{}'.format(c,e[0],e[1],e[2]), var_type=BINARY)
    k1={}
    k2={}
    for c in colors1:
        k1[c] = m.add_var(name='k1_{}'.format(c), var_type=BINARY)
    for c in colors2:
        k2[c] = m.add_var(name='k2_{}'.format(c), var_type=BINARY)

    a1 = m.add_var(name='a1', var_type=BINARY)
    a2 = m.add_var(name='a2', var_type=BINARY)
    l= m.add_var(name='l', lb=0.0, var_type=CONTINUOUS)
    wl=args.wl
    if args.obj=='longest':
        wl=wl*0.7
    cost=define_variable_cost(x,path,term, l, m)
    m.objective = maximize(xsum(cost[c][e]*x[c][e] for c,xx in x.items() for e,var in xx.items() ) +\
                            xsum(1000*number_of_upstreams1[c]*k1[c] for c in colors1) +\
                            xsum(1000*number_of_upstreams2[c]*k2[c] for c in colors2) - args.wa*a1 - args.wa*a2 - wl*l)

    if no_gap:
        m += xsum(k1[c] for c in colors1) >= tree_num1,"local_connectivity1"+rowId()
        m += xsum(k2[c] for c in colors2) >= tree_num2,"local_connectivity2"+rowId()

    #every edge has at most one color
    for e in new_edges1:
        m += xsum(x[c][e] for c in colors1) <= 1,"oneEdgeOneColor1_"+rowId()
    for e in new_edges2:
        m += xsum(x[c][e] for c in colors2) <= 1,"oneEdgeOneColor2_"+rowId()
    for e in new_edges_between1+new_edges_between2:
        m += xsum(x[c][e] for c in common_colors) <= 1,"oneEdgeOneColor3_"+rowId()

    #no loop edges
    for e in new_edges1:
        out_edge_colors_e=out_edge_colors(G,e[1])
        for c in colors1:
            for rev_e in G[e[1]][e[0]]:
                if G[e[1]][e[0]][rev_e]['color']==c:
                    m += x[c][e] == 0,"noLoopback"+rowId()
                    break
            if e[1]!=root and c not in out_edge_colors_e:
                m += x[c][e] == 0,"falling_tree1"+rowId()

    for e in new_edges2:
        out_edge_colors_e=out_edge_colors(G,e[1])
        for c in colors2:
            for rev_e in G[e[1]][e[0]]:
                if G[e[1]][e[0]][rev_e]['color']==c:
                    m += x[c][e] == 0,"noLoopback"+rowId()
                    break
            if e[1]!=root and c not in out_edge_colors_e:
                m += x[c][e] == 0,"falling_tree1"+rowId()

    # no loop between the new nodes eq (9)
    for c in common_colors:
        for e1 in new_edges_between1:
            for e2 in new_edges_between2:
                m += x[c][e1] + x[c][e2] <= 1,"noLoopbackBetweenN1andN2"+rowId()

    #there are one same colored out edge
    for c in colors1:
        if c in common_colors:
            m += xsum(x[c][e] for e in new_edges1+new_edges_between1) == k1[c],"oneColorOneOutedgeN1_"+rowId()
        else:
            m += xsum(x[c][e] for e in new_edges1) == k1[c],"oneColorOneOutedgeN1_"+rowId()
    for c in colors2:
        if c in common_colors:
            m += xsum(x[c][e] for e in new_edges2+new_edges_between2) == k2[c],"oneColorOneOutedgeN2_"+rowId()
        else:
            m += xsum(x[c][e] for e in new_edges2) == k2[c],"oneColorOneOutedgeN2_"+rowId()

    # Eq (10)
    for c in common_colors:
        for e in new_edges_between1:
            m += x[c][e] <= k2[c],"no_orphan_betweenedge_to_n2"+rowId()
        for e in new_edges_between2:
            m += x[c][e] <= k1[c],"no_orphan_betweenedge_to_n1"+rowId()


    if no_gap:
        for c in colors1: #must_colors
            m += k1[c] == 1,"must_colors1"+rowId()
        for c in colors2: #must_colors
            m += k2[c] == 1,"must_colors2"+rowId()

    # no loops in the tree
    # ez tul szigoru a masik ponton keresztul lemehet!!!!!
    for c in colors1:
        for e in new_edges1:
            if e[1] not in path[c]:
                if term[c][e[1]]!=n2:
                    log2('avoid loops',c,e)
                    m += x[c][e] == 0,"avoidLoops1_"+rowId()
                else:
                    log2('avoid orphan edge1 ',c,e)
                    m += x[c][e]  <= k2[c],"no_orphan_edge_to_n1"+rowId()
                    #m += 1 - x[c][e] + k2[c]  >= k1[c],"no_orphan_edge_to_n1"+rowId()
                    # n1->e[1] is upstream to n2
                    if c in common_colors:
                        for ee in new_edges_between2:
                            log2('avoid loop through n2',c,ee,'because of',e)
                            m += x[c][ee] + x[c][e] <= 1,"avoidLoops_n2_n1_"+rowId()
                    # and all of n1-s upstream node upstream nodes
                    parent_nodes,parent_edges=find_parents(G,n1,c)
                    log2('parent nodes of ',n1,'in color',c,parent_nodes)
                    # Eq
                    for ee in new_edges2:
                        if ee[1] in parent_nodes:
                            log2('Avoid loop through n2',c,ee,'because of',e)
                            m += x[c][ee] + x[c][e] <= 1,"avoidLoops_n2_"+rowId()
    for c in colors2:
        for e in new_edges2:
            if e[1] not in path[c]:
                if term[c][e[1]]!=n1:
                    log2('avoid loops',c,e)
                    m += x[c][e] == 0,"avoidLoops2_"+rowId()
                else:
                    log2('avoid orphan edge2 ',c,e)
                    #x^c_a \leq y^c
                    #ha v-ből a v_i elérhető a c fában?
                    m += x[c][e]  <= k1[c],"no_orphan_edge_to_n1"+rowId()
                    #m += 1 - x[c][e] + k1[c]  >= k2[c],"no_orphan_edge_to_n2"+rowId()
                    if c in common_colors:
                        for ee in new_edges_between1:
                            log2('avoid loop through n1',c,ee,'because of',e)
                            m += x[c][ee] + x[c][e] <= 1,"avoidLoops_n1_n2_"+rowId()
                    # and all of n1-s upstream node upstream nodes
                    parent_nodes,parent_edges=find_parents(G,n2,c)
                    log2('parent nodes of ',n2,'in color',c,parent_nodes)
                    for ee in new_edges1:
                        if ee[1] in parent_nodes:
                            log2('Avoid loop through n1',c,ee,'because of',e)
                            m += x[c][ee] + x[c][e] <= 1,"avoidLoops_n1_"+rowId()

    for c1,v1,c2,v2 in avoid_pairs1:
        for e1 in new_edges1:
            if e1[1]==v1:
                for e2 in new_edges1:
                    if e2[1]==v2:
                        m += x[c1][e1]+x[c2][e2] <= 1 + a1,"noCrossDownstreamN1"+rowId()

    for c1,v1,c2,v2 in avoid_pairs2:
        for e1 in new_edges2:
            if e1[1]==v1:
                for e2 in new_edges2:
                    if e2[1]==v2:
                        m += x[c1][e1]+x[c2][e2] <= 1 + a2,"noCrossDownstreamN2"+rowId()
    for c1,v1 in avoid_edges1:
        for e1 in new_edges1:
            if e1[1]==v1:
                log2('edge:',e1,v1)
                m += x[c1][e1] == 0 + a1,"no_cross_upstreamN1"+rowId()
    for c,v in avoid_edges2:
        for e in new_edges:
            if e[1]==v:
                log2('edge:',e,v)
                m += x[c][e] == 0 + a2,"no_cross_upstreamN2"+rowId()
    if is_debug(2):
        m.write('model.lp')
    status = m.optimize()
    if status == OptimizationStatus.OPTIMAL or status == OptimizationStatus.FEASIBLE:
        log2('optimization: ',m.objective_value,'l=',70*l.x,'a1=',args.wa*a1.x,'a2=',args.wa*a2.x)
        if is_debug(2):
            for v in m.vars:
               if abs(v.x) > 1e-6: # only printing non-zeros
                  print('{} : {}'.format(v.name, v.x))
        selected = [(c,e) for c in colors1 for e in new_edges1 if x[c][e].x >= 0.99]
        selected += [(c,e) for c in colors2 for e in new_edges2 if x[c][e].x >= 0.99]
        selected += [(c,e) for c in common_colors for e in new_edges_between1+new_edges_between2 if x[c][e].x >= 0.99]
        for c,e in selected:
            log2('Edge',e,'has color',c)
            nx.set_edge_attributes(G, {e: {"color": c}})
        trees1=0
        for c in colors1:
            if k1[c].x >= 0.5:
                trees1+=1
        for c in colors1:
            if c in must_colors1 or tree_num1>trees1:
                if k1[c].x <= 0.5:
                    parent_nodes,parent_arcs=find_parents(G,n1,c)
                    log1('We lost subtree of color1 ',c,'from',n1,'parent links',parent_nodes,parent_arcs)
                    #sys.exit(0)
                    for e in parent_arcs:
                        nx.set_edge_attributes(G, {e: {"color": 'black'}})
                    if disjointness=='arc' and not args.nopostprocess:
                        BuildTreeGreedy(G, c, root,parent_nodes)
        trees2=0
        for c in colors2:
            if k2[c].x >= 0.5:
                trees2+=1
        for c in colors2:
            if c in must_colors2 or tree_num2>trees2:
                if k2[c].x <= 0.5:
                    parent_nodes,parent_arcs=find_parents(G,n2,c)
                    log2('We lost subtree of color2 ',c,'from',n2,'parent links',parent_nodes,parent_arcs)
                    #sys.exit(0)
                    for e in parent_arcs:
                        nx.set_edge_attributes(G, {e: {"color": 'black'}})
                    if disjointness=='arc' and not args.nopostprocess:
                        BuildTreeGreedy(G, c, root,parent_nodes)
        return True
    if args.debug:
        log1('adding nodes',n1,n2,'is failed.')
        show_graph(G,True)
    return False

def map_edges_to_parallel_arcs(G,removed_edges,root,colors):
    # if parallel edges we remove the one with the highest id
    ret=[]
    id_used={}
    for u,v in removed_edges:
        if u==v:
            # if the edge was parallel it may have missing:
            if G.has_edge(u,u)==False or id_used[(u,u)]==len(G[u][u])-1:
                log3('Add loop edge for node',u)
                if u!=root:
                    color1='black'
                    color2='black'
                else:
                    used_colors=[]
                    for uu,vv,ii in G.in_edges(root,keys=True):
                        #log1(G[u][v][i]['color'])
                        used_colors.append(G[uu][vv][ii]['color'])
                    unused_colors=[]
                    for c in colors:
                        if c not in used_colors:
                            unused_colors.append(c)
                    log2('used colors',used_colors,'unused colors',unused_colors)
                    if len(unused_colors)<2:
                        log1('Error too few colors')
                        sys.exit(0)
                    color1=unused_colors[0]
                    color2=unused_colors[1]
                    log2('Assign colors',color1,'and',color2,'to the loop edge of the root')
                id=G.add_edge(u,u,color=color1,capacity=1)
                ret.append((u,u,id,color1))
                #id_used[(u,u)]=len(G[u][u])-1
                id=G.add_edge(u,u,color=color2,capacity=1)
                ret.append((u,u,id,color2))
                id_used[(u,u)]=len(G[u][u])-1
                continue
        if len(G[u][v])==1:
            ret.append((u,v,0,G[u][v][0]['color']))
        else:
            if (u,v) in id_used:
                id_used[(u,v)]-=1
            else:
                id_used[(u,v)]=len(G[u][v])-1
            ret.append((u,v,id_used[(u,v)],G[u][v][id_used[(u,v)]]['color']))
        if len(G[v][u])==1:
            ret.append((v,u,0,G[v][u][0]['color']))
        else:
            if (v,u) in id_used:
                id_used[(v,u)]-=1
            else:
                id_used[(v,u)]=len(G[v][u])-1
            ret.append((v,u,id_used[(v,u)],G[v][u][id_used[(v,u)]]['color']))
    log3('edges',removed_edges,'are mapped to',ret)
    return ret

def TreeConstructor(graph,code,colors,root, compute_trees=True, disjointness='arc'):
    output = nx.MultiDiGraph()
    # first list is the edges
    for u,v in graph[0]:
        output.add_edge(u,v,color='black')
        output.add_edge(v,u,color='black')
    # second and third list are the nodes and coordinates
    for i,n in enumerate(graph[1]):
        output.nodes[n]['pos']=graph[2][i]
    #show_graph(output)
    if len(output.nodes)==2:
        solve_two_node_graph(output,root,colors)
    elif len(output.nodes)==3:
        solve_three_node_graph(output,root,colors)
    show_graph(output)
    if args.tikz:
        ddraw.showGraphTreeTex(output, 'graph-tree_1.tex', root,args.tikz_scale,args.mirror)
    ii=2
    log3(code)
    for transformation in code:
        log3('transfromation', transformation)
        if len(transformation)==2:
            removed_edges, new_nodes= transformation
            # add singlee node
            (neighbors, n, pos)=new_nodes
            log1('Add singe node',n,'connect to',neighbors)
            # now we modify the graph
            output.add_node(n,pos=pos)
            new_edges=[]
            for u,v,id,color in map_edges_to_parallel_arcs(output,removed_edges,root,colors):
                output.remove_edge(u,v)
                output.add_edge(u,n,color=color,capacity=1)
                new_edge=output.add_edge(n,u,color='black',capacity=1)
                new_edges.append((n,u,new_edge))
            if compute_trees:
                show_graph(output)
                # neext we extend the trees
                succeed=solve_add_node_graph(output,root,n, new_edges,colors,disjointness)
                if args.tikz:
                    ddraw.showGraphTreeTex(output, 'graph-tree'+str(ii)+'.tex', root,args.tikz_scale,args.mirror)
                    ii+=1
                if not succeed:
                    xml_desc='<failed>'
                    xml_desc+='<method>ilp_one_node</method>'
                    xml_desc+='<size_at_failed>'+str(len(output.nodes))+'</size_at_failed>'
                    xml_desc+='</failed>'
                    return None,xml_desc
                show_graph(output)
            #sys.exit(0)
        elif len(transformation)==3:
            # add two nodes
            removed_edges, new_nodes1,new_nodes2= transformation
            (neighbors1, n1, pos1)=new_nodes1
            (neighbors2, n2, pos2)=new_nodes2
            log1('Add two nodes',n1,'and',n2,'connect to',neighbors1,'and',neighbors2,', respectively.')
            # now we modify the graph
            output.add_node(n1,pos=pos1)
            output.add_node(n2,pos=pos2)
            new_edges1=[]
            new_edges2=[]
            new_edges_between1=[]
            new_edges_between2=[]
            # we copy these list because we will remove elements one-by-one
            neigh1=neighbors1.copy()
            neigh2=neighbors2.copy()
            for u,v,id,color_u in map_edges_to_parallel_arcs(output,removed_edges,root,colors):
                log3('Take removed edge',u,v,id)
                #color_u=output[u][v][id]['color']
                output.remove_edge(u,v)
                # decide to add to n1 or n2
                un=-1
                for i,nn in enumerate(neigh1):
                    if nn==u:
                        un=n1
                        neigh1=neigh1[:i]+neigh1[i+1:]
                        break
                if un==-1:
                    for i,nn in enumerate(neigh2):
                        if nn==u:
                            un=n2
                            neigh2=neigh2[:i]+neigh2[i+1:]
                            break
                if un==-1:
                    log1('Error with data structure: removed edge (',v,u,') does not match neighbours',neighbors1,neighbors2,'currently',neigh1,neigh2)
                else:
                    output.add_edge(u,un,color=color_u,capacity=1)
                    new_edge=output.add_edge(un,u,color="black")
                    if un==n1:
                        new_edges1.append((un,u,new_edge))
                    else:
                        new_edges2.append((un,u,new_edge))
            # now we add the edges between n1 and n2:
            for nn in neigh1:
                if nn!=n2:
                    log1('Error neighbour',nn,'does not match to',n2,'neigh',neigh1)
                else:
                    new_edge=output.add_edge(n1,n2,color="black")
                    new_edges_between1.append((n1,n2,new_edge))
            for nn in neigh2:
                if nn!=n1:
                    log1('Error neighbour',nn,'does not match to',n1,'neigh',neigh2)
                else:
                    new_edge=output.add_edge(n2,n1,color="black")
                    new_edges_between2.append((n2,n1,new_edge))
            if compute_trees:
                show_graph(output)
                succeed=solve_add_two_nodes_graph(output,root,n1, n2, new_edges1, new_edges2, new_edges_between1,new_edges_between2, colors,disjointness)
                if args.tikz:
                    ddraw.showGraphTreeTex(output, 'graph-tree'+str(ii)+'.tex', root,args.tikz_scale,args.mirror)
                    ii+=1
                if not succeed:
                    xml_desc='<failed>'
                    xml_desc+='<method>ilp_two_nodes</method>'
                    xml_desc+='<size_at_failed>'+str(len(output.nodes))+'</size_at_failed>'
                    xml_desc+='</failed>'
                    return None,xml_desc
                show_graph(output)
            #sys.exit(0)
        else:
            log1('Error! The graph transformation is not recognized:',transformation)
    return output,""



if __name__ == "__main__":
    with open(args.file, 'r') as fp:
        construct_list = json.load(fp)
        log3(construct_list)
        #colors=[0.2, 0.5, 0.7]
        #root=args.root
        root=construct_list[0][-1]
        log2('root:',root)
        # for efficient computing cuts we need a DIgraph representation of the graph
        final_graph_,xml_desc=TreeConstructor(construct_list[0],construct_list[1:],all_colors,root,False)
        for u,v,i in final_graph_.edges:
            final_graph.add_edge(u,v,capacity=1)
        for n in final_graph_.nodes:
            final_graph.nodes[n]['pos']=final_graph_.nodes[n]['pos']
        all_colors=all_colors[:len(final_graph_.edges(root))]
        # now we can construct trees
        log2('Building up digraph is finished, now we start again by building trees as well')
        start = time.time()
        G,xml_desc=TreeConstructor(construct_list[0],construct_list[1:],all_colors,root,True,args.dis)
        end = time.time()
        xml_desc+='<runtime>'+str(end - start)+'</runtime>'
        xml_desc+='<target_disjointness>'+args.dis+'</target_disjointness>'
        if G!=None:
            if not args.nopostprocess:
                ReBuildTreesGreedy(G, all_colors, root)
            node_pos=[]
            for n in G.nodes:
                node_pos.append(G.nodes[n]['pos'])
            edge_list=[]
            for u,v,i in G.edges:
                edge_list.append((u,v,G[u][v][i]["color"]))
            routing=(edge_list,list(G.nodes),node_pos,root)
            file_name=args.file+'__IterativeILP_'+args.dis
            if args.nopostprocess:
                file_name+='_nopostprocess'
            file_name+='_'+args.id+'-'
            with open(file_name+'.rtn', 'w') as fp:
                json.dump(routing, fp)
            log1('routing:',routing)
            colors=set()
            for u,v,i in G.edges:
                color=G[u][v][i]['color']
                final_graph[u][v]['color']=color
                if v==root and color!='black':
                    colors.add(color)
            log2('colors:',colors)
            valid,non_disjoint,xml_desc_=verifyRouting(final_graph,root,list(colors))
            xml_desc+=xml_desc_
            coverage=analyzeRouting(final_graph,root,list(colors),file_name+'.xml',xml_desc)
            log1('Solution with coverage',coverage,'found')
            if coverage!=1 or args.dat:
                log1('Saving as',file_name+'.dat')
                with open(file_name+'.dat', 'w') as fp:
                    fp.write(str(coverage))
        else:
            log1('Failed to find trees')
            analyzeRouting(final_graph,root,[],file_name+'.xml',xml_desc)
