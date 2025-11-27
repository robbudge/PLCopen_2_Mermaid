import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import xml.etree.ElementTree as ET
import os
import subprocess
import tempfile
import webbrowser
from pathlib import Path
from xml_parser import CodesysXMLParser
from mermaid_converter import MermaidConverter
from gui_export import GUIExport


class CodesysToMermaidGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Codesys XML to Mermaid Converter")
        self.root.geometry("1200x800")

        self.parser = None
        self.current_pou = None
        self.current_action = None
        self.current_method = None
        self.selected_item_type = None  # "POU", "Action", or "Method"
        self.output_folder = None
        self.export_handler = GUIExport(self)  # Add export handler
        # Add these for recursive processing
        self.recursive_mode = False
        self.current_recursive_pou = None
        self.all_flowcharts = {}

        self.setup_gui()

    def setup_gui(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Main tab
        main_tab = ttk.Frame(notebook)
        notebook.add(main_tab, text="Main")

        # Debug tab
        debug_tab = ttk.Frame(notebook)
        notebook.add(debug_tab, text="Debug")

        self.setup_main_tab(main_tab)
        self.setup_debug_tab(debug_tab)

    def setup_main_tab(self, parent):
        # Main frame
        main_frame = ttk.Frame(parent, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # File selection
        file_frame = ttk.LabelFrame(main_frame, text="XML File Selection", padding="5")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.file_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path, width=80).grid(row=0, column=0, padx=5)
        ttk.Button(file_frame, text="Browse", command=self.browse_file).grid(row=0, column=1, padx=5)
        ttk.Button(file_frame, text="Load XML", command=self.load_xml).grid(row=0, column=2, padx=5)

        # Output folder selection
        output_frame = ttk.LabelFrame(main_frame, text="Output Folder", padding="5")
        output_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)

        self.output_folder_var = tk.StringVar()
        ttk.Entry(output_frame, textvariable=self.output_folder_var, width=80).grid(row=0, column=0, padx=5)
        ttk.Button(output_frame, text="Browse", command=self.browse_output_folder).grid(row=0, column=1, padx=5)
        ttk.Button(output_frame, text="Use Current", command=self.use_current_folder).grid(row=0, column=2, padx=5)

        # Project tree and POU selection
        tree_frame = ttk.LabelFrame(main_frame, text="Project Structure", padding="5")
        tree_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=(0, 5))

        self.tree_view = ttk.Treeview(tree_frame)
        self.tree_view.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_view.yview)
        tree_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tree_view.configure(yscrollcommand=tree_scroll.set)

        # Bind tree selection
        self.tree_view.bind('<<TreeviewSelect>>', self.on_tree_select)

        # POU details and conversion
        details_frame = ttk.LabelFrame(main_frame, text="POU Details & Conversion", padding="5")
        details_frame.grid(row=2, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        # POU info
        info_frame = ttk.Frame(details_frame)
        info_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)

        ttk.Label(info_frame, text="Selected POU:").grid(row=0, column=0, sticky=tk.W)
        self.selected_pou_label = ttk.Label(info_frame, text="None")
        self.selected_pou_label.grid(row=0, column=1, sticky=tk.W, padx=5)

        ttk.Label(info_frame, text="Language:").grid(row=1, column=0, sticky=tk.W)
        self.language_label = ttk.Label(info_frame, text="None")
        self.language_label.grid(row=1, column=1, sticky=tk.W, padx=5)

        ttk.Label(info_frame, text="POU Type:").grid(row=2, column=0, sticky=tk.W)
        self.pou_type_label = ttk.Label(info_frame, text="None")
        self.pou_type_label.grid(row=2, column=1, sticky=tk.W, padx=5)

        # Convert buttons
        button_frame = ttk.Frame(details_frame)
        button_frame.grid(row=1, column=0, pady=10)

        ttk.Button(button_frame, text="Generate Mermaid Flowchart",
                   command=self.generate_mermaid).grid(row=0, column=0, padx=5)
        #ttk.Button(button_frame, text="Save Mermaid",
                   #command=self.save_mermaid).grid(row=0, column=1, padx=5)
        #ttk.Button(button_frame, text="Save HTML",
                   #command=self.save_html).grid(row=0, column=2, padx=5)
        #ttk.Button(button_frame, text="Generate PDF",
                   #command=self.generate_pdf).grid(row=0, column=3, padx=5)

        # Add recursive processing button
        ttk.Button(button_frame, text="Generate Recursive (POU + Actions)",
                   command=self.generate_recursive_mermaid).grid(row=1, column=0, columnspan=2, pady=5, sticky=tk.W)

        # Mermaid output
        output_frame = ttk.LabelFrame(main_frame, text="Mermaid Flowchart", padding="5")
        output_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        self.mermaid_output = scrolledtext.ScrolledText(output_frame, width=100, height=15)
        self.mermaid_output.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Copy button
        ttk.Button(output_frame, text="Copy to Clipboard",
                   command=self.copy_to_clipboard).grid(row=1, column=0, pady=5)

        # Configure grid weights
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        main_frame.rowconfigure(3, weight=1)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        details_frame.columnconfigure(0, weight=1)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)

    def setup_debug_tab(self, parent):
        # Debug info frame
        debug_frame = ttk.Frame(parent, padding="10")
        debug_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Debug controls
        controls_frame = ttk.Frame(debug_frame)
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)

        ttk.Button(controls_frame, text="Refresh Debug Info",
                   command=self.refresh_debug).grid(row=0, column=0, padx=5)
        ttk.Button(controls_frame, text="Clear Debug",
                   command=self.clear_debug).grid(row=0, column=1, padx=5)
        ttk.Button(controls_frame, text="Show XML Structure",
                   command=self.show_xml_structure).grid(row=0, column=2, padx=5)

        # Debug output
        self.debug_output = scrolledtext.ScrolledText(debug_frame, width=120, height=30)
        self.debug_output.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure weights
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)
        debug_frame.columnconfigure(0, weight=1)
        debug_frame.rowconfigure(1, weight=1)

    def browse_file(self):
        filename = filedialog.askopenfilename(
            title="Select Codesys XML File",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if filename:
            self.file_path.set(filename)
            self.add_debug(f"Selected file: {filename}")

    def browse_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder_var.set(folder)
            self.output_folder = folder
            self.add_debug(f"Output folder set to: {folder}")

    def use_current_folder(self):
        """Use the current XML file's folder as output folder"""
        if self.file_path.get():
            folder = os.path.dirname(self.file_path.get())
            self.output_folder_var.set(folder)
            self.output_folder = folder
            self.add_debug(f"Output folder set to XML folder: {folder}")

    def load_xml(self):
        if not self.file_path.get():
            messagebox.showerror("Error", "Please select an XML file first")
            return

        try:
            self.add_debug("=" * 50)
            self.add_debug("STARTING XML LOAD")
            self.add_debug(f"File: {self.file_path.get()}")

            self.parser = CodesysXMLParser(self.file_path.get())

            # Add parser debug info to our debug output
            for debug_msg in self.parser.get_debug_info():
                self.add_debug(debug_msg)

            self.populate_tree()
            self.add_debug("XML loading completed successfully")

            # Set default output folder to XML file's folder
            if not self.output_folder:
                self.use_current_folder()

            messagebox.showinfo("Success", "XML file loaded successfully")

        except Exception as e:
            error_msg = f"Failed to load XML file: {str(e)}"
            self.add_debug(f"ERROR: {error_msg}")
            messagebox.showerror("Error", error_msg)

    def populate_tree(self):
        self.tree_view.delete(*self.tree_view.get_children())

        if not self.parser:
            self.add_debug("No parser available for populating tree")
            return

        pous = self.parser.get_pous()
        self.add_debug(f"Populating tree with {len(pous)} POUs")

        # Add POUs
        pou_parent = self.tree_view.insert("", "end", text="POUs", open=True)
        for pou_name, pou_data in pous.items():
            pou_id = self.tree_view.insert(pou_parent, "end", text=pou_name,
                                           values=("POU", pou_name, pou_data.get('pouType', 'unknown')))
            self.add_debug(f"Added POU to tree: {pou_name}")

            # Add actions
            for action_name in pou_data.get('actions', []):
                self.tree_view.insert(pou_id, "end", text=f"Action: {action_name}",
                                      values=("Action", pou_name, action_name))

            # Add methods
            for method_name in pou_data.get('methods', []):
                self.tree_view.insert(pou_id, "end", text=f"Method: {method_name}",
                                      values=("Method", pou_name, method_name))

    def on_tree_select(self, event):
        selection = self.tree_view.selection()
        if not selection:
            return

        item = selection[0]
        item_values = self.tree_view.item(item, "values")

        if item_values:
            item_type = item_values[0]

            if item_type == "POU":
                pou_name = item_values[1]
                self.current_pou = pou_name
                self.current_action = None
                self.current_method = None
                self.selected_item_type = "POU"
                self.selected_pou_label.config(text=pou_name)

                # Get POU details - FIXED: Get proper language information
                pou_data = self.parser.get_pous().get(pou_name, {})

                # Get language with proper fallback
                language = pou_data.get('language', 'Unknown')
                body_language = pou_data.get('bodyLanguage', 'Unknown')
                pou_type = pou_data.get('pouType', 'Unknown')

                # Use bodyLanguage if main language is Unknown but bodyLanguage is known
                if language == 'Unknown' and body_language != 'Unknown':
                    language = body_language

                self.language_label.config(text=language)
                self.pou_type_label.config(text=pou_type)

                self.add_debug(f"Selected POU: {pou_name}")
                self.add_debug(f"  POU Type: {pou_type}")
                self.add_debug(f"  Language: {language}")
                self.add_debug(f"  Body Language: {body_language}")
                self.add_debug(f"  Body Length: {len(pou_data.get('body', ''))}")

            elif item_type == "Action":
                pou_name = item_values[1]
                action_name = item_values[2]
                self.current_pou = pou_name
                self.current_action = action_name
                self.current_method = None
                self.selected_item_type = "Action"
                self.selected_pou_label.config(text=f"{pou_name}.{action_name} (Action)")

                # Get action details
                pou_data = self.parser.get_pous().get(pou_name, {})
                action_info = pou_data.get('actionsInfo', {}).get(action_name, {})

                # Get language information with proper fallbacks
                language = action_info.get('language', 'Unknown')
                body_language = action_info.get('bodyLanguage', 'Unknown')

                # If language is unknown, try to detect from body content
                if language == 'Unknown' and body_language != 'Unknown':
                    language = body_language
                elif language == 'Unknown':
                    # Fallback to parent POU language
                    language = pou_data.get('language', 'Unknown')

                self.language_label.config(text=f"Action: {language}")
                self.pou_type_label.config(text=f"Body: {body_language}")

                self.add_debug(f"Selected Action: {pou_name}.{action_name}")
                self.add_debug(f"  Action Language: {language}")
                self.add_debug(f"  Body Language: {body_language}")
                self.add_debug(f"  Body Length: {len(action_info.get('body', ''))}")

            elif item_type == "Method":
                pou_name = item_values[1]
                method_name = item_values[2]
                self.current_pou = pou_name
                self.current_method = method_name
                self.current_action = None
                self.selected_item_type = "Method"
                self.selected_pou_label.config(text=f"{pou_name}.{method_name} (Method)")

                # Get method details
                pou_data = self.parser.get_pous().get(pou_name, {})
                method_info = pou_data.get('methodsInfo', {}).get(method_name, {})

                # Get language information with proper fallbacks
                language = method_info.get('language', 'Unknown')
                body_language = method_info.get('bodyLanguage', 'Unknown')

                # If language is unknown, try to detect from body content
                if language == 'Unknown' and body_language != 'Unknown':
                    language = body_language
                elif language == 'Unknown':
                    # Fallback to parent POU language
                    language = pou_data.get('language', 'Unknown')

                self.language_label.config(text=f"Method: {language}")
                self.pou_type_label.config(text=f"Body: {body_language}")

                self.add_debug(f"Selected Method: {pou_name}.{method_name}")
                self.add_debug(f"  Method Language: {language}")
                self.add_debug(f"  Body Language: {body_language}")
                self.add_debug(f"  Body Length: {len(method_info.get('body', ''))}")

    def generate_mermaid(self):
        if not self.current_pou or not self.parser:
            messagebox.showerror("Error", "Please select a POU, Action, or Method first")
            return

        try:
            # Get POU information for logging
            pous = self.parser.get_pous()
            pou_info = pous.get(self.current_pou, {})

            if self.selected_item_type == "POU":
                self.add_debug(f"Generating Mermaid for POU: {self.current_pou}")
                code = pou_info.get('body', '')
                item_name = self.current_pou
                language = pou_info.get('language', 'Unknown')
                body_language = pou_info.get('bodyLanguage', 'Unknown')

            elif self.selected_item_type == "Action":
                action_name = getattr(self, 'current_action', None)
                if not action_name:
                    messagebox.showerror("Error", "No action selected")
                    return

                self.add_debug(f"Generating Mermaid for Action: {self.current_pou}.{action_name}")
                action_info = pou_info.get('actionsInfo', {}).get(action_name, {})
                code = action_info.get('body', '')
                item_name = f"{self.current_pou}.{action_name}"

                # Use the language information that was already detected by the XML parser
                language = action_info.get('language', 'Unknown')
                body_language = action_info.get('bodyLanguage', 'Unknown')

                # If the XML parser detected CFC, preserve that information
                if language == 'Unknown' and body_language != 'Unknown':
                    language = body_language
                elif language == 'Unknown':
                    # Fallback to parent POU language
                    language = pou_info.get('language', 'Unknown')

            elif self.selected_item_type == "Method":
                method_name = getattr(self, 'current_method', None)
                if not method_name:
                    messagebox.showerror("Error", "No method selected")
                    return

                self.add_debug(f"Generating Mermaid for Method: {self.current_pou}.{method_name}")
                method_info = pou_info.get('methodsInfo', {}).get(method_name, {})
                code = method_info.get('body', '')
                item_name = f"{self.current_pou}.{method_name}"

                # Similar language detection for methods
                language = method_info.get('language', 'Unknown')
                body_language = method_info.get('bodyLanguage', 'Unknown')

                if language == 'Unknown' and body_language != 'Unknown':
                    language = body_language
                elif language == 'Unknown':
                    language = pou_info.get('language', 'Unknown')
            else:
                messagebox.showerror("Error", "Unknown item type selected")
                return

            # Log details based on selected item type
            self.add_debug(f"=== {self.selected_item_type.upper()} DETAILS ===")
            self.add_debug(f"Name: {item_name}")

            if self.selected_item_type == "POU":
                self.add_debug(f"Type: {pou_info.get('pouType', 'Unknown')}")
                self.add_debug(f"Language: {language}")
                self.add_debug(f"Body Language: {body_language}")
                self.add_debug(f"Body Length: {len(code)} characters")

            elif self.selected_item_type == "Action":
                self.add_debug(f"Parent POU: {self.current_pou}")
                self.add_debug(f"Action Language: {language}")
                self.add_debug(f"Body Language: {body_language}")
                self.add_debug(f"Body Length: {len(code)} characters")
                self.add_debug(
                    f"Language source: {'From XML parser' if language != 'Unknown' else 'Used parent POU language'}")

            elif self.selected_item_type == "Method":
                self.add_debug(f"Parent POU: {self.current_pou}")
                self.add_debug(f"Method Language: {language}")
                self.add_debug(f"Body Language: {body_language}")
                self.add_debug(f"Body Length: {len(code)} characters")
                self.add_debug(
                    f"Language source: {'From XML parser' if language != 'Unknown' else 'Used parent POU language'}")

            self.add_debug(f"=== END {self.selected_item_type.upper()} DETAILS ===")

            if not code:
                self.add_debug(f"ERROR: No code found for {self.selected_item_type.lower()}")
                messagebox.showerror("Error", f"No code found for {self.selected_item_type.lower()} {item_name}")
                return

            # Create a custom pou_info for the selected item - PRESERVE THE LANGUAGE INFO
            custom_pou_info = {
                'name': item_name,
                'pouType': self.selected_item_type,
                'language': language,  # Use the detected language
                'bodyLanguage': body_language,  # Use the detected body language
                'body': code
            }

            #converter = MermaidConverter()
            converter = MermaidConverter(self.output_folder)

            # For actions and methods, we need to pass the custom info and use the code directly
            if self.selected_item_type in ["Action", "Method"]:
                # Create a mock parser-like object that returns our custom info
                class MockParser:
                    def __init__(self, pou_info):
                        self.pou_info = pou_info

                    def get_pous(self):
                        return {item_name: self.pou_info}

                mock_parser = MockParser(custom_pou_info)
                mermaid_code = converter.convert_pou_to_mermaid(mock_parser, item_name)
            else:
                # For regular POUs, use the normal approach but with updated info
                pou_info.update(custom_pou_info)
                mermaid_code = converter.convert_pou_to_mermaid(self.parser, self.current_pou)

            self.mermaid_output.delete(1.0, tk.END)
            self.mermaid_output.insert(1.0, mermaid_code)

            # AUTOMATICALLY SAVE FILES
            if self.output_folder:
                # Always save .mmd and .html files
                mmd_success = self.export_handler.save_mermaid(mermaid_code, f"{item_name}.mmd")
                html_success = self.export_handler.save_html(mermaid_code, f"{item_name}_flowchart.html")

                # For CFC content, also save .cfc2st file
                #if language.upper() == 'CFC' or body_language.upper() == 'CFC':
                    # Extract the ST code from the converter if available
                    # We need to get the ST code that was generated during CFC conversion
                #    cfc2st_success = self._save_cfc2st_file(item_name, code, converter)
                #else:
                    #cfc2st_success = False

                # Log the results
                if mmd_success and html_success:
                    self.add_debug(f"✓ Automatic file creation completed for {item_name}")
                    #if cfc2st_success:
                    #    self.add_debug(f"✓ CFC to ST conversion file created")
                else:
                    self.add_debug(f"⚠ Some files could not be created automatically")

            self.add_debug(f"Mermaid generation completed for {item_name}")

        except Exception as e:
            error_msg = f"Failed to generate Mermaid flowchart: {str(e)}"
            self.add_debug(f"ERROR: {error_msg}")
            import traceback
            self.add_debug(f"Traceback: {traceback.format_exc()}")
            messagebox.showerror("Error", error_msg)

    def _save_cfc2st_file(self, item_name: str, cfc_code: str, converter) -> bool:
        """Save CFC to ST conversion file"""
        try:
            # Alternative approach: Check if FBD processor already generated ST code
            if (hasattr(converter, 'fbd_processor') and
                    converter.fbd_processor is not None and
                    hasattr(converter.fbd_processor, 'cfc_converter')):

                # Get the ST code that was already generated during flowchart creation
                cfc_converter = converter.fbd_processor.cfc_converter
                if hasattr(cfc_converter, 'last_generated_st_code'):
                    st_code = cfc_converter.last_generated_st_code
                else:
                    # Generate it fresh
                    st_code = cfc_converter.convert_cfc_to_st(cfc_code)

                # Save the ST code to .cfc2st file
                filename = f"{item_name}.cfc2st"
                filepath = os.path.join(self.output_folder, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(st_code)

                self.add_debug(f"✓ CFC to ST file saved: {filepath}")
                return True
            else:
                self.add_debug("⚠ CFC to ST conversion not available")
                return False

        except Exception as e:
            self.add_debug(f"⚠ Failed to save CFC to ST file: {str(e)}")
            return False

    def generate_recursive_mermaid(self):
        """Generate Mermaid flowchart for POU including all actions and methods recursively"""
        if not self.current_pou or not self.parser:
            messagebox.showerror("Error", "Please select a POU first")
            return

        if self.selected_item_type != "POU":
            messagebox.showerror("Error", "Please select a POU (not an action or method) for recursive processing")
            return

        try:
            self.add_debug(f"Generating recursive Mermaid for POU: {self.current_pou}")

            # Get POU information
            pous = self.parser.get_pous()
            pou_info = pous.get(self.current_pou, {})

            # Log all available actions and methods
            actions = pou_info.get('actions', [])
            methods = pou_info.get('methods', [])

            self.add_debug(f"=== RECURSIVE PROCESSING FOR {self.current_pou} ===")
            self.add_debug(f"Main POU: {self.current_pou}")
            self.add_debug(f"Available actions: {len(actions)}")
            self.add_debug(f"Available methods: {len(methods)}")

            # Track processing results
            processed_items = {
                'successful': [],
                'no_code': [],
                'no_processor': [],
                'errors': []
            }

            # Create converter with output folder
            converter = MermaidConverter(self.output_folder)

            # Generate main POU flowchart
            try:
                self.add_debug(f"Generating flowchart for main POU: {self.current_pou}")
                pou_language = pou_info.get('language', 'Unknown')
                pou_body_language = pou_info.get('bodyLanguage', 'Unknown')
                pou_code = pou_info.get('body', '')

                # Use bodyLanguage if main language is Unknown but bodyLanguage is known
                if pou_language == 'Unknown' and pou_body_language != 'Unknown':
                    pou_language = pou_body_language

                if not pou_code:
                    self.add_debug(f"  ⚠ No code found for main POU: {self.current_pou}")
                    processed_items['no_code'].append(f"POU: {self.current_pou} (language: {pou_language})")
                else:
                    # Check if language is supported - CFC is handled by FBD processor
                    supported_languages = converter.get_supported_languages()
                    language_to_check = pou_language.upper()

                    # Map CFC to FBD processor
                    if language_to_check == 'CFC':
                        language_to_check = 'FBD'

                    if language_to_check not in [lang.upper() for lang in supported_languages]:
                        self.add_debug(f"  ✗ No processor for POU language: {pou_language}")
                        processed_items['no_processor'].append(f"POU: {self.current_pou} (language: {pou_language})")
                    else:
                        main_mermaid = converter.convert_pou_to_mermaid(self.parser, self.current_pou)
                        self.all_flowcharts = {self.current_pou: main_mermaid}
                        processed_items['successful'].append(f"POU: {self.current_pou} (language: {pou_language})")
                        self.add_debug(f"  ✓ Successfully generated main POU flowchart")
            except Exception as e:
                error_msg = f"Error generating main POU {self.current_pou}: {str(e)}"
                self.add_debug(f"  ✗ {error_msg}")
                processed_items['errors'].append(f"POU: {self.current_pou} - {str(e)}")
                import traceback
                self.add_debug(f"  Traceback: {traceback.format_exc()}")

            # Generate flowcharts for all actions
            for action in actions:
                try:
                    self.add_debug(f"Generating flowchart for action: {self.current_pou}.{action}")

                    action_info = pou_info.get('actionsInfo', {}).get(action, {})
                    action_code = action_info.get('body', '')
                    action_language = action_info.get('language', 'Unknown')
                    action_body_language = action_info.get('bodyLanguage', 'Unknown')

                    # Use bodyLanguage if main language is Unknown but bodyLanguage is known
                    if action_language == 'Unknown' and action_body_language != 'Unknown':
                        action_language = action_body_language

                    if not action_code:
                        self.add_debug(f"  ⚠ No code found for action: {action}")
                        processed_items['no_code'].append(
                            f"Action: {self.current_pou}.{action} (language: {action_language})")
                        continue

                    # Check if language is supported - CFC is handled by FBD processor
                    supported_languages = converter.get_supported_languages()
                    language_to_check = action_language.upper()

                    # Map CFC to FBD processor
                    if language_to_check == 'CFC':
                        language_to_check = 'FBD'

                    if language_to_check not in [lang.upper() for lang in supported_languages]:
                        self.add_debug(f"  ✗ No processor for action language: {action_language}")
                        processed_items['no_processor'].append(
                            f"Action: {self.current_pou}.{action} (language: {action_language})")
                        continue

                    # Create custom POU info for the action - PRESERVE THE LANGUAGE INFO
                    custom_pou_info = {
                        'name': f"{self.current_pou}.{action}",
                        'pouType': 'Action',
                        'language': action_language,  # Use the detected language
                        'bodyLanguage': action_body_language,  # Use the detected body language
                        'body': action_code
                    }

                    # Create mock parser for the action
                    class MockParser:
                        def __init__(self, pou_info, pou_name, action_name):
                            self.pou_info = pou_info
                            self.pou_name = pou_name
                            self.action_name = action_name

                        def get_pous(self):
                            return {f"{self.pou_name}.{self.action_name}": self.pou_info}

                    mock_parser = MockParser(custom_pou_info, self.current_pou, action)
                    action_mermaid = converter.convert_pou_to_mermaid(mock_parser, f"{self.current_pou}.{action}")
                    self.all_flowcharts[f"{self.current_pou}.{action}"] = action_mermaid
                    processed_items['successful'].append(
                        f"Action: {self.current_pou}.{action} (language: {action_language})")
                    self.add_debug(f"  ✓ Successfully generated action flowchart")

                except Exception as e:
                    error_msg = f"Error generating action {self.current_pou}.{action}: {str(e)}"
                    self.add_debug(f"  ✗ {error_msg}")
                    processed_items['errors'].append(f"Action: {self.current_pou}.{action} - {str(e)}")
                    import traceback
                    self.add_debug(f"  Traceback: {traceback.format_exc()}")

            # Generate flowcharts for all methods
            for method in methods:
                try:
                    self.add_debug(f"Generating flowchart for method: {self.current_pou}.{method}")

                    method_info = pou_info.get('methodsInfo', {}).get(method, {})
                    method_code = method_info.get('body', '')
                    method_language = method_info.get('language', 'Unknown')
                    method_body_language = method_info.get('bodyLanguage', 'Unknown')

                    # Use bodyLanguage if main language is Unknown but bodyLanguage is known
                    if method_language == 'Unknown' and method_body_language != 'Unknown':
                        method_language = method_body_language

                    if not method_code:
                        self.add_debug(f"  ⚠ No code found for method: {method}")
                        processed_items['no_code'].append(
                            f"Method: {self.current_pou}.{method} (language: {method_language})")
                        continue

                    # Check if language is supported - CFC is handled by FBD processor
                    supported_languages = converter.get_supported_languages()
                    language_to_check = method_language.upper()

                    # Map CFC to FBD processor
                    if language_to_check == 'CFC':
                        language_to_check = 'FBD'

                    if language_to_check not in [lang.upper() for lang in supported_languages]:
                        self.add_debug(f"  ✗ No processor for method language: {method_language}")
                        processed_items['no_processor'].append(
                            f"Method: {self.current_pou}.{method} (language: {method_language})")
                        continue

                    # Create custom POU info for the method - PRESERVE THE LANGUAGE INFO
                    custom_pou_info = {
                        'name': f"{self.current_pou}.{method}",
                        'pouType': 'Method',
                        'language': method_language,  # Use the detected language
                        'bodyLanguage': method_body_language,  # Use the detected body language
                        'body': method_code
                    }

                    # Create mock parser for the method
                    class MockParser:
                        def __init__(self, pou_info, pou_name, method_name):
                            self.pou_info = pou_info
                            self.pou_name = pou_name
                            self.method_name = method_name

                        def get_pous(self):
                            return {f"{self.pou_name}.{self.method_name}": self.pou_info}

                    mock_parser = MockParser(custom_pou_info, self.current_pou, method)
                    method_mermaid = converter.convert_pou_to_mermaid(mock_parser, f"{self.current_pou}.{method}")
                    self.all_flowcharts[f"{self.current_pou}.{method}"] = method_mermaid
                    processed_items['successful'].append(
                        f"Method: {self.current_pou}.{method} (language: {method_language})")
                    self.add_debug(f"  ✓ Successfully generated method flowchart")

                except Exception as e:
                    error_msg = f"Error generating method {self.current_pou}.{method}: {str(e)}"
                    self.add_debug(f"  ✗ {error_msg}")
                    processed_items['errors'].append(f"Method: {self.current_pou}.{method} - {str(e)}")
                    import traceback
                    self.add_debug(f"  Traceback: {traceback.format_exc()}")

            # Create comprehensive summary with processing results
            summary_output = f"%% Recursive Flowchart Generation Summary\n"
            summary_output += f"%% Main POU: {self.current_pou}\n"
            summary_output += f"%% Total items processed: {len(actions) + len(methods) + 1}\n"
            summary_output += f"%% Successfully generated: {len(processed_items['successful'])}\n"
            summary_output += f"%% No code found: {len(processed_items['no_code'])}\n"
            summary_output += f"%% No language processor: {len(processed_items['no_processor'])}\n"
            summary_output += f"%% Errors: {len(processed_items['errors'])}\n\n"

            # Add detailed breakdown
            if processed_items['successful']:
                summary_output += f"%% === SUCCESSFULLY GENERATED ===\n"
                for item in processed_items['successful']:
                    summary_output += f"%% ✓ {item}\n"
                summary_output += "\n"

            if processed_items['no_processor']:
                summary_output += f"%% === NO LANGUAGE PROCESSOR ===\n"
                summary_output += f"%% These items couldn't be processed due to unsupported language:\n"
                for item in processed_items['no_processor']:
                    summary_output += f"%% ✗ {item}\n"
                summary_output += "\n"

            if processed_items['no_code']:
                summary_output += f"%% === NO CODE FOUND ===\n"
                summary_output += f"%% These items had empty code bodies:\n"
                for item in processed_items['no_code']:
                    summary_output += f"%% ⚠ {item}\n"
                summary_output += "\n"

            if processed_items['errors']:
                summary_output += f"%% === ERRORS ===\n"
                summary_output += f"%% These items encountered errors during processing:\n"
                for item in processed_items['errors']:
                    summary_output += f"%% 💥 {item}\n"
                summary_output += "\n"

            summary_output += f"%% Available flowcharts for export:\n"
            for item_name in sorted(self.all_flowcharts.keys()):
                if item_name == self.current_pou:
                    summary_output += f"%% - {item_name} (Main POU)\n"
                else:
                    summary_output += f"%% - {item_name}\n"

            summary_output += f"\n%% To view individual flowchart, select it from the tree and click 'Generate Mermaid'\n"

            # Display summary in the output window
            self.mermaid_output.delete(1.0, tk.END)
            self.mermaid_output.insert(1.0, summary_output)

            # Save all individual flowcharts to files
            if hasattr(self, 'all_flowcharts') and self.all_flowcharts:
                if self.export_handler.save_recursive_flowcharts(self.all_flowcharts):
                    self.add_debug(f"✓ All recursive flowcharts saved to individual files")

            # Set flag to indicate we're in recursive mode
            self.recursive_mode = True
            self.current_recursive_pou = self.current_pou

            # Add final debug summary
            self.add_debug(f"=== RECURSIVE PROCESSING COMPLETED ===")
            self.add_debug(f"Main POU: {self.current_pou}")
            self.add_debug(f"Total items: {len(actions) + len(methods) + 1}")
            self.add_debug(f"Successful: {len(processed_items['successful'])}")
            self.add_debug(f"No code: {len(processed_items['no_code'])}")
            self.add_debug(f"No processor: {len(processed_items['no_processor'])}")
            self.add_debug(f"Errors: {len(processed_items['errors'])}")

            if processed_items['no_processor']:
                self.add_debug("Items with no language processor:")
                for item in processed_items['no_processor']:
                    self.add_debug(f"  - {item}")

            messagebox.showinfo(
                "Recursive Generation Complete",
                f"Processing completed for {self.current_pou}\n\n"
                f"✓ Successfully generated: {len(processed_items['successful'])}\n"
                f"⚠ No code found: {len(processed_items['no_code'])}\n"
                f"✗ No language processor: {len(processed_items['no_processor'])}\n"
                f"💥 Errors: {len(processed_items['errors'])}\n\n"
                f"Check the output window for detailed breakdown."
            )

        except Exception as e:
            error_msg = f"Failed to generate recursive Mermaid flowchart: {str(e)}"
            self.add_debug(f"ERROR: {error_msg}")
            import traceback
            self.add_debug(f"Traceback: {traceback.format_exc()}")
            messagebox.showerror("Error", error_msg)

    def save_mermaid(self):
        """Save Mermaid code to a file"""
        mermaid_text = self.mermaid_output.get(1.0, tk.END).strip()
        if self.export_handler.save_mermaid(mermaid_text):
            messagebox.showinfo("Success", f"Mermaid code saved to output folder")
        else:
            messagebox.showerror("Error", "Failed to save Mermaid file")

    def save_html(self):
        """Save Mermaid diagram as standalone HTML file"""
        mermaid_text = self.mermaid_output.get(1.0, tk.END).strip()
        if self.export_handler.save_html(mermaid_text):
            # Ask if user wants to open it
            open_browser = messagebox.askyesno(
                "Success",
                "HTML file saved successfully!\n\nWould you like to open it in your browser?"
            )
            if open_browser:
                self.export_handler.open_html_in_browser()
        else:
            messagebox.showerror("Error", "Failed to save HTML file")

    def generate_pdf(self):
        """Generate HTML file with Mermaid diagram for browser PDF printing"""
        mermaid_text = self.mermaid_output.get(1.0, tk.END).strip()
        if self.export_handler.generate_pdf(mermaid_text):
            # Ask if user wants to open it
            open_browser = messagebox.askyesno(
                "HTML File Created",
                "HTML file created successfully!\n\nWould you like to open it in your browser to create PDF?"
            )
            if open_browser:
                self.export_handler.open_html_in_browser()

            messagebox.showinfo(
                "Success",
                "HTML file created!\n\nTo create PDF:\n"
                "1. Open the HTML file in browser\n"
                "2. Press Ctrl+P to print\n"
                "3. Choose 'Save as PDF' as destination\n"
                "4. Adjust margins and layout as needed"
            )
        else:
            messagebox.showerror("Error", "Failed to create HTML file for PDF")

    def copy_to_clipboard(self):
        mermaid_text = self.mermaid_output.get(1.0, tk.END).strip()
        if mermaid_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(mermaid_text)
            messagebox.showinfo("Success", "Mermaid code copied to clipboard")

    def add_debug(self, message):
        """Add message to debug output"""
        self.debug_output.insert(tk.END, message + "\n")
        self.debug_output.see(tk.END)
        print(f"[{self.__class__.__name__}] {message}")

    def refresh_debug(self):
        """Refresh debug information"""
        if self.parser:
            for debug_msg in self.parser.get_debug_info():
                self.add_debug(debug_msg)

    def clear_debug(self):
        """Clear debug output"""
        self.debug_output.delete(1.0, tk.END)

    def show_xml_structure(self):
        """Show XML structure sample"""
        if self.parser:
            structure = self.parser.get_xml_structure_sample()
            self.add_debug("=== XML STRUCTURE SAMPLE ===")
            self.add_debug(structure)
            self.add_debug("=== END XML STRUCTURE SAMPLE ===")

    def get_supported_languages(self):
        """Get supported languages for display"""
        if hasattr(self, 'converter'):
            return self.converter.get_supported_languages()
        return []