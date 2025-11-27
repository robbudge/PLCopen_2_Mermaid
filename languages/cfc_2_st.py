import xml.etree.ElementTree as ET
import re
from typing import List, Dict, Any


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
        self._add_debug(f"[CFC_TO_ST] Input XML:\n{cfc_xml}")

        st_lines = []

        try:
            # Clean XML namespaces
            cfc_xml_clean = self._clean_xml_namespaces(cfc_xml)

            self._add_debug("[CFC_TO_ST] === CLEANED XML ===")
            self._add_debug(cfc_xml_clean)

            # Parse XML
            root = ET.fromstring(cfc_xml_clean)
            self._add_debug("[CFC_TO_ST] XML parsed successfully")

            # Process direct variable assignments (inVariable -> outVariable)
            st_lines.extend(self._process_direct_assignments(root))

            # Process function blocks
            st_lines.extend(self._process_function_blocks(root))

            # Process other CFC elements
            st_lines.extend(self._process_other_elements(root))

        except Exception as e:
            self._add_debug(f"[CFC_TO_ST] Error in CFC to ST conversion: {str(e)}")
            import traceback
            self._add_debug(f"[CFC_TO_ST] Traceback: {traceback.format_exc()}")

        self._add_debug("[CFC_TO_ST] === FINAL ST CODE ===")
        final_st = "\n".join(st_lines) if st_lines else "// No ST code generated"
        self._add_debug(final_st)
        self._add_debug("[CFC_TO_ST] === END CFC TO ST CONVERSION ===")

        return final_st

    def _clean_xml_namespaces(self, xml_string: str) -> str:
        """Clean XML namespaces for easier parsing"""
        # Remove namespace prefixes from opening tags
        cleaned = re.sub(r'<ns\d*:', '<', xml_string)
        # Remove namespace prefixes from closing tags
        cleaned = re.sub(r'</ns\d*:', '</', cleaned)
        # Remove namespace declarations
        cleaned = re.sub(r' xmlns:ns\d*="[^"]*"', '', cleaned)
        return cleaned

    def _process_direct_assignments(self, root: ET.Element) -> List[str]:
        """Process direct variable assignments (inVariable -> outVariable)"""
        st_lines = []
        out_vars = root.findall(".//outVariable")

        self._add_debug(f"[CFC_TO_ST] Processing {len(out_vars)} outVariables for direct assignments")

        for i, out_var in enumerate(out_vars):
            self._add_debug(f"[CFC_TO_ST] --- Processing outVariable {i + 1} ---")

            # Get output expression
            out_expr_elem = out_var.find("expression")
            out_expression = out_expr_elem.text if out_expr_elem is not None else ""
            self._add_debug(f"[CFC_TO_ST] Output expression: {out_expression}")

            if not out_expression:
                continue

            # Find source connection
            source_expr = self._find_source_expression(out_var, root)
            if source_expr:
                st_line = f"{out_expression} := {source_expr};"
                st_lines.append(st_line)
                self._add_debug(f"[CFC_TO_ST] Generated ST: {st_line}")
            else:
                self._add_debug(f"[CFC_TO_ST] No source expression found for output")

            self._add_debug(f"[CFC_TO_ST] --- End outVariable {i + 1} ---")

        return st_lines

    def _find_source_expression(self, element: ET.Element, root: ET.Element) -> str:
        """Find the source expression for an element by tracing connections"""
        connection_point = element.find(".//connectionPointIn/connection")
        if connection_point is None:
            return ""

        source_id = connection_point.get('refLocalId')
        self._add_debug(f"[CFC_TO_ST] Connected to source ID: {source_id}")

        source_element = self._find_element_by_local_id(root, source_id)
        if source_element is None:
            self._add_debug(f"[CFC_TO_ST] Source element not found for ID: {source_id}")
            return ""

        source_tag = source_element.tag
        self._add_debug(f"[CFC_TO_ST] Source element tag: {source_tag}")

        if source_tag == 'connector':
            # Trace through connector
            conn_connection = source_element.find(".//connectionPointIn/connection")
            if conn_connection is not None:
                actual_source_id = conn_connection.get('refLocalId')
                self._add_debug(f"[CFC_TO_ST] Connector leads to: {actual_source_id}")
                actual_source = self._find_element_by_local_id(root, actual_source_id)
                return self._get_expression_from_element(actual_source)
            else:
                self._add_debug(f"[CFC_TO_ST] Connector has no connection")

        elif source_tag == 'inVariable':
            return self._get_expression_from_element(source_element)

        elif source_tag == 'block':
            # For blocks, we need to compute the block output
            block_type = source_element.get('typeName', 'UNKNOWN')
            self._add_debug(f"[CFC_TO_ST] Source is block type: {block_type}")
            return self._get_block_output_expression(source_element, root)

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
            self._add_debug(f"[CFC_TO_ST] Block type: {block_type}, ID: {local_id}")

            # Convert block based on type
            block_st = self._convert_block_to_st(block, root)
            if block_st:
                st_lines.append(block_st)
                self._add_debug(f"[CFC_TO_ST] Generated block ST: {block_st}")
            else:
                self._add_debug(f"[CFC_TO_ST] No ST generated for block")

            self._add_debug(f"[CFC_TO_ST] --- End block {i + 1} ---")

        return st_lines

    def _convert_block_to_st(self, block: ET.Element, root: ET.Element) -> str:
        """Convert a specific block type to ST"""
        block_type = block.get('typeName', '').upper()

        if block_type in ['OR', 'AND', 'XOR']:
            return self._convert_logic_block(block, root, block_type)
        elif block_type in ['NOT']:
            return self._convert_not_block(block, root)
        else:
            return self._convert_generic_block(block, root)

    def _convert_logic_block(self, block: ET.Element, root: ET.Element, operator: str) -> str:
        """Convert logic blocks (OR, AND, XOR) to ST"""
        # Get all inputs to the block
        inputs = []
        input_vars = block.findall(".//inputVariables/variable")

        for input_var in input_vars:
            connection = input_var.find(".//connection")
            if connection is not None:
                source_id = connection.get('refLocalId')
                source_element = self._find_element_by_local_id(root, source_id)
                if source_element is not None and source_element.tag == 'inVariable':
                    source_expr = self._get_expression_from_element(source_element)
                    if source_expr:
                        inputs.append(source_expr)
                        self._add_debug(f"[CFC_TO_ST] Block input: {source_expr}")

        # Find what this block outputs to
        output_expr = self._get_block_output_assignment(block, root)

        # Generate ST code
        if len(inputs) >= 2 and output_expr:
            st_operator = " OR " if operator == 'OR' else " AND " if operator == 'AND' else " XOR "
            input_expr = st_operator.join(inputs)
            return f"{output_expr} := {input_expr};"
        elif inputs and output_expr:
            # Single input case (shouldn't happen for OR/AND but handle it)
            return f"{output_expr} := {inputs[0]};"

        return ""

    def _get_block_output_assignment(self, block: ET.Element, root: ET.Element) -> str:
        """Get what a block's output is assigned to"""
        local_id = block.get('localId')

        # Find outVariables that connect to this block
        out_vars = root.findall(".//outVariable")
        for out_var in out_vars:
            connection = out_var.find(".//connectionPointIn/connection")
            if connection is not None and connection.get('refLocalId') == local_id:
                expr_elem = out_var.find("expression")
                if expr_elem is not None and expr_elem.text:
                    self._add_debug(f"[CFC_TO_ST] Block output assigned to: {expr_elem.text}")
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
                            self._add_debug(f"[CFC_TO_ST] Block output via connector to: {expr_elem.text}")
                            return expr_elem.text

        self._add_debug(f"[CFC_TO_ST] No output assignment found for block {local_id}")
        return ""

    def _find_source_expression(self, element: ET.Element, root: ET.Element) -> str:
        """Find the source expression for an element by tracing connections"""
        connection_point = element.find(".//connectionPointIn/connection")
        if connection_point is None:
            return ""

        source_id = connection_point.get('refLocalId')
        self._add_debug(f"[CFC_TO_ST] Connected to source ID: {source_id}")

        source_element = self._find_element_by_local_id(root, source_id)
        if source_element is None:
            return ""

        source_tag = source_element.tag
        self._add_debug(f"[CFC_TO_ST] Source element tag: {source_tag}")

        if source_tag == 'connector':
            # Trace through connector
            conn_connection = source_element.find(".//connectionPointIn/connection")
            if conn_connection is not None:
                actual_source_id = conn_connection.get('refLocalId')
                self._add_debug(f"[CFC_TO_ST] Connector leads to: {actual_source_id}")
                actual_source = self._find_element_by_local_id(root, actual_source_id)
                return self._get_expression_from_element(actual_source)

        elif source_tag == 'inVariable':
            return self._get_expression_from_element(source_element)

        elif source_tag == 'block':
            return self._get_block_output_expression(source_element, root)

        return ""

    def _get_expression_from_element(self, element: ET.Element) -> str:
        """Get expression from various element types"""
        if element is None:
            return ""

        if element.tag == 'inVariable':
            expr_elem = element.find("expression")
            return expr_elem.text if expr_elem is not None and expr_elem.text else ""

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
            self._add_debug(f"[CFC_TO_ST] Block type: {block_type}, ID: {local_id}")

            # Convert block based on type
            block_st = self._convert_block_to_st(block, root)
            if block_st:
                st_lines.append(block_st)
                self._add_debug(f"[CFC_TO_ST] Generated block ST: {block_st}")

            self._add_debug(f"[CFC_TO_ST] --- End block {i + 1} ---")

        return st_lines

    def _convert_block_to_st(self, block: ET.Element, root: ET.Element) -> str:
        """Convert a specific block type to ST"""
        block_type = block.get('typeName', '').upper()

        if block_type in ['OR', 'AND', 'XOR']:
            return self._convert_logic_block(block, root, block_type)
        elif block_type in ['NOT']:
            return self._convert_not_block(block, root)
        elif block_type in ['ADD', 'SUB', 'MUL', 'DIV']:
            return self._convert_math_block(block, root, block_type)
        elif block_type in ['GT', 'GE', 'LT', 'LE', 'EQ', 'NE']:
            return self._convert_comparison_block(block, root, block_type)
        else:
            return self._convert_generic_block(block, root)

    def _convert_logic_block(self, block: ET.Element, root: ET.Element, operator: str) -> str:
        """Convert logic blocks (OR, AND, XOR) to ST"""
        inputs = self._get_block_inputs(block, root)
        output_expr = self._get_block_output_assignment(block, root)

        if len(inputs) >= 2 and output_expr:
            st_operator = " OR " if operator == 'OR' else " AND " if operator == 'AND' else " XOR "
            input_expr = st_operator.join(inputs)
            return f"{output_expr} := {input_expr};"

        return ""

    def _convert_not_block(self, block: ET.Element, root: ET.Element) -> str:
        """Convert NOT block to ST"""
        inputs = self._get_block_inputs(block, root)
        output_expr = self._get_block_output_assignment(block, root)

        if inputs and output_expr:
            return f"{output_expr} := NOT {inputs[0]};"

        return ""

    def _convert_math_block(self, block: ET.Element, root: ET.Element, operator: str) -> str:
        """Convert math blocks to ST"""
        inputs = self._get_block_inputs(block, root)
        output_expr = self._get_block_output_assignment(block, root)

        if len(inputs) >= 2 and output_expr:
            st_operator = {
                'ADD': '+', 'SUB': '-', 'MUL': '*', 'DIV': '/'
            }.get(operator, '+')
            input_expr = f" {st_operator} ".join(inputs)
            return f"{output_expr} := {input_expr};"

        return ""

    def _convert_comparison_block(self, block: ET.Element, root: ET.Element, operator: str) -> str:
        """Convert comparison blocks to ST"""
        inputs = self._get_block_inputs(block, root)
        output_expr = self._get_block_output_assignment(block, root)

        if len(inputs) >= 2 and output_expr:
            st_operator = {
                'GT': '>', 'GE': '>=', 'LT': '<', 'LE': '<=', 'EQ': '=', 'NE': '<>'
            }.get(operator, '=')
            input_expr = f" {st_operator} ".join(inputs)
            return f"{output_expr} := {input_expr};"

        return ""

    def _convert_generic_block(self, block: ET.Element, root: ET.Element) -> str:
        """Convert generic function block to ST"""
        block_type = block.get('typeName', 'UNKNOWN')
        inputs = self._get_block_inputs(block, root)
        output_expr = self._get_block_output_assignment(block, root)

        if inputs and output_expr:
            input_str = ", ".join([f"{param}:={value}" for param, value in inputs.items()])
            return f"{output_expr} := {block_type}({input_str});"

        return ""

    def _get_block_inputs(self, block: ET.Element, root: ET.Element) -> Dict[str, str]:
        """Get all inputs for a block as parameter->expression mapping"""
        inputs = {}
        input_vars = block.findall(".//inputVariables/variable")

        for input_var in input_vars:
            formal_param = input_var.get('formalParameter', '?')
            source_expr = self._find_source_expression(input_var, root)
            if source_expr:
                inputs[formal_param] = source_expr

        return inputs

    def _get_block_output_assignment(self, block: ET.Element, root: ET.Element) -> str:
        """Get what a block's output is assigned to"""
        local_id = block.get('localId')

        # Find outVariables that connect to this block
        out_vars = root.findall(".//outVariable")
        for out_var in out_vars:
            connection = out_var.find(".//connectionPointIn/connection")
            if connection is not None and connection.get('refLocalId') == local_id:
                expr_elem = out_var.find("expression")
                if expr_elem is not None and expr_elem.text:
                    return expr_elem.text

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