import argparse
def arg_func(args):
    if args.foo:
        print(args.foo)

def a_arg_func(args):
    if args.bar:
        print(args.bar)


def b_arg_func(args):
    if args.baz:
        print(args.baz)

parser = argparse.ArgumentParser(prog='TempSampling')
parser.add_argument('--foo',
                    help='foo help',
                    action='store_true',
                    dest='foo')
parser.set_defaults(func=arg_func)
sub_parsers = parser.add_subparsers(help='sub-command help')
parser_a = sub_parsers.add_parser('a', help='a help')
parser_a.add_argument('bar', type=int, help='bar help')
parser_a.set_defaults(func=a_arg_func)

parser_b = sub_parsers.add_parser('b', help='b help')
parser_b.add_argument('--foo', choices='XYZ', help='baz help',dest ='baz')
parser_b.set_defaults(func=b_arg_func)
args = parser.parse_args()
print(args)



