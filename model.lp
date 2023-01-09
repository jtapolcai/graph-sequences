\Problem name: network

Minimize
OBJROW: -10.36364 x_red16to15id0 -10.66667 x_red16to12id0 -10.36364 x_green16to15id0 -10.36364 x_green16to12id0 -10.80000 x_blue16to15id0 -10.36364 x_blue16to12id0 -2000 k_red -1000 k_green -2000 k_blue + 1000 a
 + 100 l
Subject To
one_edge_one_colorr163:  x_red16to15id0 + x_green16to15id0 + x_blue16to15id0 <= 1
one_edge_one_colorr164:  x_red16to12id0 + x_green16to12id0 + x_blue16to12id0 <= 1
no_loopbackr165:  x_red16to15id0 = 0
no_loopbackr166:  x_blue16to12id0 = 0
avoid_loopsr167:  x_red16to15id0 = 0
avoid_loopsr168:  x_green16to12id0 = 0
avoid_loopsr169:  x_blue16to12id0 = 0
one_color_one_outedger170:  x_red16to15id0 + x_red16to12id0 - k_red = -0
one_color_one_outedger171:  x_green16to15id0 + x_green16to12id0 - k_green = -0
one_color_one_outedger172:  x_blue16to15id0 + x_blue16to12id0 - k_blue = -0
Bounds
 0 <= x_red16to15id0 <= 1
 0 <= x_red16to12id0 <= 1
 0 <= x_green16to15id0 <= 1
 0 <= x_green16to12id0 <= 1
 0 <= x_blue16to15id0 <= 1
 0 <= x_blue16to12id0 <= 1
 0 <= k_red <= 1
 0 <= k_green <= 1
 0 <= k_blue <= 1
 0 <= a <= 1
Integers
x_red16to15id0 x_red16to12id0 x_green16to15id0 x_green16to12id0 x_blue16to15id0 x_blue16to12id0 k_red k_green k_blue a 
End
