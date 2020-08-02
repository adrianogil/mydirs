#!/usr/bin/env python3
import sys

from mydirscontroller import MyDirsController
import utils

try:
    range = xrange
except NameError:
    pass

controller = MyDirsController()
commands_parse = controller.get_commands()

def parse_arguments():

    args = {}

    last_key = ''

    if len(sys.argv) == 1:
        controller.handle_no_args()
        return None

    for i in range(1, len(sys.argv)):
        a = sys.argv[i]
        if a[0] == '-' and not utils.is_float(a):
            last_key = a
            args[a] = []
        elif last_key != '':
            arg_values = args[last_key]
            arg_values.append(a)
            args[last_key] = arg_values

    return args

def parse_commands(args):
    if args is None:
        return

    # print('DEBUG: Parsing args: ' + str(args))
    for a in args:
        if a in commands_parse:
            commands_parse[a](args[a], args)

args = parse_arguments()
parse_commands(args)

controller.finish()
