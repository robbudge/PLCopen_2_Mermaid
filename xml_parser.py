import xml.etree.ElementTree as ET
import re
from typing import Dict, List, Any


class CodesysXMLParser:
    def __init__(self, xml_file_path):
        self.xml_file_path = xml_file_path
        self.debug_info = []
        self._add_debug(f"Initializing parser for file: {xml_file_path}")

        try:
            # Parse XML
            self.tree = ET.parse(xml_file_path)
            self.root = self.tree.getroot()
            self._add_debug(f"XML root tag: {self.root.tag}")
            self._add_debug(f"XML root attributes: {self.root.attrib}")

            # Use iterative search to find POUs regardless of namespace
            self.pous = self._find_pous_iterative()
            self._add_debug(f"Found {len(self.pous)} POUs: {list(self.pous.keys())}")

        except Exception as e:
            self._add_debug(f"Error during initialization: {str(e)}")
            import traceback
            self._add_debug(f"Traceback: {traceback.format_exc()}")
            raise

    def _add_debug(self, message: str):
        """Add debug message with timestamp"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        debug_msg = f"[{timestamp}] {message}"
        self.debug_info.append(debug_msg)
        print(debug_msg)

    def _find_pous_iterative(self) -> Dict[str, Any]:
        """Find all POU elements by iterating through the tree"""
        pous = {}

        self._add_debug("Starting iterative POU search...")

        # Iterate through all elements looking for those with pouType attribute
        all_elements = list(self.root.iter())
        self._add_debug(f"Total elements in XML: {len(all_elements)}")

        pou_elements = []
        for elem in all_elements:
            if elem.get('pouType') and elem.get('name'):
                pou_elements.append(elem)

        self._add_debug(f"Found {len(pou_elements)} elements with pouType and name attributes")

        for pou_element in pou_elements:
            pou_name = pou_element.get('name')
            pou_type = pou_element.get('pouType')

            self._add_debug(f"Processing POU: {pou_name} (type: {pou_type})")

            pou_data = {
                'name': pou_name,
                'pouType': pou_type,
                'language': 'Unknown',  # Default, will be updated
                'actions': [],
                'methods': [],
                'body': None,
                'bodyLanguage': 'Unknown',
                'actionsInfo': {},  # Store language per action
                'methodsInfo': {}  # Store language per method
            }

            # Detect language from POU element
            pou_language = pou_element.get('language', 'Unknown')
            pou_data['language'] = pou_language
            self._add_debug(f"  POU '{pou_name}' main language: {pou_language}")

            # Parse actions with language detection
            self._add_debug(f"  Looking for actions in POU {pou_name}")
            actions_element = None

            # Find actions element
            for child in pou_element:
                tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if tag == 'actions':
                    actions_element = child
                    break

            if actions_element is not None:
                self._add_debug(f"  Found actions element for {pou_name}")
                for action in actions_element:
                    action_name = action.get('name')
                    if action_name:
                        action_language = action.get('language', 'Unknown')
                        pou_data['actions'].append(action_name)
                        pou_data['actionsInfo'][action_name] = {
                            'language': action_language,
                            'body': None
                        }
                        self._add_debug(f"    Found action: {action_name} (language: {action_language})")

                        # Extract action body and language
                        action_body, action_body_lang = self._extract_body_and_language(action)
                        pou_data['actionsInfo'][action_name]['body'] = action_body
                        pou_data['actionsInfo'][action_name]['bodyLanguage'] = action_body_lang
                        self._add_debug(
                            f"      Action body language: {action_body_lang}, length: {len(action_body) if action_body else 0}")
            else:
                self._add_debug(f"  No actions element found for {pou_name}")

            # Parse methods with language detection
            self._add_debug(f"  Looking for methods in POU {pou_name}")
            methods_element = None

            # Find methods element
            for child in pou_element:
                tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if tag == 'methods':
                    methods_element = child
                    break

            if methods_element is not None:
                self._add_debug(f"  Found methods element for {pou_name}")
                for method in methods_element:
                    method_name = method.get('name')
                    if method_name:
                        method_language = method.get('language', 'Unknown')
                        pou_data['methods'].append(method_name)
                        pou_data['methodsInfo'][method_name] = {
                            'language': method_language,
                            'body': None
                        }
                        self._add_debug(f"    Found method: {method_name} (language: {method_language})")

                        # Extract method body and language
                        method_body, method_body_lang = self._extract_body_and_language(method)
                        pou_data['methodsInfo'][method_name]['body'] = method_body
                        pou_data['methodsInfo'][method_name]['bodyLanguage'] = method_body_lang
                        self._add_debug(
                            f"      Method body language: {method_body_lang}, length: {len(method_body) if method_body else 0}")
            else:
                self._add_debug(f"  No methods element found for {pou_name}")

            # Parse main body with language detection
            self._add_debug(f"  Looking for main body in POU {pou_name}")
            body_element = None

            # Find body element
            for child in pou_element:
                tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if tag == 'body':
                    body_element = child
                    break

            if body_element is not None:
                body_text, body_language = self._extract_body_and_language(body_element)
                pou_data['body'] = body_text
                pou_data['bodyLanguage'] = body_language
                self._add_debug(
                    f"  Found main body for {pou_name} (language: {body_language}, length: {len(body_text) if body_text else 0})")
                if body_text:
                    self._add_debug(f"  Body preview: {body_text[:200]}...")
            else:
                self._add_debug(f"  No main body element found for {pou_name}")

            pous[pou_name] = pou_data
            self._add_debug(f"Completed processing POU: {pou_name}")

        return pous

    def _extract_body_and_language(self, element) -> tuple:
        """Extract body content and detect language from an element"""
        body_text = ""
        language = "Unknown"

        # Get language from element attribute
        language = element.get('language', 'Unknown')

        # Try multiple strategies to extract body content
        body_element = element

        # Strategy 1: Look for ST, LD, FBD, etc. elements
        language_elements = ['ST', 'LD', 'FBD', 'SFC', 'IL', 'CFC']
        found_language_element = None

        for lang_elem in language_elements:
            lang_element = body_element.find(lang_elem)
            if lang_element is None:
                # Try with namespace
                for child in body_element:
                    tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if tag == lang_elem:
                        lang_element = child
                        break

            if lang_element is not None:
                found_language_element = lang_element
                language = lang_elem  # Override with detected language
                self._add_debug(f"      Detected language element: {lang_elem}")
                break

        if found_language_element is not None:
            # Extract text from language-specific element
            body_text = self._extract_text_from_element(found_language_element)
        else:
            # Strategy 2: Direct text content from body element
            body_text = self._extract_text_from_element(body_element)

            # Try to detect language from content if still unknown
            if language == 'Unknown':
                language = self._detect_language_from_content(body_text)

        return body_text, language

    def _extract_text_from_element(self, element):
        """Extract all text content from an element and its children"""
        if element is None:
            return ""

        text = element.text or ""

        # Recursively get text from all children
        for child in element:
            if child.text:
                text += child.text
            if child.tail:
                text += child.tail

        # Clean up the text
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text

    def _detect_language_from_content(self, content: str) -> str:
        """Detect programming language from content heuristics"""
        if not content:
            return "Unknown"

        content_upper = content.upper()

        # ST (Structured Text) patterns
        st_patterns = [
            r'IF\s+.+\s+THEN',
            r'END_IF',
            r':=',
            r'FOR\s+.+\s+TO\s+.+\s+DO',
            r'END_FOR',
            r'CASE\s+.+\s+OF',
            r'END_CASE',
            r'WHILE\s+.+\s+DO',
            r'END_WHILE'
        ]

        # LD (Ladder Diagram) patterns - would have contacts, coils, etc.
        ld_patterns = [
            r'---|\|\s+|\s+\|',  # Ladder rungs
            r'\(\s*\)',  # Contacts
            r'\[\s*\]',  # Coils
        ]

        # FBD (Function Block Diagram) patterns
        fbd_patterns = [
            r'BLOCK\s+',
            r'FB_\w+',
            r'IN\s+OUT\s+',
        ]

        # Check for ST patterns
        st_score = 0
        for pattern in st_patterns:
            if re.search(pattern, content_upper):
                st_score += 1

        if st_score >= 2:
            return "ST"

        # Check for LD patterns (simplified)
        if any(re.search(pattern, content) for pattern in ld_patterns):
            return "LD"

        # Check for FBD patterns
        if any(re.search(pattern, content_upper) for pattern in fbd_patterns):
            return "FBD"

        # Default to ST if it has common ST constructs but not enough patterns
        if ';' in content and ('IF' in content_upper or ':=' in content):
            return "ST"

        return "Unknown"

    def get_pous(self) -> Dict[str, Any]:
        return self.pous

    def get_pou_body(self, pou_name: str) -> str:
        pou = self.pous.get(pou_name)
        if pou:
            return pou.get('body', '')
        return ''

    def get_pou_language(self, pou_name: str) -> str:
        """Get the main language of the POU"""
        pou = self.pous.get(pou_name)
        if pou:
            return pou.get('language', 'Unknown')
        return 'Unknown'

    def get_pou_body_language(self, pou_name: str) -> str:
        """Get the language specifically used in the body"""
        pou = self.pous.get(pou_name)
        if pou:
            return pou.get('bodyLanguage', 'Unknown')
        return 'Unknown'

    def get_action_language(self, pou_name: str, action_name: str) -> str:
        """Get the language of a specific action"""
        pou = self.pous.get(pou_name)
        if pou and action_name in pou.get('actionsInfo', {}):
            return pou['actionsInfo'][action_name].get('language', 'Unknown')
        return 'Unknown'

    def get_action_body_language(self, pou_name: str, action_name: str) -> str:
        """Get the body language of a specific action"""
        pou = self.pous.get(pou_name)
        if pou and action_name in pou.get('actionsInfo', {}):
            return pou['actionsInfo'][action_name].get('bodyLanguage', 'Unknown')
        return 'Unknown'

    def get_method_language(self, pou_name: str, method_name: str) -> str:
        """Get the language of a specific method"""
        pou = self.pous.get(pou_name)
        if pou and method_name in pou.get('methodsInfo', {}):
            return pou['methodsInfo'][method_name].get('language', 'Unknown')
        return 'Unknown'

    def get_method_body_language(self, pou_name: str, method_name: str) -> str:
        """Get the body language of a specific method"""
        pou = self.pous.get(pou_name)
        if pou and method_name in pou.get('methodsInfo', {}):
            return pou['methodsInfo'][method_name].get('bodyLanguage', 'Unknown')
        return 'Unknown'

    def get_action_body(self, pou_name: str, action_name: str) -> str:
        """Get the body content of a specific action"""
        pou = self.pous.get(pou_name)
        if pou and action_name in pou.get('actionsInfo', {}):
            return pou['actionsInfo'][action_name].get('body', '')
        return ''

    def get_method_body(self, pou_name: str, method_name: str) -> str:
        """Get the body content of a specific method"""
        pou = self.pous.get(pou_name)
        if pou and method_name in pou.get('methodsInfo', {}):
            return pou['methodsInfo'][method_name].get('body', '')
        return ''

    def get_debug_info(self) -> List[str]:
        return self.debug_info

    def get_pou_detailed_info(self, pou_name: str) -> Dict[str, Any]:
        """Get detailed information about a POU including all languages"""
        pou = self.pous.get(pou_name)
        if not pou:
            return {}

        detailed_info = {
            'name': pou_name,
            'pouType': pou.get('pouType', 'Unknown'),
            'mainLanguage': pou.get('language', 'Unknown'),
            'bodyLanguage': pou.get('bodyLanguage', 'Unknown'),
            'bodyLength': len(pou.get('body', '')),
            'actions': [],
            'methods': []
        }

        # Add action details
        for action_name in pou.get('actions', []):
            action_info = pou['actionsInfo'].get(action_name, {})
            detailed_info['actions'].append({
                'name': action_name,
                'language': action_info.get('language', 'Unknown'),
                'bodyLanguage': action_info.get('bodyLanguage', 'Unknown'),
                'bodyLength': len(action_info.get('body', ''))
            })

        # Add method details
        for method_name in pou.get('methods', []):
            method_info = pou['methodsInfo'].get(method_name, {})
            detailed_info['methods'].append({
                'name': method_name,
                'language': method_info.get('language', 'Unknown'),
                'bodyLanguage': method_info.get('bodyLanguage', 'Unknown'),
                'bodyLength': len(method_info.get('body', ''))
            })

        return detailed_info