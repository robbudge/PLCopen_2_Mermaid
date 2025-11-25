from typing import Dict, List
from languages.st_processor import STProcessor


# Future imports:
# from languages.cfc_processor import CFCProcessor
# from languages.ld_processor import LDProcessor

class MermaidConverter:
    def __init__(self):
        self.processors = []
        self._initialize_processors()

    def _initialize_processors(self):
        """Initialize all language processors"""
        self.processors.append(STProcessor())
        # Future processors:
        # self.processors.append(CFCProcessor())
        # self.processors.append(LDProcessor())

    def convert_pou_to_mermaid(self, parser, pou_name: str) -> str:
        """Convert POU to Mermaid flowchart using appropriate processor"""
        body = parser.get_pou_body(pou_name)
        language = parser.get_pou_language(pou_name)

        if not body:
            return f"%% No body found for POU {pou_name}"

        # Find appropriate processor
        processor = self._get_processor(language)
        if not processor:
            return f"%% Language '{language}' not supported. Available: {self.get_supported_languages()}"

        return processor.generate_flowchart(body, pou_name)

    def _get_processor(self, language: str):
        """Get the appropriate processor for the language"""
        for processor in self.processors:
            if processor.can_process(language):
                return processor
        return None

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        languages = []
        for processor in self.processors:
            if hasattr(processor, 'LANGUAGE_NAME'):
                languages.append(processor.LANGUAGE_NAME)
            else:
                languages.append(processor.__class__.__name__.replace('Processor', ''))
        return languages

    def get_debug_info(self, language: str = None) -> List[str]:
        """Get debug information from processors"""
        debug_info = []
        for processor in self.processors:
            if not language or processor.can_process(language):
                debug_info.extend(processor.get_debug_info())
        return debug_info