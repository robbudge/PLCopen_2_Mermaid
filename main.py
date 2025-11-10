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
        """Scan the PLCopen XML file for POUs"""
        if not self.file_path:
            return

        try:
            self.log_message("INFO", "Scanning PLCopen XML file for POUs...")
            self.update_progress("Loading XML file...", 10)

            self.discovered_pous = []
            self.selected_pous.clear()
            self.pou_name_map = {}

            tree = ET.parse(self.file_path)
            root = tree.getroot()

            self.update_progress("Searching for POUs...", 30)

            ns = {
                'ns': 'http://www.plcopen.org/xml/tc6_0200',
                'xhtml': 'http://www.w3.org/1999/xhtml'
            }

            pou_elements = root.findall('.//ns:pou', ns)
            self.log_message("INFO", f"Found {len(pou_elements)} POU elements")

            for i, pou in enumerate(pou_elements):
                self.update_progress(f"Processing POU {i + 1}/{len(pou_elements)}...",
                                     30 + (i / len(pou_elements)) * 60)
                pou_infos = self.extract_pou_info(pou, ns)  # now returns a list
                for pou_info in pou_infos:
                    self.discovered_pous.append(pou_info)
                    self.pou_name_map[pou_info['name']] = pou_info
                    self.log_message("DEBUG",
                                     f"Extracted {pou_info['type']} {pou_info['name']} ({pou_info['lines']} lines)")

            self.update_progress("Scan complete!", 100)
            self.display_scan_results()
            self.populate_pou_list()

            if self.discovered_pous:
                self.process_btn.config(state=tk.NORMAL)
                self.notebook.select(self.selection_tab)
            else:
                self.log_message("WARNING", "No POUs with executable logic found")

        except Exception as e:
            error_msg = f"Error scanning file: {str(e)}"
            self.log_message("ERROR", error_msg)
            messagebox.showerror("Error", error_msg)

    def extract_pou_info(self, pou_element, ns):
        """Extract complete POU information including actions and methods as separate entries."""
        try:
            name = pou_element.get('name', 'Unknown')
            pou_type = pou_element.get('pouType', 'Unknown')
            self.log_message("DEBUG", f"Processing POU: {name} (Type: {pou_type})")

            pou_entries = []  # List to hold main and internal POUs

            # ===== Main POU =====
            main_st_content = self.extract_st_from_element(pou_element.find('ns:body', ns), ns)
            if main_st_content:
                main_entry = self.build_pou_entry(name, pou_type, main_st_content, ns, parent=None, internal=False)
                pou_entries.append(main_entry)

            # ===== Actions =====
            for action in pou_element.findall('.//ns:action', ns):
                action_name = action.get('name', 'Unknown')
                action_st = self.extract_st_from_element(action, ns)
                if action_st:
                    internal_name = f"{name}.{action_name}"
                    action_entry = self.build_pou_entry(internal_name, 'action', action_st, ns, parent=name,
                                                        internal=True)
                    pou_entries.append(action_entry)

            # ===== Methods =====
            for method in pou_element.findall('.//ns:method', ns):
                method_name = method.get('name', 'Unknown')
                method_st = self.extract_st_from_element(method, ns)
                if method_st:
                    internal_name = f"{name}.{method_name}"
                    method_entry = self.build_pou_entry(internal_name, 'method', method_st, ns, parent=name,
                                                        internal=True)
                    pou_entries.append(method_entry)

            if not pou_entries:
                self.log_message("DEBUG", f"No ST content found for POU: {name}")
                return []

            return pou_entries

        except Exception as e:
            self.log_message("ERROR", f"Error extracting POU {pou_element.get('name', 'Unknown')}: {str(e)}")
            return []

    def build_pou_entry(self, name, pou_type, st_content, ns, parent=None, internal=False):
        """Helper to standardize POU record creation."""
        st_content = self.clean_st_content(st_content)

        # Extract executable part (remove comments and declarations)
        executable_lines = []
        for line in st_content.split('\n'):
            clean_line = line.strip()
            if (clean_line and
                    not clean_line.startswith('//') and
                    not clean_line.upper().startswith(('VAR', 'END_VAR')) and
                    not clean_line.upper().startswith(('PROGRAM', 'FUNCTION_BLOCK', 'FUNCTION'))):
                executable_lines.append(clean_line)

        executable_content = '\n'.join(executable_lines)
        lines = len([l for l in executable_content.split('\n') if l.strip()])
        size = len(executable_content)
        sub_pou_calls = self.extract_sub_pou_calls(executable_content)

        return {
            'name': name,
            'type': pou_type,
            'st_content': st_content,
            'executable_content': executable_content,
            'lines': lines,
            'size': size,
            'sub_pou_calls': sub_pou_calls,
            'is_internal': internal,
            'parent': parent
        }

    def extract_sub_pou_calls(self, st_code: str):
        """
        Detect likely POU calls inside ST code.
        Handles simple calls (MyFunc()), qualified calls (Block.Method()),
        and nested library calls (Lib.SubLib.Func()).
        """
        # Remove comments
        code = re.sub(r'//.*', '', st_code)
        code = re.sub(r'\(\*.*?\*\)', '', code, flags=re.DOTALL)

        # Match patterns like "Something(" but not "IF (", "CASE (", etc.
        pattern = re.compile(
            r'\b(?!IF\b|ELSIF\b|CASE\b|FOR\b|WHILE\b|REPEAT\b|UNTIL\b|EXIT\b|RETURN\b|END_IF\b|END_CASE\b|END_FOR\b)'
            r'([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)\s*\('
        )

        matches = pattern.findall(code)
        # Deduplicate and filter out common built-ins
        ignore_list = {
            'TO_STRING', 'REPLACE_ALL', 'MIN', 'MAX', 'ABS',
            'NOT', 'AND', 'OR', 'XOR', 'MOD', 'TRUE', 'FALSE'
        }

        sub_pous = sorted({m for m in matches if m.upper() not in ignore_list})
        self.log_message("DEBUG", f"Extracted sub-POU calls: {sub_pous}")
        return sub_pous

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

        if not self.discovered_pous:
            self.results_text.insert(tk.END, "No POUs with executable logic found in the file.")
            return

        self.results_text.insert(tk.END, f"Found {len(self.discovered_pous)} POUs with executable logic:\n\n")

        for pou in self.discovered_pous:
            preview = pou['executable_content'][:400] + "..." if len(pou['executable_content']) > 400 else pou[
                'executable_content']
            sub_calls = ", ".join(pou['sub_pou_calls']) if pou['sub_pou_calls'] else "None"
            self.results_text.insert(tk.END,
                                     f"Name: {pou['name']}\n"
                                     f"Type: {pou['type']}\n"
                                     f"Executable Lines: {pou['lines']}, Size: {pou['size']} chars\n"
                                     f"Sub-POU Calls: {sub_calls}\n"
                                     f"Logic Preview:\n{preview}\n"
                                     f"{'-' * 60}\n"
                                     )

    def populate_pou_list(self):
        """Populate the POU selection listbox"""
        self.pou_listbox.delete(0, tk.END)

        for i, pou in enumerate(self.discovered_pous):
            type_abbr = {'program': 'P', 'functionBlock': 'FB', 'function': 'F', 'action': 'A', 'method': 'M'}.get(
                pou['type'].lower(), 'U')
            prefix = "  ↳ " if pou.get('is_internal') else ""
            display_text = f"{prefix}[{type_abbr}] {pou['name']} ({pou['lines']} lines)"
            if pou.get('parent'):
                display_text += f" (of {pou['parent']})"
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
        total_count = len(self.discovered_pous)
        self.selection_info.config(text=f"Selected: {selected_count} of {total_count} POUs")

    def select_all_pous(self):
        """Select all POUs"""
        self.pou_listbox.selection_set(0, tk.END)
        self.selected_pous = set(range(len(self.discovered_pous)))
        self.update_selection_info()

    def select_none_pous(self):
        """Deselect all POUs"""
        self.pou_listbox.selection_clear(0, tk.END)
        self.selected_pous.clear()
        self.update_selection_info()

    def select_programs_only(self):
        """Select only programs"""
        self.select_none_pous()
        for i, pou in enumerate(self.discovered_pous):
            if pou['type'].lower() == 'program':
                self.pou_listbox.selection_set(i)
                self.selected_pous.add(i)
        self.update_selection_info()

    def select_fbs_only(self):
        """Select only function blocks"""
        self.select_none_pous()
        for i, pou in enumerate(self.discovered_pous):
            if pou['type'].lower() == 'functionblock':
                self.pou_listbox.selection_set(i)
                self.selected_pous.add(i)
        self.update_selection_info()

    def st_to_mermaid_nodes(self, st_content, pou_name):
        lines = [ln.strip() for ln in st_content.splitlines() if ln.strip()]
        nodes = []
        for i, line in enumerate(lines):
            node_name = f"{pou_name}_{i}"
            nodes.append(f"{node_name}({line})")
            if i > 0:
                prev = f"{pou_name}_{i - 1}"
                nodes.append(f"{prev} --> {node_name}")
        return nodes

    def filter_pous(self, event=None):
        """Filter POUs based on search text"""
        search_text = self.search_var.get().lower()
        self.pou_listbox.delete(0, tk.END)

        for i, pou in enumerate(self.discovered_pous):
            if (search_text in pou['name'].lower() or
                    search_text in pou['executable_content'].lower()):

                type_abbr = {'program': 'P', 'functionBlock': 'FB', 'function': 'F'}.get(pou['type'].lower(), 'U')
                first_line = pou['executable_content'].split('\n')[0] if pou[
                    'executable_content'] else "No executable content"
                sub_calls_count = len(pou['sub_pou_calls'])
                display_text = f"[{type_abbr}] {pou['name']} ({pou['lines']} lines, {sub_calls_count} sub-calls) - {first_line[:80]}..."
                self.pou_listbox.insert(tk.END, display_text)
                if i in self.selected_pous:
                    self.pou_listbox.selection_set(tk.END)

    def preview_pou(self, event):
        """Preview selected POU"""
        selection = self.pou_listbox.curselection()
        if selection:
            pou_index = selection[0]
            pou = self.discovered_pous[pou_index]

            preview_win = tk.Toplevel(self.root)
            preview_win.title(f"Preview: {pou['name']}")
            preview_win.geometry("800x600")

            header_frame = tk.Frame(preview_win)
            header_frame.pack(fill=tk.X, padx=10, pady=5)

            tk.Label(header_frame, text=f"POU: {pou['name']}", font=("Arial", 12, "bold")).pack(anchor="w")
            tk.Label(header_frame,
                     text=f"Type: {pou['type']} | Executable Lines: {pou['lines']} | Sub-Calls: {len(pou['sub_pou_calls'])}",
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
        """Process selected POUs and generate smart flowcharts"""
        if not self.selected_pous:
            messagebox.showwarning("Warning", "No POUs selected!")
            return

        selected_indices = list(self.selected_pous)
        self.log_message("INFO", f"Processing {len(selected_indices)} selected POUs with full text flowcharts...")

        base_name = os.path.splitext(os.path.basename(self.file_path))[0]
        output_dir = f"{base_name}_full_text_flowcharts"
        os.makedirs(output_dir, exist_ok=True)

        # Track all POUs that need processing (selected + their sub-POUs)
        all_pous_to_process = set()

        # First pass: collect all POUs that need processing
        for pou_index in selected_indices:
            pou = self.discovered_pous[pou_index]
            all_pous_to_process.add(pou['name'])
            self.log_message("DEBUG", f"Selected POU: {pou['name']} with sub-calls: {pou['sub_pou_calls']}")

            # Add all sub-POUs
            for sub_call in pou['sub_pou_calls']:
                sub_pou = self.find_pou_by_name(sub_call)
                if sub_pou:
                    all_pous_to_process.add(sub_pou['name'])
                    self.log_message("DEBUG", f"Added sub-POU for processing: {sub_pou['name']}")
                else:
                    self.log_message("WARNING", f"Sub-POU not found: {sub_call}")

        self.log_message("INFO", f"Total POUs to process: {len(all_pous_to_process)} - {list(all_pous_to_process)}")

        success_count = 0
        # Process all collected POUs
        for pou_name in all_pous_to_process:
            pou = self.find_pou_by_name(pou_name)
            if pou:
                self.log_message("INFO", f"Processing {pou['name']} ({success_count + 1}/{len(all_pous_to_process)})")

                try:
                    mermaid_content = self.generate_full_text_mermaid_flowchart(pou)
                    safe_name = re.sub(r'[^\w\-_\. ]', '_', pou['name'])
                    mermaid_filename = f"{output_dir}/{safe_name}.mmd"
                    self.save_file(mermaid_content, mermaid_filename)
                    self.log_message("SUCCESS", f"Created Full Text Mermaid: {mermaid_filename}")
                    success_count += 1

                except Exception as e:
                    self.log_message("ERROR", f"Failed to process {pou['name']}: {str(e)}")
            else:
                self.log_message("ERROR", f"POU not found for processing: {pou_name}")

        self.log_message("SUCCESS", f"Successfully processed {success_count}/{len(all_pous_to_process)} POUs")
        messagebox.showinfo("Complete", f"Processing complete!\nGenerated {success_count} flowcharts in: {output_dir}")

    def find_pou_by_name(self, pou_name):
        """Find a POU by name, handling various call formats - IMPROVED VERSION"""
        # Direct name match (case insensitive)
        for pou in self.discovered_pous:
            if pou['name'].lower() == pou_name.lower():
                return pou

        # Handle method calls: instance.Method -> look for Method
        if '.' in pou_name:
            method_name = pou_name.split('.')[-1]
            for pou in self.discovered_pous:
                if pou['name'].lower() == method_name.lower():
                    return pou

        # Partial match (contains)
        for pou in self.discovered_pous:
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

    def generate_mermaid_from_pou(self, pou_info, visited=None, depth=0):
        """
        Recursively generate Mermaid flowchart for a POU and its sub-POUs.
        """
        if visited is None:
            visited = set()
        name = pou_info["name"]
        if name in visited:
            return f"%% Skipping recursive call to {name}\n"
        visited.add(name)

        mermaid_lines = [f"%% Flowchart for {name}", "flowchart TD"]

        # Convert this POU’s own logic into Mermaid nodes
        logic_nodes = self.st_to_mermaid_nodes(pou_info["executable_content"], pou_info["name"])
        mermaid_lines.extend(logic_nodes)

        # Handle sub-POU calls
        for call in pou_info.get("sub_pou_calls", []):
            if call in self.pou_name_map:
                sub_pou = self.pou_name_map[call]
                sub_chart = self.generate_mermaid_from_pou(sub_pou, visited, depth + 1)

                # embed as subgraph in the main diagram
                mermaid_lines.append(f"subgraph {call}")
                mermaid_lines.append(sub_chart)
                mermaid_lines.append("end")

                # also export a separate file
                sub_path = os.path.join(self.output_dir, f"{call}.mmd")
                with open(sub_path, "w", encoding="utf-8") as f:
                    f.write(sub_chart)
                self.log_message("INFO", f"Saved sub-POU Mermaid: {sub_path}")

            else:
                mermaid_lines.append(f"%% Unresolved sub-POU call: {call}")

        return "\n".join(mermaid_lines)

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
        for sub_call in current_pou['sub_pou_calls']:
            # More flexible matching - check if sub_call appears in the line
            if sub_call in line and '(' in line:  # Basic call pattern check
                return True
        return False

    def extract_sub_pou_name(self, line):
        """Extract the sub-POU name from a line"""
        # Try to find the best match from the discovered POUs
        for pou in self.discovered_pous:
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