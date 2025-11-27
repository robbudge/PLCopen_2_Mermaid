import re
from typing import List, Dict, Any, Tuple, Optional
from .base_processor import BaseLanguageProcessor
from .st_if import STIfProcessor
from .st_case import STCaseProcessor
from .st_sel import STSelProcessor
from .st_max import STMaxProcessor
from .st_or import STOrProcessor
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
        self.max_processor = STMaxProcessor(self)
        self.or_processor = STOrProcessor(self)  # Add OR processor

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

    def generate_flowchart(self, code: str, pou_name: str, pou_info: dict = None) -> str:
        """Generate Mermaid flowchart from ST code"""
        self.clear_debug()
        self._add_debug(f"[MAIN] Generating flowchart for POU: {pou_name}")

        # Log POU information including actions and methods
        if pou_info:
            self._add_debug(f"[MAIN] POU Type: {pou_info.get('pouType', 'Unknown')}")
            self._add_debug(f"[MAIN] Language: {pou_info.get('language', 'Unknown')}")

            actions = pou_info.get('actions', [])
            methods = pou_info.get('methods', [])

            self._add_debug(f"[MAIN] Actions found: {len(actions)}")
            for action in actions:
                action_info = pou_info.get('actionsInfo', {}).get(action, {})
                action_lang = action_info.get('language', 'Unknown')
                action_body_lang = action_info.get('bodyLanguage', 'Unknown')
                action_body_len = len(action_info.get('body', ''))

                self._add_debug(
                    f"[MAIN]   - {action} (lang: {action_lang}, body lang: {action_body_lang}, body length: {action_body_len})")

            self._add_debug(f"[MAIN] Methods found: {len(methods)}")
            for method in methods:
                method_info = pou_info.get('methodsInfo', {}).get(method, {})
                method_lang = method_info.get('language', 'Unknown')
                method_body_lang = method_info.get('bodyLanguage', 'Unknown')
                method_body_len = len(method_info.get('body', ''))

                self._add_debug(
                    f"[MAIN]   - {method} (lang: {method_lang}, body lang: {method_body_lang}, body length: {method_body_len})")
        else:
            self._add_debug("[MAIN] No additional POU information provided")

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

        # Parse the code
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

    def _parse_recursive(self, code: str, current_node: str, node_counter: List[int], in_if_branch: bool = False) -> List[str]:
        """Main recursive parsing routine - UPDATED to include OR processing"""
        nodes = []
        remaining_code = code.strip()
        exit_node = current_node

        while remaining_code:
            self._line_counter += 1
            processed = False

            # Check for OR statements FIRST (before other processors)
            if self.or_processor.find_or_statement(remaining_code):
                self._add_debug("[MAIN] Processing OR statement")
                try:
                    result = self.or_processor.process_or_statement(remaining_code, exit_node, node_counter)
                    if result:
                        or_nodes, next_exit_node, consumed = result
                        if consumed > 0:
                            nodes.extend(or_nodes)
                            exit_node = next_exit_node
                            remaining_code = remaining_code[consumed:].strip()
                            self._add_debug(f"[MAIN] OR processed, consumed {consumed} chars")
                            processed = True
                            continue
                    else:
                        self._add_debug("[MAIN] OR processor returned no result")
                except Exception as e:
                    self._add_debug(f"[MAIN] Error in OR processor: {e}")

            # Check for MAX statements
            if self._find_max_statement(remaining_code):
                try:
                    result = self.max_processor.process_max_statement(remaining_code, exit_node, node_counter)
                    if result:
                        max_nodes, next_exit_node, consumed = result
                        if consumed > 0:
                            nodes.extend(max_nodes)
                            exit_node = next_exit_node
                            remaining_code = remaining_code[consumed:].strip()
                            processed = True
                            continue
                except Exception:
                    pass

            # Check for SEL statements
            if self._find_sel_statement(remaining_code):
                try:
                    result = self.sel_processor.process_sel_statement(remaining_code, exit_node, node_counter)
                    if result:
                        sel_nodes, next_exit_node, consumed = result
                        if consumed > 0:
                            nodes.extend(sel_nodes)
                            exit_node = next_exit_node
                            remaining_code = remaining_code[consumed:].strip()
                            processed = True
                            continue
                except Exception:
                    pass

            # Check for IF statements
            if_match = self._find_if_statement(remaining_code)
            if if_match:
                try:
                    result = self.if_processor.process_if_statement(remaining_code, exit_node, node_counter)
                    if result:
                        if_nodes, next_exit_node, consumed = result
                        if consumed > 0:
                            # FIX: Always connect current exit node to first IF node if needed
                            if exit_node and exit_node != "Start" and if_nodes:
                                first_if_node = self._find_first_decision_node(if_nodes)
                                if first_if_node:
                                    connection_exists = any(
                                        node.startswith(f"{exit_node} -->") and first_if_node in node
                                        for node in if_nodes
                                    )
                                    if not connection_exists:
                                        connection = self._create_safe_connection(exit_node, first_if_node)
                                        nodes.append(connection)

                            nodes.extend(if_nodes)
                            exit_node = next_exit_node
                            remaining_code = remaining_code[consumed:].strip()
                            processed = True
                            continue
                except Exception:
                    pass

            # Check for CASE statements
            case_match = self._find_case_statement(remaining_code)
            if case_match:
                try:
                    result = self.case_processor.process_case_statement(remaining_code, exit_node, node_counter)
                    if result:
                        case_nodes, next_exit_node, consumed = result
                        if consumed > 0:
                            if exit_node and exit_node != "Start" and case_nodes:
                                first_case_node = self._find_first_decision_node(case_nodes)
                                if first_case_node:
                                    connection = self._create_safe_connection(exit_node, first_case_node)
                                    nodes.append(connection)

                            nodes.extend(case_nodes)
                            exit_node = next_exit_node
                            remaining_code = remaining_code[consumed:].strip()
                            processed = True
                            continue
                except Exception:
                    pass

            # Terminal statements (assignments and function calls) - FALLBACK
            statement, consumed = self._extract_terminal_statement(remaining_code)
            if statement and consumed > 0:
                node_id = f"N{node_counter[0]}"
                node_counter[0] += 1

                node_content = self._create_terminal_node(statement, node_id)

                if not self._is_empty_node(node_content):
                    # Connect from current exit_node
                    if exit_node and exit_node != "Start":
                        connection = self._create_safe_connection(exit_node, node_id)
                        nodes.append(connection)

                    nodes.append(node_content)
                    exit_node = node_id

                remaining_code = remaining_code[consumed:].strip()
                processed = True
            else:
                # If we can't process anything and no progress is made, break to prevent infinite loop
                if not processed:
                    break

        return nodes

    def _find_max_statement(self, code: str) -> bool:
        """Check if the next complete statement contains a MAX assignment"""
        # Find the first complete statement (up to semicolon)
        first_semicolon = code.find(';')
        if first_semicolon == -1:
            return False

        first_statement = code[:first_semicolon + 1].strip()

        # More reliable check: look for the pattern of MAX assignment
        max_pattern = r'\w+(?:\.\w+)*\s*:=\s*MAX\s*\([^;]+\)\s*;'
        is_max = re.search(max_pattern, first_statement, re.IGNORECASE | re.DOTALL) is not None

        if is_max:
            # Additional check: verify balanced parentheses
            open_paren = first_statement.count('(')
            close_paren = first_statement.count(')')
            if open_paren == close_paren:
                return True
            else:
                return False
        else:
            return False

    def _find_if_statement(self, code: str) -> bool:
        """Check if code starts with an IF statement"""
        # Simple check for IF keyword at beginning
        return code.upper().startswith('IF ')

    def _find_case_statement(self, code: str) -> bool:
        """Check if code starts with a CASE statement"""
        # Simple check for CASE keyword at beginning
        is_case = code.upper().startswith('CASE ')
        if is_case:
            self._add_debug(f"[MAIN] Found CASE statement: {code[:100]}...")
        return is_case

    def _find_sel_statement(self, code: str) -> bool:
        """Check if the next complete statement contains a SEL assignment"""
        # Find the first complete statement (up to semicolon)
        first_semicolon = code.find(';')
        if first_semicolon == -1:
            self._add_debug("[MAIN] No complete statement found for SEL check")
            return False

        first_statement = code[:first_semicolon + 1].strip()

        # Check if this statement contains a SEL assignment
        sel_pattern = r'\w+(?:\.\w+)*\s*:=\s*SEL\s*\([^;]+\)\s*;'
        is_sel = re.search(sel_pattern, first_statement, re.IGNORECASE | re.DOTALL) is not None

        if is_sel:
            self._add_debug(f"[MAIN] Found SEL assignment: {first_statement[:100]}...")
        return is_sel

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