import re
from typing import List, Dict, Any, Tuple, Optional
from .base_processor import BaseLanguageProcessor
from .st_if import STIfProcessor
from .st_case import STCaseProcessor
from .st_sel import STSelProcessor


class STProcessor(BaseLanguageProcessor):
    """Main ST processor that coordinates specialized processors"""

    def __init__(self):
        super().__init__()
        self._compile_patterns()

        # Initialize specialized processors with self as coordinator
        self.if_processor = STIfProcessor(self)
        self.case_processor = STCaseProcessor(self)
        self.sel_processor = STSelProcessor(self)

        self._add_debug("[MAIN] ST Processor initialized with specialized processors")

    def _compile_patterns(self):
        """Compile regex patterns for basic ST parsing"""
        self.patterns = {
            'assignment': re.compile(r'(\w+(?:\.\w+)*)\s*:=\s*(.+?);', re.IGNORECASE),
            'function_call': re.compile(r'(\w+)\s*\([^)]*\)', re.IGNORECASE),
            'comment_single': re.compile(r'//.*', re.IGNORECASE),
            'comment_multi': re.compile(r'\(\*.*?\*\)', re.DOTALL),
            'pragma': re.compile(r'{\s*.+?\s*}', re.DOTALL),
        }

    def can_process(self, language: str) -> bool:
        """Check if this processor can handle ST language"""
        return language.upper() in ['ST', 'STRUCTURED TEXT', 'UNKNOWN']

    def generate_flowchart(self, code: str, pou_name: str) -> str:
        """Generate Mermaid flowchart from ST code"""
        self.clear_debug()
        self._add_debug(f"[MAIN] Generating flowchart for POU: {pou_name}")

        clean_code = self._clean_code(code)
        if not clean_code:
            return f"%% No ST code found for POU {pou_name}"

        self._add_debug(f"[MAIN] Cleaned code preview: {clean_code[:200]}...")

        # Generate flowchart
        mermaid_lines = ["flowchart TD"]
        node_counter = [0]

        # Start with Start node
        nodes = [self._create_safe_node("Start", "Start")]
        current_node = "Start"

        # Parse the code
        parsed_nodes = self._parse_recursive(clean_code, current_node, node_counter)
        nodes.extend(parsed_nodes)

        # Add final End node
        end_nodes = self._add_final_end_node(nodes, node_counter)
        nodes.extend(end_nodes)

        # Debug: Show all nodes before final output
        self._debug_node_list(nodes)

        mermaid_lines.extend(nodes)

        result = '\n'.join(mermaid_lines)

        # Validate the output
        validation_errors = self._validate_mermaid_output(result)
        if validation_errors:
            self._add_debug(f"[MAIN] Mermaid validation errors: {validation_errors}")
            for error in validation_errors:
                result += f"\n%% ERROR: {error}"

        self._add_debug(f"[MAIN] Generated flowchart with {len(nodes)} nodes")
        return result

    def _debug_node_list(self, nodes: List[str]):
        """Debug method to show all nodes and their content"""
        self._add_debug("[MAIN] === NODE LIST DEBUG ===")
        for i, node in enumerate(nodes):
            self._add_debug(f"[MAIN] Node {i}: {node}")
        self._add_debug("[MAIN] === END NODE LIST DEBUG ===")

    def _clean_code(self, code: str) -> str:
        """Clean and extract ST code"""
        if not code:
            return ""

        self._add_debug("[MAIN] Cleaning ST code")

        # Decode XML entities
        code = self._decode_xml_entities(code)

        # Remove XML tags if present
        if '<' in code and '>' in code:
            self._add_debug("[MAIN] Detected XML-like content, stripping tags")
            code = re.sub(r'<[^>]+>', ' ', code)
            code = re.sub(r'<!\[CDATA\[(.*?)\]\]>', r'\1', code, flags=re.DOTALL)

        # Clean up whitespace
        code = re.sub(r'\s+', ' ', code)

        # Remove comments and pragmas
        code = self.patterns['comment_single'].sub('', code)
        code = self.patterns['comment_multi'].sub('', code)
        code = self.patterns['pragma'].sub('', code)

        return code.strip()

    def _decode_xml_entities(self, text: str) -> str:
        """Decode common XML entities in ST code"""
        replacements = {
            '&lt;': '<',
            '&gt;': '>',
            '&amp;': '&',
            '&quot;': '"',
            '&apos;': "'"
        }

        for entity, replacement in replacements.items():
            text = text.replace(entity, replacement)

        return text

    def _parse_recursive(self, code: str, current_node: str, node_counter: List[int]) -> List[str]:
        """Main recursive parsing routine - processes statements until empty"""
        nodes = []
        remaining_code = code.strip()

        while remaining_code:
            self._add_debug(f"[MAIN] Processing: {remaining_code[:100]}...")

            # Check for recursive constructs first (IF, CASE, SEL)
            if remaining_code.upper().startswith('IF '):
                self._add_debug("[MAIN] Found IF statement - delegating to IF processor")
                try:
                    result = self.if_processor.process_if_statement(remaining_code, current_node, node_counter)
                    if result:
                        if_nodes, next_node, consumed = result
                        self._add_debug(
                            f"[MAIN] IF processor returned {len(if_nodes)} nodes, next_node: {next_node}, consumed: {consumed}")

                        # Filter out any empty nodes from the IF processor
                        if_nodes = [node for node in if_nodes if not self._is_empty_node(node)]
                        nodes.extend(if_nodes)

                        current_node = next_node
                        remaining_code = remaining_code[consumed:].strip()
                        continue
                    else:
                        self._add_debug("[MAIN] IF processor returned no result")
                except Exception as e:
                    self._add_debug(f"[MAIN] Error in IF processor: {e}")
                    # Fall through to terminal statement processing

            elif remaining_code.upper().startswith('CASE '):
                self._add_debug("[MAIN] Found CASE statement - delegating to CASE processor")
                try:
                    result = self.case_processor.process_case_statement(remaining_code, current_node, node_counter)
                    if result:
                        case_nodes, next_node, consumed = result
                        self._add_debug(
                            f"[MAIN] CASE processor returned {len(case_nodes)} nodes, next_node: {next_node}, consumed: {consumed}")

                        # Filter out any empty nodes from the CASE processor
                        case_nodes = [node for node in case_nodes if not self._is_empty_node(node)]
                        nodes.extend(case_nodes)

                        current_node = next_node
                        remaining_code = remaining_code[consumed:].strip()
                        continue
                    else:
                        self._add_debug("[MAIN] CASE processor returned no result")
                except Exception as e:
                    self._add_debug(f"[MAIN] Error in CASE processor: {e}")
                    # Fall through to terminal statement processing

            elif remaining_code.upper().startswith('SEL('):
                self._add_debug("[MAIN] Found SEL function - delegating to SEL processor")
                try:
                    result = self.sel_processor.process_sel_function(remaining_code, current_node, node_counter)
                    if result:
                        sel_nodes, next_node, consumed = result
                        self._add_debug(
                            f"[MAIN] SEL processor returned {len(sel_nodes)} nodes, next_node: {next_node}, consumed: {consumed}")

                        # Filter out any empty nodes from the SEL processor
                        sel_nodes = [node for node in sel_nodes if not self._is_empty_node(node)]
                        nodes.extend(sel_nodes)

                        current_node = next_node
                        remaining_code = remaining_code[consumed:].strip()
                        continue
                    else:
                        self._add_debug("[MAIN] SEL processor returned no result")
                except Exception as e:
                    self._add_debug(f"[MAIN] Error in SEL processor: {e}")
                    # Fall through to terminal statement processing

            # Terminal statements (non-recursive) - assignments and function calls
            statement, consumed = self._extract_terminal_statement(remaining_code)
            if statement:
                self._add_debug(f"[MAIN] Found terminal statement: {statement}")
                node_id = f"N{node_counter[0]}"
                node_counter[0] += 1

                # Create appropriate node type
                node_content = self._create_terminal_node(statement, node_id)

                # Only add the node if it's not empty
                if not self._is_empty_node(node_content):
                    self._add_debug(f"[MAIN] Created terminal node {node_id}: {node_content}")
                    nodes.append(node_content)

                    if current_node and current_node != "Start":
                        connection = self._create_safe_connection(current_node, node_id)
                        self._add_debug(f"[MAIN] Created connection: {connection}")
                        nodes.append(connection)

                    current_node = node_id
                else:
                    self._add_debug(f"[MAIN] Skipped empty node: {node_content}")
                    # Don't update current_node since we skipped this node

                remaining_code = remaining_code[consumed:].strip()
            else:
                self._add_debug("[MAIN] No recognizable statements found, stopping")
                break

        return nodes

    def _is_empty_node(self, node_content: str) -> bool:
        """Check if a node is empty (has no content)"""
        # Check for empty nodes like "N24[]"
        if '[]' in node_content:
            return True

        # Check for nodes with only whitespace in the label
        match = re.search(r'^\w+\[(.+)\]$', node_content)
        if match:
            label_content = match.group(1)
            # If the label is empty or just special characters, consider it empty
            if not label_content.strip() or label_content.isspace():
                return True

        return False

    def _add_final_end_node(self, nodes: List[str], node_counter: List[int]) -> List[str]:
        """Add final End node and connect last node to it"""
        end_nodes = []

        if nodes:
            # Find the last node that's not "Start" or "End"
            last_node_id = None
            for node in reversed(nodes):
                # Look for node definitions like "N0[Label]" or "Start[Start]"
                match = re.search(r'^(\w+)\[', node)
                if match:
                    node_id = match.group(1)
                    if node_id not in ["Start", "End"] and not self._is_empty_node(node):
                        last_node_id = node_id
                        break

            if last_node_id:
                connection = self._create_safe_connection(last_node_id, "End")
                self._add_debug(f"[MAIN] Creating final connection: {connection}")
                end_nodes.append(connection)

        end_node = self._create_safe_node("End", "End")
        self._add_debug(f"[MAIN] Creating End node: {end_node}")
        end_nodes.append(end_node)
        return end_nodes

    def _extract_terminal_statement(self, code: str) -> Tuple[Optional[str], int]:
        """Extract a single terminal statement (assignment or function call)"""
        # Look for the next semicolon first (most common case)
        semi_pos = code.find(';')
        if semi_pos != -1:
            statement = code[:semi_pos + 1].strip()

            # Skip empty statements (just a semicolon)
            if statement == ';':
                self._add_debug("[MAIN] Skipping empty statement (semicolon only)")
                return None, semi_pos + 1

            return statement, semi_pos + 1

        # If no semicolon found, look for function calls without semicolons
        func_match = self.patterns['function_call'].search(code)
        if func_match:
            func_call = func_match.group(0).strip()
            consumed = func_match.end()
            self._add_debug(f"[MAIN] Found function call without semicolon: {func_call}")
            return func_call, consumed

        # No statements found
        self._add_debug("[MAIN] No terminal statements found (no semicolon or function call)")
        return None, 0

    def _create_terminal_node(self, statement: str, node_id: str) -> str:
        """Create a node for terminal statements (assignments or function calls)"""
        statement_upper = statement.upper().strip()

        # Check for assignment
        assign_match = self.patterns['assignment'].search(statement)
        if assign_match:
            var = assign_match.group(1)
            value = assign_match.group(2)
            if value.endswith(';'):
                value = value[:-1].strip()
            safe_label = self._sanitize_label(f"{var} := {value}")
            return self._create_safe_node(node_id, safe_label)

        # Check for function call (with or without semicolon)
        func_match = self.patterns['function_call'].search(statement)
        if func_match:
            func_name = func_match.group(1)
            safe_label = self._sanitize_label(f"Call {func_name}")
            return self._create_safe_node(node_id, safe_label)

        # Check if this is just a semicolon (should have been filtered above)
        if statement.strip() == ';':
            self._add_debug(f"[MAIN] WARNING: Creating empty node for semicolon: {node_id}")
            return self._create_safe_node(node_id, "")  # This creates the problematic empty node

        # Generic statement (fallback)
        clean_stmt = statement[:-1].strip() if statement.endswith(';') else statement.strip()
        safe_label = self._sanitize_label(clean_stmt)
        return self._create_safe_node(node_id, safe_label)