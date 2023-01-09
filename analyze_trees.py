# -*- coding: utf-8 -*-
import networkx as nx
from itertools import combinations, groupby
import DrawGraph as dg
import json
import graph_draw as ddraw
from logger import log1,log2,log3,log4,log5,log6,is_debug,set_debug
import matplotlib.pyplot as plt
import sys, os
import argparse
from Graphhandler import findpath,isoverlapping,hasoutedge,hasinedge,findpath_root
#import graph_construct *

set_debug(2)

def show_graph(G, force=False):
    global argparse
    if not args.fig and not force:
        return
    #log3(G.nodes())
    pos = nx.get_node_attributes(G, 'pos')
    #log2(nx.get_edge_attributes(G,'color'))
    nx.draw(G, pos, with_labels = True,edge_color='white')
    ax = plt.gca()
    for u,v in G.edges:
        arc_color=G[u][v]['color']
        log3('draw graph:',u,v,arc_color)
        if u!=v:
            ax.annotate("",
                xy=pos[u], xycoords='data',
                xytext=pos[v], textcoords='data',
                arrowprops=dict(arrowstyle="<-", color=arc_color,
                                shrinkA=10, shrinkB=10,
                                patchA=None, patchB=None,
                                connectionstyle="arc3,rad=rrr".replace('rrr',str(0.06)),),)
        else:
            pu=(pos[v][0]+2,pos[v][1]+3)
            pv=(pos[v][0]+2,pos[v][1]-3)
            ax.annotate("",
                xy=pu, xycoords='data',
                xytext=pv, textcoords='data',
                arrowprops=dict(arrowstyle="<-", color=arc_color,
                                shrinkA=10, shrinkB=10,
                                patchA=None, patchB=None,
                                connectionstyle="arc3,rad=rrr".replace('rrr',str(0.1)),),)
    plt.show()

def verifyRouting(G,root,colors):
    valid=True
    non_disjoint={}
    non_disjoint['arc']=0
    non_disjoint['edge']=0
    non_disjoint['node']=0
    xml_desc=''
    for n in G.nodes:
        if n!=root:
            paths=[]
            for c in colors:
                P,dest=findpath_root(G,n,c,root)
                log2('Path from',n,'in color',c,'is',P)
                if dest!=root and len(P)>1:
                    log1('Path does not reach the root',P,'color',c)
                    valid=False
                else:
                    paths.append(P)
            for P1,P2 in combinations(paths,2):
                if P1==None or P2==None:
                    continue
                for dis,count in non_disjoint.items():
                    log2('Check paths',P1,P2,dis)
                    if isoverlapping(P1,P2,dis,root):
                        log1('Paths are not '+dis+'-disjoint!!!',P1,P2)
                        non_disjoint[dis]=count+1
                    else:
                        log3('Paths are fine')
    if valid:
        log1('All paths reach the root.')
    else:
        log1('Warning! Not all paths reach the root.')
    xml_desc+='<reach>'+str(valid)+'</reach>'
    for dis,count in non_disjoint.items():
        if count==0:
            log1('All paths are '+dis+'-disjoint.')
        else:
            log1('Not all paths are '+dis+'-disjoint.',count)
        xml_desc+='<'+dis+'_disjoint>'+str(count)+'</'+dis+'_disjoint>\n'
    return valid,non_disjoint,xml_desc

def log_string(file_descriptor,string):
    file_descriptor.write(string+"\n")

def analyzeRouting(G,root,colors, file_name,xml_desc):
    valid=True
    xml_output = open(file_name, "w") # used to be "a"
    log_string(xml_output, '<?xml version="1.0" encoding="UTF-8"?>')
    log_string(xml_output, '<simulation>')
    log_string(xml_output, "<file>"+file_name+"</file>")
    method_name=file_name.split('-')
    if len(method_name)>=2:
        algo_name=method_name[1].replace('.dgh','').replace('_',' ')
        log_string(xml_output, "<algorithm>"+algo_name+"</algorithm>")
    log_string(xml_output, "<node_num>"+str(len(G.nodes))+"</node_num>")
    log_string(xml_output, "<edge_num>"+str(len(G.edges))+"</edge_num>")
    log_string(xml_output, "<root>"+str(root)+"</root>")
    log_string(xml_output, "<runtime_desc>"+xml_desc+"</runtime_desc>")
    local_connectivity_gap=0
    local_connectivity_sum=0
    if len(colors)!=0:
        log_string(xml_output, "<succeed>1</succeed>")
        log_string(xml_output, "<all_tree_num>"+str(len(colors))+"</all_tree_num>")
        for n in G.nodes:
            if n!=root:
                log_string(xml_output, '<source>')
                log_string(xml_output, '<node>'+str(n)+'</node>')
                # shortest path
                length=nx.shortest_path_length(G, root, n)
                log_string(xml_output, "<sp_hop_length>"+str(length)+"</sp_hop_length>")
                # max flow
                max_flow=nx.maximum_flow_value(G, n, root)
                log_string(xml_output, "<edge_con>"+str(max_flow)+"</edge_con>")
                path_num=0
                min_length=-1
                max_length=0
                for c in colors:
                    P,dest=findpath_root(G,n,c,root)
                    if dest==root:
                        path_num+=1
                        log_string(xml_output, '<tree>')
                        log_string(xml_output, "<tree_name>"+c+"</tree_name>")
                        log2('Path from',n,'in color',c,'is',P)
                        length=len(P)
                        if min_length==-1:
                            min_length=length
                        min_length=min(min_length,length)
                        max_length=max(max_length,length)
                        log_string(xml_output, "<hop_length>"+str(length)+"</hop_length>")
                        log_string(xml_output, '</tree>')
                log_string(xml_output, "<tree_num>"+str(path_num)+"</tree_num>")
                local_connectivity_sum+=max_flow
                if path_num<max_flow:
                    log1('The number of trees',path_num,'max flow',max_flow,'from node',n)
                    local_connectivity_gap+=max_flow-path_num
                log_string(xml_output, "<min_hop_length>"+str(min_length)+"</min_hop_length>")
                log_string(xml_output, "<max_hop_length>"+str(max_length)+"</max_hop_length>")
                log_string(xml_output, '</source>')
        log_string(xml_output, "<gap>"+str(local_connectivity_gap)+"</gap>")
        log_string(xml_output, "<coverage>"+str(100-100*local_connectivity_gap/local_connectivity_sum)+"</coverage>")
        log2("gap:",local_connectivity_gap,'relative gap:',local_connectivity_gap/local_connectivity_sum)
    else:
        log_string(xml_output, "<succeed>0</succeed>")
    log_string(xml_output, '</simulation>')
    xml_output.close()
    log2('Analysis is written in file',file_name)
    if local_connectivity_sum==0:
        return -1
    return 1 - local_connectivity_gap/local_connectivity_sum

def run(command):
    log1('------------------------------')
    log1(command)
    os.system(command)

if __name__ == "__main__":
    aparser = argparse.ArgumentParser()
    aparser.add_argument("-fig", help="Show graphs with Matplotlib", action='store_true')
    aparser.add_argument("-log", type=int, help="The logging level: 1- main info, 3- detailed  ", default=3)
    aparser.add_argument("-file", type=str, help="The input .json network file", default='net/22_optic_eu.lgf.json.dgh.root4.rtn')#'22_optic_eu'')
    aparser.add_argument("-xml_outfile", type=str, help="The xml file where the results are stored", default='result.xml')
    aparser.add_argument("-test", help="Run tests", action='store_true')
    aparser.add_argument("-command", help="Generate command line", action='store_true')
    aparser.add_argument("-alpha", type=float, help="Punishing prallel edges", default=100)
    aparser.add_argument("-beta", type=float, help="Rewarding loop edges edges", default=100)
    aparser.add_argument("-dis", type=str, help="Disjointness arc, edge, node", default='arc')
    #aparser.add_argument("-filter", type=int, help="Evaluate network with given nodenum", default=-1)
    args = aparser.parse_args()
    set_debug(args.log)

    with open(args.file, 'r') as fp:
        routing_list = json.load(fp)
    log2(routing_list)
    G = nx.DiGraph()
    # first list is the edges
    for u,v,c in routing_list[0]:
        e=G.add_edge(u,v,color=c,capacity=1)
    # second and third list are the nodes and coordinates
    for i,n in enumerate(routing_list[1]):
        G.nodes[n]['pos']=routing_list[2][i]
    root=routing_list[3]
    colors=set()
    for v,u in G.in_edges(root):
        in_edge_color=G[v][u]['color']
        log2('in edge',v,u,i,'has color',in_edge_color)
        if in_edge_color!='black':
            colors.add(in_edge_color)
    show_graph(G)
    log2('colors:',colors)
    valid,non_disjoint,xml_desc=verifyRouting(G,root,list(colors))
    analyzeRouting(G,root,list(colors),args.file+'.xml',xml_desc)
    if args.command:
        nets = {
        17: '17_optic_german',
        20: '20_optic_arpa',
        21: '21_test_tnet',
        22: '22_optic_eu',
        26: '26_optic_usa',
        28: '28_optic_eu',
        33: '33_optic_italian',
        37: '37_optic_european',
        39: '39_optic_north_american',
        79: '79_optic_nfsnet'
        }
        net_file='net/'+nets[len(G.nodes)]+'.lgf.json'
        print('-file '+net_file+' -root '+str(root))
        for con in ['','_con']:
            #for obj_ in ['random','grow','even_nodes_first', 'even_nodes_first_chi']:
            for obj_ in ['random','grow','even_nodes_first','grow_chi', 'even_nodes_first_chi']:
                if obj_=='random' and con!='':
                    continue
                obj=obj_+con
                run('python3 graph_construct.py -log 2 -obj '+obj+' -alpha '+str(args.alpha)+' -beta '+str(args.beta)+' -root '+str(root)+' -file '+net_file)
                filename=net_file.replace('net/','res/')+'.root'+str(root)+'-'+obj+'.dgh'
                run('python3 build_trees.py -log 2 -file '+filename)
                run('python3 build_trees.py -nopostprocess -log 2 -file '+filename)
                #run('python3 build_trees.py -dis arc -obj avg -id avg_'+obj+' -log 2 -file '+filename)
                #run('python3 build_trees.py -dis arc -obj avg -nopostprocess -id avg_'+obj+'_nopostprocess -log 2 -file '+filename)
                #run('python3 build_trees.py -dis arc -obj shortest -id shortest_'+obj+' -log 2 -file '+filename)
                #run('python3 build_trees.py -dis arc -obj shortest -nopostprocess -id shortest_'+obj+'_nopostprocess -log 2 -file '+filename)
                #if obj!='random':
                #    run('python3 build_trees.py -dis arc -obj longest -id longest_'+obj+' -wl 50 -log 2 -file '+filename)
                #    run('python3 build_trees.py -dis arc -obj longest -nopostprocess -id longest_'+obj+'_nopostprocess -wl 50 -log 2 -file '+filename)
                #run('python3 build_trees.py -dis edge -obj avg -nopostprocess -log 2 -file '+filename)
                #run('python3 build_trees.py -dis node -obj avg -nopostprocess -log 2 -file '+filename)
                #for wa,wl in [(1000,50),(1000,200)]:
                    #run('python3 build_trees.py -dis arc -obj avg -log 2 -wa '+str(wa)+' -wl '+str(wl)+' -file '+filename)
                    #run('python3 build_trees.py -dis arc -obj shortest -log 2 -wa '+str(wa)+' -wl '+str(wl)+' -file '+filename)
                    #run('python3 build_trees.py -dis arc -obj longest -log 2 -wa '+str(wa)+' -wl '+str(wl)+' -file '+filename)
