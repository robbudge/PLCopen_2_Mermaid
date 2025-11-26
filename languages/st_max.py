import re
from typing import List, Tuple, Optional
from .base_processor import BaseLanguageProcessor
from .sanitizer import MermaidSanitizer


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

        # Find the first complete statement (up to semicolon)
        first_semicolon = code.find(';')
        if first_semicolon == -1:
            self._add_debug("[MAX] No complete statement found")
            return None

        first_statement = code[:first_semicolon + 1].strip()
        consumed = first_semicolon + 1  # Include the semicolon

        self._add_debug(f"[MAX] First complete statement: {first_statement}")
        self._add_debug(f"[MAX] Will consume {consumed} characters")

        # Now check if this statement is a MAX assignment
        max_match = self._find_max_assignment(first_statement)
        if not max_match:
            self._add_debug("[MAX] First statement is not a MAX assignment")
            return None

        # Create node for the MAX assignment
        node_id = f"N{node_counter[0]}"
        node_counter[0] += 1

        # Extract the variable and MAX call
        var = max_match.group(1)
        max_call = f"MAX{max_match.group(2)}"

        # USE SANITIZER
        safe_label = MermaidSanitizer.sanitize_label(f"{var} := {max_call}")
        max_node = MermaidSanitizer.create_safe_node(node_id, safe_label)

        self._add_debug(f"[MAX] Created MAX node: {max_node}")

        nodes = [max_node]

        # Connect from entry node if needed
        if entry_node and entry_node != "Start":
            connection = MermaidSanitizer.create_safe_connection(entry_node, node_id)
            nodes.append(connection)
            self._add_debug(f"[MAX] Added connection: {connection}")

        return nodes, node_id, consumed

    def _find_max_assignment(self, statement: str) -> Optional[re.Match]:
        """Find MAX function call in a complete statement"""
        # Pattern to match: variable := MAX(parameters);
        pattern = r'(\w+(?:\.\w+)*)\s*:=\s*MAX\s*(\([^;]+\));'
        match = re.search(pattern, statement, re.IGNORECASE | re.DOTALL)

        if match:
            self._add_debug(f"[MAX] Found MAX assignment: {match.group(0)}")
            self._add_debug(f"[MAX] Group 1 (var): {match.group(1)}")
            self._add_debug(f"[MAX] Group 2 (params): {match.group(2)}")
            return match

        self._add_debug("[MAX] No MAX assignment pattern matched")
        return None