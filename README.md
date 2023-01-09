# graph-sequences

The source code of paper:

J. Tapolcai, P. Babarczi, P. Ho, and Lajos Rónyai, “Resilient Routing Table Computation Based on Connectivity Preserving Graph Sequences,” in Proc. IEEE INFOCOM, New York City, USA, 2023.

## To generate degree and local connectivity preserving (DLCP) graph sequence

graph_construct.py [-h] [-fig] [-tikz] [-mirror] [-tikz_scale TIKZ_SCALE] [-root ROOT] [-log LOG] [-file FILE] [-xml_outfile XML_OUTFILE] [-test] [-alpha ALPHA] [-beta BETA]
                          [-obj OBJ]

optional arguments:
  -h, --help            show this help message and exit
  -fig                  Show graphs with Matplotlib
  -tikz                 Export graphs in tikz
  -mirror               Show the graph upside down
  -tikz_scale TIKZ_SCALE
                        Scale tikz figures
  -root ROOT            The root node
  -log LOG              The logging level: 1- main info, 3- detailed
  -file FILE            The input .json network file
  -xml_outfile XML_OUTFILE
                        The xml file where the results are stored
  -test                 Run tests
  -alpha ALPHA          Punishing parallel edges
  -beta BETA            Rewarding loop edges edges
  -obj OBJ              Use special objective in deconstruction: grow, even_nodes_first, even_nodes_first_chi, random

For example, first create a /res directory (mkdir res) then run:

python3 graph_construct.py -file net/17_optic_german.lgf.json

Than the directoy will have a 17_optic_german.lgf.json.root0-.dgh file with the decomposition. It will also have an  xml file with some runtime statistics.

## Iterative Arborescence Construction algorithm

build_trees.py [-h] [-fig] [-tikz] [-tikz_scale TIKZ_SCALE] [-mirror] [-log LOG] [-wa WA] [-wl WL] [-file FILE] [-test] [-debug] [-id ID] [-dis DIS] [-obj OBJ] [-nopostprocess]
                      [-dat]

optional arguments:
  -h, --help            show this help message and exit
  -fig                  Show graphs with Matplotlib
  -tikz                 Export graphs in tikz
  -tikz_scale TIKZ_SCALE
                        Scale tikz figures
  -mirror               Show the graph upside down
  -log LOG              The logging level: 1- main info, 3- detailed
  -wa WA                The weight in ILP for variable a
  -wl WL                The weight in ILP for variable l
  -file FILE            The input .json network file
  -test                 Run tests
  -debug                Show figures for debuging
  -id ID                An id added to the result files
  -dis DIS              Disjointness arc, edge, node
  -obj OBJ              The objective of the path lenght in the optimization: avg, longest, shortest
  -nopostprocess        Disable post processing
  -dat                  Write coverage in dat file

  For example run:

  python3 build_trees.py -file res/17_optic_german.lgf.json.root0-.dgh

  See the results in the file res/17_optic_german.lgf.json.root0-.dgh__IterativeILP_arc_0-.rtn

  
