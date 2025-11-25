import re
from typing import List


class MermaidSanitizer:
    """Sanitizes text for Mermaid flowchart compatibility"""

    @staticmethod
    def sanitize_label(text: str) -> str:
        """
        Sanitize text for use in Mermaid node labels.
        Mermaid has specific rules for what characters are allowed in labels.
        """
        if not text:
            return ""

        # First, remove any existing HTML entities to avoid double encoding
        text = MermaidSanitizer._decode_html_entities(text)

        # Replace problematic characters with safe alternatives
        replacements = {
            # Parentheses - replace with unicode alternatives or remove
            '(': '&#40;',  # HTML entity for (
            ')': '&#41;',  # HTML entity for )

            # Quotes - replace with HTML entities
            '"': '&quot;',
            "'": '&apos;',

            # Angle brackets - replace with HTML entities
            '<': '&lt;',
            '>': '&gt;',

            # Ampersand - must be replaced first to avoid breaking other entities
            '&': '&amp;',

            # Square brackets - these can cause parsing issues in labels
            '[': '&#91;',
            ']': '&#93;',

            # Curly braces - these are used for Mermaid syntax
            '{': '&#123;',
            '}': '&#125;',

            # Pipe character - used for Mermaid links
            '|': '&#124;',

            # Semicolon - used to terminate HTML entities
            ';': '&#59;',

            # Colon - can cause issues in some contexts
            ':': '&#58;',

            # Backslash - escape character
            '\\': '&#92;',

            # Forward slash
            '/': '&#47;',

            # Newlines and tabs - replace with spaces
            '\n': ' ',
            '\r': ' ',
            '\t': ' ',
        }

        # Apply replacements
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)

        # Remove or replace any remaining control characters
        text = re.sub(r'[\x00-\x1F\x7F]', ' ', text)

        # Collapse multiple spaces
        text = re.sub(r'\s+', ' ', text)

        # Trim and return
        return text.strip()

    @staticmethod
    def sanitize_condition(text: str) -> str:
        """
        Sanitize text for use in Mermaid condition nodes (diamonds).
        Conditions have the same requirements as labels.
        """
        return MermaidSanitizer.sanitize_label(text)

    @staticmethod
    def sanitize_link_label(text: str) -> str:
        """
        Sanitize text for use in Mermaid link labels.
        Link labels are more restrictive than node labels.
        """
        if not text:
            return ""

        # Use the same sanitization as labels
        sanitized = MermaidSanitizer.sanitize_label(text)

        # Additional restrictions for link labels:
        # - Remove any remaining special characters that might break the link syntax
        sanitized = re.sub(r'[{}]', '', sanitized)

        return sanitized

    @staticmethod
    def _decode_html_entities(text: str) -> str:
        """
        Decode HTML entities to avoid double encoding.
        This is a basic implementation - for production use html.unescape instead.
        """
        # Basic HTML entity decoding
        entities = {
            '&amp;': '&',
            '&lt;': '<',
            '&gt;': '>',
            '&quot;': '"',
            '&apos;': "'",
            '&#40;': '(',
            '&#41;': ')',
            '&#91;': '[',
            '&#93;': ']',
            '&#123;': '{',
            '&#125;': '}',
            '&#124;': '|',
            '&#59;': ';',
            '&#58;': ':',
            '&#92;': '\\',
            '&#47;': '/',
        }

        for entity, char in entities.items():
            text = text.replace(entity, char)

        return text

    @staticmethod
    def validate_mermaid_syntax(mermaid_code: str) -> List[str]:
        """
        Validate Mermaid syntax and return any errors found.
        This is a basic validation - for comprehensive validation, use Mermaid's own parser.
        """
        errors = []
        lines = mermaid_code.split('\n')

        # Check for basic structure
        if not any(line.strip().startswith('flowchart') for line in lines):
            errors.append("Missing 'flowchart' declaration")

        # Check node definitions
        node_pattern = re.compile(r'^\s*(\w+)\[([^\]]+)\]$')
        decision_pattern = re.compile(r'^\s*(\w+)\{([^}]+)\}$')

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith('%'):
                continue

            # Check for node definitions
            if node_pattern.match(line) or decision_pattern.match(line):
                continue

            # Check for connections
            if '-->' in line:
                # Basic connection syntax check
                if not re.match(r'^\s*\w+\s*-->\s*\w+', line) and not re.match(r'^\s*\w+\s*-->\|.*\|\s*\w+', line):
                    errors.append(f"Line {i}: Invalid connection syntax: {line}")
                continue

            # Check for flowchart declaration
            if line.startswith('flowchart'):
                continue

            # If we get here, it's an unrecognized line
            errors.append(f"Line {i}: Unrecognized syntax: {line}")

        return errors

    @staticmethod
    def create_safe_node(node_id: str, label: str, node_type: str = "rectangle") -> str:
        """
        Create a safe Mermaid node with sanitized label.

        Args:
            node_id: The node identifier (e.g., "N1")
            label: The node label text
            node_type: "rectangle", "circle", "stadium", etc.

        Returns:
            Safe Mermaid node definition
        """
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
            return f"{node_id}[{safe_label}]"  # Default to rectangle

    @staticmethod
    def create_safe_connection(from_node: str, to_node: str, label: str = "") -> str:
        """
        Create a safe Mermaid connection with sanitized label.

        Args:
            from_node: Source node ID
            to_node: Target node ID
            label: Optional link label

        Returns:
            Safe Mermaid connection definition
        """
        if label:
            safe_label = MermaidSanitizer.sanitize_link_label(label)
            return f"    {from_node} -->|{safe_label}| {to_node}"
        else:
            return f"    {from_node} --> {to_node}"