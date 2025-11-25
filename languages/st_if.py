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
        """Compile regex patterns for IF statement parsing"""
        self.patterns = {
            'if_start': re.compile(r'IF\s+(.+?)\s+THEN', re.IGNORECASE | re.DOTALL),
            'elsif': re.compile(r'ELSIF\s+(.+?)\s+THEN', re.IGNORECASE | re.DOTALL),
            'else': re.compile(r'ELSE', re.IGNORECASE),
            'end_if': re.compile(r'END_IF;?', re.IGNORECASE),
        }

    def process_if_statement(self, code: str, entry_node: str, node_counter: List[int]) -> Optional[
        Tuple[List[str], str, int]]:
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

        # Show content immediately after THEN for debugging
        then_content_preview = code[condition_end:min(condition_end + 100, len(code))].strip()
        self._add_debug(f"[IF] Content after THEN: {then_content_preview}...")

        # Step 2: Find the matching END_IF using simple search
        end_if_pos = self._find_matching_end_if_simple(code, condition_end)
        if end_if_pos == -1:
            self._add_debug("[IF] No matching END_IF found")
            return None

        total_consumed = end_if_pos
        self._add_debug(f"[IF] Total consumed: {total_consumed}")

        # Step 3: Parse the IF structure
        nodes = []

        # Create decision diamond node - CORRECT MERMAID DIAMOND SYNTAX
        decision_node_id = f"N{node_counter[0]}"
        node_counter[0] += 1
        decision_label = self._sanitize_label(if_condition)
        # Use diamond shape for decision node - Mermaid uses {id}{shape} syntax
        nodes.append(f"{decision_node_id}{{{decision_label}}}")  # This creates a diamond!

        # Connect entry node to decision node
        if entry_node and entry_node != "Start":
            nodes.append(self._create_safe_connection(entry_node, decision_node_id))

        # Step 4: Extract and parse the IF block content (between THEN and END_IF)
        if_block_content = code[condition_end:end_if_pos].strip()
        self._add_debug(f"[IF] Complete IF block content: {if_block_content}")
        self._add_debug(f"[IF] IF block content length: {len(if_block_content)}")

        # Step 5: Parse branches - IF creates exactly two paths: True and False
        branch_nodes, exit_node = self._parse_if_as_decision_diamond(if_block_content, decision_node_id, node_counter)
        nodes.extend(branch_nodes)

        self._add_debug(f"[IF] Successfully processed IF statement, returning {len(nodes)} nodes")
        return nodes, exit_node, total_consumed

    def _find_matching_end_if_simple(self, code: str, start_pos: int) -> int:
        """Simple and reliable END_IF detection using word boundaries"""
        self._add_debug(f"[IF] Simple END_IF search from position {start_pos}")

        # Look for END_IF with word boundaries
        end_if_pattern = re.compile(r'\bEND_IF\b;?', re.IGNORECASE)
        match = end_if_pattern.search(code, start_pos)

        if match:
            end_pos = match.end()
            self._add_debug(f"[IF] Found END_IF at position {match.start()}, returning {end_pos}")
            self._add_debug(f"[IF] Context: ...{code[max(0, match.start() - 20):min(len(code), match.end() + 20)]}...")
            return end_pos
        else:
            self._add_debug(f"[IF] No END_IF found after position {start_pos}")
            self._add_debug(f"[IF] Remaining code: {code[start_pos:min(start_pos + 100, len(code))]}")
            return -1

    def _parse_if_as_decision_diamond(self, if_block_content: str, decision_node: str, node_counter: List[int]) -> \
    Tuple[List[str], str]:
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

        # Connect both branches to merge node
        if true_exit:
            nodes.append(self._create_safe_connection(true_exit, merge_node_id))
            self._add_debug(f"[IF] Connected true exit {true_exit} to merge {merge_node_id}")
        else:
            # If no true branch content, connect decision directly to merge
            nodes.append(f"{decision_node} -->|YES| {merge_node_id}")
            self._add_debug(f"[IF] Connected decision {decision_node} to merge {merge_node_id} (YES)")

        if false_exit:
            nodes.append(self._create_safe_connection(false_exit, merge_node_id))
            self._add_debug(f"[IF] Connected false exit {false_exit} to merge {merge_node_id}")
        else:
            # If no false branch content, connect decision directly to merge
            nodes.append(f"{decision_node} -->|NO| {merge_node_id}")
            self._add_debug(f"[IF] Connected decision {decision_node} to merge {merge_node_id} (NO)")

        self._add_debug(f"[IF] Decision diamond completed with {len(nodes)} total nodes")
        return nodes, merge_node_id

    def _extract_true_false_branches(self, if_block_content: str) -> Tuple[str, str]:
        """Extract True branch (IF content) and False branch (ELSIF/ELSE combined)"""
        self._add_debug(f"[IF] Extracting true/false branches from: '{if_block_content}'")

        # Remove any trailing END_IF from the content first
        if_block_content = self._remove_trailing_end_if(if_block_content)

        # Find first ELSIF or ELSE
        first_elsif = self.patterns['elsif'].search(if_block_content)
        first_else = self.patterns['else'].search(if_block_content)

        self._add_debug(f"[IF] First ELSIF at: {first_elsif.start() if first_elsif else 'not found'}")
        self._add_debug(f"[IF] First ELSE at: {first_else.start() if first_else else 'not found'}")

        first_branch_pos = len(if_block_content)
        if first_elsif:
            first_branch_pos = min(first_branch_pos, first_elsif.start())
        if first_else:
            first_branch_pos = min(first_branch_pos, first_else.start())

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

    def _remove_trailing_end_if(self, content: str) -> str:
        """Remove any trailing END_IF from branch content"""
        # Look for END_IF at the end of the content
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

        # Replace ELSIF conditions with just the content
        while True:
            elsif_match = self.patterns['elsif'].search(simplified)
            if not elsif_match:
                break

            # Find the end of this ELSIF's content
            next_elsif = self.patterns['elsif'].search(simplified, elsif_match.end())
            next_else = self.patterns['else'].search(simplified, elsif_match.end())

            end_pos = len(simplified)
            if next_elsif:
                end_pos = min(end_pos, next_elsif.start())
            if next_else:
                end_pos = min(end_pos, next_else.start())

            # Extract just the content (after ELSIF condition)
            content = simplified[elsif_match.end():end_pos].strip()

            # Replace this ELSIF section with just the content
            simplified = simplified[:elsif_match.start()] + content + simplified[end_pos:]

        return self._remove_trailing_end_if(simplified.strip())

    def _process_branch(self, content: str, decision_node: str, node_counter: List[int], arrow_label: str) -> Tuple[
        List[str], Optional[str]]:
        """Process a single branch content"""
        nodes = []

        if content and content.strip():
            self._add_debug(f"[IF] Processing {arrow_label} branch content: '{content}'")

            # Process the branch content through main processor
            content_nodes = self.main_processor._parse_recursive(content, decision_node, node_counter)

            # Filter out empty nodes
            content_nodes = [node for node in content_nodes if not self.main_processor._is_empty_node(node)]
            nodes.extend(content_nodes)

            # Find the exit node from content processing
            exit_node = self._find_exit_node(content_nodes, decision_node)

            # Add arrow label to the first connection if it exists
            if content_nodes and content_nodes[0].startswith(f"{decision_node} -->"):
                first_conn = content_nodes[0]
                # Replace with labeled connection
                target_node = first_conn.split('-->')[1].strip().split(' ')[0]
                labeled_conn = f"{decision_node} -->|{arrow_label}| {target_node}"
                nodes[0] = labeled_conn

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