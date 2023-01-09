#!/usr/bin/env python
import networkx as nx
import matplotlib.pyplot as plt
from networkx.drawing.layout import spring_layout
from networkx.readwrite import json_graph
import matplotlib.pyplot as plt
import hashlib
import json
from logger import log1,log2,log3,log4,log5,log6,is_debug,set_debug

set_debug(5)
fname={}
id={}
number={}
f=None
latex = True
prefix=''

def drawG(G,minimumconnectivity):
    global latex, fname, id, number,prefix
    if latex :
        from network2tikz import plot
        visual_style={}
        visual_style['standalone'] = False
        visual_style['vertex_size'] = .2
        visual_style['layout'] = 'spring layout'
        node_num=G.number_of_nodes()
        if node_num in number:
            number[node_num] += 1
        else:
            number[node_num] = 1
        file_name=prefix
        if file_name!='':
            file_name+='_'
        file_name+="n"+str(node_num)+"_k"+str(minimumconnectivity)+"_id"+str(number[node_num])
        plot(G,file_name+'.csv',**visual_style)
        plot(G,('latex/'+file_name+'_nodes.csv','latex/'+file_name+'_edges.csv'),**visual_style)
        id[G]=number[node_num]
        fname[G]=file_name
    else:
        if is_debug(2):
            nx.draw_networkx(G)
            plt.show()

def begin_doc(title,file_suffix='all'):
    global f, prefix
    prefix=title.replace(' ','_')
    f = open(prefix+'_'+file_suffix+'.tex', 'w')
    f.write('\\documentclass[10pt, conference]{IEEEtran}\n\\usepackage{tikz-network}\n')
    f.write('\\tikzset{every picture/.append style={scale=0.6}}\n\\usepackage{subfig}')
    f.write('\\begin{document}\n\\title{'+title.replace('_',' ')+'}\\maketitle\n')
    f.write('\\begin{figure}')


def name(G,caption):
    if caption!='':
        caption+=', '
    caption+='$G^{'+str(G.number_of_nodes())+'}_{'+str(id[G])+'}$'
    return caption

def add_subfig(G, caption, desc=True):
    global f,id
    if f:
        if desc:
            caption='$G^{'+str(G.number_of_nodes())+'}_{'+str(id[G])+'}$ parent of '+caption
#        f.write('\\subfloat['+caption+']{\\input{'+fname[G]+'.tex}}\n')
        f.write('\\subfloat['+caption+']{\n\\begin{tikzpicture}\n  \\Vertices{'+fname[G]+'_nodes.csv}\n')
        f.write('  \\Edges{'+fname[G]+'_edges.csv}\n\\end{tikzpicture}}')

def end_fig():
    global f
    if f:
        f.write('\\end{figure}\n')

def end_doc():
    global f
    if f:
        f.write('\\end{document}\n')
        f.close()


# to generate deterministic labels
# returns a 3 bit long hash of the string
def hashID(inside):
	h = hashlib.sha256()
	h.update(inside.replace(" ", "").replace("\n", "").encode('utf-8'))
	return str(h.hexdigest())[:3]

def showGraphJS(G, json_file_name, html_file_name, root=None):
    # write in node-link format to serialize
    d = json_graph.node_link_data(G,{'link': 'edges', 'source': 'from', 'target': 'to'}) 
    for n in d["nodes"]:
        if root!=None and n["id"]==root:
            n["label"]="r"
        else:
            n["label"]=str(n["id"]) 
    multi_edge={}
    for e in d["edges"]:
        u=e["from"]
        v=e["to"]
        if u<v:
            tmp=u
            u=v
            v=tmp
        me=0
        if (u,v) in multi_edge:
            me=multi_edge[(u,v)]
            #print(u,v,'is multiple edge',me)
        multi_edge[(u,v)]=me+1
        if me>0:
            e["smooth"]={'type': "curvedCCW", 'roundness': 0.1*me}
    createHtmlFile(json.dumps(d), html_file_name)


def createHtmlFile(json_graph, filename):	
	id=hashID(json_graph)
	html_file="""<!doctype html>
<html><head><title>Graph</title></head>
<body>
<script type=\'text/javascript\' src=\'https://unpkg.com/vis-network@latest/dist/vis-network.js\'></script>
<link href=\'https://unpkg.com/vis-network@latest/dist/vis-network.min.css\' rel=\'stylesheet\' type=\'text/css\'/>
<style type="text/css">#mynetwork"""+id+""" {width: 1000px;height: 800px;border: 1px solid lightgray;}</style>
<div id="mynetwork"""+id+'"></div><script type="text/javascript">\n'+ \
'var data'+id+" =JSON.parse('"+json_graph+"')\n"+ \
'var options'+id+""" = {
    nodes: {
    "fixed": {
      "x": true,
      "y": true
      }
    },
	edges: {
    "arrows": {
      "to": {
        "enabled": true
      }
    },
		smooth: {
			type: 'dynamic',
			roundness: 0.5
		}
	},
	physics: {
    	repulsion: {
      	springLength: 40
    	},
    	minVelocity: 0.75,
    	solver: 'repulsion'
  	},
  configure: false
};
var container"""+id+" = document.getElementById('mynetwork"+id+"');\n"+\
"var network"+id+"= new vis.Network(container"+id+", data"+id+", options"+id+");\n"+\
'network'+id+'.on("stabilizationIterationsDone", function () {\n'+\
"    network"+id+""".setOptions( { physics: false } );
});
</script>
</body>
</html>"""
	try:	  
		f = open(filename,'w', encoding="utf-8")
		f.write(html_file) 
		f.close() 
	except IOError:
		print("failed to write file "+filename+"\nError:"+IOError)


# a pinch
def verify_pinch(erased_e,added_n,untouched_e,node_map,from_graph,to_graph):
    for u in from_graph.nodes():
        for v in from_graph.nodes():
            if from_graph.has_edge(u,v):
                if (node_map[u],node_map[v]) not in erased_e and (node_map[v],node_map[u]) not in erased_e:
                    if not to_graph.has_edge(node_map[u],node_map[v]):
                        log1('Error! edge ',u,v,' of the from_graph does not exists in the to_graph as (',node_map[u],node_map[v],')')
                        return False
            else:
                if to_graph.has_edge(node_map[u],node_map[v]):
                    log1('Error! there is no edge ',u,v,' of the from_graph while there exists in the to_graph as (',node_map[u],node_map[v],')')
                    return False
    log3('Verified, OK')
    return True


# compute all possible pinches
def ruleGraphJS(graphgraph):
    html_file=''
    # generate all unique rules
    rules={}
    for from_g,to_g in graphgraph.edges():
        for rule in graphgraph[from_g][to_g]['desc']:
            untouched_e=rule.untouched_edges(False,False)
            if rule.to_graph.name=="final":
                log4(from_g.name,' isomorphisms ',from_g.isomorphisms)
                log4(to_g.name,' isomorphisms ',to_g.isomorphisms)
            for from_imap in from_g.isomorphisms:
                rev_from_imap={}
                for k,v in from_imap.items():
                    rev_from_imap[v]=k
                from_to_node_map={}
                if rule.node_map!=None:
                    for n,t in rule.node_map.items():
                        if n not in set(from_g.G.nodes()):
                            added_n=t
                            from_to_node_map[n]=t
                        else:
                            from_to_node_map[rev_from_imap[n]]=t
                else:
                    for n in to_g.G.nodes():
                        if n not in set(from_g.G.nodes()):
                            added_n=n
                            from_to_node_map[n]=n
                        else:
                            from_to_node_map[rev_from_imap[n]]=n
                for to_imap in to_g.isomorphisms:
                    # convert with to_imap:
                    c_added_n=to_imap[added_n]
                    c_to_from_node_map={}
                    c_from_to_node_map={}
                    for n,t in from_to_node_map.items():
                        c_to_from_node_map[to_imap[t]]=n
                        c_from_to_node_map[n]=to_imap[t]
                    c_untouched_e=[]
                    for u,v in untouched_e:
                        c_untouched_e.append((to_imap[rule.map_from_to(u)],to_imap[rule.map_from_to(v)]))
                    c_erased_e=[]
                    # create a unique name
                    rule_id=rule.to_graph.name
                    sorted_pinch_edges=set()
                    for u,v in rule.pinch_edges:
                        # they are defined on the from_graph
                        uu=to_imap[rule.map_from_to(u)]
                        vv=to_imap[rule.map_from_to(v)]
                        #uu=c_from_to_node_map[u]
                        #vv=c_from_to_node_map[v]
                        c_erased_e.append((uu,vv))
                        if uu>vv:
                            tt=uu
                            uu=vv
                            vv=tt
                        sorted_pinch_edges.add((uu,vv))
                    for u,v in sorted_pinch_edges:
                            rule_id+='('+str(u)+','+str(v)+')' 
                    if len(rule.connect_nodes)>0:
                        rule_id+='+'
                        for u in rule.connect_nodes:
                            rule_id+=str(to_imap[rule.map_from_to(u)])+'_'
                            #rule_id+='='+str(c_from_to_node_map[u])  
                            #rule_id+='='+str(to_imap[u])
                            #rule_id+='='+str(u)
                    rule_id+='['+str(c_added_n)+']'
                    if rule.to_graph.name=="final" and not verify_pinch(c_erased_e,c_added_n,c_untouched_e,c_from_to_node_map,rule.from_graph,rule.to_graph):
                        log1(rule_id,'|','c_added_n',c_added_n)
                        log1('c_to_from_node_map',c_to_from_node_map)
                        log1('c_erased_e',c_erased_e)
                        log1('rule.pinch_edges',rule.pinch_edges)
                        log1('c_from_to_node_map',c_from_to_node_map)
                        log1('to_imap',to_imap)
                        log1('from_imap',from_imap)
                        log1('rule.node_map',rule.node_map)
                        log1('from_graph',rule.from_graph.G.edges())
                        msg='from_graph_iso:'
                        for u,v in rule.from_graph.G.edges():
                            msg+='('+str(from_imap[u])+','+str(from_imap[v])+'), '
                        log1(msg)
                        msg='from_graph_mapped:'
                        for u,v in rule.from_graph.G.edges():
                            msg+='('+str(c_from_to_node_map[u])+','+str(c_from_to_node_map[v])+'), '
                        log1(msg)
                        log1('to_graph',rule.to_graph.G.edges())
                        #if not ok:
                        log1('#Warning!')
                    if rule_id not in rules:
                        if c_added_n>=0 and rule.to_graph.name=="final":
                            log1(rule_id,'|',c_added_n,c_to_from_node_map)#, c_erased_e,c_from_to_node_map,to_imap,from_imap,rule.node_map)
                        rules[rule_id]=[c_erased_e,c_added_n,c_untouched_e,c_from_to_node_map,rule.from_graph.name,rule.to_graph.name]
                    else:
                        log3('rule (',rule_id,')is redundant',rule.full_description())
    log4(rules)
    # now 
    for desc, rr in rules.items():
        erased_e=rr[0]
        added_n=rr[1]
        untouched_e=rr[2]
        node_map_orig=rr[3]
        from_graph_name=rr[4]
        to_graph_name=rr[5]
        html_file+='\n if (graph_id=="'+to_graph_name+'" && clicked_node=="'+str(added_n)+'" && (slider=="" || slider=="'+desc+'") ) {'
        html_file+='\n    split_edges=['
        for u,v in erased_e:
            html_file+="{from:'"+str(u)+"', to:'"+str(v)+"'}, "
        html_file+='];'
        html_file+='\n    map_nodes={'
        for n,to in node_map_orig.items():
            html_file+="'"+str(to)+"':'"+str(n)+"', "
        html_file+='};'
        html_file+='\n    if (slider!="" || pinch_options.length===0)'
        html_file+=" pinch('"+from_graph_name+"', split_edges, '"+str(added_n)+"', map_nodes, ee, nn);"
        html_file+='\n    if (slider!="'+desc+'") pinch_options.push("'+desc+'");\n   }'
    return html_file

def showAllGraphJS(graph,graphgraph, json_file_name, html_file_name):
    html_file="""<!doctype html>
<html><head><title>Graph</title>
<style>
    .slidecontainer {width: 50%;}
    .slider {width: 50%;height: 25px;}
    </style><html><head><title>Graph</title>
</head>
<body>
    <div class="slidecontainer">
        <button onclick="showGraphUndo()">Undo</button>
        <input type="range" min="0" max="2" value="1" class="slider" hidden=true id="graphID###">\n'
    </div>
<script type=\'text/javascript\' src=\'https://unpkg.com/vis-network@latest/dist/vis-network.js\'></script>
<link href=\'https://unpkg.com/vis-network@latest/dist/dist/vis-network.min.css\' rel=\'stylesheet\' type=\'text/css\'/>
<style type="text/css">#mynetwork### {width: 1000px;height: 700px;border: 1px solid lightgray;}</style>
<div id="mynetwork###"></div><script type="text/javascript">
var nodes = new vis.DataSet(); \n  nodes.add(["""
    for n in graph.G.nodes:
        html_file+="\n{id: '"+str(n)+"',label: '"+str(n)+"', hidden:false},"
    html_file+="\n]);\n var edges = new vis.DataSet(); \n  edges.add(["
    for u,v in graph.G.edges:
        print(graph.G.number_of_edges(u, v))
        if graph.G.number_of_edges(u, v) > 0:
            for i in range(len(graph.G.number_of_edges(u, v))):
                print(i)
                html_file+="\n{from: '"+str(u)+"', to: '"+str(v)+"', color :{ color: '#080808'}, roundness: '"+ str(i)+ "', hidden:false },"
    html_file+="""\n]);
var data= {nodes: nodes,edges: edges};
var options### = {
    edges: {
        smooth: {
            type: 'dynamic'
        },
        color: {
            inherit: false
        }
    },
    physics: {
            repulsion: {
            springLength: 100
            },
            minVelocity: 0.75,
            solver: 'repulsion'
        },
    configure: false
};
var container### = document.getElementById('mynetwork###');
var network###= new vis.Network(container###, data###, options###);
network###.on("stabilizationIterationsDone", function () {
    network###.setOptions( { physics: false } );
        });"""
    html_file+='\nvar slider = document.getElementById("graphID###");'
    html_file+="""
var undo_list=[];
var pinch_options=[]
var last_clicked=null;
var graph_id="""
    html_file+='"'+graph.name+'";'
    html_file+="""
function pinch(new_graph_id, split_edges, remove_node, map_nodes, ee, nn) {
    prev_ee=JSON.parse(JSON.stringify(ee));// deep copy
    prev_nn=JSON.parse(JSON.stringify(nn));
    // save coords
    for (i = 0; i < nn.length; i++) {
        var pos=network###.getPosition(prev_nn[i].id);
        prev_nn[i].x=pos.x;
        prev_nn[i].y=pos.y;
    }
    prev_graph=graph_id;
    graph_id=new_graph_id;
    document.getElementById("graph_name").innerHTML = graph_id;
    for (j = 0; j < split_edges.length; j++) {
        var exists=false;
        var new_from=split_edges[j].from;
        var new_to=split_edges[j].to;
        for (i = 0; i < ee.length; i++) {
            if ((ee[i].from===new_from && ee[i].to===new_to) ||
                (ee[i].from===new_to && ee[i].to===new_from) ){
                exists=true;
                ee[i].hidden=false;
                break;
            }
        }
        if (exists===false) {
            var ne = new Object();
            ne.from=split_edges[j].from;
            ne.to=split_edges[j].to;
            ne.hidden=false;
            ne.color = { color: '#080808'};
            ee.push(ne);
        }
    }
    for (i = 0; i < ee.length; i++) {
        ee[i].color.color='#080808'
        for (j = 0; j < split_edges.length; j++) {
            var new_from=split_edges[j].from;
            var new_to=split_edges[j].to;
            if ((ee[i].from===new_from && ee[i].to===new_to) ||
                (ee[i].from===new_to && ee[i].to===new_from))
                ee[i].color.color='#ff0000';
        }
    }
    // full map the graph
    for (i = 0; i < nn.length; i++) {
        var idn=prev_nn[i].id;
        if (idn!= undefined){
            var pos=network###.getPosition(idn);
            //var n=network###.canvasToDOM(pos);
            nn[i].x=pos.x;
            nn[i].y=pos.y;
        }
        if (nn[i].id==remove_node)
            nn[i].hidden=true;
    } 
    //map_nodes[remove_node]=
    //remove_node+'_';
    for (i = 0; i < nn.length; i++) {
        if (map_nodes[prev_nn[i].id]!=undefined)
            nn[i].id=map_nodes[prev_nn[i].id];
        //  else  map_nodes[prev_nn[i].id]=prev_nn[i].id;
    }
    for (i = 0; i < ee.length; i++) {
        if (map_nodes[ee[i].to]!=undefined)
            ee[i].to=map_nodes[ee[i].to];
        if (map_nodes[ee[i].from]!=undefined)
            ee[i].from=map_nodes[ee[i].from];
    }
    nodes.update(nn);
    edges.update(ee);
    undo_list.push({"ee":prev_ee,"nn": prev_nn, "graph_id":prev_graph})
}
network.on("doubleClick", function (params) {
    if (params.nodes.length != 1) return;
    var ee=edges.get();
    var nn=nodes.get();
    var cnode=params.nodes[0];
    var clicked_node=nodes.get(cnode).id;
    pinch_options=showGraphID(graph_id,clicked_node,ee,nn,"");
    if (pinch_options.length>0) {
        document.getElementById("graphID###").hidden=false;
        document.getElementById("graphID###").max=pinch_options.length-1;
    } else 
        document.getElementById("graphID###").hidden=true;
 });
 slider.oninput = function() {
    network###.selectEdges([]);
    network###.selectNodes([]);
    saved=undo_list.pop()
    nodes.update(saved["nn"])
    hideAllEdges();
    edges.update(saved["ee"]);
    graph_id=saved["graph_id"];
    showGraphID(saved["graph_id"],last_clicked,saved["ee"],saved["nn"],pinch_options[this.value]);
    network###.redraw();
}
// pintch if space is pressed
//function doc_keyUp(e) { 
//    if (e.keyCode == 32) {
//        showGraph(); 
//    }
//}
// register the handler 
//document.addEventListener('keyup', doc_keyUp, false);
function showGraphUndo() {
    network###.selectEdges([]);
    network###.selectNodes([]);
    if (undo_list.lenght===0) return;
    saved=undo_list.pop()
    nodes.update(saved["nn"])
    hideAllEdges();
    edges.update(saved["ee"]);
    graph_id=saved["graph_id"];
    document.getElementById("graphID###").hidden=true;
    network.redraw();
}
function hideAllEdges(){
    var ee=edges.get();
    for (i = 0; i < ee.length; i++) {
        ee[i].hidden=true;
        ee[i].color.color='#080808';
    }
    edges.update(ee);
}
function showGraphID(graph_id,clicked_node,ee,nn,slider){
  if (slider=="") pinch_options=[];last_clicked=clicked_node"""
    # ensure all graph.name's are unique
    names=set()
    for gn in graphgraph.nodes():
        if gn.name in names:
            log1('Error duplicated graph name')
        else:
            names.add(gn.name)
    html_file+=ruleGraphJS(graphgraph)
    html_file+="\n return pinch_options;\n }"
    #
    html_file+="\n</script>"
    html_file+='<p id="graph_name"></p>\n</body>\n</html>\n'
    html_file=html_file.replace('###','') #  #hashID(json_graph)
    try:	  
        f = open(html_file_name,'w', encoding="utf-8")
        f.write(html_file) 
        f.close() 
    except IOError:
        print("failed to write file "+html_file_name+"\nError:"+IOError)
        