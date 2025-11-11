import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk
import xml.etree.ElementTree as ET
import re
import os
from datetime import datetime
import logging


class SmartMermaidProcessor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Smart Mermaid Processor - Full Text Flowcharts with Sub-POU Support")
        self.root.geometry("1400x900")

        # Setup logging
        self.setup_logging()

        # Data storage
        self.file_path = None
        self.discovered_pous = []
        self.discovered_actions = []  # Separate list for actions
        self.selected_pous = set()
        self.pou_name_map = {}  # Map POU names to their data for quick lookup

        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # File selection tab
        self.file_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.file_tab, text="File Selection")

        # POU selection tab
        self.selection_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.selection_tab, text="POU Selection")

        # Output tab
        self.output_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.output_tab, text="Processing Output")

        self.setup_file_tab()
        self.setup_selection_tab()
        self.setup_output_tab()

    def setup_logging(self):
        """Setup file logging for debugging"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            filename='smart_mermaid_processor.log',
            filemode='w'
        )
        self.logger = logging.getLogger()

    def setup_file_tab(self):
        """Setup file selection tab"""
        file_frame = tk.LabelFrame(self.file_tab, text="File Selection", font=("Arial", 10, "bold"))
        file_frame.pack(fill=tk.X, pady=5, padx=10)

        self.select_btn = tk.Button(
            file_frame,
            text="Select PLCopen XML File",
            command=self.select_file,
            font=("Arial", 11),
            bg="#4CAF50",
            fg="white"
        )
        self.select_btn.pack(side=tk.LEFT, padx=5, pady=5)

        self.file_label = tk.Label(file_frame, text="No file selected", wraplength=1000, justify=tk.LEFT)
        self.file_label.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)

        self.scan_btn = tk.Button(
            file_frame,
            text="Scan for POUs",
            command=self.scan_file,
            font=("Arial", 10),
            bg="#FF9800",
            fg="white",
            state=tk.DISABLED
        )
        self.scan_btn.pack(side=tk.RIGHT, padx=5, pady=5)

        progress_frame = tk.LabelFrame(self.file_tab, text="Scanning Progress", font=("Arial", 10, "bold"))
        progress_frame.pack(fill=tk.X, pady=5, padx=10)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)

        self.progress_label = tk.Label(progress_frame, text="Ready to scan...")
        self.progress_label.pack(fill=tk.X, padx=5, pady=2)

        results_frame = tk.LabelFrame(self.file_tab, text="Scan Results Preview", font=("Arial", 10, "bold"))
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=10)

        self.results_text = scrolledtext.ScrolledText(
            results_frame,
            wrap=tk.WORD,
            width=120,
            height=20,
            font=("Consolas", 9)
        )
        self.results_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def setup_selection_tab(self):
        """Setup POU selection tab"""
        controls_frame = tk.LabelFrame(self.selection_tab, text="Selection Controls", font=("Arial", 10, "bold"))
        controls_frame.pack(fill=tk.X, pady=5, padx=10)

        btn_frame = tk.Frame(controls_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(btn_frame, text="Select All", command=self.select_all_pous, font=("Arial", 9)).pack(side=tk.LEFT,
                                                                                                      padx=2)
        tk.Button(btn_frame, text="Select None", command=self.select_none_pous, font=("Arial", 9)).pack(side=tk.LEFT,
                                                                                                        padx=2)
        tk.Button(btn_frame, text="Select Programs Only", command=self.select_programs_only, font=("Arial", 9)).pack(
            side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Select Function Blocks Only", command=self.select_fbs_only, font=("Arial", 9)).pack(
            side=tk.LEFT, padx=2)

        search_frame = tk.Frame(controls_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Label(search_frame, text="Search:", font=("Arial", 9)).pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        self.search_entry.bind('<KeyRelease>', self.filter_pous)

        self.selection_info = tk.Label(controls_frame, text="No POUs selected", font=("Arial", 9), fg="blue")
        self.selection_info.pack(pady=5)

        self.process_btn = tk.Button(
            controls_frame,
            text="Generate Full Text Mermaid Flowcharts",
            command=self.process_selected_pous,
            font=("Arial", 11, "bold"),
            bg="#2196F3",
            fg="white",
            state=tk.DISABLED
        )
        self.process_btn.pack(pady=10)

        list_frame = tk.LabelFrame(self.selection_tab, text="Available POUs - Click to select/deselect",
                                   font=("Arial", 10, "bold"))
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=10)

        listbox_frame = tk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.pou_listbox = tk.Listbox(
            listbox_frame,
            selectmode=tk.MULTIPLE,
            font=("Consolas", 10),
            height=20
        )

        scrollbar = tk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=self.pou_listbox.yview)
        self.pou_listbox.configure(yscrollcommand=scrollbar.set)

        self.pou_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.pou_listbox.bind('<<ListboxSelect>>', self.on_pou_select)
        self.pou_listbox.bind('<Double-1>', self.preview_pou)

    def setup_output_tab(self):
        """Setup output tab"""
        output_frame = tk.LabelFrame(self.output_tab, text="Processing Output", font=("Arial", 10, "bold"))
        output_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=10)

        button_frame = tk.Frame(output_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=2)

        tk.Button(button_frame, text="Clear Log", command=self.clear_log, font=("Arial", 9)).pack(side=tk.RIGHT)
        tk.Button(button_frame, text="Open Output Folder", command=self.open_output_folder, font=("Arial", 9)).pack(
            side=tk.RIGHT, padx=5)

        self.output_text = scrolledtext.ScrolledText(
            output_frame,
            wrap=tk.WORD,
            width=120,
            height=30,
            font=("Consolas", 9)
        )
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def select_file(self):
        file_path = filedialog.askopenfilename(
            title="Select PLCopen XML File",
            filetypes=[("PLCopen XML", "*.xml"), ("All files", "*.*")]
        )

        if file_path:
            self.file_path = file_path
            self.file_label.config(text=f"Selected: {file_path}")
            self.scan_btn.config(state=tk.NORMAL)
            self.log_message("INFO", f"PLCopen XML file selected: {file_path}")
            self.notebook.select(self.file_tab)

    def scan_file(self):
        """Scan the PLCopen XML file for POUs using project structure"""
        if not self.file_path:
            return

        try:
            self.log_message("INFO", "Scanning PLCopen XML file using project structure...")
            self.update_progress("Loading XML file...", 10)

            self.discovered_pous = []
            self.discovered_actions = []
            self.selected_pous.clear()
            self.pou_name_map = {}
            self.object_id_map = {}
            self.structure_tree = {}

            tree = ET.parse(self.file_path)
            root = tree.getroot()

            # Debug the XML structure first
            self.debug_xml_structure(root)

            self.update_progress("Processing project structure...", 30)

            ns = {
                'ns': 'http://www.plcopen.org/xml/tc6_0200',
                'xhtml': 'http://www.w3.org/1999/xhtml'
            }

            # Build structure tree
            self.build_structure_tree(root, ns)

            # Display structure for debugging
            if self.structure_tree:
                self.display_structure_tree()
            else:
                self.log_message("WARNING", "No structure tree built, falling back to element scanning")
                # Fall back to scanning all POU elements directly
                pou_elements = root.findall('.//ns:pou', ns)
                for pou_element in pou_elements:
                    pou_info, actions = self.extract_pou_and_actions_fallback(pou_element, ns)
                    if pou_info:
                        self.discovered_pous.append(pou_info)
                    for action in actions:
                        self.discovered_actions.append(action)

                self.update_progress("Scan complete!", 100)
                self.display_scan_results()
                self.populate_pou_list()
                return

            self.update_progress("Extracting POU content...", 50)

            # Extract content for all POUs found in structure
            self.extract_all_pou_content(root, ns)

            self.update_progress("Scan complete!", 100)
            self.display_scan_results()
            self.populate_pou_list()

            total_pous = len(self.discovered_pous) + len(self.discovered_actions)
            if total_pous:
                self.process_btn.config(state=tk.NORMAL)
                self.notebook.select(self.selection_tab)
                self.log_message("INFO",
                                 f"Scan complete: Found {len(self.discovered_pous)} main POUs and {len(self.discovered_actions)} actions")
                self.log_message("INFO", f"Structure contains {len(self.object_id_map)} objects")
            else:
                self.log_message("WARNING", "No POUs with executable logic found")

        except Exception as e:
            error_msg = f"Error scanning file: {str(e)}"
            self.log_message("ERROR", error_msg)
            messagebox.showerror("Error", error_msg)
            import traceback
            self.log_message("ERROR", f"Traceback: {traceback.format_exc()}")



    def build_structure_tree(self, root, ns):
        """Build complete project structure tree from projectStructure"""
        try:
            self.log_message("INFO", "Building structure tree from addData section...")

            # Look for the specific addData that contains project structure
            add_data_elements = root.findall('.//{http://www.plcopen.org/xml/tc6_0200}addData')

            project_structure = None

            for add_data in add_data_elements:
                data_elements = add_data.findall('{http://www.plcopen.org/xml/tc6_0200}data')
                for data in data_elements:
                    data_name = data.get('name', '')
                    self.log_message("DEBUG", f"Checking data element: {data_name}")

                    if 'projectstructure' in data_name.lower():
                        self.log_message("INFO", "Found project structure data element!")
                        # The ProjectStructure is inside this data element
                        project_structure = data.find('{http://www.plcopen.org/xml/tc6_0200}ProjectStructure')
                        if project_structure is not None:
                            break
                if project_structure is not None:
                    break

            if project_structure is None:
                self.log_message("WARNING", "No projectStructure found in XML")
                # Try alternative location without namespace
                project_structure = root.find('.//ProjectStructure')
                if project_structure is None:
                    self.log_message("WARNING", "No ProjectStructure found in any location")
                    return

            # Start building the tree from root using the correct namespace
            self.structure_tree = self.process_structure_node(project_structure, "Root")
            self.log_message("INFO", f"Built structure tree with {len(self.object_id_map)} POUs")

        except Exception as e:
            self.log_message("ERROR", f"Error building structure tree: {str(e)}")
            import traceback
            self.log_message("ERROR", f"Traceback: {traceback.format_exc()}")

    def process_structure_node(self, element, node_path):
        """Recursively process a structure node and return its tree"""
        node_info = {
            'path': node_path,
            'type': 'folder',
            'children': []
        }

        # Process Object elements (with capital O)
        objects = element.findall('{http://www.plcopen.org/xml/tc6_0200}Object')
        if not objects:
            # Try with lowercase
            objects = element.findall('{http://www.plcopen.org/xml/tc6_0200}object')
        if not objects:
            # Try without namespace
            objects = element.findall('Object')
        if not objects:
            objects = element.findall('object')

        self.log_message("DEBUG", f"Found {len(objects)} objects in {node_path}")

        for obj in objects:
            obj_name = obj.get('Name') or obj.get('name', 'Unknown')
            obj_id = obj.get('ObjectId') or obj.get('objectId', '')

            if obj_name and obj_id:
                full_path = f"{node_path}.{obj_name}" if node_path != "Root" else obj_name

                obj_info = {
                    'name': obj_name,
                    'object_id': obj_id,
                    'path': full_path,
                    'type': 'object',
                    'children': []
                }

                node_info['children'].append(obj_info)

                # Add to ObjectId map
                self.object_id_map[obj_id] = {
                    'name': obj_name,
                    'full_path': full_path,
                    'type': 'object'
                }
                self.log_message("DEBUG", f"Structure: Mapped Object {obj_id} -> {full_path}")

                # Recursively process the Object's children (Folders inside Objects)
                obj_children = self.process_object_children(obj, full_path)
                node_info['children'].extend(obj_children)

        # Process Folder elements
        folders = element.findall('{http://www.plcopen.org/xml/tc6_0200}Folder')
        if not folders:
            # Try with lowercase
            folders = element.findall('{http://www.plcopen.org/xml/tc6_0200}folder')
        if not folders:
            # Try without namespace
            folders = element.findall('Folder')
        if not folders:
            folders = element.findall('folder')

        self.log_message("DEBUG", f"Found {len(folders)} folders in {node_path}")

        for folder in folders:
            folder_name = folder.get('Name') or folder.get('name', 'Unknown')
            folder_path = f"{node_path}.{folder_name}" if node_path != "Root" else folder_name

            folder_info = self.process_structure_node(folder, folder_path)
            node_info['children'].append(folder_info)

        return node_info

    def process_object_children(self, obj_element, parent_path):
        """Process children of an Object element (Folders and Objects inside Objects)"""
        children = []

        # Process Folders inside Objects
        folders = obj_element.findall('{http://www.plcopen.org/xml/tc6_0200}Folder')
        if not folders:
            folders = obj_element.findall('{http://www.plcopen.org/xml/tc6_0200}folder')
        if not folders:
            folders = obj_element.findall('Folder')
        if not folders:
            folders = obj_element.findall('folder')

        for folder in folders:
            folder_name = folder.get('Name') or folder.get('name', 'Unknown')
            folder_path = f"{parent_path}.{folder_name}"
            folder_info = self.process_structure_node(folder, folder_path)
            children.append(folder_info)

        # Process Objects inside Objects
        objects = obj_element.findall('{http://www.plcopen.org/xml/tc6_0200}Object')
        if not objects:
            objects = obj_element.findall('{http://www.plcopen.org/xml/tc6_0200}object')
        if not objects:
            objects = obj_element.findall('Object')
        if not objects:
            objects = obj_element.findall('object')

        for obj in objects:
            obj_name = obj.get('Name') or obj.get('name', 'Unknown')
            obj_id = obj.get('ObjectId') or obj.get('objectId', '')

            if obj_name and obj_id:
                full_path = f"{parent_path}.{obj_name}"

                obj_info = {
                    'name': obj_name,
                    'object_id': obj_id,
                    'path': full_path,
                    'type': 'object',
                    'children': []
                }

                children.append(obj_info)

                # Add to ObjectId map
                self.object_id_map[obj_id] = {
                    'name': obj_name,
                    'full_path': full_path,
                    'type': 'object'
                }
                self.log_message("DEBUG", f"Structure: Mapped Nested Object {obj_id} -> {full_path}")

                # Recursively process nested object children
                nested_children = self.process_object_children(obj, full_path)
                children.extend(nested_children)

        return children
    #//////////

    def extract_all_pou_content(self, root, ns):
        """Extract content for all POUs found in the structure"""
        # Get all ObjectIds from structure
        all_object_ids = list(self.object_id_map.keys())
        self.log_message("INFO",
                         f"Processing content for {len(all_object_ids)} POUs from structure: {list(self.object_id_map.keys())}")

        # Find all POU elements in the XML and map them by name first (since we might not have ObjectId in POU elements)
        pou_elements = root.findall('.//{http://www.plcopen.org/xml/tc6_0200}pou', ns)
        pou_name_map = {}

        for pou_element in pou_elements:
            pou_name = pou_element.get('name', 'Unknown')
            pou_name_map[pou_name] = pou_element
            self.log_message("DEBUG", f"Found POU element: {pou_name}")

        # Process each POU found in structure
        processed_count = 0
        for object_id, pou_info in self.object_id_map.items():
            pou_name = pou_info['name']
            pou_element = pou_name_map.get(pou_name)

            if pou_element is not None:
                self.log_message("DEBUG", f"Processing POU from structure: {pou_name} (ObjectId: {object_id})")
                self.process_pou_element(pou_element, ns, pou_info)
                processed_count += 1
            else:
                self.log_message("WARNING", f"POU element not found for: {pou_name} (ObjectId: {object_id})")
                # Try to find by partial name match
                for known_pou_name, known_element in pou_name_map.items():
                    if pou_name in known_pou_name or known_pou_name in pou_name:
                        self.log_message("DEBUG", f"Found partial match: {pou_name} -> {known_pou_name}")
                        self.process_pou_element(known_element, ns, pou_info)
                        processed_count += 1
                        break

        self.log_message("INFO", f"Successfully processed {processed_count}/{len(all_object_ids)} POUs from structure")

    def extract_pous_fallback(self, root, ns):
        """Fallback method to extract POUs directly from XML elements"""
        self.log_message("INFO", "Using fallback POU extraction...")

        pou_elements = root.findall('.//{http://www.plcopen.org/xml/tc6_0200}pou', ns)
        self.log_message("INFO", f"Found {len(pou_elements)} POU elements directly")

        for pou_element in pou_elements:
            pou_name = pou_element.get('name', 'Unknown')
            pou_type = pou_element.get('pouType', 'Unknown')

            self.log_message("DEBUG", f"Processing POU: {pou_name} (Type: {pou_type})")

            # Extract content using existing method
            pou_info = self.extract_pou_content(pou_element, ns, pou_name)
            if pou_info:
                self.discovered_pous.append(pou_info)
                self.pou_name_map[pou_name] = pou_info
                self.log_message("DEBUG", f"Extracted POU: {pou_name} with {pou_info['lines']} lines")

            # Extract actions
            actions = self.extract_actions_from_pou(pou_element, ns, pou_name)
            for action in actions:
                self.discovered_actions.append(action)
                self.pou_name_map[action['name']] = action
                self.log_message("DEBUG", f"Extracted Action: {action['name']} with {action['lines']} lines")

    def debug_xml_structure(self, root):
        """Debug method to see the actual XML structure"""
        self.log_message("DEBUG", "=== XML STRUCTURE DEBUG ===")

        # Check addData sections specifically
        add_data_elements = root.findall('.//{http://www.plcopen.org/xml/tc6_0200}addData')
        self.log_message("DEBUG", f"Found {len(add_data_elements)} addData elements")

        for i, add_data in enumerate(add_data_elements):
            self.log_message("DEBUG", f"addData {i}:")
            data_elements = add_data.findall('{http://www.plcopen.org/xml/tc6_0200}data')
            for j, data in enumerate(data_elements):
                data_name = data.get('name', 'No name')
                self.log_message("DEBUG", f"  Data {j}: name='{data_name}'")

                # Check if this is the project structure data
                if 'projectstructure' in data_name.lower():
                    self.log_message("DEBUG", f"    -> THIS IS PROJECT STRUCTURE DATA!")

                    # Print the entire ProjectStructure content recursively
                    project_structure = data.find('{http://www.plcopen.org/xml/tc6_0200}ProjectStructure')
                    if project_structure is not None:
                        self.log_message("DEBUG", "    Found ProjectStructure element")
                        self.print_element_tree(project_structure, 3)
                    else:
                        self.log_message("DEBUG", "    No ProjectStructure element found")

                        # Try without namespace
                        project_structure = data.find('ProjectStructure')
                        if project_structure is not None:
                            self.log_message("DEBUG", "    Found ProjectStructure (no namespace)")
                            self.print_element_tree(project_structure, 3)
                        else:
                            self.log_message("DEBUG", "    No ProjectStructure found at all")

        self.log_message("DEBUG", "=== END XML STRUCTURE DEBUG ===")

    def print_element_tree(self, element, indent_level=0, max_depth=3):
        """Recursively print element tree for debugging"""
        if indent_level > max_depth * 2:
            return

        indent = "  " * indent_level
        tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
        attrs = " ".join([f"{k}=\"{v}\"" for k, v in element.attrib.items()])

        self.log_message("DEBUG", f"{indent}<{tag} {attrs}>")

        # Print text content if any
        if element.text and element.text.strip():
            self.log_message("DEBUG", f"{indent}  TEXT: {element.text.strip()}")

        # Recursively process children
        for child in element:
            self.print_element_tree(child, indent_level + 1, max_depth)

        self.log_message("DEBUG", f"{indent}</{tag}>")


    def build_structure_alternative(self, root):
        """Alternative method to build structure from addData section"""
        try:
            # Look for the specific addData that contains project structure
            add_data_elements = root.findall('.//{http://www.plcopen.org/xml/tc6_0200}addData')

            for add_data in add_data_elements:
                data_elements = add_data.findall('{http://www.plcopen.org/xml/tc6_0200}data')
                for data in data_elements:
                    if 'projectstructure' in data.get('name', '').lower():
                        self.log_message("INFO", "Found project structure in addData!")
                        project_structure = data.find('{http://www.plcopen.org/xml/tc6_0200}ProjectStructure')
                        if project_structure is not None:
                            self.structure_tree = self.process_structure_node(project_structure,
                                                                              "http://www.plcopen.org/xml/tc6_0200",
                                                                              "Root")
                            break

            if not self.object_id_map:
                self.log_message("WARNING", "Could not find project structure via alternative method either")

        except Exception as e:
            self.log_message("ERROR", f"Error in alternative structure building: {str(e)}")

    def scan_file(self):
        """Scan the PLCopen XML file for POUs using project structure"""
        if not self.file_path:
            return

        try:
            self.log_message("INFO", "Scanning PLCopen XML file using project structure...")
            self.update_progress("Loading XML file...", 10)

            self.discovered_pous = []
            self.discovered_actions = []
            self.selected_pous.clear()
            self.pou_name_map = {}
            self.object_id_map = {}
            self.structure_tree = {}

            tree = ET.parse(self.file_path)
            root = tree.getroot()

            # Debug the XML structure first
            self.debug_xml_structure(root)

            self.update_progress("Processing project structure...", 30)

            ns = {
                'ns': 'http://www.plcopen.org/xml/tc6_0200',
                'xhtml': 'http://www.w3.org/1999/xhtml'
            }

            # Build structure tree
            self.build_structure_tree(root, ns)

            # Display structure for debugging
            if self.structure_tree:
                self.display_structure_tree()
            else:
                self.log_message("WARNING", "No structure tree built")

            self.update_progress("Extracting POU content...", 50)

            # Extract content for all POUs found in structure
            if self.object_id_map:
                self.extract_all_pou_content(root, ns)
            else:
                self.log_message("WARNING", "No objects found in structure, using fallback")
                self.extract_pous_fallback(root, ns)

            self.update_progress("Scan complete!", 100)
            self.display_scan_results()
            self.populate_pou_list()

            total_pous = len(self.discovered_pous) + len(self.discovered_actions)
            if total_pous:
                self.process_btn.config(state=tk.NORMAL)
                self.notebook.select(self.selection_tab)
                self.log_message("INFO",
                                 f"Scan complete: Found {len(self.discovered_pous)} main POUs and {len(self.discovered_actions)} actions")
                if self.object_id_map:
                    self.log_message("INFO", f"Structure contains {len(self.object_id_map)} objects")
            else:
                self.log_message("WARNING", "No POUs with executable logic found")

        except Exception as e:
            error_msg = f"Error scanning file: {str(e)}"
            self.log_message("ERROR", error_msg)
            messagebox.showerror("Error", error_msg)
            import traceback
            self.log_message("ERROR", f"Traceback: {traceback.format_exc()}")
 #//////////

    def display_structure_tree(self):
        """Display the structure tree in the log for debugging"""
        self.log_message("INFO", "=== PROJECT STRUCTURE ===")
        self.print_structure_node(self.structure_tree, 0)
        self.log_message("INFO", "=== END STRUCTURE ===")

    def print_structure_node(self, node, indent_level):
        """Recursively print structure node"""
        indent = "  " * indent_level
        if node['type'] == 'folder':
            self.log_message("INFO", f"{indent}📁 {node['path']}")
        else:
            obj_id_info = f" [ObjectId: {node['object_id']}]" if node.get('object_id') else ""
            self.log_message("INFO", f"{indent}📄 {node['name']}{obj_id_info}")

        for child in node.get('children', []):
            self.print_structure_node(child, indent_level + 1)


    def process_pou_element(self, pou_element, ns, structure_info):
        """Process a single POU element and extract its content"""
        try:
            name = pou_element.get('name', 'Unknown')
            pou_type = pou_element.get('pouType', 'Unknown')
            object_id = structure_info['object_id']

            self.log_message("DEBUG", f"Extracting content for: {name} (Type: {pou_type}, ObjectId: {object_id})")

            # Extract main POU content
            pou_content = self.extract_pou_content(pou_element, ns, name)
            if pou_content:
                self.discovered_pous.append(pou_content)
                self.pou_name_map[pou_content['name']] = pou_content
                self.log_message("DEBUG",
                                 f"Extracted main POU: {pou_content['name']} with {pou_content['lines']} lines")

            # Extract actions
            actions = self.extract_actions_from_pou(pou_element, ns, name)
            for action in actions:
                self.discovered_actions.append(action)
                self.pou_name_map[action['name']] = action
                self.log_message("DEBUG", f"Extracted action: {action['name']} with {action['lines']} lines")

        except Exception as e:
            self.log_message("ERROR", f"Error processing POU {structure_info['full_path']}: {str(e)}")

    def extract_pou_content(self, pou_element, ns, pou_name):
        """Extract content from a POU element"""
        st_content = ""

        # Extract main body content
        body = pou_element.find('ns:body', ns)
        if body is not None:
            body_st = self.extract_st_from_element(body, ns)
            if body_st:
                st_content += f"// Main Body\n{body_st}\n"

        # Direct ST from main POU
        direct_st = self.extract_st_from_element(pou_element, ns)
        if direct_st and not st_content:
            st_content = direct_st

        if not st_content.strip():
            return None

        st_content = self.clean_st_content(st_content)

        # Extract executable part
        executable_lines = []
        for line in st_content.split('\n'):
            clean_line = line.strip()
            if (clean_line and
                    not clean_line.startswith('//') and
                    not clean_line.upper().startswith(('VAR', 'END_VAR')) and
                    not clean_line.upper().startswith('PROGRAM') and
                    not clean_line.upper().startswith('FUNCTION_BLOCK') and
                    not clean_line.upper().startswith('FUNCTION')):
                executable_lines.append(clean_line)

        executable_content = '\n'.join(executable_lines)
        lines = len([l for l in executable_content.split('\n') if l.strip()])
        size = len(executable_content)

        # Get ObjectId
        object_id_element = pou_element.find(
            './/ns:addData/ns:data[@name="http://www.3s-software.com/plcopenxml/objectid"]/ns:ObjectId', ns)
        object_id = object_id_element.text if object_id_element is not None else None

        # Extract sub-POU calls using structure-aware detection
        sub_pou_calls = self.extract_structured_sub_pou_calls(executable_content, pou_name)

        return {
            'name': pou_name,
            'type': 'program',  # Default type
            'object_id': object_id,
            'st_content': st_content,
            'executable_content': executable_content,
            'lines': lines,
            'size': size,
            'sub_pou_calls': sub_pou_calls,
            'is_action': False
        }

    def extract_structured_sub_pou_calls(self, executable_content, current_pou_name):
        """Extract sub-POU calls using the structure tree for accurate detection"""
        sub_pou_calls = []

        # Get all known POU names from structure
        all_known_pous = {info['name'] for info in self.object_id_map.values()}

        # Look for function call patterns
        patterns = [
            r'(\w+)\s*\([^)]*\)',  # Function calls: FunctionName(param)
        ]

        # Apply patterns
        for pattern in patterns:
            matches = re.findall(pattern, executable_content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    call_name = match[0]
                else:
                    call_name = match

                # Check if this is a known POU from structure
                if call_name in all_known_pous:
                    sub_pou_calls.append(call_name)
                    self.log_message("DEBUG", f"Structure-aware: Found call to {call_name} in {current_pou_name}")

        # Remove duplicates
        return list(set(sub_pou_calls))

    def extract_actions_from_pou(self, pou_element, ns, parent_pou_name):
        """Extract actions from a POU element"""
        actions = []

        actions_element = pou_element.find('ns:actions', ns)
        if actions_element is not None:
            action_elements = actions_element.findall('ns:action', ns)
            self.log_message("DEBUG", f"Found {len(action_elements)} actions in POU {parent_pou_name}")

            for action_element in action_elements:
                action_info = self.extract_action_info(action_element, ns, parent_pou_name)
                if action_info:
                    actions.append(action_info)

        return actions





    def build_object_id_map(self, root, ns):
        """Build mapping from ObjectIds to POU names from project structure"""
        try:
            # Find the ProjectStructure section
            project_structure = root.find('.//ns:projectStructure', ns)
            if project_structure is None:
                self.log_message("WARNING", "No projectStructure found in XML")
                return

            # Recursively process folders and objects
            self.process_structure_elements(project_structure, ns, "")

            self.log_message("DEBUG",
                             f"Built ObjectId map with {len(self.object_id_map)} entries: {self.object_id_map}")

        except Exception as e:
            self.log_message("ERROR", f"Error building ObjectId map: {str(e)}")

    def process_structure_elements(self, element, ns, parent_path):
        """Recursively process project structure elements"""
        # Process objects in current element
        objects = element.findall('ns:object', ns)
        for obj in objects:
            obj_name = obj.get('name', 'Unknown')
            obj_id = obj.get('objectId', '')

            if obj_id:
                full_name = f"{parent_path}.{obj_name}" if parent_path else obj_name
                self.object_id_map[obj_id] = full_name
                self.log_message("DEBUG", f"Mapped ObjectId {obj_id} -> {full_name}")

        # Process folders recursively
        folders = element.findall('ns:folder', ns)
        for folder in folders:
            folder_name = folder.get('name', 'Unknown')
            new_path = f"{parent_path}.{folder_name}" if parent_path else folder_name
            self.process_structure_elements(folder, ns, new_path)

    def extract_pou_and_actions(self, pou_element, ns):
        """Extract main POU information and separate actions"""
        try:
            name = pou_element.get('name', 'Unknown')
            pou_type = pou_element.get('pouType', 'Unknown')

            # Get ObjectId for this POU
            object_id_element = pou_element.find(
                './/ns:addData/ns:data[@name="http://www.3s-software.com/plcopenxml/objectid"]/ns:ObjectId', ns)
            object_id = object_id_element.text if object_id_element is not None else None

            self.log_message("DEBUG", f"Processing POU: {name} (Type: {pou_type}, ObjectId: {object_id})")

            st_content = ""
            actions = []

            # Extract main body content first
            body = pou_element.find('ns:body', ns)
            if body is not None:
                body_st = self.extract_st_from_element(body, ns)
                if body_st:
                    st_content += f"// Main Body\n{body_st}\n"

            # Extract actions as separate entities
            actions_element = pou_element.find('ns:actions', ns)
            if actions_element is not None:
                action_elements = actions_element.findall('ns:action', ns)
                self.log_message("DEBUG", f"Found {len(action_elements)} actions in POU {name}")

                for action_element in action_elements:
                    action_info = self.extract_action_info(action_element, ns, name)
                    if action_info:
                        actions.append(action_info)
                        self.log_message("DEBUG", f"Extracted action: {action_info['name']}")

            # Direct ST from main POU
            direct_st = self.extract_st_from_element(pou_element, ns)
            if direct_st and not st_content:
                st_content = direct_st

            if not st_content.strip() and not actions:
                self.log_message("DEBUG", f"No ST content found for POU: {name}")
                return None, actions

            if st_content:
                st_content = self.clean_st_content(st_content)

                # Extract only the executable part
                executable_lines = []
                for line in st_content.split('\n'):
                    clean_line = line.strip()
                    if (clean_line and
                            not clean_line.startswith('//') and
                            not clean_line.upper().startswith(('VAR', 'END_VAR')) and
                            not clean_line.upper().startswith('PROGRAM') and
                            not clean_line.upper().startswith('FUNCTION_BLOCK') and
                            not clean_line.upper().startswith('FUNCTION')):
                        executable_lines.append(clean_line)

                executable_content = '\n'.join(executable_lines)
            else:
                executable_content = ""

            lines = len([l for l in executable_content.split('\n') if l.strip()])
            size = len(executable_content)

            # Extract sub-POU calls using ObjectId mapping
            sub_pou_calls = self.extract_sub_pou_calls_with_objectids(executable_content, name)

            pou_info = {
                'name': name,
                'type': pou_type,
                'object_id': object_id,
                'st_content': st_content,
                'executable_content': executable_content,
                'lines': lines,
                'size': size,
                'sub_pou_calls': sub_pou_calls,
                'is_action': False
            }

            return pou_info, actions

        except Exception as e:
            self.log_message("ERROR", f"Error extracting POU {pou_element.get('name', 'Unknown')}: {str(e)}")
            return None, []

    def extract_sub_pou_calls_with_objectids(self, executable_content, current_pou_name):
        """Extract sub-POU calls using ObjectId mapping for accurate detection"""
        sub_pou_calls = []

        # Get all known POU names from ObjectId map and discovered POUs
        all_known_pous = set(self.object_id_map.values())
        all_known_pous.update([pou['name'] for pou in self.discovered_pous + self.discovered_actions])

        # Look for function call patterns
        patterns = [
            r'(\w+)\s*\([^)]*\)',  # Function calls: FunctionName(param)
        ]

        # Apply patterns
        for pattern in patterns:
            matches = re.findall(pattern, executable_content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    call_name = match[0]
                else:
                    call_name = match

                # Check if this is a known POU
                if self.is_known_pou_call(call_name, all_known_pous):
                    sub_pou_calls.append(call_name)

        # Also look for direct calls in lines
        lines = executable_content.split('\n')
        for line in lines:
            clean_line = line.strip()
            if clean_line and not clean_line.startswith('//'):
                # Check for calls that look like: ActionName();
                if re.match(r'^\s*(\w+)\s*\(\s*\)\s*;', clean_line):
                    call_name = clean_line.split('(')[0].strip()
                    if self.is_known_pou_call(call_name, all_known_pous):
                        sub_pou_calls.append(call_name)

                # Check for calls with parameters: ActionName(param);
                elif re.match(r'^\s*(\w+)\s*\([^)]+\)\s*;', clean_line):
                    call_name = clean_line.split('(')[0].strip()
                    if self.is_known_pou_call(call_name, all_known_pous):
                        sub_pou_calls.append(call_name)

        # Remove duplicates
        filtered_calls = list(set(sub_pou_calls))

        self.log_message("DEBUG", f"Extracted sub-POU calls for {current_pou_name}: {filtered_calls}")
        return filtered_calls

    def is_known_pou_call(self, call_name, all_known_pous):
        """Check if a call name matches a known POU from ObjectId mapping"""
        # Common built-in functions to exclude
        built_in_functions = {
            'IF', 'THEN', 'ELSE', 'ELSIF', 'END_IF', 'CASE', 'OF', 'END_CASE',
            'FOR', 'WHILE', 'REPEAT', 'END_FOR', 'END_WHILE', 'END_REPEAT',
            'VAR', 'END_VAR', 'PROGRAM', 'FUNCTION', 'FUNCTION_BLOCK', 'METHOD',
            'ACTION', 'TRUE', 'FALSE', 'AND', 'OR', 'NOT', 'XOR', 'TO_UINT',
            'SIZEOF', 'ADR', 'SEL', 'MAX', 'MIN', 'LIMIT', 'REPLACE_ALL',
            'ARRAY_AVG', 'ARRAY_HAV', 'MemMove', 'TO_STRING'
        }

        # Check if it's a built-in function
        if call_name.upper() in built_in_functions:
            return False

        # Check if it's in our known POUs list
        if call_name in all_known_pous:
            return True

        # Check for partial matches (actions without parent prefix)
        for known_pou in all_known_pous:
            if known_pou.endswith(f".{call_name}"):
                return True

        # Check if it follows POU naming conventions
        is_pascal_case = (call_name and
                          call_name[0].isupper() and
                          not call_name.upper() == call_name and
                          '_' in call_name)  # Most POUs have underscores

        return is_pascal_case and len(call_name) > 2

    def extract_action_info(self, action_element, ns, parent_pou_name):
        """Extract action information as separate POU"""
        try:
            name = action_element.get('name', 'Unknown')
            full_name = f"{parent_pou_name}.{name}"

            # Get ObjectId for this action
            object_id_element = action_element.find(
                './/ns:addData/ns:data[@name="http://www.3s-software.com/plcopenxml/objectid"]/ns:ObjectId', ns)
            object_id = object_id_element.text if object_id_element is not None else None

            # Extract ST content from action
            body = action_element.find('ns:body', ns)
            if body is None:
                self.log_message("DEBUG", f"No body found for action: {full_name}")
                return None

            st_content = self.extract_st_from_element(body, ns)
            if not st_content.strip():
                self.log_message("DEBUG", f"No ST content found for action: {full_name}")
                return None

            st_content = self.clean_st_content(st_content)

            # Extract executable part
            executable_lines = []
            for line in st_content.split('\n'):
                clean_line = line.strip()
                if (clean_line and
                        not clean_line.startswith('//') and
                        not clean_line.upper().startswith(('VAR', 'END_VAR'))):
                    executable_lines.append(clean_line)

            executable_content = '\n'.join(executable_lines)

            lines = len([l for l in executable_content.split('\n') if l.strip()])
            size = len(executable_content)

            # Extract sub-POU calls for the action
            sub_pou_calls = self.extract_sub_pou_calls_with_objectids(executable_content, full_name)

            action_info = {
                'name': full_name,
                'short_name': name,
                'type': 'action',
                'object_id': object_id,
                'st_content': st_content,
                'executable_content': executable_content,
                'lines': lines,
                'size': size,
                'sub_pou_calls': sub_pou_calls,
                'is_action': True,
                'parent_pou': parent_pou_name
            }

            self.log_message("DEBUG",
                             f"Successfully extracted action: {full_name} with {lines} lines (ObjectId: {object_id})")
            return action_info

        except Exception as e:
            self.log_message("ERROR", f"Error extracting action {action_element.get('name', 'Unknown')}: {str(e)}")
            return None

    def extract_sub_pou_calls(self, executable_content, current_pou_name=""):
        """Extract calls to other POUs (function blocks, functions, methods, actions) - IMPROVED VERSION"""
        sub_pou_calls = []

        # Get all known POU and action names for matching
        all_pou_names = [pou['name'] for pou in self.discovered_pous + self.discovered_actions]
        all_short_names = [pou.get('short_name', pou['name'].split('.')[-1]) for pou in self.discovered_actions]

        # Look for function call patterns
        patterns = [
            # Function calls: FunctionName(param)
            r'(\w+)\s*\([^)]*\)',
        ]

        # Apply patterns
        for pattern in patterns:
            matches = re.findall(pattern, executable_content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    call_name = match[0]
                else:
                    call_name = match

                sub_pou_calls.append(call_name)

        # Also look for direct calls in lines - specifically action calls
        lines = executable_content.split('\n')
        for line in lines:
            clean_line = line.strip()
            if clean_line and not clean_line.startswith('//'):
                # Check for calls that look like: ActionName();
                if re.match(r'^\s*(\w+)\s*\(\s*\)\s*;', clean_line):
                    call_name = clean_line.split('(')[0].strip()
                    if self.is_valid_pou_call(call_name, all_short_names):
                        sub_pou_calls.append(call_name)

                # Check for calls with parameters: ActionName(param);
                elif re.match(r'^\s*(\w+)\s*\([^)]+\)\s*;', clean_line):
                    call_name = clean_line.split('(')[0].strip()
                    if self.is_valid_pou_call(call_name, all_short_names):
                        sub_pou_calls.append(call_name)

        # Remove duplicates and filter
        filtered_calls = []
        for call in set(sub_pou_calls):
            call_clean = call.strip()
            if self.is_valid_pou_call(call_clean, all_short_names):
                filtered_calls.append(call_clean)

        self.log_message("DEBUG", f"Extracted sub-POU calls for {current_pou_name}: {filtered_calls}")
        return filtered_calls

    def is_valid_pou_call(self, call_name, action_short_names=None):
        """Check if a call name is a valid POU call (not a built-in function)"""
        if action_short_names is None:
            action_short_names = []

        # Common built-in functions to exclude
        built_in_functions = {
            'IF', 'THEN', 'ELSE', 'ELSIF', 'END_IF', 'CASE', 'OF', 'END_CASE',
            'FOR', 'WHILE', 'REPEAT', 'END_FOR', 'END_WHILE', 'END_REPEAT',
            'VAR', 'END_VAR', 'PROGRAM', 'FUNCTION', 'FUNCTION_BLOCK', 'METHOD',
            'ACTION', 'TRUE', 'FALSE', 'AND', 'OR', 'NOT', 'XOR', 'TO_UINT',
            'SIZEOF', 'ADR', 'SEL', 'MAX', 'MIN', 'LIMIT', 'REPLACE_ALL',
            'ARRAY_AVG', 'ARRAY_HAV', 'MemMove', 'TO_STRING'
        }

        # Check if it's a known action short name
        is_action_call = call_name in action_short_names

        return (call_name and
                len(call_name) > 1 and
                not call_name.upper() in built_in_functions and
                not call_name.startswith('//') and
                (is_action_call or not call_name[0].islower()))  # Most POUs start with uppercase

    def extract_st_from_element(self, element, ns):
        """Extract ST code from an element, handling XHTML content"""
        st_content = ""

        st_element = element.find('ns:ST', ns)
        if st_element is not None:
            if st_element.text and st_element.text.strip():
                st_content = st_element.text

            xhtml_elements = st_element.findall('.//xhtml:xhtml', ns)
            for xhtml_elem in xhtml_elements:
                if xhtml_elem.text and xhtml_elem.text.strip():
                    st_content = xhtml_elem.text
                if xhtml_elem.tail and xhtml_elem.tail.strip():
                    st_content += "\n" + xhtml_elem.tail

            if not st_content:
                all_text = ''.join(st_element.itertext())
                if all_text.strip():
                    st_content = all_text

        return st_content.strip()

    def clean_st_content(self, content):
        """Clean and format ST content"""
        content = content.replace('&lt;', '<')
        content = content.replace('&gt;', '>')
        content = content.replace('&amp;', '&')

        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            cleaned_line = line.strip()
            if cleaned_line:
                cleaned_lines.append(cleaned_line)

        return '\n'.join(cleaned_lines)

    def display_scan_results(self):
        """Display scan results in preview"""
        self.results_text.delete(1.0, tk.END)

        total_pous = len(self.discovered_pous) + len(self.discovered_actions)
        if not total_pous:
            self.results_text.insert(tk.END, "No POUs with executable logic found in the file.")
            return

        self.results_text.insert(tk.END, f"Found {total_pous} POUs and Actions with executable logic:\n\n")

        # Display main POUs
        for pou in self.discovered_pous:
            preview = pou['executable_content'][:400] + "..." if len(pou['executable_content']) > 400 else pou[
                'executable_content']
            sub_calls = ", ".join(pou['sub_pou_calls']) if pou['sub_pou_calls'] else "None"
            self.results_text.insert(tk.END,
                                     f"MAIN POU: {pou['name']}\n"
                                     f"Type: {pou['type']}\n"
                                     f"Executable Lines: {pou['lines']}, Size: {pou['size']} chars\n"
                                     f"Sub-POU Calls: {sub_calls}\n"
                                     f"Logic Preview:\n{preview}\n"
                                     f"{'-' * 60}\n"
                                     )

        # Display actions
        for action in self.discovered_actions:
            preview = action['executable_content'][:400] + "..." if len(action['executable_content']) > 400 else action[
                'executable_content']
            sub_calls = ", ".join(action['sub_pou_calls']) if action['sub_pou_calls'] else "None"
            self.results_text.insert(tk.END,
                                     f"ACTION: {action['name']}\n"
                                     f"Parent POU: {action.get('parent_pou', 'Unknown')}\n"
                                     f"Executable Lines: {action['lines']}, Size: {action['size']} chars\n"
                                     f"Sub-POU Calls: {sub_calls}\n"
                                     f"Logic Preview:\n{preview}\n"
                                     f"{'-' * 60}\n"
                                     )

    def populate_pou_list(self):
        """Populate the POU selection listbox"""
        self.pou_listbox.delete(0, tk.END)

        all_pous = self.discovered_pous + self.discovered_actions

        for i, pou in enumerate(all_pous):
            if pou.get('is_action', False):
                type_abbr = 'A'
                parent_info = f" ({pou.get('parent_pou', 'Unknown')})"
            else:
                type_abbr = {'program': 'P', 'functionBlock': 'FB', 'function': 'F'}.get(pou['type'].lower(), 'U')
                parent_info = ""

            first_line = pou['executable_content'].split('\n')[0] if pou[
                'executable_content'] else "No executable content"
            sub_calls_count = len(pou['sub_pou_calls'])
            display_text = f"[{type_abbr}] {pou['name']}{parent_info} ({pou['lines']} lines, {sub_calls_count} sub-calls) - {first_line[:80]}..."
            self.pou_listbox.insert(tk.END, display_text)

        self.update_selection_info()

    def on_pou_select(self, event):
        """Handle POU selection in listbox"""
        selected_indices = self.pou_listbox.curselection()
        self.selected_pous = set(selected_indices)
        self.update_selection_info()

    def update_selection_info(self):
        """Update selection information display"""
        selected_count = len(self.selected_pous)
        total_count = len(self.discovered_pous) + len(self.discovered_actions)
        self.selection_info.config(text=f"Selected: {selected_count} of {total_count} POUs")

    def select_all_pous(self):
        """Select all POUs"""
        total_count = len(self.discovered_pous) + len(self.discovered_actions)
        self.pou_listbox.selection_set(0, total_count - 1)
        self.selected_pous = set(range(total_count))
        self.update_selection_info()

    def select_none_pous(self):
        """Deselect all POUs"""
        self.pou_listbox.selection_clear(0, tk.END)
        self.selected_pous.clear()
        self.update_selection_info()

    def select_programs_only(self):
        """Select only programs"""
        self.select_none_pous()
        all_pous = self.discovered_pous + self.discovered_actions
        for i, pou in enumerate(all_pous):
            if pou['type'].lower() == 'program' or pou.get('is_action', False):
                self.pou_listbox.selection_set(i)
                self.selected_pous.add(i)
        self.update_selection_info()

    def select_fbs_only(self):
        """Select only function blocks"""
        self.select_none_pous()
        all_pous = self.discovered_pous + self.discovered_actions
        for i, pou in enumerate(all_pous):
            if pou['type'].lower() == 'functionblock':
                self.pou_listbox.selection_set(i)
                self.selected_pous.add(i)
        self.update_selection_info()

    def filter_pous(self, event=None):
        """Filter POUs based on search text"""
        search_text = self.search_var.get().lower()
        self.pou_listbox.delete(0, tk.END)

        all_pous = self.discovered_pous + self.discovered_actions

        for i, pou in enumerate(all_pous):
            if (search_text in pou['name'].lower() or
                    search_text in pou['executable_content'].lower()):

                if pou.get('is_action', False):
                    type_abbr = 'A'
                    parent_info = f" ({pou.get('parent_pou', 'Unknown')})"
                else:
                    type_abbr = {'program': 'P', 'functionBlock': 'FB', 'function': 'F'}.get(pou['type'].lower(), 'U')
                    parent_info = ""

                first_line = pou['executable_content'].split('\n')[0] if pou[
                    'executable_content'] else "No executable content"
                sub_calls_count = len(pou['sub_pou_calls'])
                display_text = f"[{type_abbr}] {pou['name']}{parent_info} ({pou['lines']} lines, {sub_calls_count} sub-calls) - {first_line[:80]}..."
                self.pou_listbox.insert(tk.END, display_text)
                if i in self.selected_pous:
                    self.pou_listbox.selection_set(tk.END)

    def preview_pou(self, event):
        """Preview selected POU"""
        selection = self.pou_listbox.curselection()
        if selection:
            all_pous = self.discovered_pous + self.discovered_actions
            pou_index = selection[0]
            pou = all_pous[pou_index]

            preview_win = tk.Toplevel(self.root)
            preview_win.title(f"Preview: {pou['name']}")
            preview_win.geometry("800x600")

            header_frame = tk.Frame(preview_win)
            header_frame.pack(fill=tk.X, padx=10, pady=5)

            if pou.get('is_action', False):
                pou_type = f"Action (Parent: {pou.get('parent_pou', 'Unknown')})"
            else:
                pou_type = pou['type']

            tk.Label(header_frame, text=f"POU: {pou['name']}", font=("Arial", 12, "bold")).pack(anchor="w")
            tk.Label(header_frame,
                     text=f"Type: {pou_type} | Executable Lines: {pou['lines']} | Sub-Calls: {len(pou['sub_pou_calls'])}",
                     font=("Arial", 9)).pack(anchor="w")

            content_text = scrolledtext.ScrolledText(
                preview_win,
                wrap=tk.WORD,
                font=("Consolas", 10)
            )
            content_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            content_text.insert(1.0,
                                f"Sub-POU Calls: {', '.join(pou['sub_pou_calls']) if pou['sub_pou_calls'] else 'None'}\n\n")
            content_text.insert(tk.END, pou['executable_content'])
            content_text.config(state=tk.DISABLED)

    def process_selected_pous(self):
        """Process selected POUs using structure-aware approach"""
        if not self.selected_pous:
            messagebox.showwarning("Warning", "No POUs selected!")
            return

        selected_indices = list(self.selected_pous)
        self.log_message("INFO", f"Processing {len(selected_indices)} selected POUs with structure-aware flowcharts...")

        base_name = os.path.splitext(os.path.basename(self.file_path))[0]
        output_dir = f"{base_name}_structure_aware_flowcharts"
        os.makedirs(output_dir, exist_ok=True)

        # Get all POUs (main + actions)
        all_pous = self.discovered_pous + self.discovered_actions

        # Track all POUs that need processing (selected + their sub-POUs from structure)
        all_pous_to_process = set()

        # First pass: collect all POUs that need processing
        for pou_index in selected_indices:
            if pou_index < len(all_pous):
                pou = all_pous[pou_index]
                all_pous_to_process.add(pou['name'])
                self.log_message("DEBUG", f"Selected POU: {pou['name']} with sub-calls: {pou['sub_pou_calls']}")

                # Add all sub-POUs that exist in structure
                for sub_call in pou['sub_pou_calls']:
                    # Check if sub_call exists in our structure
                    if any(sub_call == pou_info['name'] for pou_info in self.object_id_map.values()):
                        all_pous_to_process.add(sub_call)
                        self.log_message("DEBUG", f"Added structured sub-POU: {sub_call}")
                    else:
                        self.log_message("WARNING", f"Sub-POU not found in structure: {sub_call}")

        self.log_message("INFO", f"Total POUs to process: {len(all_pous_to_process)} - {list(all_pous_to_process)}")

        success_count = 0
        # Process all collected POUs
        for pou_name in all_pous_to_process:
            pou = self.find_pou_by_name(pou_name)
            if pou:
                self.log_message("INFO", f"Processing {pou['name']} ({success_count + 1}/{len(all_pous_to_process)})")

                try:
                    mermaid_content = self.generate_structured_mermaid_flowchart(pou)
                    safe_name = re.sub(r'[^\w\-_\. ]', '_', pou['name'])
                    mermaid_filename = f"{output_dir}/{safe_name}.mmd"
                    self.save_file(mermaid_content, mermaid_filename)
                    self.log_message("SUCCESS", f"Created Structured Mermaid: {mermaid_filename}")
                    success_count += 1

                except Exception as e:
                    self.log_message("ERROR", f"Failed to process {pou['name']}: {str(e)}")
            else:
                self.log_message("ERROR", f"POU not found for processing: {pou_name}")

        self.log_message("SUCCESS", f"Successfully processed {success_count}/{len(all_pous_to_process)} POUs")
        messagebox.showinfo("Complete", f"Processing complete!\nGenerated {success_count} flowcharts in: {output_dir}")

    def generate_structured_mermaid_flowchart(self, pou):
        """Generate Mermaid flowchart with structure-aware sub-POU integration"""
        lines = [line.strip() for line in pou['executable_content'].split('\n') if line.strip()]

        mermaid = f"%% {pou['name']} - Structure-Aware Flowchart\n"
        mermaid += "flowchart TD\n"

        # Start node
        start_node = "Start"
        mermaid += f"    {start_node}([Start: {pou['name']}])\n"

        # Parse and generate flowchart with structure-aware sub-POU handling
        nodes, connections = self.parse_lines_with_structured_calls(lines, start_node, pou)
        mermaid += nodes
        mermaid += connections

        # End node
        end_node = "End"
        mermaid += f"    {end_node}([End])\n"

        # Connect last node to end
        if connections:
            last_node = self.get_last_node_id(connections)
            if last_node != start_node:
                mermaid += f"    {last_node} --> {end_node}\n"

        return mermaid

    def parse_lines_with_structured_calls(self, lines, start_node, pou):
        """Parse ST lines with structure-aware sub-POU call detection"""
        nodes = ""
        connections = ""
        current_node = start_node
        node_counter = 0

        i = 0
        while i < len(lines):
            line = lines[i]
            node_counter += 1
            node_id = f"N{node_counter}"

            # Check for control structures (existing logic)
            if re.match(r'CASE\s+.*\s+OF', line, re.IGNORECASE):
                case_nodes, case_connections, new_i = self.parse_case_structure_full_text(lines, i, current_node,
                                                                                          node_counter, pou)
                nodes += case_nodes
                connections += case_connections
                i = new_i
                current_node = f"CaseEnd_{node_counter}"
                node_counter += 20

            elif re.match(r'IF\s+.*\s+THEN', line, re.IGNORECASE):
                if_nodes, if_connections, new_i = self.parse_if_structure_full_text(lines, i, current_node,
                                                                                    node_counter, pou)
                nodes += if_nodes
                connections += if_connections
                i = new_i
                current_node = f"IfEnd_{node_counter}"
                node_counter += 20

            # Check for structured sub-POU calls
            elif self.is_structured_sub_pou_call(line, pou):
                sub_call_node = f"SubCall_{node_counter}"
                sub_pou_name = self.extract_sub_pou_name(line)

                # Create a special sub-POU call node
                call_text = self.clean_text_for_mermaid_full(f"CALL: {sub_pou_name}")
                nodes += f"    {sub_call_node}[{call_text}]\n"
                nodes += f"    style {sub_call_node} fill:#e1f5fe,stroke:#01579b,stroke-width:2px\n"
                connections += f"    {current_node} --> {sub_call_node}\n"
                current_node = sub_call_node
                self.log_message("DEBUG", f"Added structured sub-POU call node: {sub_pou_name} in {pou['name']}")

            # Regular statement
            else:
                display_text = self.clean_text_for_mermaid_full(line)
                nodes += f"    {node_id}[{display_text}]\n"
                connections += f"    {current_node} --> {node_id}\n"
                current_node = node_id

            i += 1

        return nodes, connections

    def is_structured_sub_pou_call(self, line, current_pou):
        """Check if a line contains a sub-POU call that exists in structure"""
        clean_line = line.strip()

        # Skip comments and control structures
        if (clean_line.startswith('//') or
                clean_line.upper().startswith(('IF', 'CASE', 'FOR', 'WHILE', 'END_'))):
            return False

        # Check for function call pattern
        if re.match(r'^\s*\w+\s*\([^)]*\)\s*;', clean_line):
            call_name = clean_line.split('(')[0].strip()

            # Check if this call exists in our structure
            return any(call_name == pou_info['name'] for pou_info in self.object_id_map.values())

        return False


    #//////////////
    def find_pou_by_name(self, pou_name):
        """Find a POU by name, handling various call formats"""
        all_pous = self.discovered_pous + self.discovered_actions

        # Direct name match (case insensitive)
        for pou in all_pous:
            if pou['name'].lower() == pou_name.lower():
                return pou

        # Handle action names without parent prefix
        if '.' in pou_name:
            action_name = pou_name.split('.')[-1]
            for pou in all_pous:
                if pou.get('is_action', False) and pou['name'].split('.')[-1].lower() == action_name.lower():
                    return pou

        # Partial match (contains)
        for pou in all_pous:
            if pou_name.lower() in pou['name'].lower():
                self.log_message("DEBUG", f"Partial match found: {pou_name} -> {pou['name']}")
                return pou

        self.log_message("DEBUG", f"No POU found for: {pou_name}")
        return None

    def generate_full_text_mermaid_flowchart(self, pou):
        """Generate Mermaid flowchart with full text content and sub-POU integration"""
        lines = [line.strip() for line in pou['executable_content'].split('\n') if line.strip()]

        mermaid = f"%% {pou['name']} - {pou['type']} - Full Text Flowchart\n"
        mermaid += "flowchart TD\n"

        # Start node
        start_node = "Start"
        mermaid += f"    {start_node}([Start: {pou['name']}])\n"

        # Parse and generate flowchart
        nodes, connections = self.parse_lines_with_full_text(lines, start_node, pou)
        mermaid += nodes
        mermaid += connections

        # End node
        end_node = "End"
        mermaid += f"    {end_node}([End])\n"

        # Connect last node to end
        if connections:
            last_node = self.get_last_node_id(connections)
            if last_node != start_node:
                mermaid += f"    {last_node} --> {end_node}\n"

        return mermaid

    def parse_lines_with_full_text(self, lines, start_node, pou):
        """Parse ST lines into Mermaid nodes with full text content and sub-POU handling"""
        nodes = ""
        connections = ""
        current_node = start_node
        node_counter = 0

        i = 0
        while i < len(lines):
            line = lines[i]
            node_counter += 1
            node_id = f"N{node_counter}"

            # Check for CASE statement
            if re.match(r'CASE\s+.*\s+OF', line, re.IGNORECASE):
                case_nodes, case_connections, new_i = self.parse_case_structure_full_text(lines, i, current_node,
                                                                                          node_counter, pou)
                nodes += case_nodes
                connections += case_connections
                i = new_i
                current_node = f"CaseEnd_{node_counter}"
                node_counter += 20  # Reserve IDs for case structure

            # Check for IF statement
            elif re.match(r'IF\s+.*\s+THEN', line, re.IGNORECASE):
                if_nodes, if_connections, new_i = self.parse_if_structure_full_text(lines, i, current_node,
                                                                                    node_counter, pou)
                nodes += if_nodes
                connections += if_connections
                i = new_i
                current_node = f"IfEnd_{node_counter}"
                node_counter += 20  # Reserve IDs for if structure

            # Check for sub-POU calls
            elif self.is_sub_pou_call(line, pou):
                sub_call_node = f"SubCall_{node_counter}"
                sub_pou_name = self.extract_sub_pou_name(line)
                sub_pou = self.find_pou_by_name(sub_pou_name)

                if sub_pou:
                    # Create a special sub-POU call node
                    call_text = self.clean_text_for_mermaid_full(f"CALL: {sub_pou_name}")
                    nodes += f"    {sub_call_node}[{call_text}]\n"
                    nodes += f"    style {sub_call_node} fill:#e1f5fe,stroke:#01579b,stroke-width:2px\n"
                    connections += f"    {current_node} --> {sub_call_node}\n"
                    current_node = sub_call_node
                    self.log_message("DEBUG", f"Added sub-POU call node: {sub_pou_name} in {pou['name']}")
                else:
                    # Regular statement if sub-POU not found
                    display_text = self.clean_text_for_mermaid_full(line)
                    nodes += f"    {node_id}[{display_text}]\n"
                    connections += f"    {current_node} --> {node_id}\n"
                    current_node = node_id

            # Regular statement - use FULL text
            else:
                display_text = self.clean_text_for_mermaid_full(line)
                nodes += f"    {node_id}[{display_text}]\n"
                connections += f"    {current_node} --> {node_id}\n"
                current_node = node_id

            i += 1

        return nodes, connections

    def is_sub_pou_call(self, line, current_pou):
        """Check if a line contains a sub-POU call"""
        # Clean the line for analysis
        clean_line = line.strip()

        # Skip comments and control structures
        if (clean_line.startswith('//') or
                clean_line.upper().startswith(('IF', 'CASE', 'FOR', 'WHILE', 'END_'))):
            return False

        # Check for function call pattern: Name(parameters)
        if re.match(r'^\s*\w+\s*\([^)]*\)\s*;', clean_line):
            call_name = clean_line.split('(')[0].strip()

            # Check if this is a call to a known sub-POU
            for sub_call in current_pou['sub_pou_calls']:
                if sub_call == call_name:
                    return True

        return False

    def extract_sub_pou_name(self, line):
        """Extract the sub-POU name from a line"""
        # Try to find the best match from the discovered POUs
        all_pous = self.discovered_pous + self.discovered_actions
        for pou in all_pous:
            if pou['name'] in line:
                return pou['name']

        # Fallback: extract text before first parenthesis
        if '(' in line:
            return line.split('(')[0].strip()

        return line.strip()

    def parse_case_structure_full_text(self, lines, start_index, parent_node, base_id, pou):
        """Parse CASE-OF structure with full text - FIXED VERSION"""
        nodes = ""
        connections = ""

        # CASE node - just the CASE statement itself
        case_node = f"Case_{base_id}"
        case_text = self.clean_text_for_mermaid_full(lines[start_index])
        nodes += f"    {case_node}[{case_text}]\n"
        connections += f"    {parent_node} --> {case_node}\n"

        i = start_index + 1
        case_options = []
        current_option = None

        while i < len(lines) and not re.match(r'END_CASE', lines[i], re.IGNORECASE):
            line = lines[i]

            # Check if this is a case option (contains colon)
            if ':' in line and not line.startswith('//'):
                # Save previous option if it exists
                if current_option:
                    case_options.append(current_option)

                # Start new case option
                parts = line.split(':', 1)
                condition = parts[0].strip()
                remaining_logic = parts[1].strip() if len(parts) > 1 else ""

                current_option = {
                    'condition': condition,
                    'logic_lines': [remaining_logic] if remaining_logic else [],
                    'node_id': f"CaseOpt_{base_id}_{len(case_options)}"
                }
            elif current_option is not None and line.strip() and not line.startswith('//'):
                # This is continuation logic for the current case option
                current_option['logic_lines'].append(line)
            elif current_option is None and line.strip() and not line.startswith('//'):
                # This might be logic before any case options (shouldn't normally happen)
                self.log_message("WARNING", f"Unexpected logic before case options: {line}")

            i += 1

        # Don't forget to add the last option
        if current_option:
            case_options.append(current_option)

        # Create branches for each case option
        for opt in case_options:
            # Condition node (the case value)
            cond_text = self.clean_text_for_mermaid_full(opt['condition'])
            nodes += f"    {opt['node_id']}[{cond_text}]\n"
            connections += f"    {case_node} --> {opt['node_id']}\n"

            # Create nodes for the logic under this case condition
            current_node = opt['node_id']
            logic_counter = 0

            for logic_line in opt['logic_lines']:
                if logic_line.strip():  # Only process non-empty lines
                    logic_counter += 1
                    logic_node_id = f"{opt['node_id']}_L{logic_counter}"

                    # Check if this is a sub-POU call
                    if self.is_sub_pou_call(logic_line, pou):
                        sub_pou_name = self.extract_sub_pou_name(logic_line)
                        call_text = self.clean_text_for_mermaid_full(f"CALL: {sub_pou_name}")
                        nodes += f"    {logic_node_id}[{call_text}]\n"
                        nodes += f"    style {logic_node_id} fill:#e1f5fe,stroke:#01579b,stroke-width:2px\n"
                        self.log_message("DEBUG", f"Added sub-POU call in CASE: {sub_pou_name}")
                    else:
                        logic_text = self.clean_text_for_mermaid_full(logic_line)
                        nodes += f"    {logic_node_id}[{logic_text}]\n"

                    connections += f"    {current_node} --> {logic_node_id}\n"
                    current_node = logic_node_id

            # Store the last node for this branch to connect to end
            opt['last_node'] = current_node

        # End of CASE
        end_node = f"CaseEnd_{base_id}"
        nodes += f"    {end_node}[Continue...]\n"

        # Connect all case option branches to end node
        for opt in case_options:
            connections += f"    {opt['last_node']} --> {end_node}\n"

        return nodes, connections, i + 1  # Skip END_CASE line

    def parse_if_structure_full_text(self, lines, start_index, parent_node, base_id, pou):
        """Parse IF-THEN-ELSIF-ELSE structure with full text"""
        nodes = ""
        connections = ""

        # IF condition node (diamond) - full text
        if_node = f"If_{base_id}"
        condition_text = self.clean_text_for_mermaid_full(lines[start_index])
        nodes += f"    {if_node}{{{{{condition_text}}}}}\n"
        connections += f"    {parent_node} --> {if_node}\n"

        i = start_index + 1
        branches = []
        current_branch = None

        while i < len(lines) and not re.match(r'END_IF', lines[i], re.IGNORECASE):
            line = lines[i]

            if re.match(r'ELSIF\s+.*\s+THEN', line, re.IGNORECASE):
                current_branch = {
                    'type': 'elsif',
                    'line': line,
                    'node_id': f"Elsif_{base_id}_{len(branches)}",
                    'statements': []
                }
                branches.append(current_branch)
            elif re.match(r'ELSE', line, re.IGNORECASE):
                current_branch = {
                    'type': 'else',
                    'line': line,
                    'node_id': f"Else_{base_id}",
                    'statements': []
                }
                branches.append(current_branch)
            else:
                if current_branch:
                    current_branch['statements'].append(line)
                else:
                    # THEN branch (first statements after IF)
                    if not any(b['type'] == 'then' for b in branches):
                        branches.append({
                            'type': 'then',
                            'line': 'THEN',
                            'node_id': f"Then_{base_id}",
                            'statements': [line]
                        })
                    else:
                        # Add to existing THEN branch
                        for branch in branches:
                            if branch['type'] == 'then':
                                branch['statements'].append(line)
                                break

            i += 1

        # Create branches with full text
        for branch in branches:
            branch_node = branch['node_id']

            if branch['type'] == 'then':
                branch_text = self.clean_text_for_mermaid_full("THEN")
                nodes += f"    {branch_node}[{branch_text}]\n"
                connections += f"    {if_node} -- Yes --> {branch_node}\n"
            elif branch['type'] == 'elsif':
                branch_text = self.clean_text_for_mermaid_full(branch['line'])
                nodes += f"    {branch_node}[{branch_text}]\n"
                # Use the actual condition text for the connection label
                cond_clean = self.clean_text_for_connection(
                    branch['line'].replace('ELSIF', '').replace('THEN', '').strip())
                connections += f"    {if_node} -- {cond_clean} --> {branch_node}\n"
            else:  # ELSE
                branch_text = self.clean_text_for_mermaid_full("ELSE")
                nodes += f"    {branch_node}[{branch_text}]\n"
                connections += f"    {if_node} -- No --> {branch_node}\n"

            # Add statements for this branch with full text
            current = branch_node
            for stmt in branch['statements']:
                if stmt.strip() and not re.match(r'IF\s+.*\s+THEN', stmt, re.IGNORECASE):
                    stmt_node = f"Stmt_{base_id}_{hash(stmt) % 10000}"

                    # Check if this is a sub-POU call
                    if self.is_sub_pou_call(stmt, pou):
                        sub_pou_name = self.extract_sub_pou_name(stmt)
                        call_text = self.clean_text_for_mermaid_full(f"CALL: {sub_pou_name}")
                        nodes += f"    {stmt_node}[{call_text}]\n"
                        nodes += f"    style {stmt_node} fill:#e1f5fe,stroke:#01579b,stroke-width:2px\n"
                        self.log_message("DEBUG", f"Added sub-POU call in IF: {sub_pou_name}")
                    else:
                        stmt_text = self.clean_text_for_mermaid_full(stmt)
                        nodes += f"    {stmt_node}[{stmt_text}]\n"

                    connections += f"    {current} --> {stmt_node}\n"
                    current = stmt_node

        # End of IF
        end_node = f"IfEnd_{base_id}"
        nodes += f"    {end_node}[Continue...]\n"

        # Connect all branch ends to end node
        for branch in branches:
            last_node = self.get_last_branch_node_full(branch, base_id)
            connections += f"    {last_node} --> {end_node}\n"

        return nodes, connections, i + 1  # Skip END_IF line

    def get_last_branch_node_full(self, branch, base_id):
        """Get the last node in a branch with full text handling"""
        if branch['statements']:
            last_stmt = branch['statements'][-1]
            return f"Stmt_{base_id}_{hash(last_stmt) % 10000}"
        else:
            return branch['node_id']

    def get_last_node_id(self, connections):
        """Extract the last node ID from connections"""
        lines = connections.strip().split('\n')
        if lines:
            last_line = lines[-1]
            if '-->' in last_line:
                parts = last_line.split('-->')
                return parts[0].strip().split()[-1]  # Get the source node
        return "Start"

    def clean_text_for_mermaid_full(self, text):
        """Clean and escape text for Mermaid syntax - FIXED VERSION"""
        # Keep most of the text - only truncate if extremely long
        if len(text) > 150:
            text = text[:147] + "..."

        # Only escape characters that are problematic in Mermaid/HTML
        # Mermaid can handle most characters including [], (), etc.
        text = text.replace('"', '&quot;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('&', '&amp;')

        # Remove or minimize newlines within a single node
        text = text.replace('\n', ' | ')

        return f'"{text}"'

    def clean_text_for_connection(self, text):
        """Clean text for connection labels (shorter)"""
        if len(text) > 30:
            text = text[:27] + "..."

        text = text.replace('"', '&quot;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('&', '&amp;')

        return f'"{text}"'

    def save_file(self, content, filename):
        """Save content to file"""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(content)

    def open_output_folder(self):
        """Open output folder"""
        if self.file_path:
            base_name = os.path.splitext(os.path.basename(self.file_path))[0]
            output_dir = f"{base_name}_full_text_flowcharts"
            if os.path.exists(output_dir):
                try:
                    os.startfile(output_dir)
                except:
                    self.log_message("INFO", f"Output folder: {os.path.abspath(output_dir)}")

    def update_progress(self, message, value):
        """Update progress bar"""
        self.progress_var.set(value)
        self.progress_label.config(text=message)
        self.root.update_idletasks()

    def log_message(self, level, message):
        """Log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] [{level}] {message}\n"
        self.output_text.insert(tk.END, formatted_message)
        self.output_text.see(tk.END)
        self.root.update()

    def clear_log(self):
        """Clear log"""
        self.output_text.delete(1.0, tk.END)

    def run(self):
        """Start application"""
        self.log_message("INFO", "Smart Mermaid Processor with Full Text Flowcharts and Sub-POU Support started")
        self.root.mainloop()


if __name__ == "__main__":
    app = SmartMermaidProcessor()
    app.run()