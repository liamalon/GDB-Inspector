class CallNode:
    def __init__(self, name, addr):
        self.name = name
        self.addr = addr
        self.children = []
    
    def add_child(self, child):
        for existing in self.children:
            if existing.addr == child.addr:
                return existing  # Don't duplicate
        self.children.append(child)
        return child

    def print_tree(self, indent=0):
        print("  " * indent + f"{self.name} (0x{self.addr:x})")
        for child in self.children:
            child.print_tree(indent + 1)
