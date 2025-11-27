import re
from typing import List, Dict, Any, Tuple, Optional
from .sanitizer import MermaidSanitizer


class STOrProcessor:
    """Processor for OR logical operations in ST code"""

    def __init__(self, coordinator):
        self.coordinator = coordinator
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for OR statement parsing"""
        self.patterns = {
            'or_assignment': re.compile(
                r'^([^:=]+):=([^;]+);',
                re.IGNORECASE
            ),
            'or_keyword': re.compile(r'\s+OR\s+', re.IGNORECASE),
        }

    def _add_debug(self, message: str):
        """Add debug message through coordinator"""
        if hasattr(self.coordinator, '_add_debug'):
            self.coordinator._add_debug(message)

    def find_or_statement(self, code: str) -> bool:
        """Check if the next complete statement contains an OR assignment"""
        first_semicolon = code.find(';')
        if first_semicolon == -1:
            return False

        first_statement = code[:first_semicolon + 1].strip()
        is_or = ' OR ' in first_statement.upper() and ':=' in first_statement

        if is_or:
            return self._validate_or_structure(first_statement)
        return False

    def _validate_or_structure(self, statement: str) -> bool:
        """Validate that the OR statement has proper structure"""
        return ':=' in statement and ' OR ' in statement.upper() and statement.strip().endswith(';')

    def process_or_statement(self, code: str, current_node: str, node_counter: List[int]) -> Tuple[List[str], str, int]:
        """Process OR statement and generate Mermaid nodes"""
        self._add_debug("[OR_PROCESSOR] Processing OR statement")

        first_semicolon = code.find(';')
        if first_semicolon == -1:
            return [], current_node, 0

        full_statement = code[:first_semicolon + 1].strip()
        consumed = first_semicolon + 1

        try:
            nodes = []

            # Extract left and right sides
            if ':=' in full_statement:
                left_side, right_side = full_statement.split(':=', 1)
                left_side = left_side.strip()
                right_side = right_side.strip().rstrip(';').strip()
            else:
                return self._create_fallback_node(full_statement, current_node, node_counter, consumed)

            # Split OR conditions
            conditions = [cond.strip() for cond in self.patterns['or_keyword'].split(right_side) if cond.strip()]

            # Create OR block structure
            or_block_id = f"OR{node_counter[0]}"
            node_counter[0] += 1

            # Start node for OR block
            start_node_id = f"{or_block_id}_Start"
            start_label = f"{left_side} Assignment"
            nodes.append(self._create_safe_node(start_node_id, start_label))

            # Connect from current node to OR start
            if current_node and current_node != "Start":
                nodes.append(self._create_safe_connection(current_node, start_node_id))

            # Create OR decision node
            or_decision_id = f"{or_block_id}_Decision"
            or_label = "OR"
            nodes.append(self._create_safe_node(or_decision_id, or_label, "diamond"))
            nodes.append(self._create_safe_connection(start_node_id, or_decision_id))

            # Create condition nodes
            condition_nodes = []
            for i, condition in enumerate(conditions):
                cond_id = f"{or_block_id}_Cond{i + 1}"
                cond_label = self._sanitize_condition(condition)
                nodes.append(self._create_safe_node(cond_id, cond_label))
                condition_nodes.append(cond_id)

                # Connect OR decision to each condition
                nodes.append(self._create_safe_connection(or_decision_id, cond_id))

            # Create TRUE and FALSE assignment nodes
            true_node_id = f"{or_block_id}_True"
            true_label = f"{left_side} := TRUE"
            nodes.append(self._create_safe_node(true_node_id, true_label))

            false_node_id = f"{or_block_id}_False"
            false_label = f"{left_side} := FALSE"
            nodes.append(self._create_safe_node(false_node_id, false_label))

            # Connect each condition to both TRUE and FALSE
            for cond_id in condition_nodes:
                nodes.append(self._create_safe_connection(cond_id, true_node_id, "True"))
                nodes.append(self._create_safe_connection(cond_id, false_node_id, "False"))

            # Create exit node
            exit_node_id = f"{or_block_id}_Exit"
            exit_label = "Merge"
            nodes.append(self._create_safe_node(exit_node_id, exit_label))

            # Connect TRUE and FALSE to exit
            nodes.append(self._create_safe_connection(true_node_id, exit_node_id))
            nodes.append(self._create_safe_connection(false_node_id, exit_node_id))

            self._add_debug(f"[OR_PROCESSOR] Successfully processed OR statement with {len(conditions)} conditions")
            return nodes, exit_node_id, consumed

        except Exception as e:
            self._add_debug(f"[OR_PROCESSOR] Error processing OR statement: {e}")
            return self._create_fallback_node(full_statement, current_node, node_counter, consumed)

    def _create_fallback_node(self, statement: str, current_node: str, node_counter: List[int], consumed: int) -> Tuple[
        List[str], str, int]:
        """Create a fallback simple node when OR processing fails"""
        node_id = f"N{node_counter[0]}"
        node_counter[0] += 1
        safe_label = self._sanitize_label(statement)
        node_content = self._create_safe_node(node_id, safe_label)

        nodes = []
        if current_node and current_node != "Start":
            connection = self._create_safe_connection(current_node, node_id)
            nodes.append(connection)
        nodes.append(node_content)

        return nodes, node_id, consumed

    def _sanitize_condition(self, condition: str) -> str:
        """Sanitize a condition for display"""
        condition = condition.strip()

        if condition.upper().endswith(' OR'):
            condition = condition[:-3].strip()

        if condition.upper() == 'FALSE':
            return "FALSE"
        elif condition.upper() == 'TRUE':
            return "TRUE"

        condition = re.sub(r'\s*=\s*', ' = ', condition)
        condition = re.sub(r'\s*<>\s*', ' <> ', condition)
        condition = re.sub(r'\s*<\s*', ' < ', condition)
        condition = re.sub(r'\s*<=\s*', ' <= ', condition)
        condition = re.sub(r'\s*>\s*', ' > ', condition)
        condition = re.sub(r'\s*>=\s*', ' >= ', condition)

        return self._sanitize_label(condition)

    def _sanitize_label(self, label: str) -> str:
        """Sanitize label for Mermaid syntax"""
        return MermaidSanitizer.sanitize_label(label)

    def _create_safe_node(self, node_id: str, label: str, node_type: str = "rectangle") -> str:
        """Create a safe Mermaid node with proper escaping"""
        return MermaidSanitizer.create_safe_node(node_id, label, node_type)

    def _create_safe_connection(self, from_node: str, to_node: str, label: str = "") -> str:
        """Create a safe Mermaid connection between nodes"""
        return MermaidSanitizer.create_safe_connection(from_node, to_node, label)