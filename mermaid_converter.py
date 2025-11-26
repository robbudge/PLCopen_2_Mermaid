import re
from typing import Dict, List, Any
from languages.st_processor import STProcessor
from languages.ld_processor import LDProcessor
from languages.fbd_processor import FBDProcessor


class MermaidConverter:
    def __init__(self):
        self.debug_info = []
        self._add_debug("[CONVERTER] Mermaid Converter initialized")

        # Initialize language processors
        self.processors = {
            'ST': STProcessor(),
            'LD': LDProcessor(),
            'FBD': FBDProcessor(),
        }
        self._add_debug(f"[CONVERTER] Available processors: {list(self.processors.keys())}")

    def _add_debug(self, message: str):
        """Add debug message with timestamp"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        debug_msg = f"[{timestamp}] {message}"
        self.debug_info.append(debug_msg)
        print(debug_msg)

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

    # In mermaid_converter.py, update the _get_processor method:
    def _get_processor(self, language: str):
        """Get the appropriate processor for the language"""
        language_upper = language.upper()

        # Map language variations to known processors
        language_map = {
            'ST': 'ST',
            'STRUCTURED TEXT': 'ST',
            'UNKNOWN': 'ST',  # Default to ST for unknown
            'LD': 'LD',
            'LADDER': 'LD',
            'LADDER DIAGRAM': 'LD',
            'FBD': 'FBD',
            'FUNCTION BLOCK DIAGRAM': 'FBD',
            'CFC': 'FBD',  # Map CFC to FBD processor
        }

        mapped_language = language_map.get(language_upper, 'ST')
        processor = self.processors.get(mapped_language)

        if processor:
            self._add_debug(f"[CONVERTER] Using {mapped_language} processor for language: {language}")
        else:
            self._add_debug(
                f"[CONVERTER] No processor available for language: {language} (mapped to: {mapped_language})")

        return processor
    def convert_pou_to_mermaid(self, parser, pou_name: str) -> str:
        """Convert a POU to Mermaid flowchart"""
        self.clear_debug()

        # Get POU information including actions and methods
        pous = parser.get_pous()
        pou_info = pous.get(pou_name, {})

        self._add_debug(f"[CONVERTER] Converting POU: {pou_name}")
        self._add_debug(f"[CONVERTER] POU Type: {pou_info.get('pouType', 'Unknown')}")
        self._add_debug(f"[CONVERTER] Language: {pou_info.get('language', 'Unknown')}")

        # Log available actions and methods for this POU
        actions = pou_info.get('actions', [])
        methods = pou_info.get('methods', [])

        self._add_debug(f"[CONVERTER] Available actions: {len(actions)}")
        for action in actions:
            action_info = pou_info.get('actionsInfo', {}).get(action, {})
            action_lang = action_info.get('language', 'Unknown')
            action_body_lang = action_info.get('bodyLanguage', 'Unknown')
            action_body_len = len(action_info.get('body', ''))
            self._add_debug(
                f"[CONVERTER]   - {action} (lang: {action_lang}, body: {action_body_lang}, length: {action_body_len})")

        self._add_debug(f"[CONVERTER] Available methods: {len(methods)}")
        for method in methods:
            method_info = pou_info.get('methodsInfo', {}).get(method, {})
            method_lang = method_info.get('language', 'Unknown')
            method_body_lang = method_info.get('bodyLanguage', 'Unknown')
            method_body_len = len(method_info.get('body', ''))
            self._add_debug(
                f"[CONVERTER]   - {method} (lang: {method_lang}, body: {method_body_lang}, length: {method_body_len})")

        # Get the appropriate processor
        language = pou_info.get('language', 'UNKNOWN').upper()
        processor = self._get_processor(language)

        if not processor:
            self._add_debug(f"[CONVERTER] No processor found for language: {language}")
            return f"%% No processor available for language: {language}"

        # Get the code
        code = pou_info.get('body', '')
        if not code:
            self._add_debug(f"[CONVERTER] No code found for POU: {pou_name}")
            return f"%% No code found for POU {pou_name}"

        # Generate flowchart with POU information
        try:
            result = processor.generate_flowchart(code, pou_name, pou_info)

            # Add converter debug info to processor debug output
            processor_debug = processor.get_debug_info()
            for debug_msg in self.get_debug_info():
                if debug_msg not in processor_debug:
                    processor._add_debug(debug_msg)

            return result
        except Exception as e:
            self._add_debug(f"[CONVERTER] Error generating flowchart: {str(e)}")
            import traceback
            self._add_debug(f"[CONVERTER] Traceback: {traceback.format_exc()}")
            return f"%% Error generating flowchart: {str(e)}"

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return list(self.processors.keys())