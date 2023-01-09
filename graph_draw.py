
#import string
import random
import networkx as nx
from networkx.readwrite import json_graph
import hashlib
import json


def hashID(inside):
	h = hashlib.sha256()
	h.update(inside.replace(" ", "").replace("\n", "").encode('utf-8'))
	return str(h.hexdigest())[:3]

def showGraphJS(G, html_file_name, root=None):
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

tikz_id=0
def showGraphTex(G, file_name, root=None, scale=100, mirror=False, highlight_nodes=[], highlight_edges=[],highlight_edges2=[]):
	out = open(file_name, "w")
	global tikz_id
	tikz_id+=1
	print('write:',file_name)
	out.write("\\begin{tikzpicture}\n")
	#out.write("\\begin{scope}[shift={(-5,0)}]\n")
	xx=[]
	yy=[]
	for n in G.nodes:
		x=str(G.nodes[n]['pos'][0]/scale)
		xx.append(float(x))
		if mirror:
			y=str(-G.nodes[n]['pos'][1]/scale)
		else:
			y=str(G.nodes[n]['pos'][1]/scale)
		yy.append(float(y))
		id=str(n)
		if n==root:
			style='rootstyle'
		else:
			style='snstyle'
		if n in highlight_nodes:
			if tikz_id%2==0:
				style+=',redstyle'
			else:
				style+=',greenstyle'
		out.write('\\node['+style+'] at ('+x+','+y+') (v'+id+') {};\n')
		#out.write('\\node['+nstyle+'] at ('+x+','+y+') (v'+id+') {$v_'+id+'$};\n')
	#print('highlight_edges2:',highlight_edges2)
	for u,v in G.edges:
		style='sestyle'
		for i,e in enumerate(highlight_edges):
			if (u==e[0] and v==e[1]) or (u==e[1] and v==e[0]):
				highlight_edges=highlight_edges[:i]+highlight_edges[i+1:]
				if tikz_id%2==0:
					style+=',redstyle'
				else:
					style+=',greenstyle'
		for i,e in enumerate(highlight_edges2):
			if (u==e[0] and v==e[1]) or (u==e[1] and v==e[0]):
				highlight_edges2=highlight_edges2[:i]+highlight_edges2[i+1:]
				if tikz_id%2==0:
					style+=',greenstyle2'
				else:
					style+=',redstyle2'
				break
		uu=str(u)
		vv=str(v)
		id=str(n)
		w=G[u][v]["capacity"]
		if u!=v:
			if w==1:
				out.write('\\draw ['+style+']   (v'+uu+') -- (v'+vv+') ;\n')
			else:
				for ww in range(w):
					shft=int(20*(w*.5-ww))
					if w%2==0:
						shft-=10
					out.write('\\draw ['+style+']   (v'+uu+') to [bend left='+str(shft)+'] (v'+vv+') ;\n')
		else:
			dir=['above','right','below','left']
			for type in dir[:w]:
				out.write('\\draw ['+style+']   (v'+uu+') to [loop '+type+'] (v'+vv+') ;\n')
	out.write('\\node at ('+str(0.5+min(xx))+','+str(min(yy))+') {\small{$G_{'+str(14-tikz_id)+'}$}};\n')
	out.write("\\end{tikzpicture}\n")
	#out.write("\\end{scope}\n")
	out.close()
	#print('highlight_edges2:',highlight_edges2)

def showGraphTreeTex(G, file_name, root=None, scale=100, mirror=False):
	out = open(file_name, "w")
	global tikz_id
	print('write:',file_name)
	out.write("\\begin{tikzpicture}\n")
	dir=['above','right','below','left']
	xx=[]
	yy=[]
	for n in G.nodes:
		x=str(G.nodes[n]['pos'][0]/scale)
		xx.append(float(x))
		if mirror:
			y=str(-G.nodes[n]['pos'][1]/scale)
		else:
			y=str(G.nodes[n]['pos'][1]/scale)
		yy.append(float(y))
		id=str(n)
		if n==root:
			style='rootstyle'
		else:
			style='snstyle'
		out.write('\\node['+style+'] at ('+x+','+y+') (v'+id+') {};\n')
		#out.write('\\node['+nstyle+'] at ('+x+','+y+') (v'+id+') {$v_'+id+'$};\n')
	for u,v,i in G.edges:
		style='sastyle'
		uu=str(u)
		vv=str(v)
		id=str(n)
		#w=len(G[u][v])
		style+=', arc'+G[u][v][i]['color']
		if u!=v:
			shft=int(10*i+5)
			out.write('\\draw ['+style+']   (v'+uu+') to [bend left='+str(shft)+'] (v'+vv+') ;\n')
		else:
			out.write('\\draw ['+style+']   (v'+uu+') to [loop '+dir[i]+'] (v'+vv+') ;\n')
	out.write('\\node at ('+str(0.5+min(xx))+','+str(min(yy))+') {\small{$G_{'+str(tikz_id)+'}$}};\n')
	out.write("\\end{tikzpicture}\n")
	out.close()
	tikz_id+=1

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
	edges: {
		smooth: {
			type: 'continuous',
			roundness: 1
		}
	},
	physics: {
    	repulsion: {
      	springLength: 200
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


if __name__ == "__main__":
    G = nx.MultiGraph()
    G.add_edge(0,1)
    G.add_edge(1,2)
    G.add_edge(0,2)
    G.add_edge(0,1)
    showGraphJS(G, "test.html")
