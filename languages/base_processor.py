from abc import ABC, abstractmethod
from typing import List, Dict, Any
from .sanitizer import MermaidSanitizer


class BaseLanguageProcessor(ABC):
    """Abstract base class for all language processors"""

    def __init__(self):
        self.debug_info = []
        self.sanitizer = MermaidSanitizer()

    @abstractmethod
    def can_process(self, language: str) -> bool:
        """Check if this processor can handle the given language"""
        pass

    @abstractmethod
    def generate_flowchart(self, code: str, pou_name: str) -> str:
        """Generate Mermaid flowchart from code"""
        pass

    def _add_debug(self, message: str):
        """Add debug message"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        debug_msg = f"[{timestamp}] {message}"
        self.debug_info.append(debug_msg)
        print(f"[{self.__class__.__name__}] {debug_msg}")

    def get_debug_info(self) -> List[str]:
        """Get all debug messages"""
        return self.debug_info

    def clear_debug(self):
        """Clear debug messages"""
        self.debug_info = []

    def _sanitize_label(self, text: str) -> str:
        """Sanitize text for Mermaid node labels"""
        return self.sanitizer.sanitize_label(text)

    def _sanitize_condition(self, text: str) -> str:
        """Sanitize text for Mermaid condition nodes"""
        return self.sanitizer.sanitize_condition(text)

    def _sanitize_link_label(self, text: str) -> str:
        """Sanitize text for Mermaid link labels"""
        return self.sanitizer.sanitize_link_label(text)

    def _create_safe_node(self, node_id: str, label: str, node_type: str = "rectangle") -> str:
        """Create a safe Mermaid node with sanitized label"""
        return self.sanitizer.create_safe_node(node_id, label, node_type)

    def _create_safe_connection(self, from_node: str, to_node: str, label: str = "") -> str:
        """Create a safe Mermaid connection with sanitized label"""
        return self.sanitizer.create_safe_connection(from_node, to_node, label)

    def _validate_mermaid_output(self, mermaid_code: str) -> List[str]:
        """Validate generated Mermaid code for syntax errors"""
        return self.sanitizer.validate_mermaid_syntax(mermaid_code)