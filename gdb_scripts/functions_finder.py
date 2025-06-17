from dataclasses import dataclass
from functools import cached_property
import gdb
import re

try:
    import capstone
except ImportError:
    gdb.write("[!] Capstone not found in GDB’s Python. Try launching GDB with: `gdb -ex 'python sys.path.append(\"/path/to/python/site-packages\")'`\n", gdb.STDERR)
    raise

@dataclass
class ProcMappingEntry:
    start_addr: int
    end_addr: int
    size: int
    offset: int
    perms: str
    # some entries may not have a name
    objfile: str = ""

    def __post_init__(self):
        # TODO: rewrite this ugly shit
        if isinstance(self.start_addr, str):
            self.start_addr = int(self.start_addr, 0)

        if isinstance(self.end_addr, str):
            self.end_addr = int(self.end_addr, 0)
        
        if isinstance(self.size, str):
            self.size = int(self.size, 0)
        
        if isinstance(self.offset, str):
            self.offset = int(self.offset, 0)

DISASSEMBLERS: dict[str, capstone.Cs] = {
    "x86-64": capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64),
    "i386": capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32),
    "arm": capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM),
    "aarch64": capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM),
    "mips": capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32),
    "mips64": capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS64),
}

FUNCTIONS_STARTS: dict[str, list[int]] = {
    "x86-64": [0x55, 0x48, 0x89, 0xe5],  # push rbp; mov rbp, rsp
    "i386": [0x55, 0x89, 0xe5],  # push ebp; mov ebp, esp
    "arm": [0xe9, 0x2d, 0x40, 0x52],  # push {fp, lr}
    "aarch64": [0xfd, 0x7b, 0x01, 0xa9],  # stp x29, x30, [sp, #-...]
    "mips": [0x27, 0xbd, 0xff, 0xff],  # addiu 
    "mips64": [0x27, 0xbd, 0xff, 0xff],  # addiu
}

class FunctionFinder:
    @cached_property
    def inferior(self) -> gdb.Inferior:
        return gdb.selected_inferior()

    @cached_property
    def proc_arch(self) -> str:
        return self.inferior.architecture().name()

    @cached_property
    def proc_name(self) -> str:
        return self.inferior.progspace.filename

    def get_mappings_columns(self, mappings: list[str]) -> list:
        for entry in mappings:
            entry = entry.strip()
            if entry.startswith("Start Addr"):
                # Use regex to extract the columns
                return re.split(r'\s{2,}', entry)
        return []

    def parse_mappings(self, mappings: list[str], columns: list[str]) -> list[ProcMappingEntry]:
        parsed_mappings = []
        num_columns = len(columns)
        for entry in mappings:
            entry = entry.strip()
            if entry.startswith("0x"):
                tokens = re.split(r'\s{2,}', entry, maxsplit=num_columns-1)

                # this will also validate the number of columns
                parsed_entry = ProcMappingEntry(*tokens)
                
                if parsed_entry.objfile == self.proc_name:
                    parsed_mappings.append(parsed_entry)

        return parsed_mappings
            

    def get_proc_mappings(self) -> list[ProcMappingEntry]:     
        mappings = gdb.execute("info proc mappings", to_string=True).splitlines()
        columns = self.get_mappings_columns(mappings)
        return self.parse_mappings(mappings, columns)
    
    def get_disassembler(self, arch: str) -> capstone.Cs:
        if disassembler := DISASSEMBLERS.get(arch.split(":")[-1]):
            disassembler.detail = False
            return disassembler
        raise NotImplementedError(f"Unsupported Capstone arch: {arch}")


    def looks_like_function_start(self, insns, arch):
        if not insns or len(insns) < 2:
            return False

        # Get first 4 byte values from instruction bytes
        first_bytes = []
        for insn in insns:
            first_bytes.extend(insn.bytes)
            if len(first_bytes) >= 4:
                break
        first_bytes = first_bytes[:4]

        expected = FUNCTIONS_STARTS.get(arch.split(":")[-1])
        if not expected:
            return False

        return first_bytes == expected
    
    def find_function_starts(self, mem: bytes, base_addr: int, md: capstone.Cs) -> list[int]:
        candidates = []
        for offset in range(0, len(mem) - 16):  # scan with 1-byte granularity
            try:
                code = mem[offset:offset + 16]
                insns = list(md.disasm(code, base_addr + offset))
                if self.looks_like_function_start(insns, self.proc_arch):
                    candidates.append(base_addr + offset)
            except Exception:
                continue
        return sorted(candidates)


    def get_function_starts(self, mem: bytes, base_addr: int, md: capstone.Cs) -> list[int]:
        return self.find_function_starts(mem, base_addr, md)

    def get_functions_addresses(self) -> set[int]:
        mappings = self.get_proc_mappings()
        md = self.get_disassembler(self.proc_arch)
        
        functions_addrs = set()
        for mapping in mappings:
            if mapping.perms == "r-xp":
                mem = gdb.selected_inferior().read_memory(mapping.start_addr, mapping.size)
                functions_starts = self.get_function_starts(mem, mapping.start_addr, md)
                functions_addrs.update(functions_starts)
        return functions_addrs
