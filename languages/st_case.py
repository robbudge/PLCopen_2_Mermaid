import re
from typing import List, Tuple, Callable, Dict, Optional


class STCaseProcessor:
    """ST CASE statement processor - handles CASE...OF...END_CASE"""

    def __init__(self, main_processor):
        self.main_processor = main_processor
        self.debug = main_processor._add_debug
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for CASE statement parsing"""
        self.patterns = {
            'case': re.compile(r'CASE\s+(.+?)\s+OF', re.IGNORECASE | re.DOTALL),
            'end_case': re.compile(r'END_CASE', re.IGNORECASE),
            'case_branch': re.compile(r'(\w+(?:\.\w+)*)\s*:', re.IGNORECASE),
            'function_call': re.compile(r'(\w+)\s*\([^)]*\)', re.IGNORECASE),
            'assignment': re.compile(r'(\w+(?:\.\w+)*)\s*:=\s*(.+?);', re.IGNORECASE),
        }

    def process_case_statement(self, case_statement: str, entry_node: str, node_counter: List[int]) -> Tuple[
        List[str], str, int]:
        """Process CASE statement and return nodes and end node"""
        self.debug(f"[CASE] === CASE PROCESSOR START ===")
        self.debug(f"[CASE] Processing CASE statement: {case_statement[:100]}...")

        # Extract CASE expression
        case_match = self.patterns['case'].search(case_statement)
        if not case_match:
            self.debug("[CASE] Failed to extract CASE expression")
            return [], entry_node, 0

        case_expression = case_match.group(1).strip()
        self.debug(f"[CASE] CASE expression: {case_expression}")

        nodes = []

        # Create CASE decision node
        case_node_id = f"N{node_counter[0]}"
        node_counter[0] += 1
        case_node = self.main_processor._create_safe_node(case_node_id, f"CASE {case_expression}", "rhombus")
        self.debug(f"[CASE] Created CASE node: {case_node}")
        nodes.append(case_node)

        connection = self.main_processor._create_safe_connection(entry_node, case_node_id)
        self.debug(f"[CASE] Created connection to CASE: {connection}")
        nodes.append(connection)

        # Extract case content (find END_CASE)
        of_pos = case_match.end()
        end_case_pos = case_statement.upper().find('END_CASE')
        if end_case_pos == -1:
            self.debug("[CASE] No END_CASE found")
            return nodes, case_node_id, of_pos

        case_content = case_statement[of_pos:end_case_pos].strip()
        total_consumed = end_case_pos + 8  # "END_CASE" is 8 characters

        self.debug(f"[CASE] Raw CASE content: {case_content}")

        # Parse CASE branches using a more robust approach
        branch_ends = []
        remaining_content = case_content

        while remaining_content.strip():
            self.debug(f"[CASE] Remaining CASE content: {remaining_content[:100]}...")

            # Find the next case branch
            branch_match = self.patterns['case_branch'].search(remaining_content)
            if not branch_match:
                break

            branch_value = branch_match.group(1).strip()
            branch_start = branch_match.end()

            self.debug(f"[CASE] Found branch: {branch_value} at position {branch_start}")

            # Find the end of this branch (next branch or end of content)
            next_branch_match = self.patterns['case_branch'].search(remaining_content[branch_start:])
            if next_branch_match:
                branch_end = branch_start + next_branch_match.start()
                branch_code = remaining_content[branch_start:branch_end].strip()
                remaining_content = remaining_content[branch_end:].strip()
            else:
                branch_code = remaining_content[branch_start:].strip()
                remaining_content = ""

            # Clean up branch code - remove any trailing semicolons
            branch_code = branch_code.rstrip(';').strip()

            self.debug(f"[CASE] Case branch '{branch_value}': '{branch_code}'")

            # Handle the branch - this returns the end node of the branch
            branch_end_node = self._process_case_branch(branch_value, branch_code, case_node_id, node_counter, nodes)
            if branch_end_node:
                branch_ends.append(branch_end_node)

        # Create end node where all branches meet
        end_node = f"N{node_counter[0]}"
        node_counter[0] += 1
        end_node_content = self.main_processor._create_safe_node(end_node, "End CASE")
        self.debug(f"[CASE] Created CASE end node: {end_node_content}")
        nodes.append(end_node_content)

        # Connect all branch ends to the end node
        for branch_end in branch_ends:
            connection = self.main_processor._create_safe_connection(branch_end, end_node)
            self.debug(f"[CASE] Connecting branch end {branch_end} to CASE end: {connection}")
            nodes.append(connection)

        # If no branches were processed, connect CASE node directly to end
        if not branch_ends:
            connection = self.main_processor._create_safe_connection(case_node_id, end_node, "No Match")
            self.debug(f"[CASE] No branches found, connecting CASE to end: {connection}")
            nodes.append(connection)

        self.debug(f"[CASE] === CASE PROCESSOR END with {len(branch_ends)} branches ===")
        return nodes, end_node, total_consumed

    def _process_case_branch(self, branch_value: str, branch_code: str, case_node_id: str,
                             node_counter: List[int], nodes: List[str]) -> Optional[str]:
        """Process a single CASE branch and return its end node"""
        self.debug(f"[CASE] Processing CASE branch '{branch_value}': '{branch_code}'")

        # Handle empty branches
        if not branch_code or branch_code.isspace():
            self.debug(f"[CASE] Branch '{branch_value}' has no action")
            # For empty branches, create a "No Action" node and connect directly from CASE
            no_action_node = f"N{node_counter[0]}"
            node_counter[0] += 1
            no_action_content = self.main_processor._create_safe_node(no_action_node, "No Action")
            self.debug(f"[CASE] Created no action node: {no_action_content}")
            nodes.append(no_action_content)

            # Connect CASE node directly to no action node
            connection = self.main_processor._create_safe_connection(case_node_id, no_action_node, branch_value)
            self.debug(f"[CASE] Connected CASE to no action: {connection}")
            nodes.append(connection)

            return no_action_node

        # Process branch code directly to get the first content node
        first_content_node = None
        current_node = None
        remaining_code = branch_code.strip()

        while remaining_code and not first_content_node:
            self.debug(f"[CASE] Processing branch statement for first node: {remaining_code[:50]}...")

            # Try to extract a function call first (most common in CASE branches)
            func_match = self.patterns['function_call'].search(remaining_code)
            if func_match:
                func_call = func_match.group(0).strip()
                func_name = func_match.group(1).strip()
                consumed = func_match.end()

                self.debug(f"[CASE] Found function call: {func_call}")

                # Create function call node
                node_id = f"N{node_counter[0]}"
                node_counter[0] += 1
                node_content = self.main_processor._create_safe_node(node_id, f"Call {func_name}")
                self.debug(f"[CASE] Created function call node: {node_content}")
                nodes.append(node_content)

                first_content_node = node_id
                current_node = node_id
                remaining_code = remaining_code[consumed:].strip()

                # Skip any trailing semicolon
                if remaining_code.startswith(';'):
                    remaining_code = remaining_code[1:].strip()
                continue

            # Try to extract an assignment
            assign_match = self.patterns['assignment'].search(remaining_code)
            if assign_match:
                var = assign_match.group(1)
                value = assign_match.group(2)
                consumed = assign_match.end()

                self.debug(f"[CASE] Found assignment: {var} := {value}")

                # Create assignment node
                node_id = f"N{node_counter[0]}"
                node_counter[0] += 1
                safe_label = self.main_processor._sanitize_label(f"{var} := {value}")
                node_content = self.main_processor._create_safe_node(node_id, safe_label)
                self.debug(f"[CASE] Created assignment node: {node_content}")
                nodes.append(node_content)

                first_content_node = node_id
                current_node = node_id
                remaining_code = remaining_code[consumed:].strip()
                continue

            # If no patterns match, try to use the main processor's recursive parser as fallback
            self.debug(f"[CASE] No direct patterns matched, trying recursive parser for: {remaining_code}")
            fallback_nodes = self.main_processor._parse_recursive(remaining_code, case_node_id, node_counter)

            if fallback_nodes:
                nodes.extend(fallback_nodes)
                # Find the first content node from the fallback processing
                first_content_node = self._find_first_content_node(fallback_nodes, case_node_id)
                if first_content_node:
                    current_node = self._find_last_node(fallback_nodes, case_node_id) or first_content_node
                    remaining_code = ""
                else:
                    break
            else:
                self.debug("[CASE] No patterns matched and recursive parser found nothing, stopping")
                break

        # If we found a content node, connect CASE directly to it
        if first_content_node:
            connection = self.main_processor._create_safe_connection(case_node_id, first_content_node, branch_value)
            self.debug(f"[CASE] Connected CASE directly to content: {connection}")
            nodes.append(connection)

            # Process any remaining code in the branch
            if remaining_code.strip():
                self.debug(f"[CASE] Processing remaining branch code: {remaining_code}")
                remaining_nodes = self.main_processor._parse_recursive(remaining_code, current_node, node_counter)
                nodes.extend(remaining_nodes)
                # Update current_node to the end of the branch
                current_node = self._find_last_node(remaining_nodes, current_node) or current_node

            self.debug(f"[CASE] Branch '{branch_value}' ends at node: {current_node}")
            return current_node
        else:
            self.debug(f"[CASE] No content found for branch '{branch_value}', using CASE node as end")
            return case_node_id

    def _find_first_content_node(self, nodes: List[str], exclude_node: str) -> Optional[str]:
        """Find the first content node ID in a list of nodes, excluding the specified node"""
        for node_str in nodes:
            match = re.search(r'^(\w+)\[', node_str)
            if match and match.group(1) != exclude_node and not self.main_processor._is_empty_node(node_str):
                return match.group(1)
        return None

    def _find_last_node(self, nodes: List[str], exclude_node: str) -> Optional[str]:
        """Find the last node ID in a list of nodes, excluding the specified node"""
        for node_str in reversed(nodes):
            match = re.search(r'^(\w+)\[', node_str)
            if match and match.group(1) != exclude_node and not self.main_processor._is_empty_node(node_str):
                return match.group(1)
        return None