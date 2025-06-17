import sys
import os
import gdb

# Add the directory containing this script to sys.path
sys.path.append(os.path.dirname(__file__))

from functions_finder import FunctionFinder


class ListFunctions(gdb.Command):
    """List potential function addresses in executable memory without relying on symbols."""

    def __init__(self):
        super().__init__("list_functions", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        finder = FunctionFinder()
        addresses = finder.get_functions_addresses()
        print(f"[*] Functions addresses:")
        for addr in sorted(addresses):
            print(f"\t0x{addr:x}")

ListFunctions()