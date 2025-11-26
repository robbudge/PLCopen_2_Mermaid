import re
from typing import List, Dict, Any


class LDProcessor:
    def __init__(self):
        self.debug_info = []
        self._add_debug("[LD_PROCESSOR] Ladder Diagram Processor initialized")

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
        """Generate Mermaid flowchart from Ladder Diagram code"""
        self.clear_debug()
        self._add_debug(f"[LD_PROCESSOR] Generating flowchart for POU: {pou_name}")
        self._add_debug(f"[LD_PROCESSOR] Code length: {len(code)} characters")

        # Basic parsing of LD elements
        lines = code.split('\n')
        self._add_debug(f"[LD_PROCESSOR] Found {len(lines)} lines of code")

        # Extract basic LD components
        contacts = self._extract_contacts(code)
        coils = self._extract_coils(code)
        networks = self._extract_networks(code)

        self._add_debug(f"[LD_PROCESSOR] Found {len(contacts)} contacts, {len(coils)} coils, {len(networks)} networks")

        # Generate simple Mermaid flowchart as placeholder
        mermaid_code = self._generate_placeholder_flowchart(pou_name, contacts, coils, networks)

        self._add_debug(f"[LD_PROCESSOR] Flowchart generation completed")
        return mermaid_code

    def _extract_contacts(self, code: str) -> List[str]:
        """Extract contact elements from LD code"""
        contacts = []
        # Basic contact patterns
        contact_patterns = [
            r'(\w+)\s*\(\s*\)',  # Basic contact
            r'(\w+)\s*\(\s*/\s*\)',  # Normally closed contact
        ]

        for pattern in contact_patterns:
            found = re.findall(pattern, code, re.IGNORECASE)
            contacts.extend(found)

        return list(set(contacts))  # Remove duplicates

    def _extract_coils(self, code: str) -> List[str]:
        """Extract coil elements from LD code"""
        coils = []
        # Basic coil patterns
        coil_patterns = [
            r'-\s*\(\s*\)\s*(\w+)',  # Basic coil
            r'-\s*\(\s*/\s*\)\s*(\w+)',  # Normally closed coil
            r'-\s*\(\s*S\s*\)\s*(\w+)',  # Set coil
            r'-\s*\(\s*R\s*\)\s*(\w+)',  # Reset coil
        ]

        for pattern in coil_patterns:
            found = re.findall(pattern, code, re.IGNORECASE)
            coils.extend(found)

        return list(set(coils))

    def _extract_networks(self, code: str) -> List[str]:
        """Extract network sections from LD code"""
        networks = []
        # Look for network comments or separators
        network_pattern = r'NETWORK\s*(\d+):?(.*)'
        networks_found = re.findall(network_pattern, code, re.IGNORECASE)

        for num, title in networks_found:
            networks.append(f"Network {num}: {title.strip()}")

        return networks

    def _generate_placeholder_flowchart(self, pou_name: str, contacts: List[str], coils: List[str], networks: List[str]) -> str:
        """Generate a placeholder flowchart for LD code"""
        mermaid_lines = [
            "flowchart TD",
            f"    Start([Start: {pou_name}])",
        ]

        # Add networks as subgraphs if available
        if networks:
            for i, network in enumerate(networks):
                mermaid_lines.append(f"    subgraph {network}")
                mermaid_lines.append(f"        direction LR")
                mermaid_lines.append(f"        N{i}_Start[Network {i}] --> N{i}_End[End Network]")
                mermaid_lines.append(f"    end")
                if i == 0:
                    mermaid_lines.append(f"    Start --> N{i}_Start")
                if i < len(networks) - 1:
                    mermaid_lines.append(f"    N{i}_End --> N{i+1}_Start")
        else:
            # Simple flow based on contacts and coils
            mermaid_lines.append("    Start --> ProcessLD[Process Ladder Logic]")

            if contacts:
                mermaid_lines.append("    ProcessLD --> CheckContacts[Check Contacts]")
                for i, contact in enumerate(contacts[:5]):  # Limit to first 5 contacts
                    mermaid_lines.append(f"    CheckContacts --> Contact{i}[Contact: {contact}]")

            if coils:
                mermaid_lines.append("    ProcessLD --> ActivateCoils[Activate Coils]")
                for i, coil in enumerate(coils[:5]):  # Limit to first 5 coils
                    mermaid_lines.append(f"    ActivateCoils --> Coil{i}[Coil: {coil}]")

        mermaid_lines.append("    ProcessLD --> End([End])")

        # Add note about LD processing
        mermaid_lines.append("")
        mermaid_lines.append("    %% Note: LD Processor is a placeholder")
        mermaid_lines.append(f"    %% Found {len(contacts)} contacts and {len(coils)} coils")
        mermaid_lines.append("    %% Full LD to flowchart conversion coming soon")

        return "\n".join(mermaid_lines)

    def get_supported_elements(self) -> List[str]:
        """Get list of supported LD elements"""
        return ["Contacts", "Coils", "Networks", "Branches"]