import re
from typing import List, Tuple, Optional
from .base_processor import BaseLanguageProcessor
from .sanitizer import MermaidSanitizer


class STSelProcessor(BaseLanguageProcessor):
    """ST SEL function processor - handles SEL(condition, true_value, false_value)"""

    def __init__(self, coordinator):
        super().__init__()
        self.coordinator = coordinator

    def can_process(self, language: str) -> bool:
        return False

    def generate_flowchart(self, code: str, pou_name: str) -> str:
        return f"%% SEL processor cannot generate standalone flowchart for {pou_name}"

    def process_sel_statement(self, code: str, entry_node: str, node_counter: List[int]) -> Optional[
        Tuple[List[str], str, int]]:
        """Process SEL function assignment and return nodes, exit node, and consumed characters"""
        self._add_debug("[SEL] Processing SEL statement")

        # Find the first complete statement (up to semicolon)
        first_semicolon = code.find(';')
        if first_semicolon == -1:
            self._add_debug("[SEL] No complete statement found")
            return None

        first_statement = code[:first_semicolon + 1].strip()
        consumed = first_semicolon + 1

        self._add_debug(f"[SEL] First complete statement: {first_statement[:100]}...")
        self._add_debug(f"[SEL] Will consume {consumed} characters")

        # Check if this statement is a SEL assignment
        sel_match = self._find_sel_assignment(first_statement)
        if not sel_match:
            self._add_debug("[SEL] No SEL assignment found in statement")
            return None

        # Extract the components
        var = sel_match.group(1)
        condition = sel_match.group(2).strip()
        true_value = sel_match.group(3).strip()
        false_value = sel_match.group(4).strip()

        self._add_debug(f"[SEL] SEL components:")
        self._add_debug(f"[SEL]   Variable: {var}")
        self._add_debug(f"[SEL]   Condition: {condition}")
        self._add_debug(f"[SEL]   True value: {true_value}")
        self._add_debug(f"[SEL]   False value: {false_value}")

        nodes = []

        # Create decision node for SEL condition
        decision_node_id = f"N{node_counter[0]}"
        node_counter[0] += 1

        safe_condition = MermaidSanitizer.sanitize_label(f"SEL: {condition}")
        decision_node = MermaidSanitizer.create_safe_node(decision_node_id, safe_condition, "rhombus")
        nodes.append(decision_node)

        # Connect from entry node to decision node
        if entry_node and entry_node != "Start":
            connection = MermaidSanitizer.create_safe_connection(entry_node, decision_node_id)
            nodes.append(connection)

        # Create true branch node
        true_node_id = f"N{node_counter[0]}"
        node_counter[0] += 1

        true_label = MermaidSanitizer.sanitize_label(f"{var} := {true_value}")
        true_node = MermaidSanitizer.create_safe_node(true_node_id, true_label)
        nodes.append(true_node)

        # Create false branch node
        false_node_id = f"N{node_counter[0]}"
        node_counter[0] += 1

        false_label = MermaidSanitizer.sanitize_label(f"{var} := {false_value}")
        false_node = MermaidSanitizer.create_safe_node(false_node_id, false_label)
        nodes.append(false_node)

        # Create merge node where both branches meet
        merge_node_id = f"N{node_counter[0]}"
        node_counter[0] += 1
        merge_node = MermaidSanitizer.create_safe_node(merge_node_id, "SEL End")
        nodes.append(merge_node)

        # Connect decision to true branch with label
        true_connection = MermaidSanitizer.create_safe_connection(decision_node_id, true_node_id, "True")
        nodes.append(true_connection)

        # Connect decision to false branch with label
        false_connection = MermaidSanitizer.create_safe_connection(decision_node_id, false_node_id, "False")
        nodes.append(false_connection)

        # Connect both branches to merge node
        true_to_merge = MermaidSanitizer.create_safe_connection(true_node_id, merge_node_id)
        nodes.append(true_to_merge)

        false_to_merge = MermaidSanitizer.create_safe_connection(false_node_id, merge_node_id)
        nodes.append(false_to_merge)

        self._add_debug(f"[SEL] Created SEL decision structure:")
        self._add_debug(f"[SEL]   Decision: {decision_node_id}")
        self._add_debug(f"[SEL]   True branch: {true_node_id}")
        self._add_debug(f"[SEL]   False branch: {false_node_id}")
        self._add_debug(f"[SEL]   Merge: {merge_node_id}")

        return nodes, merge_node_id, consumed

    def _find_sel_assignment(self, statement: str) -> Optional[re.Match]:
        """Find SEL function call in a complete statement with parameter extraction"""
        # Improved pattern to capture SEL parameters individually
        # Pattern: variable := SEL(condition, true_value, false_value);
        pattern = r'(\w+(?:\.\w+)*)\s*:=\s*SEL\s*\(\s*(.+?)\s*,\s*(.+?)\s*,\s*(.+?)\s*\)\s*;'
        match = re.search(pattern, statement, re.IGNORECASE | re.DOTALL)

        if match:
            self._add_debug(f"[SEL] Found SEL assignment: {match.group(1)}")
        else:
            self._add_debug(f"[SEL] No SEL pattern matched in: {statement[:100]}...")

        return match

    def process_sel_function(self, code: str, entry_node: str, node_counter: List[int]) -> Optional[
        Tuple[List[str], str, int]]:
        """Process standalone SEL function (not in assignment)"""
        self._add_debug("[SEL] Processing standalone SEL function")

        # This would handle cases like: SEL(condition, true_val, false_val);
        # For now, just return None since we're focusing on assignment format
        return None