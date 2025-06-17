import sys
import os
import gdb

# Add the directory containing this script to sys.path
sys.path.append(os.path.dirname(__file__))

from break_on_functions import BreakOnFunctions, BreakInfo
from run_trigger import RunTrigger

MAX_STUCK_NARROW_AMOUNT: int = 3

class TrackFlow(gdb.Command):
    def __init__(self):
        self.break_on_functions = BreakOnFunctions()
        self.run_trigger = RunTrigger()
        super().__init__("track_flow", gdb.COMMAND_USER)
    
    def _can_narrow_down(self, current_call_info: BreakInfo, previous_call_info: BreakInfo) -> bool:
        """
        Determine if we can narrow down the search space based on the current and previous call information.
        """
        print(f"[*] Current call info: {current_call_info}")
        print(f"[*] Previous call info: {previous_call_info}")
        return previous_call_info != current_call_info

    def narrow_down(self, trigger_path: str):
        stuck_narrow_cnt = 0
        current_break_info = BreakInfo()
        prev_break_info = BreakInfo()

        while stuck_narrow_cnt < MAX_STUCK_NARROW_AMOUNT:
            if self._can_narrow_down(current_break_info, prev_break_info):
                stuck_narrow_cnt = 0
            else: 
                stuck_narrow_cnt += 1
            print(f"[*] Stuck narrow count: {stuck_narrow_cnt}")

            self.break_on_functions.start()
            self.run_trigger.run_script(trigger_path)
            self.break_on_functions.stop()

            # get the break info after the iteration
            current_break_info = self.break_on_functions.get_break_info()
            
            print(f"[*] Narrowing down from {len(self.break_on_functions.proc_functions_address)} to {len(current_break_info)}")

                # we want to put breakpoints only on what was hit!
            self.break_on_functions.set_break_addresses(list(map(lambda x: int(x,16), current_break_info)))
            
            prev_break_info = current_break_info

        self.break_on_functions.print_results()

    def invoke(self, arg, from_tty):
        args = gdb.string_to_argv(arg)

        if not args:
            print("[!] Usage: track_flow /path/to/script.py")
            return
        
        trigger_path = args[0]
        self.narrow_down(trigger_path)

        
# Register the command
TrackFlow()
