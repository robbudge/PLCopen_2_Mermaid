import re
from typing import List, Dict, Any


class FBDProcessor:
    def __init__(self):
        self.debug_info = []
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
        """Generate Mermaid flowchart from Function Block Diagram code"""
        self.clear_debug()
        self._add_debug(f"[FBD_PROCESSOR] Generating flowchart for POU: {pou_name}")
        self._add_debug(f"[FBD_PROCESSOR] Code length: {len(code)} characters")

        # Basic parsing of FBD elements
        lines = code.split('\n')
        self._add_debug(f"[FBD_PROCESSOR] Found {len(lines)} lines of code")

        # Extract basic FBD components
        function_blocks = self._extract_function_blocks(code)
        connections = self._extract_connections(code)
        variables = self._extract_variables(code)

        self._add_debug(
            f"[FBD_PROCESSOR] Found {len(function_blocks)} function blocks, {len(connections)} connections, {len(variables)} variables")

        # Generate simple Mermaid flowchart as placeholder
        mermaid_code = self._generate_placeholder_flowchart(pou_name, function_blocks, connections, variables)

        self._add_debug(f"[FBD_PROCESSOR] Flowchart generation completed")
        return mermaid_code

    def _extract_function_blocks(self, code: str) -> List[Dict[str, str]]:
        """Extract function blocks from FBD code"""
        blocks = []

        # Look for common function block patterns
        block_patterns = [
            r'(\w+)\s*:\s*(\w+)',  # Instance : BlockType
            r'(\w+)\s*\(\s*\)',  # Function calls
        ]

        for pattern in block_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) == 2:
                    blocks.append({
                        'instance': match.group(1),
                        'type': match.group(2)
                    })
                else:
                    blocks.append({
                        'instance': match.group(1),
                        'type': 'FUNCTION'
                    })

        return blocks

    def _extract_connections(self, code: str) -> List[str]:
        """Extract connection patterns from FBD code"""
        connections = []

        # Look for connection patterns (variable assignments, etc.)
        connection_patterns = [
            r'(\w+)\s*:=\s*(\w+)',  # Simple assignment
            r'(\w+)\s*->\s*(\w+)',  # Connection arrow
        ]

        for pattern in connection_patterns:
            matches = re.finditer(pattern, code, re.IGNORECASE)
            for match in matches:
                connections.append(f"{match.group(1)} -> {match.group(2)}")

        return connections

    def _extract_variables(self, code: str) -> List[str]:
        """Extract variable names from FBD code"""
        variables = []

        # Look for variable patterns (avoiding keywords)
        var_pattern = r'\b([A-Za-z_]\w*)\b'
        keywords = {'VAR', 'END_VAR', 'IF', 'THEN', 'ELSE', 'END_IF', 'TRUE', 'FALSE'}

        matches = re.finditer(var_pattern, code, re.IGNORECASE)
        for match in matches:
            var_name = match.group(1)
            if var_name.upper() not in keywords and not var_name.isdigit():
                variables.append(var_name)

        return list(set(variables))  # Remove duplicates

    def _generate_placeholder_flowchart(self, pou_name: str, function_blocks: List[Dict], connections: List[str],
                                        variables: List[str]) -> str:
        """Generate a placeholder flowchart for FBD code"""
        mermaid_lines = [
            "flowchart TD",
            f"    Start([Start: {pou_name}])",
            "    Start --> InitVars[Initialize Variables]",
        ]

        # Add variable initialization
        if variables:
            mermaid_lines.append("    InitVars --> ProcessFBD[Process FBD]")
            for i, var in enumerate(variables[:5]):  # Limit to first 5 variables
                mermaid_lines.append(f"    ProcessFBD --> Var{i}[Var: {var}]")

        # Add function blocks
        if function_blocks:
            mermaid_lines.append("    ProcessFBD --> ExecuteBlocks[Execute Function Blocks]")
            for i, block in enumerate(function_blocks[:5]):  # Limit to first 5 blocks
                block_label = f"{block.get('instance', f'Block{i}')}: {block.get('type', 'FUNCTION')}"
                mermaid_lines.append(f"    ExecuteBlocks --> FB{i}[{block_label}]")

        # Add connections
        if connections:
            mermaid_lines.append("    ProcessFBD --> ProcessConnections[Process Connections]")
            for i, connection in enumerate(connections[:5]):  # Limit to first 5 connections
                mermaid_lines.append(f"    ProcessConnections --> Conn{i}[{connection}]")

        mermaid_lines.append("    ProcessFBD --> End([End])")

        # Add note about FBD processing
        mermaid_lines.append("")
        mermaid_lines.append("    %% Note: FBD Processor is a placeholder")
        mermaid_lines.append(f"    %% Found {len(function_blocks)} function blocks and {len(connections)} connections")
        mermaid_lines.append("    %% Full FBD to flowchart conversion coming soon")

        return "\n".join(mermaid_lines)

    def get_supported_elements(self) -> List[str]:
        """Get list of supported FBD elements"""
        return ["Function Blocks", "Connections", "Variables", "Data Flow"]