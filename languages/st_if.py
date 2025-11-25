import re
from typing import List, Tuple, Callable, Dict, Optional


class STIfProcessor:
    """ST IF statement processor - handles IF, ELSIF, ELSE conditions"""

    def __init__(self, main_processor):
        self.main_processor = main_processor
        self.debug = main_processor._add_debug
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for IF statement parsing"""
        self.patterns = {
            'if': re.compile(r'IF\s+(.+?)\s+THEN', re.IGNORECASE | re.DOTALL),
            'end_if': re.compile(r'END_IF', re.IGNORECASE),
            'else': re.compile(r'ELSE', re.IGNORECASE),
        }

    def process_if_statement(self, if_statement: str, entry_node: str, node_counter: List[int]) -> Tuple[
        List[str], str, int]:
        """Process IF statement and return nodes and end node"""
        self.debug(f"=== IF PROCESSOR START ===")
        self.debug(f"Processing IF statement: {if_statement[:100]}...")

        # Extract IF structure
        condition, then_code, else_code, total_consumed = self._extract_if_structure(if_statement)
        if not condition:
            self.debug("Failed to extract IF structure")
            return [], entry_node, 0

        self.debug(f"IF Condition: {condition}")
        self.debug(f"THEN Branch: {then_code[:50]}...")
        self.debug(f"ELSE Branch: {else_code[:50]}...")

        nodes = []

        # Create IF decision node
        if_node_id = f"N{node_counter[0]}"
        node_counter[0] += 1
        if_node = self.main_processor._create_safe_node(if_node_id, f"IF {condition}", "rhombus")
        self.debug(f"Created IF node: {if_node}")
        nodes.append(if_node)

        connection = self.main_processor._create_safe_connection(entry_node, if_node_id)
        self.debug(f"Created connection to IF: {connection}")
        nodes.append(connection)

        # Process THEN branch recursively
        self.debug(f"Processing THEN branch with code: {then_code[:50]}...")
        then_nodes = self.main_processor._parse_recursive(then_code, if_node_id, node_counter)
        nodes.extend(then_nodes)

        # Process ELSE branch if it exists
        if else_code.strip():
            self.debug(f"Processing ELSE branch with code: {else_code[:50]}...")
            else_nodes = self.main_processor._parse_recursive(else_code, if_node_id, node_counter)
            nodes.extend(else_nodes)

            # Create merge point
            merge_node = f"N{node_counter[0]}"
            node_counter[0] += 1
            merge_node_content = self.main_processor._create_safe_node(merge_node, "End IF")
            self.debug(f"Created merge node: {merge_node_content}")
            nodes.append(merge_node_content)

            # Connect branches to merge - only if they have content
            if then_nodes:
                # Find the last node in THEN branch
                last_then_node = self._find_last_node(then_nodes, if_node_id)
                if last_then_node:
                    then_to_merge = self.main_processor._create_safe_connection(last_then_node, merge_node)
                    self.debug(f"Created THEN to merge: {then_to_merge}")
                    nodes.append(then_to_merge)
                else:
                    # If THEN branch has no content, connect directly from IF node
                    then_to_merge = self.main_processor._create_safe_connection(if_node_id, merge_node, "Yes")
                    self.debug(f"Created direct THEN connection: {then_to_merge}")
                    nodes.append(then_to_merge)
            else:
                # If no THEN nodes, connect directly from IF node
                then_to_merge = self.main_processor._create_safe_connection(if_node_id, merge_node, "Yes")
                self.debug(f"Created direct THEN connection: {then_to_merge}")
                nodes.append(then_to_merge)

            if else_nodes:
                # Find the last node in ELSE branch
                last_else_node = self._find_last_node(else_nodes, if_node_id)
                if last_else_node:
                    else_to_merge = self.main_processor._create_safe_connection(last_else_node, merge_node)
                    self.debug(f"Created ELSE to merge: {else_to_merge}")
                    nodes.append(else_to_merge)
                else:
                    # If ELSE branch has no content, connect directly from IF node
                    else_to_merge = self.main_processor._create_safe_connection(if_node_id, merge_node, "No")
                    self.debug(f"Created direct ELSE connection: {else_to_merge}")
                    nodes.append(else_to_merge)
            else:
                # If no ELSE nodes, connect directly from IF node
                else_to_merge = self.main_processor._create_safe_connection(if_node_id, merge_node, "No")
                self.debug(f"Created direct ELSE connection: {else_to_merge}")
                nodes.append(else_to_merge)

            self.debug(f"=== IF PROCESSOR END (with ELSE) ===")
            return nodes, merge_node, total_consumed
        else:
            # No ELSE branch
            merge_node = f"N{node_counter[0]}"
            node_counter[0] += 1
            merge_node_content = self.main_processor._create_safe_node(merge_node, "End IF")
            self.debug(f"Created merge node: {merge_node_content}")
            nodes.append(merge_node_content)

            # Connect THEN branch to merge - only if it has content
            if then_nodes:
                last_then_node = self._find_last_node(then_nodes, if_node_id)
                if last_then_node:
                    then_to_merge = self.main_processor._create_safe_connection(last_then_node, merge_node)
                    self.debug(f"Created THEN to merge: {then_to_merge}")
                    nodes.append(then_to_merge)
                else:
                    # If THEN branch has no content, connect directly from IF node
                    then_to_merge = self.main_processor._create_safe_connection(if_node_id, merge_node, "Yes")
                    self.debug(f"Created direct THEN connection: {then_to_merge}")
                    nodes.append(then_to_merge)
            else:
                # If no THEN nodes, connect directly from IF node
                then_to_merge = self.main_processor._create_safe_connection(if_node_id, merge_node, "Yes")
                self.debug(f"Created direct THEN connection: {then_to_merge}")
                nodes.append(then_to_merge)

            # Connect NO branch directly from IF node
            no_connection = self.main_processor._create_safe_connection(if_node_id, merge_node, "No")
            self.debug(f"Created NO branch connection: {no_connection}")
            nodes.append(no_connection)

            self.debug(f"=== IF PROCESSOR END (no ELSE) ===")
            return nodes, merge_node, total_consumed

    def _find_last_node(self, nodes: List[str], exclude_node: str) -> Optional[str]:
        """Find the last node ID in a list of nodes, excluding the specified node"""
        for node_str in reversed(nodes):
            match = re.search(r'^(\w+)\[', node_str)
            if match and match.group(1) != exclude_node and not self.main_processor._is_empty_node(node_str):
                return match.group(1)
        return None

    def _extract_if_structure(self, code: str) -> Tuple[str, str, str, int]:
        """Extract IF condition, THEN branch, and ELSE branch"""
        # Find IF and THEN
        if_match = re.search(r'IF\s+(.+?)\s+THEN', code, re.IGNORECASE | re.DOTALL)
        if not if_match:
            return "", "", "", 0

        condition = if_match.group(1).strip()
        then_start = if_match.end()

        # Find END_IF
        end_if_pos = code.upper().find('END_IF')
        if end_if_pos == -1:
            return condition, code[then_start:], "", len(code)

        # Check for ELSE
        else_pos = code.upper().find('ELSE', then_start, end_if_pos)
        if else_pos != -1:
            then_code = code[then_start:else_pos].strip()
            else_code = code[else_pos + 4:end_if_pos].strip()
            return condition, then_code, else_code, end_if_pos + 6
        else:
            then_code = code[then_start:end_if_pos].strip()
            return condition, then_code, "", end_if_pos + 6