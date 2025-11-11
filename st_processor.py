"""
ST (Structured Text) Processor for Codesys to Mermaid conversion
Updated with proper nested IF-THEN-ELSE parsing and improved statement parsing
"""

import logging
import re
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class STProcessor:
    def __init__(self):
        self.namespace = ''

    def set_namespace(self, namespace: str):
        """Set the XML namespace"""
        self.namespace = namespace
        logger.info(f"STProcessor namespace set to: {namespace}")

    def extract_code(self, body_element, name: str) -> Optional[str]:
        """Extract ST code from body element - properly handles xhtml wrapper"""
        try:
            # Method 1: Look for direct ST element
            st_elem = body_element.find(f"{self.namespace}ST")

            if st_elem is not None:
                # Check if ST element has direct text content
                if st_elem.text and st_elem.text.strip():
                    logger.info(f"Found direct ST text for {name}, length: {len(st_elem.text)}")
                    return st_elem.text

                # Method 2: Look for XHTML wrapper within ST element
                xhtml_elem = st_elem.find(f"{self.namespace}xhtml")
                if xhtml_elem is not None:
                    # Extract all text content from xhtml
                    full_text = self._extract_text_from_xhtml(xhtml_elem)
                    if full_text and full_text.strip():
                        logger.info(f"Found XHTML ST code for {name}, length: {len(full_text)}")
                        return full_text

                # Method 3: Look for any text in ST element children
                all_text = ''.join(st_elem.itertext())
                if all_text and all_text.strip():
                    logger.info(f"Found ST code from itertext for {name}, length: {len(all_text)}")
                    return all_text

            logger.warning(f"No ST code found for {name}")
            return None

        except Exception as e:
            logger.error(f"Error extracting ST code for {name}: {e}")
            return None

    def _extract_text_from_xhtml(self, xhtml_elem) -> str:
        """Extract all text content from XHTML element"""
        try:
            # Get all text content, preserving line breaks
            texts = []
            for elem in xhtml_elem.iter():
                if elem.text and elem.text.strip():
                    texts.append(elem.text.strip())
                if elem.tail and elem.tail.strip():
                    texts.append(elem.tail.strip())

            return '\n'.join(texts)
        except Exception as e:
            logger.error(f"Error extracting text from XHTML: {e}")
            return ""

    def convert_to_mermaid(self, st_code: str, pou_name: str) -> str:
        """
        Convert ST code to Mermaid flowchart - main entry point called by mermaid_processor
        """
        return self.process_code(st_code, pou_name)

    def process_code(self, st_code: str, pou_name: str) -> str:
        """
        Process Structured Text code and convert to Mermaid flowchart
        UPDATED: Improved statement parsing and structure detection
        """
        try:
            if not st_code or not st_code.strip():
                logger.warning(f"No ST code to process for {pou_name}")
                return self._create_empty_flowchart(pou_name)

            logger.info(f"Processing ST code for {pou_name}, length: {len(st_code)} characters")

            # Clean the code - preserve actual content
            cleaned_code = self._clean_st_code(st_code)
            logger.info(f"After cleaning: {len(cleaned_code)} characters")

            if not cleaned_code.strip():
                logger.warning(f"No meaningful ST code after cleaning for {pou_name}")
                return self._create_empty_flowchart(pou_name)

            # Parse statements with improved parser
            statements = self._parse_st_statements(cleaned_code)
            logger.info(f"Parsed {len(statements)} statements for {pou_name}")

            # Build flowchart with proper structure
            flowchart = self._build_flowchart_from_statements(statements, pou_name, st_code)

            return flowchart

        except Exception as e:
            logger.error(f"Error processing ST code for {pou_name}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return self._create_error_flowchart(pou_name, str(e))

    def _clean_st_code(self, st_code: str) -> str:
        """Clean and normalize ST code while preserving all content"""
        if not st_code:
            return ""

        # Remove HTML entities and decode special characters
        cleaned = st_code.replace('&gt;', '>').replace('&lt;', '<').replace('&amp;', '&')

        # Split into lines and clean each line
        lines = cleaned.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if line:
                # Normalize whitespace but keep the content
                line = re.sub(r'\s+', ' ', line)
                cleaned_lines.append(line)

        result = '\n'.join(cleaned_lines)
        logger.info(f"Cleaned code sample: {result[:200]}...")
        return result

    def _parse_st_statements(self, st_code: str) -> List[Dict[str, Any]]:
        """
        Parse ST code into structured statements
        IMPROVED: Better handling of nested IF, CASE statements and control structures
        """
        statements = []
        if not st_code or not st_code.strip():
            return statements

        logger.info(f"Parsing ST code: {st_code[:100]}...")

        # Use recursive parsing to handle nested structures
        statements = self._parse_nested_structures(st_code)

        return statements

    def _parse_nested_structures(self, st_code: str, depth: int = 0) -> List[Dict[str, Any]]:
        """Parse nested control structures recursively"""
        statements = []
        remaining_code = st_code

        while remaining_code.strip():
            # Look for the next control structure
            next_control = self._find_next_control_structure(remaining_code)

            if not next_control:
                # No more control structures, parse remaining as simple statements
                if remaining_code.strip():
                    statements.extend(self._parse_simple_statements(remaining_code))
                break

            control_type, start_pos, end_pos, content = next_control

            # Add content before control structure
            before_control = remaining_code[:start_pos].strip()
            if before_control:
                statements.extend(self._parse_simple_statements(before_control))

            # Process the control structure
            if control_type == 'IF':
                # Parse IF-THEN-ELSE structure
                if_match = re.match(r'IF\s+(.*?)\s+THEN\s*(.*?)\s*(?:ELSE\s*(.*?)\s*)?END_IF', content,
                                    re.IGNORECASE | re.DOTALL)
                if if_match:
                    condition = if_match.group(1).strip()
                    then_block = if_match.group(2).strip()
                    else_block = if_match.group(3).strip() if if_match.group(3) else ""

                    # Recursively parse nested structures in THEN and ELSE blocks
                    then_statements = self._parse_nested_structures(then_block, depth + 1)
                    else_statements = self._parse_nested_structures(else_block, depth + 1)

                    statements.append({
                        'type': 'IF',
                        'content': condition,
                        'raw': f"IF {condition} THEN",
                        'then_block': then_block,
                        'else_block': else_block,
                        'then_statements': then_statements,
                        'else_statements': else_statements
                    })

            elif control_type == 'CASE':
                # Parse CASE structure
                case_match = re.match(r'CASE\s+([^:]*?)\s+OF\s*(.*?)\s*END_CASE', content, re.IGNORECASE | re.DOTALL)
                if case_match:
                    case_var = case_match.group(1).strip()
                    case_content = case_match.group(2).strip()

                    statements.append({
                        'type': 'CASE',
                        'content': case_var,
                        'raw': f"CASE {case_var} OF"
                    })

                    # Parse CASE branches
                    branches = self._parse_case_branches(case_content)
                    statements.extend(branches)

                    statements.append({
                        'type': 'END_CONTROL',
                        'content': 'END_CASE',
                        'raw': 'END_CASE'
                    })

            # Move to remaining code after this control structure
            remaining_code = remaining_code[end_pos:]

        return statements

    def _find_next_control_structure(self, st_code: str) -> Optional[tuple]:
        """Find the next control structure in the code"""
        # Look for IF statements
        if_pattern = r'IF\s+.*?\s+THEN\s*.*?\s*END_IF'
        if_match = re.search(if_pattern, st_code, re.IGNORECASE | re.DOTALL)

        # Look for CASE statements
        case_pattern = r'CASE\s+.*?\s+OF\s*.*?\s*END_CASE'
        case_match = re.search(case_pattern, st_code, re.IGNORECASE | re.DOTALL)

        # Find the earliest occurring control structure
        matches = []
        if if_match:
            matches.append(('IF', if_match.start(), if_match.end(), if_match.group()))
        if case_match:
            matches.append(('CASE', case_match.start(), case_match.end(), case_match.group()))

        if matches:
            # Return the earliest match
            return min(matches, key=lambda x: x[1])

        return None

    def _parse_simple_statements(self, st_code: str) -> List[Dict[str, Any]]:
        """Parse simple statements (non-control structures)"""
        statements = []
        lines = st_code.split('\n')
        current_statement = ""

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Add line to current statement
            if current_statement:
                current_statement += " " + line
            else:
                current_statement = line

            # Check if we have complete statements ending with semicolon
            while ';' in current_statement:
                semicolon_pos = self._find_outer_semicolon(current_statement)
                if semicolon_pos == -1:
                    break

                statement_text = current_statement[:semicolon_pos].strip()
                if statement_text:
                    stmt_info = self._classify_statement(statement_text)
                    statements.append(stmt_info)

                current_statement = current_statement[semicolon_pos + 1:].strip()

            # Handle control structures without semicolons
            if current_statement and any(keyword in current_statement.upper() for keyword in
                                         ['IF ', 'FOR ', 'WHILE ', 'REPEAT ', 'END_IF', 'END_FOR']):
                stmt_info = self._classify_statement(current_statement)
                statements.append(stmt_info)
                current_statement = ""

        # Add any remaining statement
        if current_statement.strip():
            stmt_info = self._classify_statement(current_statement.strip())
            statements.append(stmt_info)

        return statements

    def _find_outer_semicolon(self, text: str) -> int:
        """Find the first semicolon that's not inside parentheses"""
        paren_level = 0
        bracket_level = 0

        for i, char in enumerate(text):
            if char == '(':
                paren_level += 1
            elif char == ')':
                paren_level -= 1
            elif char == '[':
                bracket_level += 1
            elif char == ']':
                bracket_level -= 1
            elif char == ';' and paren_level == 0 and bracket_level == 0:
                return i

        return -1

    def _parse_case_branches(self, case_content: str) -> List[Dict[str, Any]]:
        """Parse individual CASE branches"""
        branches = []
        lines = case_content.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # CASE branch pattern: condition : action
            if ':' in line:
                parts = line.split(':', 1)
                condition = parts[0].strip()
                action = parts[1].strip().rstrip(';')

                branches.append({
                    'type': 'CASE_BRANCH',
                    'content': f"{condition}: {action}",
                    'raw': line,
                    'condition': condition,
                    'action': action
                })
            else:
                # Branch without colon - could be condition only or malformed
                branches.append({
                    'type': 'CASE_BRANCH',
                    'content': line,
                    'raw': line,
                    'condition': line,
                    'action': 'NA'
                })

        return branches

    def _classify_statement(self, statement: str) -> Dict[str, Any]:
        """
        Classify statement type - NO SIMPLIFICATION of complex expressions
        """
        stmt_lower = statement.lower().strip()

        # Control structures
        if stmt_lower.startswith('if '):
            return {
                'type': 'IF',
                'content': statement,
                'raw': statement
            }
        elif stmt_lower.startswith('case '):
            return {
                'type': 'CASE',
                'content': statement,
                'raw': statement
            }
        elif stmt_lower.startswith('for '):
            return {
                'type': 'FOR',
                'content': statement,
                'raw': statement
            }
        elif stmt_lower.startswith('while '):
            return {
                'type': 'WHILE',
                'content': statement,
                'raw': statement
            }
        elif stmt_lower.startswith('repeat '):
            return {
                'type': 'REPEAT',
                'content': statement,
                'raw': statement
            }
        elif stmt_lower.startswith('end_if') or stmt_lower.startswith('end_case') or stmt_lower.startswith('end_for'):
            return {
                'type': 'END_CONTROL',
                'content': statement,
                'raw': statement
            }

        # SEL function - treat as decision
        elif 'sel(' in stmt_lower and ':=' in statement:
            return {
                'type': 'SEL_DECISION',
                'content': statement,
                'raw': statement
            }

        # Function calls
        elif re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\(.*\)$', statement.strip()):
            return {
                'type': 'FUNCTION_CALL',
                'content': statement,
                'raw': statement
            }

        # Assignments
        elif ':=' in statement:
            return {
                'type': 'ASSIGNMENT',
                'content': statement,
                'raw': statement
            }

        # Default
        return {
            'type': 'STATEMENT',
            'content': statement,
            'raw': statement
        }

    def _build_flowchart_from_statements(self, statements: List[Dict[str, Any]], pou_name: str,
                                         original_code: str) -> str:
        """
        Build Mermaid flowchart from parsed statements
        FIXED: Proper nested IF-THEN-ELSE with correct branching
        """
        lines = []

        # Header with metadata
        lines.append('%% ST to Mermaid Flowchart Conversion')
        lines.append(f'%% Program: {pou_name}')

        code_lines = original_code.split('\n')
        non_empty_lines = [line for line in code_lines if line.strip()]
        lines.append(f'%% Original code length: {len(original_code)} characters')
        lines.append(f'%% Lines: {len(code_lines)} total, {len(non_empty_lines)} non-empty')

        # Calculate max line length
        if code_lines:
            max_line_len = max([len(line) for line in code_lines])
            lines.append(f'%% Max line length: {max_line_len} characters')
        else:
            lines.append(f'%% Max line length: 0 characters')

        lines.append('%% No line length limits applied - all content preserved')
        lines.append('')
        lines.append('flowchart TD')
        lines.append(f'    Start["Start: {pou_name}"]')

        if not statements:
            lines.append(f'    Start --> NoCode["No ST statements parsed"]')
            lines.append(f'    NoCode --> End["End: {pou_name}"]')
            return '\n'.join(lines)

        node_id = 1
        previous_node = "Start"

        i = 0
        while i < len(statements):
            stmt = statements[i]

            if stmt['type'] == 'IF' and 'then_statements' in stmt:
                # IF statement with nested THEN and ELSE blocks
                if_node = f"If{node_id}"
                condition = stmt["content"].replace('"', '\\"')
                lines.append(f'    {if_node}{{"IF {condition}"}}')
                lines.append(f'    {previous_node} --> {if_node}')

                # Build THEN branch
                then_start_node = f"ThenStart{node_id}"
                then_end_node = f"ThenEnd{node_id}"

                # Create start of THEN branch
                lines.append(f'    {if_node} -->|True| {then_start_node}["THEN branch"]')

                # Build nested statements for THEN branch
                then_previous = then_start_node
                then_sub_id = node_id * 100

                for then_stmt in stmt['then_statements']:
                    if then_stmt['type'] == 'IF' and 'then_statements' in then_stmt:
                        # Nested IF in THEN branch - build it properly
                        nested_if_node = f"If{then_sub_id}"
                        nested_condition = then_stmt["content"].replace('"', '\\"')
                        lines.append(f'    {nested_if_node}{{"IF {nested_condition}"}}')
                        lines.append(f'    {then_previous} --> {nested_if_node}')

                        # Build nested THEN branch
                        nested_then_start = f"ThenStart{then_sub_id}"
                        nested_then_end = f"ThenEnd{then_sub_id}"
                        lines.append(f'    {nested_if_node} -->|True| {nested_then_start}["THEN branch"]')

                        nested_then_previous = nested_then_start
                        nested_then_sub_id = then_sub_id + 1

                        for nested_then_stmt in then_stmt['then_statements']:
                            nested_then_node = f"Then{nested_then_sub_id}"
                            nested_then_content = nested_then_stmt["content"].replace('"', '\\"')
                            lines.append(f'    {nested_then_node}["{nested_then_content}"]')
                            lines.append(f'    {nested_then_previous} --> {nested_then_node}')
                            nested_then_previous = nested_then_node
                            nested_then_sub_id += 1

                        lines.append(f'    {nested_then_previous} --> {nested_then_end}')

                        # Build nested ELSE branch
                        nested_else_start = f"ElseStart{then_sub_id}"
                        nested_else_end = f"ElseEnd{then_sub_id}"
                        lines.append(f'    {nested_if_node} -->|False| {nested_else_start}["ELSE branch"]')

                        nested_else_previous = nested_else_start
                        nested_else_sub_id = then_sub_id + 100

                        for nested_else_stmt in then_stmt['else_statements']:
                            nested_else_node = f"Else{nested_else_sub_id}"
                            nested_else_content = nested_else_stmt["content"].replace('"', '\\"')
                            lines.append(f'    {nested_else_node}["{nested_else_content}"]')
                            lines.append(f'    {nested_else_previous} --> {nested_else_node}')
                            nested_else_previous = nested_else_node
                            nested_else_sub_id += 1

                        lines.append(f'    {nested_else_previous} --> {nested_else_end}')

                        # Create merge point for nested IF
                        nested_merge_node = f"Merge{then_sub_id}"
                        lines.append(f'    {nested_then_end} --> {nested_merge_node}')
                        lines.append(f'    {nested_else_end} --> {nested_merge_node}')

                        then_previous = nested_merge_node
                        then_sub_id = nested_else_sub_id + 1

                    else:
                        # Regular statement in THEN branch
                        then_node_name = f"Then{then_sub_id}"
                        then_content = then_stmt["content"].replace('"', '\\"')
                        lines.append(f'    {then_node_name}["{then_content}"]')
                        lines.append(f'    {then_previous} --> {then_node_name}')
                        then_previous = then_node_name
                        then_sub_id += 1

                # Connect last THEN statement to THEN end
                lines.append(f'    {then_previous} --> {then_end_node}')

                # Build ELSE branch
                else_start_node = f"ElseStart{node_id}"
                else_end_node = f"ElseEnd{node_id}"

                # Create start of ELSE branch
                lines.append(f'    {if_node} -->|False| {else_start_node}["ELSE branch"]')

                # Build nested statements for ELSE branch
                else_previous = else_start_node
                else_sub_id = node_id * 1000

                for else_stmt in stmt['else_statements']:
                    if else_stmt['type'] == 'IF' and 'then_statements' in else_stmt:
                        # Nested IF in ELSE branch - build it properly
                        nested_if_node = f"If{else_sub_id}"
                        nested_condition = else_stmt["content"].replace('"', '\\"')
                        lines.append(f'    {nested_if_node}{{"IF {nested_condition}"}}')
                        lines.append(f'    {else_previous} --> {nested_if_node}')

                        # Build nested THEN branch
                        nested_then_start = f"ThenStart{else_sub_id}"
                        nested_then_end = f"ThenEnd{else_sub_id}"
                        lines.append(f'    {nested_if_node} -->|True| {nested_then_start}["THEN branch"]')

                        nested_then_previous = nested_then_start
                        nested_then_sub_id = else_sub_id + 1

                        for nested_then_stmt in else_stmt['then_statements']:
                            nested_then_node = f"Then{nested_then_sub_id}"
                            nested_then_content = nested_then_stmt["content"].replace('"', '\\"')
                            lines.append(f'    {nested_then_node}["{nested_then_content}"]')
                            lines.append(f'    {nested_then_previous} --> {nested_then_node}')
                            nested_then_previous = nested_then_node
                            nested_then_sub_id += 1

                        lines.append(f'    {nested_then_previous} --> {nested_then_end}')

                        # Build nested ELSE branch
                        nested_else_start = f"ElseStart{else_sub_id}"
                        nested_else_end = f"ElseEnd{else_sub_id}"
                        lines.append(f'    {nested_if_node} -->|False| {nested_else_start}["ELSE branch"]')

                        nested_else_previous = nested_else_start
                        nested_else_sub_id = else_sub_id + 100

                        for nested_else_stmt in else_stmt['else_statements']:
                            nested_else_node = f"Else{nested_else_sub_id}"
                            nested_else_content = nested_else_stmt["content"].replace('"', '\\"')
                            lines.append(f'    {nested_else_node}["{nested_else_content}"]')
                            lines.append(f'    {nested_else_previous} --> {nested_else_node}')
                            nested_else_previous = nested_else_node
                            nested_else_sub_id += 1

                        lines.append(f'    {nested_else_previous} --> {nested_else_end}')

                        # Create merge point for nested IF
                        nested_merge_node = f"Merge{else_sub_id}"
                        lines.append(f'    {nested_then_end} --> {nested_merge_node}')
                        lines.append(f'    {nested_else_end} --> {nested_merge_node}')

                        else_previous = nested_merge_node
                        else_sub_id = nested_else_sub_id + 1

                    else:
                        # Regular statement in ELSE branch
                        else_node_name = f"Else{else_sub_id}"
                        else_content = else_stmt["content"].replace('"', '\\"')
                        lines.append(f'    {else_node_name}["{else_content}"]')
                        lines.append(f'    {else_previous} --> {else_node_name}')
                        else_previous = else_node_name
                        else_sub_id += 1

                # Connect last ELSE statement to ELSE end
                lines.append(f'    {else_previous} --> {else_end_node}')

                # Create merge point after both branches
                merge_node = f"Merge{node_id}"
                lines.append(f'    {then_end_node} --> {merge_node}')
                lines.append(f'    {else_end_node} --> {merge_node}')

                previous_node = merge_node
                node_id += 1

            elif stmt['type'] == 'CASE':
                # CASE statement with branches
                case_node = f"Case{node_id}"
                lines.append(f'    {case_node}{{"CASE {stmt["content"]}"}}')
                lines.append(f'    {previous_node} --> {case_node}')

                # Process all CASE_BRANCH statements until END_CASE
                branch_id = 1
                i += 1  # Move to first branch

                while i < len(statements) and statements[i]['type'] != 'END_CONTROL':
                    branch_stmt = statements[i]
                    if branch_stmt['type'] == 'CASE_BRANCH':
                        branch_node = f"Branch{node_id}_{branch_id}"
                        action = branch_stmt.get('action', branch_stmt['content'])

                        # Handle empty actions - use 'NA' instead of empty string
                        if not action or action.strip() == '':
                            action_content = "NA"
                        else:
                            action_content = action.replace('"', '\\"')

                        lines.append(f'    {branch_node}["{action_content}"]')

                        condition = branch_stmt.get('condition', 'condition')
                        condition_content = condition.replace('"', '\\"')
                        lines.append(f'    {case_node} -->|"{condition_content}"| {branch_node}')

                        branch_id += 1
                    i += 1

                # Create merge point after all branches
                merge_node = f"Merge{node_id}"
                lines.append(f'    {merge_node}["Continue after CASE"]')

                # Connect all branches to merge point
                for bid in range(1, branch_id):
                    branch_node = f"Branch{node_id}_{bid}"
                    lines.append(f'    {branch_node} --> {merge_node}')

                previous_node = merge_node
                node_id += 1

            elif stmt['type'] == 'SEL_DECISION':
                # Parse SEL function properly
                sel_content = stmt["content"]

                # Extract the assignment target and SEL parameters
                sel_match = re.match(r'(.+?):=\s*SEL\s*\(\s*(.+?)\s*,\s*(.+?)\s*,\s*(.+?)\s*\)', sel_content,
                                     re.IGNORECASE)

                if sel_match:
                    target_var = sel_match.group(1).strip()
                    condition = sel_match.group(2).strip()
                    false_value = sel_match.group(3).strip()
                    true_value = sel_match.group(4).strip()

                    # Create SEL decision node with just the condition
                    sel_node = f"SEL{node_id}"
                    condition_content = condition.replace('"', '\\"')
                    lines.append(f'    {sel_node}{{"SEL: {condition_content}"}}')
                    lines.append(f'    {previous_node} --> {sel_node}')

                    # Create True branch (first value after condition)
                    true_node = f"SEL_True{node_id}"
                    true_assignment = f"{target_var} := {true_value}"
                    true_content = true_assignment.replace('"', '\\"')
                    lines.append(f'    {true_node}["{true_content}"]')
                    lines.append(f'    {sel_node} -->|True| {true_node}')

                    # Create False branch (second value after condition)
                    false_node = f"SEL_False{node_id}"
                    false_assignment = f"{target_var} := {false_value}"
                    false_content = false_assignment.replace('"', '\\"')
                    lines.append(f'    {false_node}["{false_content}"]')
                    lines.append(f'    {sel_node} -->|False| {false_node}')

                    # Create merge point
                    merge_node = f"Merge{node_id}"
                    lines.append(f'    {true_node} --> {merge_node}')
                    lines.append(f'    {false_node} --> {merge_node}')

                    previous_node = merge_node
                else:
                    # Fallback if SEL parsing fails
                    node_name = f"Action{node_id}"
                    content = stmt["content"].replace('"', '\\"')
                    lines.append(f'    {node_name}["{content}"]')
                    lines.append(f'    {previous_node} --> {node_name}')
                    previous_node = node_name

                node_id += 1

            elif stmt['type'] in ['FOR', 'WHILE', 'REPEAT']:
                node_name = f"Action{node_id}"
                content = stmt["content"].replace('"', '\\"')
                lines.append(f'    {node_name}["{content}"]')
                lines.append(f'    {previous_node} --> {node_name}')
                previous_node = node_name
                node_id += 1

            elif stmt['type'] == 'END_CONTROL':
                # Skip END_* statements as they're handled by their control structures
                pass

            else:
                # Regular statements - use full content without simplification
                node_name = f"Action{node_id}"
                content = stmt["content"].replace('"', '\\"')
                lines.append(f'    {node_name}["{content}"]')
                lines.append(f'    {previous_node} --> {node_name}')
                previous_node = node_name
                node_id += 1

            i += 1

        lines.append(f'    {previous_node} --> End["End: {pou_name}"]')

        return '\n'.join(lines)

    def _build_nested_if(self, if_stmt: Dict[str, Any], base_id: int, previous_node: str, end_node: str) -> List[str]:
        """Build nested IF statement"""
        lines = []

        if_node = f"If{base_id}"
        condition = if_stmt["content"].replace('"', '\\"')
        lines.append(f'    {if_node}{{"IF {condition}"}}')
        lines.append(f'    {previous_node} --> {if_node}')

        # Build THEN branch for nested IF
        then_start_node = f"ThenStart{base_id}"
        then_end_node = f"ThenEnd{base_id}"

        lines.append(f'    {if_node} -->|True| {then_start_node}["THEN branch"]')

        then_previous = then_start_node
        then_sub_id = base_id + 1

        for then_stmt in if_stmt['then_statements']:
            then_node_name = f"Then{then_sub_id}"
            then_content = then_stmt["content"].replace('"', '\\"')
            lines.append(f'    {then_node_name}["{then_content}"]')
            lines.append(f'    {then_previous} --> {then_node_name}')
            then_previous = then_node_name
            then_sub_id += 1

        lines.append(f'    {then_previous} --> {then_end_node}')

        # Build ELSE branch for nested IF
        else_start_node = f"ElseStart{base_id}"
        else_end_node = f"ElseEnd{base_id}"

        lines.append(f'    {if_node} -->|False| {else_start_node}["ELSE branch"]')

        else_previous = else_start_node
        else_sub_id = base_id + 100

        for else_stmt in if_stmt['else_statements']:
            else_node_name = f"Else{else_sub_id}"
            else_content = else_stmt["content"].replace('"', '\\"')
            lines.append(f'    {else_node_name}["{else_content}"]')
            lines.append(f'    {else_previous} --> {else_node_name}')
            else_previous = else_node_name
            else_sub_id += 1

        lines.append(f'    {else_previous} --> {else_end_node}')

        # Create merge point for nested IF
        merge_node = f"Merge{base_id}"
        lines.append(f'    {then_end_node} --> {merge_node}')
        lines.append(f'    {else_end_node} --> {merge_node}')
        lines.append(f'    {merge_node} --> {end_node}')

        return lines

    def _create_empty_flowchart(self, pou_name: str) -> str:
        """Create empty flowchart for POU with no code"""
        return f"""%% ST to Mermaid Flowchart Conversion
%% Program: {pou_name}
%% No ST code found

flowchart TD
    Start["Start: {pou_name}"]
    Start --> End["End: {pou_name} (No Code)"]
"""

    def _create_error_flowchart(self, pou_name: str, error_msg: str) -> str:
        """Create error flowchart"""
        return f"""%% ST to Mermaid Flowchart Conversion
%% Program: {pou_name}
%% Error processing ST code: {error_msg}

flowchart TD
    Start["Start: {pou_name}"]
    Start --> Error["Error: {error_msg}"]
    Error --> End["End: {pou_name}"]
"""