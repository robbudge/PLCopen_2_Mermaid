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


class CodesysToMermaidGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Codesys XML to Mermaid Converter - Debug Version")
        self.root.geometry("1200x800")

        self.parser = None
        self.current_pou = None
        self.output_folder = None

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
        ttk.Button(button_frame, text="Save Mermaid",
                   command=self.save_mermaid).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="Save HTML",
                   command=self.save_html).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="Generate PDF",
                   command=self.generate_pdf).grid(row=0, column=3, padx=5)

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
            self.add_debug_message(f"Selected file: {filename}")

    def browse_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder_var.set(folder)
            self.output_folder = folder
            self.add_debug_message(f"Output folder set to: {folder}")

    def use_current_folder(self):
        """Use the current XML file's folder as output folder"""
        if self.file_path.get():
            folder = os.path.dirname(self.file_path.get())
            self.output_folder_var.set(folder)
            self.output_folder = folder
            self.add_debug_message(f"Output folder set to XML folder: {folder}")

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

            # Set default output folder to XML file's folder
            if not self.output_folder:
                self.use_current_folder()

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

    def save_mermaid(self):
        """Save Mermaid code to a file"""
        if not self.current_pou:
            messagebox.showerror("Error", "Please generate Mermaid code first")
            return

        if not self.output_folder:
            messagebox.showerror("Error", "Please select an output folder first")
            return

        mermaid_text = self.mermaid_output.get(1.0, tk.END).strip()
        if not mermaid_text:
            messagebox.showerror("Error", "No Mermaid code to save")
            return

        try:
            filename = f"{self.current_pou}.mmd"
            filepath = os.path.join(self.output_folder, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(mermaid_text)

            self.add_debug_message(f"Mermaid code saved to: {filepath}")
            messagebox.showinfo("Success", f"Mermaid code saved to:\n{filepath}")

        except Exception as e:
            error_msg = f"Failed to save Mermaid file: {str(e)}"
            self.add_debug_message(f"ERROR: {error_msg}")
            messagebox.showerror("Error", error_msg)

    def save_html(self):
        """Save Mermaid diagram as standalone HTML file"""
        if not self.current_pou:
            messagebox.showerror("Error", "Please generate Mermaid code first")
            return

        if not self.output_folder:
            messagebox.showerror("Error", "Please select an output folder first")
            return

        mermaid_text = self.mermaid_output.get(1.0, tk.END).strip()
        if not mermaid_text:
            messagebox.showerror("Error", "No Mermaid code to save")
            return

        try:
            html_filename = f"{self.current_pou}_flowchart.html"
            html_path = os.path.join(self.output_folder, html_filename)

            html_content = self._create_mermaid_html(mermaid_text, self.current_pou)

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            self.add_debug_message(f"HTML file saved: {html_path}")

            # Ask if user wants to open it
            open_browser = messagebox.askyesno(
                "Success",
                f"HTML file saved:\n{html_path}\n\nWould you like to open it in your browser?"
            )

            if open_browser:
                webbrowser.open(f"file://{html_path}")

        except Exception as e:
            error_msg = f"Failed to save HTML file: {str(e)}"
            self.add_debug_message(f"ERROR: {error_msg}")
            messagebox.showerror("Error", error_msg)

    def generate_pdf(self):
        """Generate HTML file with Mermaid diagram for browser PDF printing"""
        if not self.current_pou:
            messagebox.showerror("Error", "Please generate Mermaid code first")
            return

        if not self.output_folder:
            messagebox.showerror("Error", "Please select an output folder first")
            return

        mermaid_text = self.mermaid_output.get(1.0, tk.END).strip()
        if not mermaid_text:
            messagebox.showerror("Error", "No Mermaid code to convert to PDF")
            return

        try:
            # Create HTML file with Mermaid diagram
            html_filename = f"{self.current_pou}_flowchart.html"
            html_path = os.path.join(self.output_folder, html_filename)

            # Create the HTML content
            html_content = self._create_mermaid_html(mermaid_text, self.current_pou)

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            self.add_debug_message(f"HTML file created: {html_path}")

            # Ask user if they want to open the file
            open_browser = messagebox.askyesno(
                "HTML File Created",
                f"HTML file created successfully:\n{html_path}\n\n"
                "Would you like to open it in your browser?\n\n"
                "In the browser, you can:\n"
                "1. Use Ctrl+P to print\n"
                "2. Choose 'Save as PDF' as the destination\n"
                "3. Adjust layout as needed"
            )

            if open_browser:
                webbrowser.open(f"file://{html_path}")

            messagebox.showinfo(
                "Success",
                f"HTML file created:\n{html_path}\n\n"
                "To create PDF:\n"
                "1. Open the HTML file in browser\n"
                "2. Press Ctrl+P to print\n"
                "3. Choose 'Save as PDF' as destination\n"
                "4. Adjust margins and layout as needed"
            )

        except Exception as e:
            error_msg = f"Failed to create HTML file: {str(e)}"
            self.add_debug_message(f"ERROR: {error_msg}")
            messagebox.showerror("Error", error_msg)

    def _create_mermaid_html(self, mermaid_code: str, pou_name: str) -> str:
        """Create HTML file with Mermaid diagram"""
        html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Flowchart - {pou_name}</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: white;
        }}
        .header {{
            text-align: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #333;
        }}
        .header h1 {{
            color: #333;
            margin: 0;
        }}
        .header .subtitle {{
            color: #666;
            font-size: 14px;
        }}
        .mermaid {{
            text-align: center;
            background-color: white;
            padding: 20px;
            border: 1px solid #ddd;
            border-radius: 5px;
        }}
        .instructions {{
            margin-top: 20px;
            padding: 15px;
            background-color: #f5f5f5;
            border-left: 4px solid #007acc;
            font-size: 14px;
        }}
        @media print {{
            .instructions {{
                display: none;
            }}
            body {{
                margin: 0;
                padding: 0;
            }}
            .mermaid {{
                border: none;
                padding: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{pou_name} - Flowchart</h1>
        <div class="subtitle">Generated from Codesys XML</div>
    </div>

    <div class="mermaid">
{mermaid_code}
    </div>

    <div class="instructions">
        <strong>How to save as PDF:</strong>
        <ol>
            <li>Press <kbd>Ctrl+P</kbd> (or <kbd>Cmd+P</kbd> on Mac)</li>
            <li>Choose "Save as PDF" as destination</li>
            <li>Adjust margins and layout settings if needed</li>
            <li>Click "Save"</li>
        </ol>
        <p><em>This instruction box will not appear in the printed PDF.</em></p>
    </div>

    <script>
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            flowchart: {{
                useMaxWidth: false,
                htmlLabels: true,
                curve: 'basis'
            }},
            securityLevel: 'loose'
        }});
    </script>
</body>
</html>"""

        return html_template.format(pou_name=pou_name, mermaid_code=mermaid_code)

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