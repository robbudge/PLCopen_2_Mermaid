import re
from typing import List, Tuple, Callable


class STSelProcessor:
    """ST SEL function processor - handles SEL(condition, true_value, false_value)"""

    def __init__(self, debug_callback: Callable = None):
        self.debug = debug_callback or (lambda msg: None)
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for SEL function parsing"""
        self.patterns = {
            'sel_function': re.compile(r'SEL\s*\(\s*(.+?)\s*,\s*(.+?)\s*,\s*(.+?)\s*\)', re.IGNORECASE | re.DOTALL),
        }

    def process_sel_function(self, sel_statement: str, get_next_node_id: Callable,
                             entry_node: str, create_node: Callable, create_connection: Callable) -> Tuple[
        List[str], str]:
        """Process SEL function and return nodes and end node"""
        self.debug(f"Processing SEL function: {sel_statement[:100]}...")

        # Extract SEL parameters
        sel_match = self.patterns['sel_function'].search(sel_statement)
        if not sel_match:
            self.debug("Failed to extract SEL function parameters")
            return [], entry_node

        condition = sel_match.group(1).strip()
        true_value = sel_match.group(2).strip()
        false_value = sel_match.group(3).strip()

        self.debug(f"SEL condition: {condition}")
        self.debug(f"SEL true value: {true_value}")
        self.debug(f"SEL false value: {false_value}")

        nodes = []

        # Create SEL condition node
        sel_node_id = get_next_node_id()
        nodes.append(create_node(sel_node_id, f"SEL: {condition}", "rhombus"))
        nodes.append(create_connection(entry_node, sel_node_id))

        # Create end node where both branches meet
        end_node = get_next_node_id()

        # Connect true branch
        nodes.append(create_connection(sel_node_id, end_node, f"True: {true_value[:30]}"))

        # Connect false branch
        nodes.append(create_connection(sel_node_id, end_node, f"False: {false_value[:30]}"))

        nodes.append(create_node(end_node, "End SEL"))

        self.debug("SEL function processing completed")
        return nodes, end_node