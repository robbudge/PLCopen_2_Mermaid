import re
from typing import List, Dict, Any
from languages.cfc_2_st import CFCToSTConverter
from languages.st_processor import STProcessor  # Add this import
from languages.sanitizer import MermaidSanitizer


class FBDProcessor:
    def __init__(self):
        self.debug_info = []
        self.cfc_converter = CFCToSTConverter()
        self.st_processor = STProcessor()  # Add ST processor
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

            # Generate flowchart from ST code using STProcessor
            if st_code and st_code.strip() and not st_code.startswith("// No ST"):
                self._add_debug("[FBD_PROCESSOR] Generating flowchart from converted ST using STProcessor")
                return self._generate_flowchart_from_st_with_processor(st_code, pou_name, pou_info)
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

    def _generate_flowchart_from_st_with_processor(self, st_code: str, pou_name: str, pou_info: Dict[str, Any]) -> str:
        """Generate flowchart from ST code using the STProcessor"""
        self._add_debug("[FBD_PROCESSOR] Using STProcessor to generate flowchart from ST code")

        # Extract the actual ST code from the wrapper
        # The CFC converter returns code with "// === GENERATED ST CODE ===" wrapper
        clean_st_code = self._extract_clean_st_code(st_code)

        self._add_debug(f"[FBD_PROCESSOR] Clean ST code length: {len(clean_st_code)}")
        self._add_debug(f"[FBD_PROCESSOR] Clean ST code preview: {clean_st_code[:200]}...")

        # Use STProcessor to generate the flowchart
        try:
            # Create a modified pou_info for the ST processor
            st_pou_info = {
                'pouType': 'Action',  # CFC actions are typically treated as actions
                'language': 'ST',
                'bodyLanguage': 'ST',
                'actions': [],
                'methods': []
            }

            # Generate flowchart using STProcessor
            mermaid_result = self.st_processor.generate_flowchart(clean_st_code, pou_name, st_pou_info)

            # Add ST processor debug to our debug
            for debug_msg in self.st_processor.get_debug_info():
                self._add_debug(debug_msg)

            self._add_debug(f"[FBD_PROCESSOR] STProcessor generated flowchart with length: {len(mermaid_result)}")
            return mermaid_result

        except Exception as e:
            self._add_debug(f"[FBD_PROCESSOR] Error using STProcessor: {e}")
            # Fallback to simple ST processing
            return self._generate_flowchart_from_st_fallback(st_code, pou_name)

    def _extract_clean_st_code(self, st_code: str) -> str:
        """Extract clean ST code from the CFC converter output"""
        lines = st_code.split('\n')
        clean_lines = []

        in_st_code = False
        for line in lines:
            if line.strip().startswith('// === GENERATED ST CODE ==='):
                in_st_code = True
                continue
            elif line.strip().startswith('// === END GENERATED ST CODE ==='):
                in_st_code = False
                continue
            elif in_st_code:
                # Skip comment lines within the ST code section
                if not line.strip().startswith('//'):
                    clean_lines.append(line)
            else:
                # Also capture ST code that's not wrapped in comments
                if line.strip() and not line.strip().startswith('//'):
                    clean_lines.append(line)

        # If we didn't find the wrapper, use all non-comment lines
        if not clean_lines:
            clean_lines = [line for line in lines if line.strip() and not line.strip().startswith('//')]

        return '\n'.join(clean_lines)

    def _generate_flowchart_from_st_fallback(self, st_code: str, pou_name: str) -> str:
        """Fallback method for ST code processing if STProcessor fails"""
        self._add_debug("[FBD_PROCESSOR] Using fallback ST processing")

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
        mermaid_lines.append("    %% Generated from CFC to ST conversion (Fallback)")
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