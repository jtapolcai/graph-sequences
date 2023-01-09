# graph-sequences

The source code of paper:

J. Tapolcai, P. Babarczi, P. Ho, and Lajos Rónyai, “Resilient Routing Table Computation Based on Connectivity Preserving Graph Sequences,” in Proc. IEEE INFOCOM, New York City, USA, 2023.

## To generate degree and local connectivity preserving (DLCP) graph sequence

graph_construct.py [-h] [-fig] [-tikz] [-mirror] [-tikz_scale TIKZ_SCALE] [-root ROOT] [-log LOG] [-file FILE] [-xml_outfile XML_OUTFILE] [-test] [-alpha ALPHA] [-beta BETA]
                          [-obj OBJ]

optional arguments:<br>
  -h, --help            show this help message and exit <br>
  -fig                  Show graphs with Matplotlib <br>
  -tikz                 Export graphs in tikz <br>
  -mirror               Show the graph upside down <br>
  -tikz_scale TIKZ_SCALE <br>
                        Scale tikz figures <br>
  -root ROOT            The root node <br>
  -log LOG              The logging level: 1- main info, 3- detailed <br>
  -file FILE            The input .json network file <br>
  -xml_outfile XML_OUTFILE <br>
                        The xml file where the results are stored <br>
  -test                 Run tests <br>
  -alpha ALPHA          Punishing parallel edges <br>
  -beta BETA            Rewarding loop edges edges <br>
  -obj OBJ              Use special objective in deconstruction: grow, even_nodes_first, even_nodes_first_chi, random <br>

For example, first create a /res directory (mkdir res) then run:

python3 graph_construct.py -file net/17_optic_german.lgf.json

Than the directoy will have a 17_optic_german.lgf.json.root0-.dgh file with the decomposition. It will also have an  xml file with some runtime statistics.

## Iterative Arborescence Construction algorithm

build_trees.py [-h] [-fig] [-tikz] [-tikz_scale TIKZ_SCALE] [-mirror] [-log LOG] [-wa WA] [-wl WL] [-file FILE] [-test] [-debug] [-id ID] [-dis DIS] [-obj OBJ] [-nopostprocess]
                      [-dat]

optional arguments: <br>
  -h, --help            show this help message and exit <br>
  -fig                  Show graphs with Matplotlib <br>
  -tikz                 Export graphs in tikz <br>
  -tikz_scale TIKZ_SCALE <br>
                        Scale tikz figures <br>
  -mirror               Show the graph upside down <br>
  -log LOG              The logging level: 1- main info, 3- detailed <br>
  -wa WA                The weight in ILP for variable a <br>
  -wl WL                The weight in ILP for variable l <br>
  -file FILE            The input .json network file <br>
  -test                 Run tests <br>
  -debug                Show figures for debuging <br>
  -id ID                An id added to the result files <br>
  -dis DIS              Disjointness arc, edge, node <br>
  -obj OBJ              The objective of the path lenght in the optimization: avg, longest, shortest <br>
  -nopostprocess        Disable post processing <br>
  -dat                  Write coverage in dat file <br>

  For example run:

  python3 build_trees.py -file res/17_optic_german.lgf.json.root0-.dgh

  See the results in the file res/17_optic_german.lgf.json.root0-.dgh__IterativeILP_arc_0-.rtn

  
