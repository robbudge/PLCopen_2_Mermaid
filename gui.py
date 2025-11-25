import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import xml.etree.ElementTree as ET
import os
from xml_parser import CodesysXMLParser
from mermaid_converter import MermaidConverter


class CodesysToMermaidGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Codesys XML to Mermaid Converter - Debug Version")
        self.root.geometry("1200x800")

        self.parser = None
        self.current_pou = None

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

        # Project tree and POU selection
        tree_frame = ttk.LabelFrame(main_frame, text="Project Structure", padding="5")
        tree_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5, padx=(0, 5))

        self.tree_view = ttk.Treeview(tree_frame)
        self.tree_view.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree_view.yview)
        tree_scroll.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tree_view.configure(yscrollcommand=tree_scroll.set)

        # Bind tree selection
        self.tree_view.bind('<<TreeviewSelect>>', self.on_tree_select)

        # POU details and conversion
        details_frame = ttk.LabelFrame(main_frame, text="POU Details & Conversion", padding="5")
        details_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

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

        # Convert button
        ttk.Button(details_frame, text="Generate Mermaid Flowchart",
                   command=self.generate_mermaid).grid(row=1, column=0, pady=10)

        # Mermaid output
        output_frame = ttk.LabelFrame(main_frame, text="Mermaid Flowchart", padding="5")
        output_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

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
        main_frame.rowconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
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
            self.add_debug_message(f"Selected file: {filename}")

    def load_xml(self):
        if not self.file_path.get():
            messagebox.showerror("Error", "Please select an XML file first")
            return

        try:
            self.add_debug_message("=" * 50)
            self.add_debug_message("STARTING XML LOAD")
            self.add_debug_message(f"File: {self.file_path.get()}")

            self.parser = CodesysXMLParser(self.file_path.get())

            # Add parser debug info to our debug output
            for debug_msg in self.parser.get_debug_info():
                self.add_debug_message(debug_msg)

            self.populate_tree()
            self.add_debug_message("XML loading completed successfully")

            messagebox.showinfo("Success", "XML file loaded successfully")

        except Exception as e:
            error_msg = f"Failed to load XML file: {str(e)}"
            self.add_debug_message(f"ERROR: {error_msg}")
            messagebox.showerror("Error", error_msg)

    def populate_tree(self):
        self.tree_view.delete(*self.tree_view.get_children())

        if not self.parser:
            self.add_debug_message("No parser available for populating tree")
            return

        pous = self.parser.get_pous()
        self.add_debug_message(f"Populating tree with {len(pous)} POUs")

        # Add POUs
        pou_parent = self.tree_view.insert("", "end", text="POUs", open=True)
        for pou_name, pou_data in pous.items():
            pou_id = self.tree_view.insert(pou_parent, "end", text=pou_name,
                                           values=("POU", pou_name, pou_data.get('pouType', 'unknown')))
            self.add_debug_message(f"Added POU to tree: {pou_name}")

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

        if item_values and item_values[0] == "POU":
            pou_name = item_values[1]
            self.current_pou = pou_name
            self.selected_pou_label.config(text=pou_name)

            # Get POU details
            pou_data = self.parser.get_pous().get(pou_name, {})
            language = pou_data.get('language', 'Unknown')
            pou_type = pou_data.get('pouType', 'Unknown')

            self.language_label.config(text=language)
            self.pou_type_label.config(text=pou_type)

            self.add_debug_message(f"Selected POU: {pou_name} (Language: {language}, Type: {pou_type})")

    def generate_mermaid(self):
        if not self.current_pou or not self.parser:
            messagebox.showerror("Error", "Please select a POU first")
            return

        try:
            self.add_debug_message(f"Generating Mermaid for POU: {self.current_pou}")

            converter = MermaidConverter()
            mermaid_code = converter.convert_pou_to_mermaid(self.parser, self.current_pou)

            self.mermaid_output.delete(1.0, tk.END)
            self.mermaid_output.insert(1.0, mermaid_code)

            self.add_debug_message("Mermaid generation completed")

        except Exception as e:
            error_msg = f"Failed to generate Mermaid flowchart: {str(e)}"
            self.add_debug_message(f"ERROR: {error_msg}")
            messagebox.showerror("Error", error_msg)

    def copy_to_clipboard(self):
        mermaid_text = self.mermaid_output.get(1.0, tk.END).strip()
        if mermaid_text:
            self.root.clipboard_clear()
            self.root.clipboard_append(mermaid_text)
            messagebox.showinfo("Success", "Mermaid code copied to clipboard")

    def add_debug_message(self, message):
        """Add message to debug output"""
        self.debug_output.insert(tk.END, message + "\n")
        self.debug_output.see(tk.END)

    def refresh_debug(self):
        """Refresh debug information"""
        if self.parser:
            for debug_msg in self.parser.get_debug_info():
                self.add_debug_message(debug_msg)

    def clear_debug(self):
        """Clear debug output"""
        self.debug_output.delete(1.0, tk.END)

    def show_xml_structure(self):
        """Show XML structure sample"""
        if self.parser:
            structure = self.parser.get_xml_structure_sample()
            self.add_debug_message("=== XML STRUCTURE SAMPLE ===")
            self.add_debug_message(structure)
            self.add_debug_message("=== END XML STRUCTURE SAMPLE ===")

    def get_supported_languages(self):
        """Get supported languages for display"""
        if hasattr(self, 'converter'):
            return self.converter.get_supported_languages()
        return []