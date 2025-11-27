import os
import webbrowser
from pathlib import Path
import datetime


class GUIExport:
    """Handles export operations for Mermaid flowcharts"""

    def __init__(self, gui_instance):
        self.gui = gui_instance

    def save_mermaid(self, mermaid_text: str, filename: str = None) -> bool:
        """Save Mermaid code to a file - AUTOMATICALLY CALLED"""
        if not self.gui.output_folder:
            self.gui.add_debug("ERROR: No output folder selected")
            return False

        if not mermaid_text:
            self.gui.add_debug("ERROR: No Mermaid code to save")
            return False

        try:
            if not filename:
                # Use current POU name if no filename provided
                if self.gui.current_pou:
                    filename = f"{self.gui.current_pou}.mmd"
                else:
                    self.gui.add_debug("ERROR: No POU selected and no filename provided")
                    return False

            filepath = os.path.join(self.gui.output_folder, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(mermaid_text)

            self.gui.add_debug(f"Mermaid code saved to: {filepath}")
            return True

        except Exception as e:
            error_msg = f"Failed to save Mermaid file: {str(e)}"
            self.gui.add_debug(f"ERROR: {error_msg}")
            return False

    def save_html(self, mermaid_text: str, filename: str = None) -> bool:
        """Save Mermaid diagram as standalone HTML file - AUTOMATICALLY CALLED"""
        if not self.gui.output_folder:
            self.gui.add_debug("ERROR: No output folder selected")
            return False

        if not mermaid_text:
            self.gui.add_debug("ERROR: No Mermaid code to save")
            return False

        try:
            if not filename:
                # Use current POU name if no filename provided
                if self.gui.current_pou:
                    filename = f"{self.gui.current_pou}_flowchart.html"
                else:
                    self.gui.add_debug("ERROR: No POU selected and no filename provided")
                    return False

            html_path = os.path.join(self.gui.output_folder, filename)

            # Get the actual item name for the title
            if hasattr(self.gui, 'selected_item_type'):
                if self.gui.selected_item_type == "POU":
                    item_name = self.gui.current_pou
                elif self.gui.selected_item_type == "Action":
                    item_name = f"{self.gui.current_pou}.{self.gui.current_action}"
                elif self.gui.selected_item_type == "Method":
                    item_name = f"{self.gui.current_pou}.{self.gui.current_method}"
                else:
                    item_name = self.gui.current_pou if self.gui.current_pou else "Flowchart"
            else:
                item_name = self.gui.current_pou if self.gui.current_pou else "Flowchart"

            html_content = self._create_mermaid_html(mermaid_text, item_name)

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            self.gui.add_debug(f"HTML file saved: {html_path}")
            return True

        except Exception as e:
            error_msg = f"Failed to save HTML file: {str(e)}"
            self.gui.add_debug(f"ERROR: {error_msg}")
            return False

    def save_cfc2st(self, st_code: str, filename: str = None) -> bool:
        """Save CFC to ST conversion file - AUTOMATICALLY CALLED for CFC content"""
        if not self.gui.output_folder:
            self.gui.add_debug("ERROR: No output folder selected")
            return False

        if not st_code:
            self.gui.add_debug("ERROR: No ST code to save")
            return False

        try:
            if not filename:
                # Use current POU name if no filename provided
                if self.gui.current_pou:
                    filename = f"{self.gui.current_pou}.cfc2st"
                else:
                    self.gui.add_debug("ERROR: No POU selected and no filename provided")
                    return False

            filepath = os.path.join(self.gui.output_folder, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(st_code)

            self.gui.add_debug(f"CFC to ST file saved: {filepath}")
            return True

        except Exception as e:
            error_msg = f"Failed to save CFC to ST file: {str(e)}"
            self.gui.add_debug(f"ERROR: {error_msg}")
            return False

    def generate_pdf(self, mermaid_text: str, filename: str = None) -> bool:
        """Generate HTML file with Mermaid diagram for browser PDF printing"""
        if not self.gui.output_folder:
            self.gui.add_debug("ERROR: No output folder selected")
            return False

        if not mermaid_text:
            self.gui.add_debug("ERROR: No Mermaid code to convert to PDF")
            return False

        try:
            if not filename:
                filename = f"{self.gui.current_pou}_flowchart.html"
            html_path = os.path.join(self.gui.output_folder, filename)

            html_content = self._create_mermaid_html(mermaid_text, self.gui.current_pou)

            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            self.gui.add_debug(f"HTML file created: {html_path}")
            return True

        except Exception as e:
            error_msg = f"Failed to create HTML file: {str(e)}"
            self.gui.add_debug(f"ERROR: {error_msg}")
            return False

    def open_html_in_browser(self, filename: str = None) -> bool:
        """Open HTML file in browser"""
        if not self.gui.current_pou or not self.gui.output_folder:
            return False

        try:
            if not filename:
                filename = f"{self.gui.current_pou}_flowchart.html"
            html_path = os.path.join(self.gui.output_folder, filename)

            if os.path.exists(html_path):
                webbrowser.open(f"file://{html_path}")
                return True
            else:
                self.gui.add_debug(f"ERROR: HTML file not found: {html_path}")
                return False

        except Exception as e:
            self.gui.add_debug(f"ERROR: Failed to open HTML in browser: {str(e)}")
            return False

    def save_recursive_flowcharts(self, all_flowcharts: dict) -> bool:
        """Save all flowcharts from recursive processing to individual files"""
        if not self.gui.output_folder:
            self.gui.add_debug("ERROR: No output folder selected for recursive export")
            return False

        try:
            saved_count = 0
            for item_name, flowchart in all_flowcharts.items():
                # Create safe filename
                safe_name = self._sanitize_filename(item_name)

                # Save individual flowchart
                if self.save_mermaid(flowchart, f"{safe_name}.mmd"):
                    saved_count += 1

                # Save individual HTML
                if self.save_html(flowchart, f"{safe_name}_flowchart.html"):
                    saved_count += 1

            self.gui.add_debug(f"Recursive export: Saved {saved_count} files for {len(all_flowcharts)} flowcharts")
            return True

        except Exception as e:
            error_msg = f"Failed to save recursive flowcharts: {str(e)}"
            self.gui.add_debug(f"ERROR: {error_msg}")
            return False

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

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename by removing invalid characters"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename