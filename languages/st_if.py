import re
from typing import List, Dict, Any, Tuple, Optional
from .base_processor import BaseLanguageProcessor


class STIfProcessor(BaseLanguageProcessor):
    """Processor for IF statements in Structured Text - Creates proper decision diamonds"""

    def __init__(self, main_processor):
        super().__init__()
        self.main_processor = main_processor
        self._compile_if_patterns()

    def can_process(self, language: str) -> bool:
        """Check if this processor can handle a specific language"""
        return False  # Main ST processor handles the delegation

    def generate_flowchart(self, code: str, pou_name: str) -> str:
        """Generate flowchart - not used directly, called through coordinator"""
        return f"%% IF processor should be called through main ST processor"

    def _compile_if_patterns(self):
        """Compile regex patterns for IF statement parsing with proper whitespace"""
        # Use word boundaries and whitespace to ensure exact keyword matching
        self.patterns = {
            'if_start': re.compile(r'\bIF\s+(.+?)\s+THEN\b', re.IGNORECASE | re.DOTALL),
            'elsif': re.compile(r'\bELSIF\s+(.+?)\s+THEN\b', re.IGNORECASE | re.DOTALL),
            'else': re.compile(r'\bELSE\b', re.IGNORECASE),
            'end_if': re.compile(r'\bEND_IF\b;?', re.IGNORECASE),
        }

    def process_if_statement(self, code: str, entry_node: str, node_counter: List[int]) -> Optional[Tuple[List[str], str, int]]:
        """Process a complete IF statement and return nodes, exit node, and consumed characters"""
        self._add_debug("[IF] Processing IF statement")
        self._add_debug(f"[IF] Input code: {code[:200]}...")

        # Step 1: Extract the IF condition (from IF to THEN)
        if_match = self.patterns['if_start'].match(code)
        if not if_match:
            self._add_debug("[IF] No IF condition found")
            return None

        if_condition = if_match.group(1).strip()
        condition_end = if_match.end()
        self._add_debug(f"[IF] Found IF condition: {if_condition}")
        self._add_debug(f"[IF] Condition ends at: {condition_end}")

        # Step 2: Find the matching END_IF using bracket counting for nested IFs
        end_if_pos = self._find_matching_end_if_with_nesting(code, condition_end)
        if end_if_pos == -1:
            self._add_debug("[IF] No matching END_IF found")
            return None

        total_consumed = end_if_pos
        self._add_debug(f"[IF] Total consumed: {total_consumed}")

        # Step 3: Parse the IF structure
        nodes = []

        # Create decision diamond node with proper "IF" label
        decision_node_id = f"N{node_counter[0]}"
        node_counter[0] += 1
        decision_label = self._sanitize_label(f"IF {if_condition}")  # Add "IF" prefix
        nodes.append(f"{decision_node_id}{{{decision_label}}}")  # This creates a diamond!

        # IMPORTANT: DO NOT create connection from entry_node to decision_node here
        # The main processor will handle this connection to avoid duplicates
        self._add_debug(f"[IF] Created decision node {decision_node_id}, main processor will handle connection from {entry_node}")

        # Step 4: Extract and parse the IF block content (between THEN and END_IF)
        if_block_content = code[condition_end:end_if_pos].strip()
        self._add_debug(f"[IF] Complete IF block content: {if_block_content}")
        self._add_debug(f"[IF] IF block content length: {len(if_block_content)}")

        # Step 5: Parse branches - IF creates exactly two paths: True and False
        branch_nodes, merge_node = self._parse_if_as_decision_diamond(if_block_content, decision_node_id, node_counter)
        nodes.extend(branch_nodes)

        # FIX: Return the merge node as the exit point for proper connection handling
        self._add_debug(f"[IF] Successfully processed IF statement, returning {len(nodes)} nodes with merge node: {merge_node}")
        return nodes, merge_node, total_consumed

    def _find_matching_end_if_with_nesting(self, code: str, start_pos: int) -> int:
        """Find matching END_IF accounting for nested IF statements"""
        self._add_debug(f"[IF] Finding END_IF with nesting support from position {start_pos}")

        pos = start_pos
        if_depth = 1  # Start with depth 1 since we already found one IF

        while pos < len(code):
            # Look for IF or END_IF with proper word boundaries
            if_pattern = re.compile(r'\bIF\b', re.IGNORECASE)
            end_if_pattern = re.compile(r'\bEND_IF\b;?', re.IGNORECASE)

            next_if = if_pattern.search(code, pos)
            next_end_if = end_if_pattern.search(code, pos)

            # Determine which comes first
            if_pos = next_if.start() if next_if else len(code)
            end_if_pos = next_end_if.start() if next_end_if else len(code)

            if if_pos < end_if_pos:
                # Found nested IF
                if_depth += 1
                self._add_debug(f"[IF] Found nested IF at {if_pos}, depth increased to {if_depth}")
                pos = if_pos + 2  # Move past this IF
            elif end_if_pos < len(code):
                # Found END_IF
                if_depth -= 1
                self._add_debug(f"[IF] Found END_IF at {end_if_pos}, depth decreased to {if_depth}")

                if if_depth == 0:
                    # This is the matching END_IF for our original IF
                    end_pos = next_end_if.end()
                    self._add_debug(f"[IF] Found matching END_IF at position {end_if_pos}, returning {end_pos}")
                    return end_pos
                pos = end_if_pos + 6  # Move past this END_IF
            else:
                # No more IF or END_IF found
                break

        self._add_debug(f"[IF] No matching END_IF found, final depth: {if_depth}")
        return -1

    def _parse_if_as_decision_diamond(self, if_block_content: str, decision_node: str, node_counter: List[int]) -> Tuple[List[str], str]:
        """Parse IF as a decision diamond with exactly two paths: True and False"""
        nodes = []

        self._add_debug(f"[IF] Parsing IF as decision diamond")
        self._add_debug(f"[IF] Input content: {if_block_content[:200]}...")

        # Extract True branch (IF content) and False branch (ELSIF/ELSE content)
        true_content, false_content = self._extract_true_false_branches(if_block_content)

        self._add_debug(f"[IF] True branch content: '{true_content}'")
        self._add_debug(f"[IF] False branch content: '{false_content}'")

        # Process True branch (YES path)
        true_nodes, true_exit = self._process_branch(true_content, decision_node, node_counter, "YES")
        nodes.extend(true_nodes)
        self._add_debug(f"[IF] True branch processed: {len(true_nodes)} nodes, exit: {true_exit}")

        # Process False branch (NO path)
        false_nodes, false_exit = self._process_branch(false_content, decision_node, node_counter, "NO")
        nodes.extend(false_nodes)
        self._add_debug(f"[IF] False branch processed: {len(false_nodes)} nodes, exit: {false_exit}")

        # Create merge node where both paths rejoin
        merge_node_id = f"N{node_counter[0]}"
        node_counter[0] += 1
        nodes.append(self._create_safe_node(merge_node_id, "Merge"))
        self._add_debug(f"[IF] Created merge node: {merge_node_id}")

        # Connect both branches to merge node - FIXED: Handle nested IF exits properly
        if true_exit and true_exit != merge_node_id:
            # Check if there's already a connection from true_exit to merge_node_id
            connection_exists = any(
                node.startswith(f"{true_exit} -->") and merge_node_id in node
                for node in nodes
            )
            if not connection_exists:
                nodes.append(self._create_safe_connection(true_exit, merge_node_id))
                self._add_debug(f"[IF] Connected true exit {true_exit} to merge {merge_node_id}")
        elif not true_exit:
            # If no true branch content, connect decision directly to merge with YES label
            nodes.append(f"{decision_node} -->|YES| {merge_node_id}")
            self._add_debug(f"[IF] Connected decision {decision_node} to merge {merge_node_id} (YES)")

        if false_exit and false_exit != merge_node_id:
            # Check if there's already a connection from false_exit to merge_node_id
            connection_exists = any(
                node.startswith(f"{false_exit} -->") and merge_node_id in node
                for node in nodes
            )
            if not connection_exists:
                nodes.append(self._create_safe_connection(false_exit, merge_node_id))
                self._add_debug(f"[IF] Connected false exit {false_exit} to merge {merge_node_id}")
        elif not false_exit:
            # If no false branch content, connect decision directly to merge with NO label
            nodes.append(f"{decision_node} -->|NO| {merge_node_id}")
            self._add_debug(f"[IF] Connected decision {decision_node} to merge {merge_node_id} (NO)")

        self._add_debug(f"[IF] Decision diamond completed with {len(nodes)} total nodes")
        return nodes, merge_node_id

    def _extract_true_false_branches(self, if_block_content: str) -> Tuple[str, str]:
        """Extract True branch (IF content) and False branch (ELSIF/ELSE content)"""
        self._add_debug(f"[IF] Extracting true/false branches from: '{if_block_content}'")

        # Remove any trailing END_IF from the content first
        if_block_content = self._remove_trailing_end_if(if_block_content)

        # Find first ELSIF or ELSE using bracket counting for nested IFs
        first_elsif_pos, first_else_pos = self._find_first_branch_with_nesting(if_block_content)

        self._add_debug(f"[IF] First ELSIF at: {first_elsif_pos if first_elsif_pos != -1 else 'not found'}")
        self._add_debug(f"[IF] First ELSE at: {first_else_pos if first_else_pos != -1 else 'not found'}")

        first_branch_pos = len(if_block_content)
        if first_elsif_pos != -1:
            first_branch_pos = min(first_branch_pos, first_elsif_pos)
        if first_else_pos != -1:
            first_branch_pos = min(first_branch_pos, first_else_pos)

        # True branch is content before first ELSIF/ELSE
        true_content = if_block_content[:first_branch_pos].strip()

        # False branch is all ELSIF and ELSE content combined
        false_content = if_block_content[first_branch_pos:].strip() if first_branch_pos < len(if_block_content) else ""

        self._add_debug(f"[IF] True branch position: 0 to {first_branch_pos}")
        self._add_debug(f"[IF] False branch position: {first_branch_pos} to end")

        # Clean up the false content - remove ELSIF/ELSE keywords
        if false_content:
            false_content = self._simplify_false_branch(false_content)

        return true_content, false_content

    def _find_first_branch_with_nesting(self, content: str) -> Tuple[int, int]:
        """Find first ELSIF or ELSE accounting for nested IF statements"""
        pos = 0
        if_depth = 0

        first_elsif_pos = -1
        first_else_pos = -1

        while pos < len(content):
            # Look for IF, END_IF, ELSIF, ELSE with proper word boundaries
            if_pattern = re.compile(r'\bIF\b', re.IGNORECASE)
            end_if_pattern = re.compile(r'\bEND_IF\b;?', re.IGNORECASE)
            elsif_pattern = re.compile(r'\bELSIF\b', re.IGNORECASE)
            else_pattern = re.compile(r'\bELSE\b', re.IGNORECASE)

            next_if = if_pattern.search(content, pos)
            next_end_if = end_if_pattern.search(content, pos)
            next_elsif = elsif_pattern.search(content, pos)
            next_else = else_pattern.search(content, pos)

            # Get positions
            positions = {
                'IF': next_if.start() if next_if else len(content),
                'END_IF': next_end_if.start() if next_end_if else len(content),
                'ELSIF': next_elsif.start() if next_elsif else len(content),
                'ELSE': next_else.start() if next_else else len(content),
            }

            # Find the next occurring keyword
            next_keyword = min(positions, key=positions.get)
            next_pos = positions[next_keyword]

            if next_pos == len(content):
                break  # No more keywords found

            if next_keyword == 'IF':
                if_depth += 1
                pos = next_pos + 2
            elif next_keyword == 'END_IF':
                if_depth -= 1
                pos = next_pos + 6
            elif next_keyword == 'ELSIF' and if_depth == 0 and first_elsif_pos == -1:
                first_elsif_pos = next_pos
                pos = next_pos + 5
            elif next_keyword == 'ELSE' and if_depth == 0 and first_else_pos == -1:
                first_else_pos = next_pos
                pos = next_pos + 4
            else:
                pos = next_pos + 1  # Move past this keyword

        return first_elsif_pos, first_else_pos

    def _remove_trailing_end_if(self, content: str) -> str:
        """Remove any trailing END_IF from branch content"""
        # Look for END_IF at the end of the content with word boundary
        end_if_pattern = re.compile(r'\bEND_IF\b;?\s*$', re.IGNORECASE)
        match = end_if_pattern.search(content)

        if match:
            self._add_debug(f"[IF] Removing trailing END_IF from content")
            return content[:match.start()].strip()
        return content

    def _simplify_false_branch(self, false_content: str) -> str:
        """Simplify ELSIF/ELSE branches into a single False branch representation"""
        if not false_content:
            return ""

        # If it's just an ELSE, return the content directly
        else_match = self.patterns['else'].match(false_content)
        if else_match:
            content = false_content[else_match.end():].strip()
            return self._remove_trailing_end_if(content)

        # For ELSIF branches, remove the ELSIF conditions and keep the content
        simplified = false_content

        # Replace ELSIF conditions with just the content (accounting for nesting)
        pos = 0
        while pos < len(simplified):
            elsif_match = self.patterns['elsif'].search(simplified, pos)
            if not elsif_match:
                break

            # Find the end of this ELSIF's content using bracket counting
            content_end = self._find_branch_content_end(simplified, elsif_match.end())

            # Extract just the content (after ELSIF condition)
            content = simplified[elsif_match.end():content_end].strip()

            # Replace this ELSIF section with just the content
            simplified = simplified[:elsif_match.start()] + content + simplified[content_end:]
            pos = elsif_match.start() + len(content)  # Continue from after the inserted content

        return self._remove_trailing_end_if(simplified.strip())

    def _find_branch_content_end(self, content: str, start_pos: int) -> int:
        """Find the end of branch content accounting for nested IFs"""
        pos = start_pos
        if_depth = 0

        while pos < len(content):
            # Look for IF, END_IF, ELSIF, ELSE with proper word boundaries
            if_pattern = re.compile(r'\bIF\b', re.IGNORECASE)
            end_if_pattern = re.compile(r'\bEND_IF\b;?', re.IGNORECASE)
            elsif_pattern = re.compile(r'\bELSIF\b', re.IGNORECASE)
            else_pattern = re.compile(r'\bELSE\b', re.IGNORECASE)

            next_if = if_pattern.search(content, pos)
            next_end_if = end_if_pattern.search(content, pos)
            next_elsif = elsif_pattern.search(content, pos)
            next_else = else_pattern.search(content, pos)

            # Get positions
            positions = {
                'IF': next_if.start() if next_if else len(content),
                'END_IF': next_end_if.start() if next_end_if else len(content),
                'ELSIF': next_elsif.start() if next_elsif else len(content),
                'ELSE': next_else.start() if next_else else len(content),
            }

            # Find the next occurring keyword
            next_keyword = min(positions, key=positions.get)
            next_pos = positions[next_keyword]

            if next_pos == len(content):
                return len(content)  # End of content

            if next_keyword == 'IF':
                if_depth += 1
                pos = next_pos + 2
            elif next_keyword == 'END_IF':
                if if_depth == 0:
                    # Found the end of this branch
                    return next_pos
                if_depth -= 1
                pos = next_pos + 6
            elif (next_keyword == 'ELSIF' or next_keyword == 'ELSE') and if_depth == 0:
                # Found next branch at same level
                return next_pos
            else:
                pos = next_pos + 1

        return len(content)

    def _process_branch(self, content: str, decision_node: str, node_counter: List[int], arrow_label: str) -> Tuple[List[str], Optional[str]]:
        """Process a single branch content - FIXED to handle nested IFs and proper arrow labels"""
        nodes = []

        if content and content.strip():
            self._add_debug(f"[IF] Processing {arrow_label} branch content: '{content}'")

            # Process the branch content through main processor with in_if_branch=True
            # This prevents the main processor from creating connections (we'll add labeled ones)
            content_nodes = self.main_processor._parse_recursive(content, decision_node, node_counter, in_if_branch=True)

            # Filter out any connections that might have been created (they shouldn't be now)
            content_nodes = [node for node in content_nodes if not node.strip().startswith(f"{decision_node} -->")]

            # Filter out empty nodes
            content_nodes = [node for node in content_nodes if not self.main_processor._is_empty_node(node)]

            # Find the exit node from content processing
            exit_node = self._find_exit_node(content_nodes, decision_node)

            # Add the labeled connection from decision node to first content node
            if content_nodes:
                # Find the first actual node in the branch to connect to
                first_target_node = None
                for node in content_nodes:
                    if '-->' not in node and ('[' in node or '{' in node):
                        # Look for both regular nodes [label] and decision nodes {label}
                        match = re.match(r'^(\w+)[\[\{]', node)
                        if match:
                            first_target_node = match.group(1)
                            break

                if first_target_node:
                    # Create the labeled connection
                    labeled_conn = f"{decision_node} -->|{arrow_label}| {first_target_node}"
                    nodes.append(labeled_conn)
                    self._add_debug(f"[IF] Created {arrow_label} connection: {labeled_conn}")

                # Add all content nodes (they should have their internal connections already)
                nodes.extend(content_nodes)

                # DEBUG: Check if we have proper connections between nodes in this branch
                self._add_debug(f"[IF] Branch nodes debug:")
                for i, node in enumerate(nodes):
                    self._add_debug(f"[IF]   Node {i}: {node}")
            else:
                # No content nodes - this branch is empty but we still need the labeled connection
                self._add_debug(f"[IF] {arrow_label} branch has no content nodes")

            return nodes, exit_node
        else:
            # Empty branch - no processing needed
            self._add_debug(f"[IF] {arrow_label} branch is empty")
            return nodes, None

    def _find_exit_node(self, nodes: List[str], default_node: str) -> str:
        """Find the exit node from a list of processed nodes"""
        if not nodes:
            return default_node

        # Look for the last node that's not a connection
        for node in reversed(nodes):
            if '-->' not in node and '[' in node:
                # Extract node ID from node definition like "N1[Label]"
                match = re.match(r'^(\w+)\[', node)
                if match:
                    return match.group(1)

        return default_node