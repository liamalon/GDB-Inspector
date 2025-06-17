from dataclasses import dataclass
import sys
import os
import threading
import time
import gdb

# Add the directory containing this script to sys.path
sys.path.append(os.path.dirname(__file__))

from functions_finder import FunctionFinder

@dataclass
class TraceCallInfo:
    name: str
    address: str
    count: int = 1

class BreakInfo(dict):
    def __contains__(self, key):
        """Check if a BreakInfo or address string is in the dict by address."""
        if isinstance(key, TraceCallInfo):
            key_address = key.address
        else:
            key_address = key
        return any(val.address == key_address for val in self.values())

    def __eq__(self, other):
        if not isinstance(other, BreakInfo):
            return NotImplemented
        return self._address_set() == other._address_set()

    def __ne__(self, other):
        eq = self.__eq__(other)
        if eq is NotImplemented:
            return NotImplemented
        return not eq

    def __iter__(self):
        """Make list(self) return a list of addresses."""
        return (int(val.address, 16) for val in self.values())

    def _address_set(self):
        return {int(val.address, 16) for val in self.values()}

class BreakOnFunctions(gdb.Command):
    """Set breakpoints on all detected function entry points."""

    def __init__(self):
        self.running = False
        self.proc_functions_address = self._get_initial_functions()
        self.break_info = BreakInfo()
        self.lock = threading.Lock()
        self.debug = False
        super().__init__("break_on_functions", gdb.COMMAND_USER)

    def _get_initial_functions(self):
        """
        When running the first time we want to get all the functions from the binary
        """
        finder = FunctionFinder()
        return finder.get_functions_addresses()

    def on_stop(self, event):
        if not self.running:
            return

        try:
            frame = gdb.newest_frame()
            if not frame:
                return

            addr = hex(frame.pc())
            name = frame.name() or "<stripped>"

            with self.lock:
                if addr in self.break_info:
                    self.break_info[addr].count += 1
                else:
                    self.break_info[addr] = TraceCallInfo(name=name, address=addr)
                    if self.debug:
                        print(f"[NEW] {name:30} @ {addr}")
        except Exception as e:
            print("Error in on_stop:", e)

        # Safe resume (deferred)
        gdb.post_event(lambda: gdb.execute("continue", to_string=True))
    
    def set_break_addresses(self, proc_functions_address: list[int] = None) -> None:
        """
        Because this is for use of another gdb plugin, we support communication through 
        gdb shared variables, here it is `gdb.proc_functions_address`.
        """
        self.proc_functions_address = proc_functions_address or gdb.proc_functions_address
        print(f"[*] Setting breakpoints at {len(self.proc_functions_address)} addresses.")

    def get_break_info(self) -> BreakInfo:
        return self.break_info

    def break_functions(self):
        for addr in self.proc_functions_address:
            bp = gdb.Breakpoint(f"*0x{addr:x}")
            bp.silent = True
            print(f"[*] Breakpoint set at 0x{addr:x}")

        print(f"[+] Set {len(self.proc_functions_address)} breakpoints.")
        gdb.events.stop.connect(self.on_stop)

    def start(self, timeout: float = None) -> None:
        self.running = True
        self.break_info = {}
        # stop_thread = threading.Thread(target=self.stop, args=(timeout,))
        # stop_thread.start()

        self.break_functions()
        gdb.execute("continue")

    def stop(self, timeout: float = None) -> None:
        if not self.running:
            print("[-] Breaking not running.")    
            return
         
        if timeout:
            start_time = time.time()
            while time.time() - start_time < timeout:
                time.sleep(0.2)
        
        gdb.events.stop.disconnect(self.on_stop)
        
        # give some time for the breakpoints to exit
        # this is not perfect but will do for now
        time.sleep(1)

        for bp in gdb.breakpoints():
            bp.delete()

        print("[+] Removed breakpoints.")
        print("[+] Stopping trace.")
        self.running = False
        gdb.execute("interrupt")

    def print_results(self):
        print("\n[+] Traced Function Calls:")
        with self.lock:
            for info in sorted(self.break_info.values(), key=lambda x: x.count, reverse=True):
                print(f"- {info.name:30} @ {info.address} | called {info.count} times")
        print("[+] End of trace.")

    def invoke(self, arg, from_tty):
        args = arg.strip().split()

        if not args:
            print("Usage: break_on_functions start <timeout> [debug] | stop | print | set_break_addresses <function1> <function2> ...")
            return

        cmd = args[0]

        if cmd == "start":
            timeout = float(args[1]) if len(args) > 1 else None
            
            if len(args) < 2:
                print("[#] Missing timeout, it will wait for a stop from the client.")
            
            if self.running:
                print("[-] Breaking already running.")
                return

            self.debug = len(args) > 2 and args[2].lower() == "debug"
            self.start(timeout)

        elif cmd == "stop":
            self.stop()
        
        elif cmd == "test":
            gdb.shared_list232424 = [1,23,4]
            print(gdb.shared_list232424)

        elif cmd == "print":
            self.print_results()

        elif cmd == "set_break_addresses":
            functions = list(map(lambda x: int (x, 16), args[1:]))
            self.set_break_addresses(functions)

        else:
            print("Unknown command:", cmd)
        
    def complete(self, text, word):
        # text: the full input line
        # word: the current word to complete

        # TODO: this is fcking ugly
        options = []
        word_index = len(text.split())

        if word_index == 0 or (word_index == 1 and word):
            options = ["start", "stop", "print", "set_break_addresses"]
        
        elif text.strip() == "start":
            options = ["debug"]

        if word:
            return [opt for opt in options if opt.startswith(word)]
        
        return options
        
BreakOnFunctions()
