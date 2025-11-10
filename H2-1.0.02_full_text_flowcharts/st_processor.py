"""
ST (Structured Text) Processor for Codesys to Mermaid conversion
Updated with improved statement parsing while maintaining original class structure
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
        """Extract ST code from body element - handles xhtml wrapper"""
        try:
            # Method 1: Look for direct ST element
            st_elem = body_element.find(f"{self.namespace}ST")

            if st_elem is not None:
                logger.info(f"Found direct ST element for {name}")
                return st_elem.text if st_elem.text else ""

            # Method 2: Look for XHTML wrapper
            xhtml_elem = body_element.find(f"{self.namespace}xhtml")
            if xhtml_elem is not None:
                # Look for ST code within xhtml
                for elem in xhtml_elem.iter():
                    if elem.text and "(*" in elem.text and "*)" in elem.text:
                        logger.info(f"Found ST code in xhtml for {name}")
                        return elem.text

            logger.warning(f"No ST code found for {name}")
            return None

        except Exception as e:
            logger.error(f"Error extracting ST code for {name}: {e}")
            return None

    def process_code(self, st_code: str, pou_name: str) -> str:
        """
        Process Structured Text code and convert to Mermaid flowchart
        UPDATED: Improved statement parsing and structure detection
        """
        try:
            if not st_code:
                return self._create_empty_flowchart(pou_name)

            logger.info(f"Processing ST code for {pou_name}, length: {len(st_code)}")

            # Clean the code
            cleaned_code = self._clean_st_code(st_code)

            # Parse statements with improved parser
            statements = self._parse_st_statements(cleaned_code)
            logger.info(f"Parsed {len(statements)} statements for {pou_name}")

            # Build flowchart with proper structure
            flowchart = self._build_flowchart_from_statements(statements, pou_name, st_code)

            return flowchart

        except Exception as e:
            logger.error(f"Error processing ST code for {pou_name}: {e}")
            return self._create_error_flowchart(pou_name, str(e))

    def _clean_st_code(self, st_code: str) -> str:
        """Clean and normalize ST code"""
        if not st_code:
            return ""

        # Remove excessive whitespace but preserve structure
        lines = st_code.split('\n')
        cleaned_lines = []

        for line in lines:
            line = line.strip()
            if line:
                # Normalize whitespace within line but keep basic structure
                line = re.sub(r'\s+', ' ', line)
                cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    def _parse_st_statements(self, st_code: str) -> List[Dict[str, Any]]:
        """
        Parse ST code into structured statements
        IMPROVED: Better handling of complex expressions and control structures
        """
        statements = []
        if not st_code:
            return statements

        lines = st_code.split('\n')
        current_statement = ""
        paren_level = 0
        bracket_level = 0

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith('//') or line.startswith('(*'):
                i += 1
                continue

            # Process line character by character
            for char in line:
                if char == '(':
                    paren_level += 1
                elif char == ')':
                    paren_level -= 1
                elif char == '[':
                    bracket_level += 1
                elif char == ']':
                    bracket_level -= 1
                elif char == ';' and paren_level == 0 and bracket_level == 0:
                    # End of statement
                    if current_statement.strip():
                        stmt_info = self._classify_statement(current_statement.strip())
                        statements.append(stmt_info)
                    current_statement = ""
                    continue

                current_statement += char

            # Handle multi-line statements
            if current_statement.strip() and i < len(lines) - 1:
                # Check if this looks like an incomplete statement
                if not current_statement.strip().endswith(';'):
                    current_statement += ' '
                    i += 1
                    continue

            # If we have a complete statement without semicolon (like control structures)
            if current_statement.strip() and not current_statement.strip().endswith(';'):
                stmt_info = self._classify_statement(current_statement.strip())
                statements.append(stmt_info)
                current_statement = ""

            i += 1

        # Add any remaining statement
        if current_statement.strip():
            stmt_info = self._classify_statement(current_statement.strip())
            statements.append(stmt_info)

        return statements

    def _classify_statement(self, statement: str) -> Dict[str, Any]:
        """
        Classify statement type and simplify complex expressions
        IMPROVED: Better handling of long expressions
        """
        stmt_lower = statement.lower().strip()

        # Control structures
        if stmt_lower.startswith('if '):
            return {
                'type': 'IF',
                'content': self._simplify_complex_expression(statement),
                'raw': statement
            }
        elif stmt_lower.startswith('case '):
            return {
                'type': 'CASE',
                'content': self._simplify_complex_expression(statement),
                'raw': statement
            }
        elif stmt_lower.startswith('for '):
            return {
                'type': 'FOR',
                'content': self._simplify_complex_expression(statement),
                'raw': statement
            }
        elif stmt_lower.startswith('while '):
            return {
                'type': 'WHILE',
                'content': self._simplify_complex_expression(statement),
                'raw': statement
            }
        elif stmt_lower.startswith('repeat '):
            return {
                'type': 'REPEAT',
                'content': self._simplify_complex_expression(statement),
                'raw': statement
            }

        # Function calls
        elif re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\(.*\)$', statement.strip()):
            return {
                'type': 'FUNCTION_CALL',
                'content': self._simplify_complex_expression(statement),
                'raw': statement
            }

        # Assignments
        elif ':=' in statement:
            return {
                'type': 'ASSIGNMENT',
                'content': self._simplify_assignment(statement),
                'raw': statement
            }

        # Default
        return {
            'type': 'STATEMENT',
            'content': self._simplify_complex_expression(statement),
            'raw': statement
        }

    def _simplify_complex_expression(self, expr: str) -> str:
        """
        Simplify complex expressions for better readability
        IMPROVED: Better handling of long expressions
        """
        if len(expr) <= 80:
            return expr

        # Handle function calls
        if '(' in expr and ')' in expr:
            match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_\.]*\s*)\(', expr)
            if match:
                func_name = match.group(1).strip()
                return f"{func_name}(...)"

        # Handle assignments
        if ':=' in expr:
            parts = expr.split(':=', 1)
            if len(parts) == 2:
                left = parts[0].strip()
                right = parts[1].strip()
                if len(right) > 60:
                    return f"{left} := complex_expr(...)"

        # Generic simplification
        if len(expr) > 80:
            return "complex_expression"

        return expr

    def _simplify_assignment(self, assignment: str) -> str:
        """Simplify assignment statements"""
        parts = assignment.split(':=', 1)
        if len(parts) == 2:
            left = parts[0].strip()
            right = parts[1].strip()

            if len(right) > 50:
                if '(' in right and ')' in right:
                    return f"{left} ← complex_expr(...)"
                else:
                    return f"{left} ← expression"

            return f"{left} ← {right}"

        return assignment

    def _build_flowchart_from_statements(self, statements: List[Dict[str, Any]], pou_name: str,
                                         original_code: str) -> str:
        """
        Build Mermaid flowchart from parsed statements
        IMPROVED: Creates proper visual structure instead of single massive node
        """
        lines = []

        # Header with metadata
        lines.append('%% ST to Mermaid Flowchart Conversion')
        lines.append(f'%% Program: {pou_name}')
        lines.append(f'%% Original code length: {len(original_code)} characters')

        code_lines = original_code.split('\n')
        non_empty_lines = [line for line in code_lines if line.strip()]
        lines.append(f'%% Lines: {len(code_lines)} total, {len(non_empty_lines)} non-empty')

        # Calculate max line length
        max_line_len = max([len(line) for line in code_lines]) if code_lines else 0
        lines.append(f'%% Max line length: {max_line_len} characters')

        # Line length analysis
        if max_line_len > 100:
            lines.append('%% Long lines detected - consider simplification')
        else:
            lines.append('%% Line lengths within reasonable limits')

        lines.append('')
        lines.append('flowchart TD')
        lines.append(f'    Start["Start: {pou_name}"]')

        node_id = 1
        previous_node = "Start"

        for stmt in statements:
            node_name = f"Action{node_id}"
            content = stmt["content"].replace('"', '\\"')

            if stmt['type'] == 'IF':
                lines.append(f'    {node_name}{{"IF Condition"}}')
                lines.append(f'    {previous_node} --> {node_name}')
                # Add the condition as a separate node
                cond_node = f"Cond{node_id}"
                lines.append(f'    {cond_node}["Condition: {content}"]')
                lines.append(f'    {node_name} --> {cond_node}')
                previous_node = cond_node

            elif stmt['type'] == 'CASE':
                lines.append(f'    {node_name}{{"CASE Statement"}}')
                lines.append(f'    {previous_node} --> {node_name}')
                previous_node = node_name

            elif stmt['type'] in ['FOR', 'WHILE', 'REPEAT']:
                lines.append(f'    {node_name}["Loop: {content}"]')
                lines.append(f'    {previous_node} --> {node_name}')
                previous_node = node_name

            else:
                # Regular statements
                lines.append(f'    {node_name}["{content}"]')
                lines.append(f'    {previous_node} --> {node_name}')
                previous_node = node_name

            node_id += 1

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