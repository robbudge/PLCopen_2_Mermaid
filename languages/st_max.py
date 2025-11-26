import re
from typing import List, Tuple, Optional
from .base_processor import BaseLanguageProcessor


class STMaxProcessor(BaseLanguageProcessor):
    """Processor for MAX function calls in ST"""

    def __init__(self, coordinator):
        super().__init__()
        self.coordinator = coordinator

    def can_process(self, language: str) -> bool:
        """Check if this processor can handle a language - required by base class"""
        # This processor is only used internally by STProcessor, not directly
        return False

    def generate_flowchart(self, code: str, pou_name: str) -> str:
        """Generate flowchart - required by base class but not used for MAX processor"""
        # This processor is only used internally by STProcessor
        return f"%% MAX processor cannot generate standalone flowchart for {pou_name}"

    def process_max_statement(self, code: str, entry_node: str, node_counter: List[int]) -> Optional[
        Tuple[List[str], str, int]]:
        """Process MAX function call and return nodes, exit node, and consumed characters"""
        self._add_debug("[MAX] Processing MAX statement")

        # Find MAX assignment
        max_match = self._find_max_assignment(code)
        if not max_match:
            self._add_debug("[MAX] No MAX assignment found")
            return None

        full_statement = max_match.group(0)
        consumed = len(full_statement)

        self._add_debug(f"[MAX] Found MAX assignment: {full_statement}")
        self._add_debug(f"[MAX] Consumed characters: {consumed}")

        # Create node for the MAX assignment
        node_id = f"N{node_counter[0]}"
        node_counter[0] += 1

        # Extract the variable and MAX call for the label
        var = max_match.group(1)
        max_call = max_match.group(2)

        # Create a clean label showing the assignment
        safe_label = self._sanitize_label(f"{var} := {max_call}")
        max_node = self._create_safe_node(node_id, safe_label)

        self._add_debug(f"[MAX] Created MAX node: {max_node}")

        nodes = [max_node]

        # Connect from entry node if needed
        if entry_node and entry_node != "Start":
            connection = self._create_safe_connection(entry_node, node_id)
            nodes.append(connection)
            self._add_debug(f"[MAX] Added connection: {connection}")

        return nodes, node_id, consumed

    def _find_max_assignment(self, code: str) -> Optional[re.Match]:
        """Find MAX function call in assignment"""
        # Pattern to match: variable := MAX(parameters);
        pattern = r'(\w+(?:\.\w+)*)\s*:=\s*MAX\s*\([^;]+\);'
        match = re.search(pattern, code, re.IGNORECASE | re.DOTALL)

        if match:
            self._add_debug(f"[MAX] Found MAX assignment: {match.group(0)}")
            return match

        self._add_debug("[MAX] No MAX assignment pattern matched")
        return None

    def _sanitize_label(self, label: str) -> str:
        """Sanitize label for Mermaid syntax"""
        if not label:
            return ""

        # Replace problematic characters for Mermaid
        replacements = {
            '<': '&lt;',
            '>': '&gt;',
            '&': '&amp;',
            '"': '&quot;',
            "'": '&#39;',
            '[': '&lsqb;',
            ']': '&rsqb;',
            '{': '&lcub;',
            '}': '&rcub;',
            '|': '&#124;',
        }

        for char, replacement in replacements.items():
            label = label.replace(char, replacement)

        # Remove or replace newlines
        label = label.replace('\n', ' ')
        label = label.replace('\r', ' ')

        # Collapse multiple spaces
        label = re.sub(r' +', ' ', label)

        return label.strip()

    def _create_safe_node(self, node_id: str, label: str) -> str:
        """Create a safe Mermaid node with proper escaping"""
        safe_id = self._sanitize_node_id(node_id)
        safe_label = self._sanitize_label(label)

        # Handle empty labels
        if not safe_label:
            return f"{safe_id}[\" \"]"

        return f"{safe_id}[{safe_label}]"

    def _create_safe_connection(self, from_node: str, to_node: str, label: str = "") -> str:
        """Create a safe Mermaid connection between nodes"""
        safe_from = self._sanitize_node_id(from_node)
        safe_to = self._sanitize_node_id(to_node)
        safe_label = self._sanitize_label(label)

        if safe_label:
            return f"{safe_from} -->|{safe_label}| {safe_to}"
        else:
            return f"{safe_from} --> {safe_to}"

    def _sanitize_node_id(self, node_id: str) -> str:
        """Sanitize node ID for Mermaid syntax"""
        # Remove any characters that aren't alphanumeric or underscore
        return re.sub(r'[^a-zA-Z0-9_]', '', node_id)