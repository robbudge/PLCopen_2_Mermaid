import re
from typing import List


class MermaidSanitizer:
    """Simplified sanitizer for Mermaid compatibility"""

    @staticmethod
    def sanitize_label(text: str) -> str:
        """
        Simplified sanitization - only escape the most critical characters
        """
        if not text:
            return ""

        # Only escape characters that absolutely break Mermaid syntax
        replacements = {
            # Curly braces break Mermaid syntax
            '{': '#123;',
            '}': '#125;',
            # Pipe breaks link labels
            '|': '#124;',
            # Square brackets break node syntax if unbalanced
            '[': '#91;',
            ']': '#93;',
            '(': '#40;',
            ')': '#41;',
            '=': '#61;'
        }

        # Apply minimal replacements
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)

        # Remove control characters
        text = re.sub(r'[\x00-\x1F\x7F]', ' ', text)

        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    @staticmethod
    def sanitize_condition(text: str) -> str:
        """Same as label sanitization"""
        return MermaidSanitizer.sanitize_label(text)

    @staticmethod
    def sanitize_link_label(text: str) -> str:
        """More restrictive for link labels"""
        safe_text = MermaidSanitizer.sanitize_label(text)
        # Remove any remaining problematic characters for links
        return re.sub(r'[{}|]', '', safe_text)

    # Keep the other methods the same as above...
    @staticmethod
    def create_safe_node(node_id: str, label: str, node_type: str = "rectangle") -> str:
        safe_label = MermaidSanitizer.sanitize_label(label)

        if node_type == "rectangle":
            return f"{node_id}[{safe_label}]"
        elif node_type == "circle":
            return f"{node_id}(({safe_label}))"
        elif node_type == "stadium":
            return f"{node_id}([{safe_label}])"
        elif node_type == "rhombus":
            return f"{node_id}{{{safe_label}}}"
        else:
            return f"{node_id}[{safe_label}]"

    @staticmethod
    def create_safe_connection(from_node: str, to_node: str, label: str = "") -> str:
        if label:
            safe_label = MermaidSanitizer.sanitize_link_label(label)
            return f"    {from_node} -->|{safe_label}| {to_node}"
        else:
            return f"    {from_node} --> {to_node}"

    @staticmethod
    def validate_mermaid_syntax(mermaid_code: str) -> List[str]:
        errors = []
        lines = mermaid_code.split('\n')

        if not any(line.strip().startswith('flowchart') for line in lines):
            errors.append("Missing 'flowchart' declaration")

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('%'):
                continue

            # Basic syntax checks
            if '-->' in line and not re.match(r'^\s*\w+\s*-->\s*\w+', line) and not re.match(
                    r'^\s*\w+\s*-->\|.*\|\s*\w+', line):
                errors.append(f"Line {i}: Invalid connection syntax")

        return errors