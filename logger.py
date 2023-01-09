#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-
#
# by Janos Tapolcai

import sys, re
import string

# logging level
debug =4
def log1(*args):
	global debug
	if debug>1: print(*args)
def log2(*args):
	global debug
	if debug>2: print(' ',*args)
def log3(*args):
	global debug
	if debug>3: print('  ',*args)
def log4(*args):
	global debug
	if debug>4: print('   ',*args)
def log5(*args):
	global debug
	if debug>5: print('    ',*args)
def log6(*args):
	global debug
	if debug>6: print('     ',*args)
def is_debug(level):
	global debug
	return debug>level
def set_debug(level):
	global debug
	debug=level