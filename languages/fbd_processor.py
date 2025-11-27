import re
from typing import List, Dict, Any
from languages.cfc_2_st import CFCToSTConverter
from languages.sanitizer import MermaidSanitizer


class FBDProcessor:
    def __init__(self):
        self.debug_info = []
        self.cfc_converter = CFCToSTConverter()
        self.sanitizer = MermaidSanitizer()
        self._add_debug("[FBD_PROCESSOR] Function Block Diagram Processor initialized")

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

    def generate_flowchart(self, code: str, pou_name: str, pou_info: Dict[str, Any]) -> str:
        """Generate Mermaid flowchart from Function Block Diagram or CFC code"""
        self.clear_debug()
        self._add_debug(f"[FBD_PROCESSOR] Generating flowchart for POU: {pou_name}")
        self._add_debug(f"[FBD_PROCESSOR] Code length: {len(code)} characters")
        self._add_debug(f"[FBD_PROCESSOR] POU type: {pou_info.get('pouType', 'Unknown')}")

        # Check if this is CFC XML content
        is_cfc_xml = (
                code.strip().startswith('<CFC>') or
                code.strip().startswith('<ns0:CFC') or
                ':CFC' in code and '<' in code and '>' in code
        )

        if is_cfc_xml:
            self._add_debug("[FBD_PROCESSOR] Detected CFC XML content")
            # Use CFC to ST converter
            st_code = self.cfc_converter.convert_cfc_to_st(code)

            # Add CFC converter debug to our debug
            for debug_msg in self.cfc_converter.get_debug_info():
                self._add_debug(debug_msg)

            # Generate flowchart from ST code
            if st_code and st_code.strip() and not st_code.startswith("// No ST"):
                self._add_debug("[FBD_PROCESSOR] Generating flowchart from converted ST")
                return self._generate_flowchart_from_st(st_code, pou_name)
            else:
                self._add_debug("[FBD_PROCESSOR] No ST code generated, using fallback")
                return self._generate_cfc_fallback(code, pou_name)

        # Check if this is FBD text content
        lines = code.split('\n')
        self._add_debug(f"[FBD_PROCESSOR] Found {len(lines)} lines of code")

        # Check if this looks like FBD text content
        fbd_keywords = ['FUNCTION BLOCK', 'BLOCK', 'CONNECTION', 'IN=', 'OUT=', 'FB_']
        has_fbd_keywords = any(keyword in code.upper() for keyword in fbd_keywords)

        if has_fbd_keywords:
            self._add_debug("[FBD_PROCESSOR] Detected FBD text content")
            return self._generate_fbd_placeholder_flowchart(pou_name, code)
        else:
            self._add_debug("[FBD_PROCESSOR] No specific content type detected, using generic flowchart")
            return self._generate_generic_flowchart(pou_name, code)

    def _generate_flowchart_from_st(self, st_code: str, pou_name: str) -> str:
        """Generate flowchart from ST code with proper sanitization - NO TRUNCATION"""
        lines = st_code.split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('//')]

        # Use sanitizer for the POU name
        safe_pou_name = self.sanitizer.sanitize_label(pou_name)

        mermaid_lines = [
            "flowchart TD",
            f"    Start([Start: {safe_pou_name}])",
            "    Start --> ProcessST[Process ST Logic]",
        ]

        for i, line in enumerate(non_empty_lines[:10]):
            # Use sanitizer for the ST code line - NO TRUNCATION
            safe_line = self.sanitizer.sanitize_label(line.replace(';', '').strip())
            mermaid_lines.append(f"    ProcessST --> Step{i}[{safe_line}]")

        mermaid_lines.append("    ProcessST --> End([End])")
        mermaid_lines.append("")
        mermaid_lines.append("    %% Generated from CFC to ST conversion")
        mermaid_lines.append(f"    %% {len(non_empty_lines)} lines of ST code")

        return "\n".join(mermaid_lines)

    def _generate_cfc_fallback(self, cfc_xml: str, pou_name: str) -> str:
        """Generate fallback flowchart for CFC content when conversion fails"""
        self._add_debug("[FBD_PROCESSOR] Generating CFC fallback flowchart")

        # Simple counting of elements
        input_count = len(re.findall(r'<.*?inVariable', cfc_xml))
        output_count = len(re.findall(r'<.*?outVariable', cfc_xml))
        block_count = len(re.findall(r'<.*?block', cfc_xml))
        connection_count = len(re.findall(r'<.*?connector', cfc_xml))

        # Use sanitizer for the POU name
        safe_pou_name = self.sanitizer.sanitize_label(pou_name)

        mermaid_lines = [
            "flowchart TD",
            f"    Start([Start: {safe_pou_name}])",
            f"    Start --> ProcessCFC[Process CFC Diagram]",
            f"    ProcessCFC --> Inputs[Read {input_count} Inputs]",
            f"    ProcessCFC --> Blocks[Execute {block_count} Blocks]",
            f"    ProcessCFC --> Outputs[Write {output_count} Outputs]",
            f"    ProcessCFC --> Connections[Handle {connection_count} Connections]",
            f"    ProcessCFC --> End([End])",
            "",
            f"    %% CFC Function Block Diagram",
            f"    %% Inputs: {input_count}, Outputs: {output_count}",
            f"    %% Blocks: {block_count}, Connections: {connection_count}",
            f"    %% CFC to ST conversion failed - using fallback",
        ]

        return "\n".join(mermaid_lines)

    def _generate_fbd_placeholder_flowchart(self, pou_name: str, code: str) -> str:
        """Generate placeholder flowchart for FBD content with sanitization - NO TRUNCATION"""
        self._add_debug("[FBD_PROCESSOR] Generating FBD placeholder flowchart")

        lines = code.split('\n')

        # Use sanitizer for the POU name
        safe_pou_name = self.sanitizer.sanitize_label(pou_name)

        mermaid_lines = [
            "flowchart TD",
            f"    Start([Start: {safe_pou_name}])",
            "    Start --> ProcessFBD[Process Function Blocks]",
        ]

        # Extract basic FBD-like elements - NO TRUNCATION
        blocks_found = []
        connections_found = []
        variables_found = []

        for line in lines:
            line_upper = line.upper()
            if any(keyword in line_upper for keyword in ['BLOCK', 'FB_', 'FUNCTION']):
                clean_line = self.sanitizer.sanitize_label(line.strip())
                blocks_found.append(clean_line)
            elif any(keyword in line_upper for keyword in ['->', ':=', 'CONNECTION']):
                clean_line = self.sanitizer.sanitize_label(line.strip())
                connections_found.append(clean_line)
            elif any(keyword in line_upper for keyword in ['VAR', 'INPUT', 'OUTPUT']):
                clean_line = self.sanitizer.sanitize_label(line.strip())
                variables_found.append(clean_line)

        # Add blocks to flowchart
        if blocks_found:
            mermaid_lines.append("    ProcessFBD --> ExecuteBlocks[Execute Function Blocks]")
            for i, block in enumerate(blocks_found[:5]):
                mermaid_lines.append(f"    ExecuteBlocks --> Block{i}[{block}]")

        # Add connections to flowchart
        if connections_found:
            mermaid_lines.append("    ProcessFBD --> ProcessConnections[Process Connections]")
            for i, conn in enumerate(connections_found[:5]):
                mermaid_lines.append(f"    ProcessConnections --> Conn{i}[{conn}]")

        # Add variables to flowchart
        if variables_found:
            mermaid_lines.append("    ProcessFBD --> InitVariables[Initialize Variables]")
            for i, var in enumerate(variables_found[:5]):
                mermaid_lines.append(f"    InitVariables --> Var{i}[{var}]")

        mermaid_lines.append("    ProcessFBD --> End([End])")

        # Add note
        mermaid_lines.append("")
        mermaid_lines.append("    %% Note: FBD Processor Placeholder")
        mermaid_lines.append(
            f"    %% Found {len(blocks_found)} blocks, {len(connections_found)} connections, {len(variables_found)} variables")

        return "\n".join(mermaid_lines)

    def _generate_generic_flowchart(self, pou_name: str, code: str) -> str:
        """Generate generic flowchart for unknown content with sanitization - NO TRUNCATION"""
        self._add_debug("[FBD_PROCESSOR] Generating generic flowchart")

        lines = code.split('\n')
        non_empty_lines = [line.strip() for line in lines if line.strip() and not line.strip().startswith('//')]

        # Use sanitizer for the POU name
        safe_pou_name = self.sanitizer.sanitize_label(pou_name)

        mermaid_lines = [
            "flowchart TD",
            f"    Start([Start: {safe_pou_name}])",
            "    Start --> ProcessContent[Process Content]",
        ]

        # Add some content lines as steps - NO TRUNCATION
        for i, line in enumerate(non_empty_lines[:8]):
            # Use sanitizer for the content line
            safe_line = self.sanitizer.sanitize_label(line)
            mermaid_lines.append(f"    ProcessContent --> Step{i}[{safe_line}]")

        mermaid_lines.append("    ProcessContent --> End([End])")

        # Add note
        mermaid_lines.append("")
        mermaid_lines.append("    %% Note: Generic FBD Processing")
        mermaid_lines.append(f"    %% Processed {len(non_empty_lines)} lines of content")

        return "\n".join(mermaid_lines)

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return ["FBD", "CFC", "Function Block Diagram"]

    def get_supported_elements(self) -> List[str]:
        """Get list of supported FBD elements"""
        return [
            "Function Blocks",
            "Connections",
            "Variables",
            "Data Flow",
            "CFC Diagrams"
        ]