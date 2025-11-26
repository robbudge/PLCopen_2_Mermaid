import re
from typing import List, Dict, Any, Tuple, Optional
from .base_processor import BaseLanguageProcessor
from .st_if import STIfProcessor
from .st_case import STCaseProcessor
from .st_sel import STSelProcessor
from .sanitizer import MermaidSanitizer


class STProcessor(BaseLanguageProcessor):
    """Main ST processor that coordinates specialized processors"""

    def __init__(self):
        super().__init__()
        self._compile_patterns()
        self._line_counter = 0  # Add line counter for debugging

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
            'xml_tag': re.compile(r'<[^>]+>', re.DOTALL),
            'st_comparison': re.compile(r'\w+\s*[<>]=?\s*\w+'),
        }

    def can_process(self, language: str) -> bool:
        """Check if this processor can handle ST language"""
        return language.upper() in ['ST', 'STRUCTURED TEXT', 'UNKNOWN']

    def generate_flowchart(self, code: str, pou_name: str) -> str:
        """Generate Mermaid flowchart from ST code"""
        self.clear_debug()
        self._add_debug(f"[MAIN] Generating flowchart for POU: {pou_name}")
        self._line_counter = 0  # Reset line counter for each new flowchart

        clean_code = self._clean_code(code)
        if not clean_code:
            return f"%% No ST code found for POU {pou_name}"

        # Generate flowchart
        mermaid_lines = ["flowchart TD"]
        node_counter = [0]

        # Start with Start node
        nodes = [self._create_safe_node("Start", "Start")]
        current_node = "Start"

        # Parse the code - FIXED: Use exit_node tracking
        parsed_nodes = self._parse_recursive(clean_code, current_node, node_counter)
        nodes.extend(parsed_nodes)

        # Add final End node
        end_nodes = self._add_final_end_node(nodes, node_counter)
        nodes.extend(end_nodes)

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

    def _clean_code(self, code: str) -> str:
        """Clean and extract ST code"""
        if not code:
            return ""

        self._add_debug("[MAIN] Cleaning ST code")

        # Check for XML entities before decoding
        xml_entities_found = False
        if '&lt;' in code or '&gt;' in code:
            xml_entities_found = True
            self._add_debug("[MAIN] XML entities detected - performing decoding")

        # Decode XML entities
        if xml_entities_found:
            code = self._decode_xml_entities(code)

        # Remove XML tags if present
        code = self._remove_only_real_xml_tags(code)

        # Careful whitespace handling
        code = re.sub(r'[ \t]+', ' ', code)
        code = re.sub(r'[ \t]*\n[ \t]*', '\n', code)

        # Remove comments and pragmas
        code = self.patterns['comment_single'].sub('', code)
        code = self.patterns['comment_multi'].sub('', code)
        code = self.patterns['pragma'].sub('', code)

        return code.strip()

    def _remove_only_real_xml_tags(self, code: str) -> str:
        """Remove only actual XML tags, not ST comparison operations"""
        # Look for patterns that are definitely XML tags
        xml_tag_patterns = [
            r'<[A-Za-z][A-Za-z0-9]*[^>]*>',
            r'</[A-Za-z][A-Za-z0-9]*>',
            r'<![A-Za-z][^>]*>',
            r'<\?[A-Za-z][^>]*\?>',
        ]

        # Find all potential XML tags
        potential_tags = re.findall(r'<[^>]+>', code)
        real_xml_tags = []

        for tag in potential_tags:
            # Check if this looks like a real XML tag
            is_real_xml = any(re.match(pattern, tag) for pattern in xml_tag_patterns)

            # Check if this looks like an ST comparison operation
            looks_like_st_comparison = (
                    re.search(r'\w+\s*[<>]=?\s*\w+', tag) and
                    not re.search(r'[A-Za-z]="[^"]*"', tag) and
                    not re.search(r'</?[A-Za-z]', tag)
            )

            if is_real_xml:
                real_xml_tags.append(tag)
            elif not looks_like_st_comparison:
                # If we're not sure, preserve it
                self._add_debug(f"[MAIN] Uncertain - preserving as ST logic: {tag}")

        # Remove only the real XML tags
        for tag in real_xml_tags:
            code = code.replace(tag, ' ')

        self._add_debug(f"[MAIN] Removed {len(real_xml_tags)} real XML tags")

        return code

    def _decode_xml_entities(self, text: str) -> str:
        """Decode common XML entities in ST code"""
        replacements = {
            '&lt;': '<', '&gt;': '>', '&amp;': '&', '&quot;': '"', '&apos;': "'",
            '&nbsp;': ' ', '&#60;': '<', '&#62;': '>', '&#38;': '&', '&#34;': '"', '&#39;': "'",
        }

        for entity, replacement in replacements.items():
            if entity in text:
                text = text.replace(entity, replacement)

        # Handle hex entities
        hex_entities = re.findall(r'&#x[0-9a-fA-F]+;', text)
        for entity in hex_entities:
            try:
                hex_val = entity[3:-1]
                char_code = int(hex_val, 16)
                if char_code < 128:
                    text = text.replace(entity, chr(char_code))
            except ValueError:
                pass

        return text

    def _parse_recursive(self, code: str, current_node: str, node_counter: List[int], in_if_branch: bool = False) -> \
            List[str]:
        """Main recursive parsing routine - FIXED to handle nested structure exit nodes"""
        nodes = []
        remaining_code = code.strip()

        # FIX: Track the current exit node - this is key!
        exit_node = current_node

        while remaining_code:
            self._line_counter += 1
            self._add_debug(f"[MAIN] Line {self._line_counter}: Processing: {remaining_code[:100]}...")
            self._add_debug(f"[MAIN] Current exit_node: {exit_node}")

            # Check for IF statements first
            if_match = self._find_if_statement(remaining_code)
            if if_match:
                self._add_debug("[MAIN] Found IF statement - delegating to IF processor")
                try:
                    result = self.if_processor.process_if_statement(remaining_code, exit_node, node_counter)
                    if result:
                        if_nodes, next_exit_node, consumed = result
                        self._add_debug(
                            f"[MAIN] IF processor returned {len(if_nodes)} nodes, next_exit_node: {next_exit_node}, consumed: {consumed}")

                        # FIX: Always connect current exit node to first IF node if needed
                        if exit_node and exit_node != "Start" and if_nodes:
                            first_if_node = self._find_first_decision_node(if_nodes)
                            if first_if_node:
                                # Check if connection already exists
                                connection_exists = any(
                                    node.startswith(f"{exit_node} -->") and first_if_node in node
                                    for node in if_nodes
                                )
                                if not connection_exists:
                                    connection = self._create_safe_connection(exit_node, first_if_node)
                                    nodes.append(connection)
                                    self._add_debug(f"[MAIN] Added connection to IF decision: {connection}")

                        nodes.extend(if_nodes)
                        exit_node = next_exit_node  # FIX: Update exit node to the merge node from IF
                        remaining_code = remaining_code[consumed:].strip()
                        continue
                    else:
                        self._add_debug("[MAIN] IF processor returned no result")
                except Exception as e:
                    self._add_debug(f"[MAIN] Error in IF processor: {e}")

            # Check for CASE statements
            case_match = self._find_case_statement(remaining_code)
            if case_match:
                self._add_debug("[MAIN] Found CASE statement - delegating to CASE processor")
                try:
                    result = self.case_processor.process_case_statement(remaining_code, exit_node, node_counter)
                    if result:
                        case_nodes, next_exit_node, consumed = result
                        self._add_debug(
                            f"[MAIN] CASE processor returned {len(case_nodes)} nodes, next_exit_node: {next_exit_node}, consumed: {consumed}")

                        if exit_node and exit_node != "Start" and case_nodes:
                            first_case_node = self._find_first_decision_node(case_nodes)
                            if first_case_node:
                                connection = self._create_safe_connection(exit_node, first_case_node)
                                nodes.append(connection)
                                self._add_debug(f"[MAIN] Added connection to CASE decision: {connection}")

                        nodes.extend(case_nodes)
                        exit_node = next_exit_node  # FIX: Update exit node to the merge node from CASE
                        remaining_code = remaining_code[consumed:].strip()
                        continue
                    else:
                        self._add_debug("[MAIN] CASE processor returned no result")
                except Exception as e:
                    self._add_debug(f"[MAIN] Error in CASE processor: {e}")

            # Check for MAX statements in assignments
            max_match = self._find_max_statement(remaining_code)
            if max_match:
                self._add_debug("[MAIN] Found MAX function in assignment - showing complete assignment")
                # MAX statements are handled in _create_terminal_node, just continue with normal processing

            # Check for SEL functions
            if remaining_code.upper().startswith('SEL('):
                self._add_debug("[MAIN] Found SEL function - delegating to SEL processor")
                try:
                    result = self.sel_processor.process_sel_function(remaining_code, exit_node, node_counter)
                    if result:
                        sel_nodes, next_exit_node, consumed = result
                        self._add_debug(
                            f"[MAIN] SEL processor returned {len(sel_nodes)} nodes, next_exit_node: {next_exit_node}, consumed: {consumed}")

                        nodes.extend(sel_nodes)
                        exit_node = next_exit_node  # FIX: Update exit node
                        remaining_code = remaining_code[consumed:].strip()
                        continue
                    else:
                        self._add_debug("[MAIN] SEL processor returned no result")
                except Exception as e:
                    self._add_debug(f"[MAIN] Error in SEL processor: {e}")

            # Terminal statements (assignments and function calls)
            statement, consumed = self._extract_terminal_statement(remaining_code)
            if statement:
                self._add_debug(f"[MAIN] Found terminal statement: {statement}")
                node_id = f"N{node_counter[0]}"
                node_counter[0] += 1

                node_content = self._create_terminal_node(statement, node_id)

                if not self._is_empty_node(node_content):
                    self._add_debug(f"[MAIN] Created terminal node {node_id}: {node_content}")
                    nodes.append(node_content)

                    # FIX: Always connect from current exit_node, not current_node
                    if exit_node and exit_node != "Start":
                        connection = self._create_safe_connection(exit_node, node_id)
                        self._add_debug(f"[MAIN] Created connection: {connection}")
                        nodes.append(connection)

                    exit_node = node_id  # FIX: Update exit node to this new node
                else:
                    self._add_debug(f"[MAIN] Skipped empty node: {node_content}")

                remaining_code = remaining_code[consumed:].strip()
            else:
                self._add_debug("[MAIN] No recognizable statements found, stopping")
                break

        return nodes

    def _find_if_statement(self, code: str) -> bool:
        """Check if code starts with an IF statement"""
        # Simple check for IF keyword at beginning
        return code.upper().startswith('IF ')

    def _find_case_statement(self, code: str) -> bool:
        """Check if code starts with a CASE statement"""
        # Simple check for CASE keyword at beginning
        return code.upper().startswith('CASE ')

    def _find_max_statement(self, code: str) -> bool:
        """Check if code contains a MAX function call in assignment"""
        # Look for MAX function calls in assignments (with or without space after MAX)
        pattern = r'\w+(?:\.\w+)*\s*:=\s*MAX\s*\([^;]*\)\s*;'
        match = re.search(pattern, code, re.IGNORECASE)
        if match:
            self._add_debug(f"[MAIN] Detected MAX assignment: {match.group(0)[:50]}...")
            return True
        return False

    def _find_first_decision_node(self, nodes: List[str]) -> Optional[str]:
        """Find the first decision node in a list of nodes"""
        for node in nodes:
            if '{' in node and '}' in node:
                match = re.match(r'^(\w+)\{', node)
                if match:
                    return match.group(1)
        return None

    def _is_empty_node(self, node_content: str) -> bool:
        """Check if a node is empty (has no content)"""
        if '[]' in node_content:
            return True

        match = re.search(r'^\w+\[(.+)\]$', node_content)
        if match:
            label_content = match.group(1)
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
        # Look for the next semicolon first
        semi_pos = code.find(';')
        if semi_pos != -1:
            statement = code[:semi_pos + 1].strip()

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
        # Check for assignment
        assign_match = self.patterns['assignment'].search(statement)
        if assign_match:
            var = assign_match.group(1)
            value = assign_match.group(2)
            if value.endswith(';'):
                value = value[:-1].strip()

            # Special handling for MAX function calls - show complete assignment
            if 'MAX(' in value.upper() or 'MAX (' in value.upper():
                # For MAX functions, show the complete assignment with function call
                safe_label = self._sanitize_label(f"{var} := {value}")
                self._add_debug(f"[MAIN] Creating MAX assignment node: {var} := {value[:50]}...")
            else:
                safe_label = self._sanitize_label(f"{var} := {value}")
            return self._create_safe_node(node_id, safe_label)

        # Check for function call - show complete function call with parameters
        func_match = self.patterns['function_call'].search(statement)
        if func_match:
            # Extract the complete function call with parameters
            func_call = func_match.group(0).strip()
            safe_label = self._sanitize_label(f"Call {func_call}")
            return self._create_safe_node(node_id, safe_label)

        # Check if this is just a semicolon
        if statement.strip() == ';':
            return self._create_safe_node(node_id, "")

        # Generic statement
        clean_stmt = statement[:-1].strip() if statement.endswith(';') else statement.strip()
        safe_label = self._sanitize_label(clean_stmt)
        return self._create_safe_node(node_id, safe_label)

    def _sanitize_label(self, label: str) -> str:
        """Sanitize label for Mermaid syntax using MermaidSanitizer"""
        return MermaidSanitizer.sanitize_label(label)

    def _create_safe_node(self, node_id: str, label: str, node_type: str = "rectangle") -> str:
        """Create a safe Mermaid node with proper escaping using MermaidSanitizer"""
        return MermaidSanitizer.create_safe_node(node_id, label, node_type)

    def _create_safe_connection(self, from_node: str, to_node: str, label: str = "") -> str:
        """Create a safe Mermaid connection between nodes using MermaidSanitizer"""
        return MermaidSanitizer.create_safe_connection(from_node, to_node, label)

    def _sanitize_node_id(self, node_id: str) -> str:
        """Sanitize node ID for Mermaid syntax"""
        # Remove any characters that aren't alphanumeric or underscore
        return re.sub(r'[^a-zA-Z0-9_]', '', node_id)

    def _validate_mermaid_output(self, mermaid_code: str) -> List[str]:
        """Validate Mermaid output for common issues"""
        return MermaidSanitizer.validate_mermaid_syntax(mermaid_code)