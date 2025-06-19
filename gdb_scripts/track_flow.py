import sys
import os
import threading
import time
import gdb


# Add the directory containing this script to sys.path
sys.path.append(os.path.dirname(__file__))

from call_node import CallNode
from break_on_functions import BreakOnFunctions, BreakInfo
from run_trigger import RunTrigger

MAX_STUCK_NARROW_AMOUNT: int = 3

class TrackFlow(gdb.Command):
    def __init__(self):
        self.break_on_functions = BreakOnFunctions()
        self.run_trigger = RunTrigger()
        self.root_calls = []
        self.addr_to_node = {}  # to reuse nodes
        self.last_stack = []
        super().__init__("track_flow", gdb.COMMAND_USER)
    
    def _can_narrow_down(self, current_call_info: BreakInfo, previous_call_info: BreakInfo) -> bool:
        """
        Determine if we can narrow down the search space based on the current and previous call information.
        """
        print(f"[*] Current call info: {current_call_info}")
        print(f"[*] Previous call info: {previous_call_info}")
        return previous_call_info != current_call_info

    def run_script(self, trigger_path: str) -> None:
        if not os.path.isfile(trigger_path):
            print(f"[!] File not found: {trigger_path}")
            return
        
        while not self.break_on_functions.can_run_script:
            time.sleep(0.1)

        self.run_trigger.run_script(trigger_path)

        self.break_on_functions.can_run_script = False


    def narrow_down(self, trigger_path: str):
        # wait for `break_on_functions.stop` to finish 
        while self.break_on_functions.running:
            time.sleep(0.01)

        stuck_narrow_cnt = 0
        current_break_info = BreakInfo()
        prev_break_info = BreakInfo()

        while stuck_narrow_cnt < MAX_STUCK_NARROW_AMOUNT:
            if self._can_narrow_down(current_break_info, prev_break_info):
                stuck_narrow_cnt = 0
            else: 
                stuck_narrow_cnt += 1
            print(f"[*] Stuck narrow count: {stuck_narrow_cnt}")

            script_thread = threading.Thread(target=self.run_script, args=(trigger_path,))
            script_thread.start()

            self.break_on_functions.start()
            
            # wait for the script to finish
            script_thread.join()

            # get the break info after the iteration
            current_break_info = self.break_on_functions.get_break_info()
            
            print(f"[*] Narrowing down from {len(self.break_on_functions.proc_functions_address)} to {len(current_break_info)}")

                # we want to put breakpoints only on what was hit!
            self.break_on_functions.set_break_addresses(list(map(lambda x: int(x,16), current_break_info)))
            
            prev_break_info = current_break_info

        self.break_on_functions.print_results()
    
    def get_flow_on_stop(self, event):
        if not isinstance(event, gdb.BreakpointEvent):
            return

        try:
            frame = gdb.newest_frame()
            stack = []
            while frame:
                sal = frame.find_sal()
                pc = sal.pc
                sym = frame.name()
                name = sym if sym else "unknown"
                stack.append((name, pc))
                frame = frame.older()
            stack.reverse()

            # Build or reuse tree
            current_level = None
            for name, addr in stack:
                # if addr not in self.break_on_functions.proc_functions_address:
                #     continue
                node = self.addr_to_node.get(addr)
                if not node:
                    node = CallNode(name, addr)
                    self.addr_to_node[addr] = node

                if current_level is None:
                    if node not in self.root_calls:
                        self.root_calls.append(node)
                    current_level = node
                else:
                    current_level = current_level.add_child(node)

        except Exception as e:
            print(f"[!] Error in get_flow_on_stop: {e}")

        # Resume execution
        gdb.execute("continue")

    def print_call_flows(self):
        print("[*] Call Flows:")
        for root in self.root_calls:
            root.print_tree()

    def get_flow(self, trigger_path: str):
        # wait for `break_on_functions.stop` to finish 
        while self.break_on_functions.running:
            time.sleep(0.01)

        self.break_on_functions.on_stop_function = self.get_flow_on_stop

        script_thread = threading.Thread(target=self.run_script, args=(trigger_path,))
        script_thread.start()

        self.break_on_functions.start()
            
        # wait for the script to finish
        script_thread.join()

        print("joined")

        self.print_call_flows()


    def invoke(self, arg, from_tty):
        args = gdb.string_to_argv(arg)

        if not args:
            print("[!] Usage: track_flow /path/to/script.py")
            return
        
        cmd = args[0]

        if len(args) < 2:
            print("[#] Missing trigger path")

        trigger_path = args[1]

        if cmd == "narrow":
            self.narrow_down(trigger_path)

        elif cmd == "get-flow":
            self.get_flow(trigger_path)
        
        else:
            print(f"Command: {cmd} is an Unknown command")
        
# Register the command
TrackFlow()
