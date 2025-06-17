import gdb
import os

class RunTrigger(gdb.Command):
    """Run an external Python script inside GDB.
    Usage: run_trigger /full/path/to/script.py
    """

    def __init__(self):
        super().__init__("run_trigger", gdb.COMMAND_USER)

    def run_script(self, script_path) -> None:
        if not os.path.isfile(script_path):
            print(f"[!] File not found: {script_path}")
            return

        try:
            with open(script_path, "r") as f:
                script_content = f.read()

            # Define a custom execution context
            exec_globals = {
                "__name__": "__main__",
                "__file__": script_path,
                "gdb": gdb  # Inject gdb into the script's namespace
            }

            print(f"[*] Running script: {script_path}")
            exec(script_content, exec_globals)
            print("[+] Script finished.")
        except Exception as e:
            print(f"[!] Error while executing script: {e}")

    def invoke(self, arg, from_tty):
        args = gdb.string_to_argv(arg)

        if not args:
            print("[!] Usage: run_trigger /path/to/script.py")
            return

        script_path = args[0]
        self.run_script(script_path)


# Register the command
RunTrigger()
