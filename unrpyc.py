#!/usr/bin/env python2

# Copyright (c) 2012 Yuri K. Schlesner
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import argparse
import os.path as path
import codecs
import glob
import itertools
import traceback

import decompiler
from decompiler import magic, astdump

# special definitions for special classes

class PyExpr(magic.FakeStrict, unicode):
    __module__ = "renpy.ast"
    def __new__(cls, s, filename, linenumber):
        self = unicode.__new__(cls, s)
        self.filename = filename
        self.linenumber = linenumber
        return self

class PyCode(magic.FakeStrict):
    __module__ = "renpy.ast"
    def __setstate__(self, state):
        (_, self.source, self.location, self.mode) = state
        self.bytecode = None

class_factory = magic.FakeClassFactory((PyExpr, PyCode), magic.FakeStrict)

# API

def read_ast_from_file(in_file):
    # .rpyc files are just zlib compressed pickles of a tuple of some data and the actual AST of the file
    raw_contents = in_file.read().decode('zlib')
    data, stmts = magic.safe_loads(raw_contents, class_factory, {"_ast"})
    return stmts

def decompile_rpyc(input_filename, overwrite=False, dump=False, decompile_python=False,
                   comparable=False, line_numbers=False):
    # Output filename is input filename but with .rpy extension
    filepath, ext = path.splitext(input_filename)
    out_filename = filepath + ('.txt' if dump else '.rpy')

    print "Decompiling %s to %s..." % (input_filename, out_filename)

    if not overwrite and path.exists(out_filename):
        print "Output file already exists. Pass --clobber to overwrite."
        return False # Don't stop decompiling if one file already exists

    with open(input_filename, 'rb') as in_file:
        ast = read_ast_from_file(in_file)

    with codecs.open(out_filename, 'w', encoding='utf-8') as out_file:
        if dump:
            astdump.pprint(out_file, ast, decompile_python=decompile_python, comparable=comparable,
                                          line_numbers=line_numbers)
        else:
            decompiler.pprint(out_file, ast, decompile_python=decompile_python, line_numbers=line_numbers)
    return True

def main():
    # python27 unrpyc.py [-c] [-d] [--python-screens|--ast-screens|--no-screens] file [file ...]
    parser = argparse.ArgumentParser(description="Decompile .rpyc files")

    parser.add_argument('-c', '--clobber', dest='clobber', action='store_true',
                        help="overwrites existing output files")

    parser.add_argument('-d', '--dump', dest='dump', action='store_true',
                        help="instead of decompiling, pretty print the ast to a file")

    parser.add_argument('--sl1-as-python', dest='decompile_python', action='store_true',
                        help="Only dumping and for decompiling screen language 1 screens. "
                        "Convert SL1 Python AST to Python code instead of dumping it or converting it to screenlang.")

    parser.add_argument('--comparable', dest='comparable', action='store_true',
                        help="Only for dumping, remove several false differences when comparing dumps. "
                        "This suppresses attributes that are different even when the code is identical, such as file modification times. "
                        "Line numbers are also suppressed unless the --line-numbers option is used.")

    parser.add_argument('--line-numbers', dest='line_numbers', action='store_true',
                        help="Allow line numbers to be compared. "
                        "When decompiling, this causes extra lines to be printed to make line numbers match. "
                        "When dumping the ast, this causes line numbers to be printed even when using --comparable.")

    parser.add_argument('file', type=str, nargs='+',
                        help="The filenames to decompile")

    args = parser.parse_args()

    # Expand wildcards
    files = map(glob.glob, args.file)
    # Concatenate lists
    files = list(itertools.chain(*files))

    # Check if we actually have files
    if len(files) == 0:
        parser.print_help();
        parser.error("No script files given.")

    # Check per file if everything went well and report back
    good = bad = 0
    for filename in files:
        try:
            correct = decompile_rpyc(filename, args.clobber, args.dump, decompile_python=args.decompile_python,
                                                                  comparable=args.comparable, line_numbers=args.line_numbers)
        except Exception as e:
            print traceback.format_exc()
            bad += 1

        else:
            if correct:
                good += 1
            else:
                bad += 1

    if bad == 0:
        print "Decompilation of %d script file%s successful" % (good, 's' if good>1 else '')
    elif good == 0:
        print "Decompilation of %d file%s failed" % (bad, 's' if bad>1 else '')
    else:
        print "Decompilation of %d file%s successful, but decompilation of %d file%s failed" % (good, 's' if good>1 else '', bad, 's' if bad>1 else '')

if __name__ == '__main__':
    main()