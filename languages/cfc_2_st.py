import xml.etree.ElementTree as ET
import re
from typing import List, Dict, Any, Tuple


class CFCToSTConverter:
    def __init__(self):
        self.debug_info = []
        self._add_debug("[CFC_TO_ST] CFC to ST Converter initialized")

    def _add_debug(self, message: str):
        """Add debug message with timestamp"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        debug_msg = f"[{timestamp}] {message}"
        self.debug_info.append(debug_msg)
        print(debug_msg)

    def clear_debug(self):
        """Clear debug information"""
        self.debug_info = []

    def get_debug_info(self) -> List[str]:
        """Get all debug information"""
        return self.debug_info

    def convert_cfc_to_st(self, cfc_xml: str) -> str:
        """Convert CFC XML to ST code with detailed debugging"""
        self.clear_debug()
        self._add_debug("[CFC_TO_ST] === START CFC TO ST CONVERSION ===")
        self._add_debug(f"[CFC_TO_ST] Input XML length: {len(cfc_xml)}")

        # Show only first 500 chars of XML to avoid clutter
        xml_preview = cfc_xml[:500] + "..." if len(cfc_xml) > 500 else cfc_xml
        self._add_debug(f"[CFC_TO_ST] Input XML preview:\n{xml_preview}")

        st_lines = []

        try:
            # Clean XML namespaces
            cfc_xml_clean = self._clean_xml_namespaces(cfc_xml)
            self._add_debug("[CFC_TO_ST] XML namespaces cleaned successfully")

            # Parse XML
            root = ET.fromstring(cfc_xml_clean)
            self._add_debug("[CFC_TO_ST] XML parsed successfully")

            # Count elements for debugging
            elements = {
                'inVariables': len(root.findall(".//inVariable")),
                'outVariables': len(root.findall(".//outVariable")),
                'blocks': len(root.findall(".//block")),
                'connectors': len(root.findall(".//connector"))
            }
            self._add_debug(f"[CFC_TO_ST] Element counts: {elements}")

            # Process direct variable assignments (inVariable -> outVariable)
            self._add_debug("[CFC_TO_ST] === PROCESSING DIRECT ASSIGNMENTS ===")
            direct_assignments = self._process_direct_assignments(root)
            st_lines.extend(direct_assignments)
            self._add_debug(f"[CFC_TO_ST] Generated {len(direct_assignments)} direct assignments")

            # Process function blocks
            self._add_debug("[CFC_TO_ST] === PROCESSING FUNCTION BLOCKS ===")
            block_code = self._process_function_blocks(root)
            st_lines.extend(block_code)
            self._add_debug(f"[CFC_TO_ST] Generated {len(block_code)} block statements")

            # Process other CFC elements
            self._add_debug("[CFC_TO_ST] === PROCESSING OTHER ELEMENTS ===")
            other_elements = self._process_other_elements(root)
            st_lines.extend(other_elements)
            self._add_debug(f"[CFC_TO_ST] Generated {len(other_elements)} other statements")

        except Exception as e:
            self._add_debug(f"[CFC_TO_ST] ERROR in CFC to ST conversion: {str(e)}")
            import traceback
            self._add_debug(f"[CFC_TO_ST] Traceback: {traceback.format_exc()}")

        self._add_debug("[CFC_TO_ST] === FINAL ST CODE GENERATION ===")
        final_st = "\n".join(st_lines) if st_lines else "// No ST code generated"

        # Add header to make the ST code clearly visible
        st_output = f"// === GENERATED ST CODE ===\n{final_st}\n// === END GENERATED ST CODE ==="

        self._add_debug("[CFC_TO_ST] FINAL ST CODE:")
        self._add_debug("=" * 50)
        for i, line in enumerate(st_lines, 1):
            self._add_debug(f"ST {i:2d}: {line}")
        self._add_debug("=" * 50)

        self._add_debug(f"[CFC_TO_ST] Total ST statements generated: {len(st_lines)}")
        self._add_debug("[CFC_TO_ST] === END CFC TO ST CONVERSION ===")

        return st_output


    def _clean_xml_namespaces(self, xml_string: str) -> str:
        """Clean XML namespaces for easier parsing"""
        self._add_debug("[CFC_TO_ST] Cleaning XML namespaces...")
        # Remove namespace prefixes from opening tags
        cleaned = re.sub(r'<ns\d*:', '<', xml_string)
        # Remove namespace prefixes from closing tags
        cleaned = re.sub(r'</ns\d*:', '</', cleaned)
        # Remove namespace declarations
        cleaned = re.sub(r' xmlns:ns\d*="[^"]*"', '', cleaned)
        self._add_debug("[CFC_TO_ST] XML namespaces cleaned")
        return cleaned

    def _process_direct_assignments(self, root: ET.Element) -> List[str]:
        """Process direct variable assignments (inVariable -> outVariable)"""
        st_lines = []
        out_vars = root.findall(".//outVariable")

        self._add_debug(f"[CFC_TO_ST] Processing {len(out_vars)} outVariables for direct assignments")

        for i, out_var in enumerate(out_vars):
            self._add_debug(f"[CFC_TO_ST] --- Processing outVariable {i + 1} ---")
            local_id = out_var.get('localId', '?')
            self._add_debug(f"[CFC_TO_ST] outVariable localId: {local_id}")

            # Get output expression
            out_expr_elem = out_var.find("expression")
            out_expression = out_expr_elem.text if out_expr_elem is not None else ""
            self._add_debug(f"[CFC_TO_ST] Output expression: '{out_expression}'")

            if not out_expression:
                self._add_debug(f"[CFC_TO_ST] No output expression, skipping")
                continue

            # Find source connection
            source_expr = self._find_source_expression(out_var, root)
            if source_expr:
                st_line = f"{out_expression} := {source_expr};"
                st_lines.append(st_line)
                self._add_debug(f"[CFC_TO_ST] ✓ Generated ST: {st_line}")
            else:
                self._add_debug(f"[CFC_TO_ST] ✗ No source expression found for output")

            self._add_debug(f"[CFC_TO_ST] --- End outVariable {i + 1} ---")

        return st_lines

    def _find_source_expression(self, element: ET.Element, root: ET.Element) -> str:
        """Find the source expression for an element by tracing connections"""
        self._add_debug(f"[CFC_TO_ST] Tracing source expression...")

        connection_point = element.find(".//connectionPointIn/connection")
        if connection_point is None:
            self._add_debug(f"[CFC_TO_ST] No connection point found")
            return ""

        source_id = connection_point.get('refLocalId')
        formal_param = connection_point.get('formalParameter', '')
        self._add_debug(f"[CFC_TO_ST] Connected to source ID: {source_id}, formalParameter: '{formal_param}'")

        source_element = self._find_element_by_local_id(root, source_id)
        if source_element is None:
            self._add_debug(f"[CFC_TO_ST] ✗ Source element not found for ID: {source_id}")
            return ""

        source_tag = source_element.tag
        self._add_debug(f"[CFC_TO_ST] Source element tag: {source_tag}, localId: {source_element.get('localId', '?')}")

        if source_tag == 'connector':
            self._add_debug(f"[CFC_TO_ST] Following connector...")
            # Trace through connector
            conn_connection = source_element.find(".//connectionPointIn/connection")
            if conn_connection is not None:
                actual_source_id = conn_connection.get('refLocalId')
                self._add_debug(f"[CFC_TO_ST] Connector leads to: {actual_source_id}")
                actual_source = self._find_element_by_local_id(root, actual_source_id)
                if actual_source:
                    return self._get_expression_from_element(actual_source)
                else:
                    self._add_debug(f"[CFC_TO_ST] ✗ Actual source not found for ID: {actual_source_id}")
            else:
                self._add_debug(f"[CFC_TO_ST] ✗ Connector has no connection")

        elif source_tag == 'inVariable':
            self._add_debug(f"[CFC_TO_ST] Source is inVariable, getting expression")
            return self._get_expression_from_element(source_element)

        elif source_tag == 'block':
            self._add_debug(f"[CFC_TO_ST] Source is block, computing output expression")
            return self._get_block_output_expression(source_element, root)

        self._add_debug(f"[CFC_TO_ST] ✗ Could not resolve source expression")
        return ""

    def _get_expression_from_element(self, element: ET.Element) -> str:
        """Get expression from various element types"""
        if element is None:
            return ""

        if element.tag == 'inVariable':
            expr_elem = element.find("expression")
            expr = expr_elem.text if expr_elem is not None and expr_elem.text else ""
            self._add_debug(f"[CFC_TO_ST] Got expression from inVariable: '{expr}'")
            return expr

        return ""

    def _process_function_blocks(self, root: ET.Element) -> List[str]:
        """Process function blocks and convert to ST"""
        st_lines = []
        blocks = root.findall(".//block")

        self._add_debug(f"[CFC_TO_ST] Processing {len(blocks)} function blocks")

        for i, block in enumerate(blocks):
            self._add_debug(f"[CFC_TO_ST] --- Processing block {i + 1} ---")

            block_type = block.get('typeName', 'UNKNOWN')
            local_id = block.get('localId', '?')
            execution_order = block.get('executionOrderId', '?')

            self._add_debug(
                f"[CFC_TO_ST] Block details - Type: {block_type}, ID: {local_id}, ExecutionOrder: {execution_order}")

            # Convert block based on type
            block_st = self._convert_block_to_st(block, root)
            if block_st:
                st_lines.append(block_st)
                self._add_debug(f"[CFC_TO_ST] ✓ Generated block ST: {block_st}")
            else:
                self._add_debug(f"[CFC_TO_ST] ✗ No ST generated for block")

            self._add_debug(f"[CFC_TO_ST] --- End block {i + 1} ---")

        return st_lines

    def _convert_block_to_st(self, block: ET.Element, root: ET.Element) -> str:
        """Convert a specific block type to ST"""
        block_type = block.get('typeName', '').upper()
        self._add_debug(f"[CFC_TO_ST] Converting block type: {block_type}")

        if block_type in ['OR', 'AND', 'XOR']:
            self._add_debug(f"[CFC_TO_ST] Logic block '{block_type}' detected - using boolean operator")
            return self._convert_logic_block(block, root, block_type)
        elif block_type in ['NOT']:
            self._add_debug(f"[CFC_TO_ST] NOT block detected - using NOT operator")
            return self._convert_not_block(block, root)
        elif block_type in ['ADD', 'SUB', 'MUL', 'DIV']:
            self._add_debug(f"[CFC_TO_ST] Math block '{block_type}' detected - using arithmetic operator")
            return self._convert_math_block(block, root, block_type)
        elif block_type in ['GT', 'GE', 'LT', 'LE', 'EQ', 'NE']:
            self._add_debug(f"[CFC_TO_ST] Comparison block '{block_type}' detected - using comparison operator")
            return self._convert_comparison_block(block, root, block_type)
        else:
            self._add_debug(f"[CFC_TO_ST] Generic block '{block_type}' detected - using function call syntax")
            return self._convert_generic_block(block, root)

    def _convert_logic_block(self, block: ET.Element, root: ET.Element, operator: str) -> str:
        """Convert logic blocks (OR, AND, XOR) to ST"""
        self._add_debug(f"[CFC_TO_ST] Processing logic block '{operator}'")

        # Get all inputs to the block
        inputs = self._get_block_inputs(block, root)
        self._add_debug(f"[CFC_TO_ST] Found {len(inputs)} inputs: {list(inputs.keys())}")

        output_expr = self._get_block_output_assignment(block, root)
        self._add_debug(f"[CFC_TO_ST] Output assignment: '{output_expr}'")

        if not output_expr:
            self._add_debug(f"[CFC_TO_ST] ✗ No output assignment found, skipping")
            return ""

        # For logic blocks, we need the input expressions, not parameter mapping
        input_expressions = []
        input_vars = block.findall(".//inputVariables/variable")

        for input_var in input_vars:
            formal_param = input_var.get('formalParameter')
            source_expr = self._find_source_expression(input_var, root)
            if source_expr:
                input_expressions.append(source_expr)
                self._add_debug(f"[CFC_TO_ST] Input '{formal_param}': {source_expr}")
            else:
                self._add_debug(f"[CFC_TO_ST] ✗ Could not find source for input '{formal_param}'")

        # Generate ST code
        if len(input_expressions) >= 2:
            st_operator = " OR " if operator == 'OR' else " AND " if operator == 'AND' else " XOR "
            input_expr = st_operator.join(input_expressions)
            st_code = f"{output_expr} := {input_expr};"
            self._add_debug(f"[CFC_TO_ST] ✓ Generated logic expression with {len(input_expressions)} inputs")
            return st_code
        elif input_expressions and output_expr:
            # Single input case (shouldn't happen for OR/AND but handle it)
            st_code = f"{output_expr} := {input_expressions[0]};"
            self._add_debug(f"[CFC_TO_ST] ✓ Generated single input logic expression")
            return st_code

        self._add_debug(f"[CFC_TO_ST] ✗ Insufficient inputs for logic block")
        return ""

    def _convert_not_block(self, block: ET.Element, root: ET.Element) -> str:
        """Convert NOT block to ST"""
        self._add_debug(f"[CFC_TO_ST] Processing NOT block")

        inputs = self._get_block_inputs(block, root)
        output_expr = self._get_block_output_assignment(block, root)

        if not output_expr:
            self._add_debug(f"[CFC_TO_ST] ✗ No output assignment found")
            return ""

        # For NOT block, get the first input
        input_expressions = []
        input_vars = block.findall(".//inputVariables/variable")

        for input_var in input_vars:
            source_expr = self._find_source_expression(input_var, root)
            if source_expr:
                input_expressions.append(source_expr)
                break  # NOT block typically has one input

        if input_expressions and output_expr:
            st_code = f"{output_expr} := NOT {input_expressions[0]};"
            self._add_debug(f"[CFC_TO_ST] ✓ Generated NOT expression")
            return st_code

        self._add_debug(f"[CFC_TO_ST] ✗ Could not find input for NOT block")
        return ""

    def _convert_math_block(self, block: ET.Element, root: ET.Element, operator: str) -> str:
        """Convert math blocks to ST"""
        self._add_debug(f"[CFC_TO_ST] Processing math block '{operator}'")

        inputs = self._get_block_inputs(block, root)
        output_expr = self._get_block_output_assignment(block, root)

        if not output_expr:
            self._add_debug(f"[CFC_TO_ST] ✗ No output assignment found")
            return ""

        # Get input expressions
        input_expressions = []
        input_vars = block.findall(".//inputVariables/variable")

        for input_var in input_vars:
            source_expr = self._find_source_expression(input_var, root)
            if source_expr:
                input_expressions.append(source_expr)

        if len(input_expressions) >= 2 and output_expr:
            st_operator = {
                'ADD': '+', 'SUB': '-', 'MUL': '*', 'DIV': '/'
            }.get(operator, '+')
            input_expr = f" {st_operator} ".join(input_expressions)
            st_code = f"{output_expr} := {input_expr};"
            self._add_debug(f"[CFC_TO_ST] ✓ Generated math expression with {len(input_expressions)} inputs")
            return st_code

        self._add_debug(f"[CFC_TO_ST] ✗ Insufficient inputs for math block")
        return ""

    def _convert_comparison_block(self, block: ET.Element, root: ET.Element, operator: str) -> str:
        """Convert comparison blocks to ST"""
        self._add_debug(f"[CFC_TO_ST] Processing comparison block '{operator}'")

        inputs = self._get_block_inputs(block, root)
        output_expr = self._get_block_output_assignment(block, root)

        if not output_expr:
            self._add_debug(f"[CFC_TO_ST] ✗ No output assignment found")
            return ""

        # Get input expressions
        input_expressions = []
        input_vars = block.findall(".//inputVariables/variable")

        for input_var in input_vars:
            source_expr = self._find_source_expression(input_var, root)
            if source_expr:
                input_expressions.append(source_expr)

        if len(input_expressions) >= 2 and output_expr:
            st_operator = {
                'GT': '>', 'GE': '>=', 'LT': '<', 'LE': '<=', 'EQ': '=', 'NE': '<>'
            }.get(operator, '=')
            input_expr = f" {st_operator} ".join(input_expressions)
            st_code = f"{output_expr} := {input_expr};"
            self._add_debug(f"[CFC_TO_ST] ✓ Generated comparison expression with {len(input_expressions)} inputs")
            return st_code

        self._add_debug(f"[CFC_TO_ST] ✗ Insufficient inputs for comparison block")
        return ""

    def _convert_generic_block(self, block: ET.Element, root: ET.Element) -> str:
        """Convert generic function block to ST"""
        block_type = block.get('typeName', 'UNKNOWN')
        self._add_debug(f"[CFC_TO_ST] Processing generic block '{block_type}'")

        inputs = self._get_block_inputs(block, root)
        output_expr = self._get_block_output_assignment(block, root)

        if not output_expr:
            self._add_debug(f"[CFC_TO_ST] ✗ No output assignment found")
            return ""

        if inputs and output_expr:
            input_str = ", ".join([f"{param}:={value}" for param, value in inputs.items()])
            st_code = f"{output_expr} := {block_type}({input_str});"
            self._add_debug(f"[CFC_TO_ST] ✓ Generated function call with {len(inputs)} parameters")
            return st_code

        self._add_debug(f"[CFC_TO_ST] ✗ No inputs found for generic block")
        return ""

    def _get_block_inputs(self, block: ET.Element, root: ET.Element) -> Dict[str, str]:
        """Get all inputs for a block as parameter->expression mapping"""
        inputs = {}
        input_vars = block.findall(".//inputVariables/variable")

        self._add_debug(f"[CFC_TO_ST] Getting inputs for block {block.get('localId', '?')}")

        for input_var in input_vars:
            formal_param = input_var.get('formalParameter', '?')
            source_expr = self._find_source_expression(input_var, root)
            if source_expr:
                inputs[formal_param] = source_expr
                self._add_debug(f"[CFC_TO_ST] ✓ Input '{formal_param}' -> '{source_expr}'")
            else:
                self._add_debug(f"[CFC_TO_ST] ✗ Could not find source for input '{formal_param}'")

        return inputs

    def _get_block_output_assignment(self, block: ET.Element, root: ET.Element) -> str:
        """Get what a block's output is assigned to"""
        local_id = block.get('localId')
        self._add_debug(f"[CFC_TO_ST] Finding output assignment for block {local_id}")

        # Find outVariables that connect to this block
        out_vars = root.findall(".//outVariable")
        for out_var in out_vars:
            connection = out_var.find(".//connectionPointIn/connection")
            if connection is not None and connection.get('refLocalId') == local_id:
                expr_elem = out_var.find("expression")
                if expr_elem is not None and expr_elem.text:
                    self._add_debug(f"[CFC_TO_ST] ✓ Block output assigned to: {expr_elem.text}")
                    return expr_elem.text

        # Also check connectors that might connect this block to outputs
        connectors = root.findall(".//connector")
        for connector in connectors:
            conn_connection = connector.find(".//connectionPointIn/connection")
            if conn_connection is not None and conn_connection.get('refLocalId') == local_id:
                # This connector might lead to an output
                connector_id = connector.get('localId')
                # Find outVariables connected to this connector
                for out_var in out_vars:
                    out_connection = out_var.find(".//connectionPointIn/connection")
                    if out_connection is not None and out_connection.get('refLocalId') == connector_id:
                        expr_elem = out_var.find("expression")
                        if expr_elem is not None and expr_elem.text:
                            self._add_debug(f"[CFC_TO_ST] ✓ Block output via connector to: {expr_elem.text}")
                            return expr_elem.text

        self._add_debug(f"[CFC_TO_ST] ✗ No output assignment found for block {local_id}")
        return ""

    def _get_block_output_expression(self, block: ET.Element, root: ET.Element) -> str:
        """Get the output expression for a block (used when block is source)"""
        self._add_debug(f"[CFC_TO_ST] Getting output expression for block {block.get('localId', '?')}")
        output_assignment = self._get_block_output_assignment(block, root)
        if output_assignment:
            # For blocks used as sources, we need to create the expression that computes the output
            block_type = block.get('typeName', '').upper()
            inputs = self._get_block_inputs(block, root)

            if block_type in ['OR', 'AND', 'XOR']:
                input_expressions = list(inputs.values())
                if len(input_expressions) >= 2:
                    st_operator = " OR " if block_type == 'OR' else " AND " if block_type == 'AND' else " XOR "
                    return f"({st_operator.join(input_expressions)})"

            # For other blocks, return the output assignment target
            return output_assignment

        return ""

    def _process_other_elements(self, root: ET.Element) -> List[str]:
        """Process other CFC elements that might need conversion"""
        st_lines = []
        # Add processing for other CFC elements as needed
        return st_lines

    def _find_element_by_local_id(self, root_element: ET.Element, local_id: str) -> ET.Element:
        """Find element by localId attribute"""
        if not local_id:
            return None

        for elem in root_element.iter():
            if elem.get('localId') == local_id:
                return elem
        return None

    def get_supported_block_types(self) -> List[str]:
        """Get list of supported block types"""
        return [
            'OR', 'AND', 'XOR', 'NOT',
            'ADD', 'SUB', 'MUL', 'DIV',
            'GT', 'GE', 'LT', 'LE', 'EQ', 'NE'
        ]
