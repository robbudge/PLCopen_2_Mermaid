import re
from typing import List, Dict, Any, Tuple
from .base_processor import BaseLanguageProcessor


class STProcessor(BaseLanguageProcessor):
    """Structured Text language processor"""

    def __init__(self):
        super().__init__()
        self._compile_patterns()
        self._add_debug("ST Processor initialized")

    def _compile_patterns(self):
        """Compile all regex patterns for ST parsing"""
        self.patterns = {
            'if': re.compile(r'IF\s+(.+?)\s+THEN', re.IGNORECASE | re.DOTALL),
            'elsif': re.compile(r'ELSIF\s+(.+?)\s+THEN', re.IGNORECASE | re.DOTALL),
            'else': re.compile(r'ELSE', re.IGNORECASE),
            'end_if': re.compile(r'END_IF', re.IGNORECASE),
            'case': re.compile(r'CASE\s+(.+?)\s+OF', re.IGNORECASE | re.DOTALL),
            'case_when': re.compile(r'(\w+(?:\.\w+)*)\s*:\s*(.+)', re.IGNORECASE),
            'end_case': re.compile(r'END_CASE', re.IGNORECASE),
            'for': re.compile(r'FOR\s+(\w+)\s*:=\s*(\w+)\s+TO\s+(\w+)(?:\s+BY\s+([-\w]+))?\s+DO', re.IGNORECASE),
            'end_for': re.compile(r'END_FOR', re.IGNORECASE),
            'while': re.compile(r'WHILE\s+(.+?)\s+DO', re.IGNORECASE | re.DOTALL),
            'end_while': re.compile(r'END_WHILE', re.IGNORECASE),
            'repeat': re.compile(r'REPEAT', re.IGNORECASE),
            'until': re.compile(r'UNTIL\s+(.+?)\s*;', re.IGNORECASE | re.DOTALL),
            'assignment': re.compile(r'(\w+(?:\.\w+)*)\s*:=\s*(.+?);', re.IGNORECASE),
            'function_call': re.compile(r'(\w+)\s*\([^)]*\);', re.IGNORECASE),
            'comment_single': re.compile(r'//.*', re.IGNORECASE),
            'comment_multi': re.compile(r'\(\*.*?\*\)', re.DOTALL),
            'pragma': re.compile(r'{\s*.+?\s*}', re.DOTALL),
            'xhtml_tags': re.compile(r'<xhtml[^>]*>|</xhtml>', re.IGNORECASE),
            'xml_namespace': re.compile(r'xmlns[^>]*', re.IGNORECASE)
        }

    def can_process(self, language: str) -> bool:
        """Check if this processor can handle ST language"""
        return language.upper() in ['ST', 'STRUCTURED TEXT', 'UNKNOWN']

    def generate_flowchart(self, code: str, pou_name: str) -> str:
        """Generate Mermaid flowchart from ST code"""
        self.clear_debug()
        self._add_debug(f"Generating flowchart for POU: {pou_name}")

        if not code:
            return f"%% No ST code found for POU {pou_name}"

        self._add_debug(f"Raw input code preview: {code[:500]}...")

        # Extract clean ST code
        clean_code = self._extract_st_code(code)
        self._add_debug(f"After extraction, code length: {len(clean_code)}")

        if not clean_code or clean_code.isspace():
            self._add_debug("No executable code found after extraction")
            return f"%% No executable ST code found for POU {pou_name}\n%% Raw code preview: {code[:200]}..."

        self._add_debug(f"Cleaned code preview: {clean_code[:200]}...")

        # Generate flowchart
        mermaid_lines = ["flowchart TD"]
        flowchart_nodes = self._parse_st_to_flowchart(clean_code, pou_name)
        mermaid_lines.extend(flowchart_nodes)

        result = '\n'.join(mermaid_lines)

        # Validate the output
        validation_errors = self._validate_mermaid_output(result)
        if validation_errors:
            self._add_debug(f"Mermaid validation errors: {validation_errors}")
            # Add errors as comments to the output
            for error in validation_errors:
                result += f"\n%% ERROR: {error}"

        self._add_debug(f"Generated flowchart with {len(flowchart_nodes)} nodes")

        return result

    def _extract_st_code(self, code: str) -> str:
        """Extract and clean ST code from various formats"""
        if not code:
            return ""

        self._add_debug("Extracting ST code from input")

        # Step 1: Handle XML/CDATA content
        if '<' in code and '>' in code:
            self._add_debug("Detected XML-like content")

            # Try to extract content from CDATA first
            cdata_matches = re.findall(r'<!\[CDATA\[(.*?)\]\]>', code, re.DOTALL)
            if cdata_matches:
                self._add_debug(f"Found {len(cdata_matches)} CDATA sections")
                code = ' '.join(cdata_matches)
            else:
                # Remove all XML tags but keep text content
                self._add_debug("No CDATA found, stripping XML tags")
                code = re.sub(r'<[^>]+>', ' ', code)

        # Step 2: Remove specific XML artifacts
        code = self.patterns['xhtml_tags'].sub(' ', code)
        code = self.patterns['xml_namespace'].sub(' ', code)

        # Step 3: Clean up whitespace
        code = re.sub(r'\s+', ' ', code)

        # Step 4: Remove comments and pragmas
        code = self.patterns['comment_single'].sub('', code)
        code = self.patterns['comment_multi'].sub('', code)
        code = self.patterns['pragma'].sub('', code)

        return code.strip()

    def _split_statements(self, st_code: str) -> List[str]:
        """Split ST code into individual statements"""
        if not st_code:
            return []

        statements = []
        current = ""
        paren_depth = 0
        bracket_depth = 0

        i = 0
        while i < len(st_code):
            char = st_code[i]

            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth -= 1
            elif char == '{':
                bracket_depth += 1
            elif char == '}':
                bracket_depth -= 1
            elif char == ';' and paren_depth == 0 and bracket_depth == 0:
                # End of statement
                if current.strip():
                    statements.append(current.strip())
                current = ""
                i += 1
                continue
            elif i + 6 <= len(st_code) and st_code[
                i:i + 7].upper() == 'END_IF' and paren_depth == 0 and bracket_depth == 0:
                # Handle END_IF
                if current.strip():
                    statements.append(current.strip())
                statements.append('END_IF')
                current = ""
                i += 6
                continue
            elif i + 7 <= len(st_code) and st_code[
                i:i + 8].upper() == 'END_CASE' and paren_depth == 0 and bracket_depth == 0:
                # Handle END_CASE
                if current.strip():
                    statements.append(current.strip())
                statements.append('END_CASE')
                current = ""
                i += 7
                continue

            current += char
            i += 1

        # Add the last statement if any
        if current.strip():
            statements.append(current.strip())

        # Filter out empty statements
        filtered = [s for s in statements if s.strip() and s.strip() != ';']

        self._add_debug(f"Final filtered statements: {filtered}")
        return filtered

    def _parse_st_to_flowchart(self, st_code: str, pou_name: str) -> List[str]:
        """Parse ST code and generate Mermaid flowchart nodes"""
        nodes = []

        self._add_debug(f"Parsing ST code for flowchart generation")

        # Split into statements
        statements = self._split_statements(st_code)
        self._add_debug(f"Split into {len(statements)} statements")

        if not statements:
            nodes.append(self._create_safe_node("Start", "No Executable Code"))
            nodes.append(self._create_safe_connection("Start", "End"))
            nodes.append(self._create_safe_node("End", "End"))
            return nodes

        # Generate nodes with sequential IDs
        node_counter = 0

        def get_next_node_id():
            nonlocal node_counter
            node_id = f"N{node_counter}"
            node_counter += 1
            return node_id

        stack = []  # For handling nested structures
        current_node = "Start"
        nodes.append(self._create_safe_node("Start", "Start"))

        for i, statement in enumerate(statements):
            if not statement.strip():
                continue

            self._add_debug(f"Processing statement {i}: {statement[:50]}...")

            node_type, node_info = self._create_node(statement, get_next_node_id)

            if node_type == "if_start":
                # IF statement - create decision node
                nodes.append(node_info['node'])
                nodes.append(self._create_safe_connection(current_node, node_info['node_id']))

                # Create branches
                yes_branch = get_next_node_id()
                no_branch = get_next_node_id()
                nodes.append(self._create_safe_connection(node_info['node_id'], yes_branch, "Yes"))
                nodes.append(self._create_safe_connection(node_info['node_id'], no_branch, "No"))

                stack.append({
                    'type': 'if',
                    'start_node': node_info['node_id'],
                    'yes_branch': yes_branch,
                    'no_branch': no_branch,
                    'current_yes': yes_branch,
                    'current_no': no_branch
                })

                current_node = yes_branch

            elif node_type == "if_end":
                # END_IF - close IF structure
                if stack and stack[-1]['type'] == 'if':
                    if_struct = stack.pop()
                    end_node = get_next_node_id()

                    # Connect both branches to end node
                    nodes.append(self._create_safe_connection(if_struct['current_yes'], end_node))
                    nodes.append(self._create_safe_connection(if_struct['current_no'], end_node))
                    nodes.append(self._create_safe_node(end_node, "End If"))
                    current_node = end_node

            elif node_type == "case_start":
                # CASE statement - treat as decision with multiple outcomes
                nodes.append(node_info['node'])
                nodes.append(self._create_safe_connection(current_node, node_info['node_id']))

                stack.append({
                    'type': 'case',
                    'start_node': node_info['node_id'],
                    'branches': [],
                    'case_expression': node_info['expression']
                })

                # CASE node becomes the current node for branches to connect to
                current_node = node_info['node_id']

            elif node_type == "case_when":
                # CASE branch - add as a decision branch from the CASE node
                if stack and stack[-1]['type'] == 'case':
                    case_struct = stack[-1]
                    branch_node = get_next_node_id()

                    # Add the branch content
                    nodes.append(self._create_safe_node(branch_node, node_info['action']))

                    # Connect from CASE to this branch with the case value as label
                    nodes.append(self._create_safe_connection(
                        case_struct['start_node'],
                        branch_node,
                        node_info['value']
                    ))

                    case_struct['branches'].append(branch_node)
                    # Store the last branch for connection to end
                    case_struct['last_branch'] = branch_node

            elif node_type == "case_else":
                # CASE ELSE branch
                if stack and stack[-1]['type'] == 'case':
                    case_struct = stack[-1]
                    branch_node = get_next_node_id()

                    # Add the ELSE branch content
                    nodes.append(self._create_safe_node(branch_node, node_info['action']))

                    # Connect from CASE to ELSE branch
                    nodes.append(self._create_safe_connection(
                        case_struct['start_node'],
                        branch_node,
                        "Else"
                    ))

                    case_struct['branches'].append(branch_node)
                    case_struct['last_branch'] = branch_node

            elif node_type == "case_end":
                # END_CASE - connect all branches to end
                if stack and stack[-1]['type'] == 'case':
                    case_struct = stack.pop()
                    end_node = get_next_node_id()

                    # Connect all branches to the end node
                    for branch in case_struct['branches']:
                        nodes.append(self._create_safe_connection(branch, end_node))

                    nodes.append(self._create_safe_node(end_node, "End Case"))
                    current_node = end_node

            elif node_type == "statement":
                # Regular statement
                nodes.append(node_info)

                if current_node:
                    node_id = node_info.split('[')[0].strip()
                    nodes.append(self._create_safe_connection(current_node, node_id))

                # Update current node in stack if we're in a branch
                if stack:
                    top_struct = stack[-1]
                    if top_struct['type'] == 'if':
                        node_id = node_info.split('[')[0].strip()
                        if current_node == top_struct['current_yes']:
                            top_struct['current_yes'] = node_id
                        elif current_node == top_struct['current_no']:
                            top_struct['current_no'] = node_id
                    elif top_struct['type'] == 'case' and 'last_branch' in top_struct:
                        # Update the last branch in CASE structure
                        node_id = node_info.split('[')[0].strip()
                        top_struct['last_branch'] = node_id

                current_node = node_info.split('[')[0].strip()

        # Close any open structures
        while stack:
            struct = stack.pop()
            if struct['type'] == 'if':
                end_node = get_next_node_id()
                nodes.append(self._create_safe_connection(struct['current_yes'], end_node))
                nodes.append(self._create_safe_connection(struct['current_no'], end_node))
                nodes.append(self._create_safe_node(end_node, "End If"))
                current_node = end_node
            elif struct['type'] == 'case':
                end_node = get_next_node_id()
                for branch in struct['branches']:
                    nodes.append(self._create_safe_connection(branch, end_node))
                nodes.append(self._create_safe_node(end_node, "End Case"))
                current_node = end_node

        # Add final end node
        if current_node and current_node != "Start":
            nodes.append(self._create_safe_connection(current_node, "End"))
        nodes.append(self._create_safe_node("End", "End"))

        return nodes

    def _create_node(self, statement: str, get_next_node_id) -> Tuple[str, Any]:
        """Create a flowchart node from an ST statement"""
        statement_upper = statement.upper().strip()
        node_id = get_next_node_id()

        # Check for IF statement
        if statement_upper.startswith('IF '):
            match = self.patterns['if'].match(statement)
            if match:
                condition = match.group(1).strip()
                safe_condition = self._sanitize_condition(condition)
                return ("if_start", {
                    'node': self._create_safe_node(node_id, safe_condition, "rhombus"),
                    'node_id': node_id
                })

        # Check for END_IF
        elif statement_upper == 'END_IF':
            return ("if_end", {})

        # Check for CASE statement
        elif statement_upper.startswith('CASE '):
            match = self.patterns['case'].match(statement)
            if match:
                case_expression = match.group(1).strip()
                safe_expression = self._sanitize_condition(case_expression)
                return ("case_start", {
                    'node': self._create_safe_node(node_id, safe_expression, "rhombus"),
                    'node_id': node_id,
                    'expression': case_expression
                })

        # Check for CASE branches (like value: statement)
        elif ':' in statement and not statement.strip().startswith('//'):
            # Simple case branch detection - look for pattern: value : action
            colon_pos = statement.find(':')
            if colon_pos > 0:
                case_value = statement[:colon_pos].strip()
                case_action = statement[colon_pos + 1:].strip()

                # Check if this looks like a CASE branch (not a label)
                if case_value and not case_value.startswith('//'):
                    # Remove trailing semicolon if present
                    if case_action.endswith(';'):
                        case_action = case_action[:-1].strip()

                    safe_value = self._sanitize_link_label(case_value)
                    safe_action = self._sanitize_label(case_action)

                    return ("case_when", {
                        'value': safe_value,
                        'action': safe_action
                    })

        # Check for CASE ELSE branch
        elif statement_upper.startswith('ELSE:'):
            else_action = statement[5:].strip()  # Remove "ELSE:"
            if else_action.endswith(';'):
                else_action = else_action[:-1].strip()

            safe_action = self._sanitize_label(else_action)

            return ("case_else", {
                'action': safe_action
            })

        # Check for END_CASE
        elif statement_upper == 'END_CASE':
            return ("case_end", {})

        # Check for assignment
        assign_match = self.patterns['assignment'].search(statement)
        if assign_match:
            var = assign_match.group(1)
            value = assign_match.group(2)
            # Remove trailing semicolon if present
            if value.endswith(';'):
                value = value[:-1].strip()

            safe_label = self._sanitize_label(f"{var} := {value}")
            return ("statement", self._create_safe_node(node_id, safe_label))

        # Check for function call
        func_match = self.patterns['function_call'].search(statement)
        if func_match:
            func_name = func_match.group(1)
            safe_label = self._sanitize_label(f"Call {func_name}")
            return ("statement", self._create_safe_node(node_id, safe_label))

        # Generic statement - use full text
        clean_stmt = statement
        if clean_stmt.endswith(';'):
            clean_stmt = clean_stmt[:-1].strip()

        safe_label = self._sanitize_label(clean_stmt)
        return ("statement", self._create_safe_node(node_id, safe_label))