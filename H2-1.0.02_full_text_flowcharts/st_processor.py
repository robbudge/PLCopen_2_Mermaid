"""
ST (Structured Text) Processor for Codesys to Mermaid conversion
Updated with proper XHTML extraction and improved statement parsing
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
        IMPROVED: Better handling of CASE statements and control structures
        """
        statements = []
        if not st_code or not st_code.strip():
            return statements

        logger.info(f"Parsing ST code: {st_code[:100]}...")

        # First, let's handle CASE statements specially since they have a specific structure
        case_pattern = r'CASE\s+([^:]*?)\s+OF\s*(.*?)\s*END_CASE'
        case_matches = list(re.finditer(case_pattern, st_code, re.IGNORECASE | re.DOTALL))

        if case_matches:
            # Process CASE statements separately
            remaining_code = st_code
            for match in case_matches:
                # Add content before CASE
                before_case = remaining_code[:match.start()].strip()
                if before_case:
                    statements.extend(self._parse_simple_statements(before_case))

                # Process CASE statement
                case_var = match.group(1).strip()
                case_content = match.group(2).strip()

                # Add CASE start
                statements.append({
                    'type': 'CASE',
                    'content': case_var,
                    'raw': f"CASE {case_var} OF"
                })

                # Parse CASE branches
                branches = self._parse_case_branches(case_content)
                statements.extend(branches)

                # Add CASE end
                statements.append({
                    'type': 'END_CONTROL',
                    'content': 'END_CASE',
                    'raw': 'END_CASE'
                })

                remaining_code = remaining_code[match.end():]

            # Add any remaining code after last CASE
            if remaining_code.strip():
                statements.extend(self._parse_simple_statements(remaining_code))
        else:
            # No CASE statements, use regular parsing
            statements = self._parse_simple_statements(st_code)

        return statements

    def _parse_simple_statements(self, st_code: str) -> List[Dict[str, Any]]:
        """Parse simple statements (non-CASE)"""
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
        elif 'sel(' in stmt_lower:
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
        FIXED: Handles empty CASE branches as 'NA' and SEL as decision boxes
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

            if stmt['type'] == 'CASE':
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

            elif stmt['type'] == 'IF':
                node_name = f"Action{node_id}"
                content = stmt["content"].replace('"', '\\"')
                lines.append(f'    {node_name}{{"IF {content}"}}')
                lines.append(f'    {previous_node} --> {node_name}')

                # Create True and False branches
                true_node = f"True{node_id}"
                false_node = f"False{node_id}"
                lines.append(f'    {node_name} -->|True| {true_node}["Then branch"]')
                lines.append(f'    {node_name} -->|False| {false_node}["Else branch"]')

                # Create merge point
                merge_node = f"Merge{node_id}"
                lines.append(f'    {true_node} --> {merge_node}')
                lines.append(f'    {false_node} --> {merge_node}')

                previous_node = merge_node
                node_id += 1

            elif stmt['type'] == 'SEL_DECISION':
                # SEL function as decision box
                node_name = f"SEL{node_id}"
                content = stmt["content"].replace('"', '\\"')
                lines.append(f'    {node_name}{{"SEL {content}"}}')
                lines.append(f'    {previous_node} --> {node_name}')

                # Create True and False branches for SEL
                true_node = f"SEL_True{node_id}"
                false_node = f"SEL_False{node_id}"
                lines.append(f'    {node_name} -->|True| {true_node}["First value"]')
                lines.append(f'    {node_name} -->|False| {false_node}["Second value"]')

                # Create merge point
                merge_node = f"Merge{node_id}"
                lines.append(f'    {true_node} --> {merge_node}')
                lines.append(f'    {false_node} --> {merge_node}')

                previous_node = merge_node
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