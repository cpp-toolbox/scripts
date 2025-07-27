"""
Improved C++ Compilation Error Parser and HTML Visualizer

This script parses verbose C++ compilation errors and generates a clean,
interactive HTML visualization that makes it easy to understand the error.
Handles complex template instantiation chains and cascading errors better.
"""

import re
import sys
import html
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ErrorLocation:
    file: str
    line: Optional[int] = None
    column: Optional[int] = None
    function: Optional[str] = None


@dataclass
class TemplateInstantiation:
    template_name: str
    location: ErrorLocation
    context: str
    level: int = 0


@dataclass
class CompilationError:
    main_error: str
    location: ErrorLocation
    template_chain: List[TemplateInstantiation] = field(default_factory=list)
    notes: List[Tuple[str, ErrorLocation]] = field(default_factory=list)
    candidates: List[str] = field(default_factory=list)
    error_type: str = "Unknown"
    related_errors: List['CompilationError'] = field(default_factory=list)


class ImprovedCppErrorParser:
    def __init__(self):
        self.template_instantiation_pattern = re.compile(
            r"^(.+?):\s*In instantiation of '(.+?)' \[with (.+?)\]:\s*$"
        )
        self.required_from_pattern = re.compile(
            r"^(.+?):(\d+):(\d+):\s+required from (.+)$"
        )
        self.error_pattern = re.compile(
            r"^(.+?):(\d+):(\d+):\s+error:\s+(.+)$"
        )
        self.note_pattern = re.compile(
            r"^(.+?):(\d+):(\d+):\s+note:\s+(.+)$"
        )
        self.candidate_pattern = re.compile(
            r"^\s*note:\s+candidate.*?:\s+(.+)$"
        )
        self.make_error_pattern = re.compile(
            r"^g?make.*?:\s*\*\*\*.*?Error\s+\d+$"
        )

    def parse_location(self, location_str: str) -> ErrorLocation:
        """Parse a location string like '/path/file.cpp:123:45'"""
        parts = location_str.split(':')
        if len(parts) >= 3:
            try:
                return ErrorLocation(
                    file=parts[0],
                    line=int(parts[1]),
                    column=int(parts[2])
                )
            except ValueError:
                pass
        return ErrorLocation(file=location_str)

    def classify_error_type(self, error_msg: str) -> str:
        """Classify the error type based on the message"""
        error_msg_lower = error_msg.lower()
        
        if "use of deleted function" in error_msg:
            return "Deleted Function"
        elif "no matching function" in error_msg:
            return "No Matching Function"
        elif "no member named" in error_msg:
            return "No Member"
        elif "incomplete type" in error_msg:
            return "Incomplete Type"
        elif "static assertion failed" in error_msg:
            return "Static Assertion Failed"
        elif "template" in error_msg_lower:
            return "Template Error"
        elif "cannot convert" in error_msg:
            return "Type Conversion Error"
        elif "ambiguous" in error_msg:
            return "Ambiguous Reference"
        else:
            return "Compilation Error"

    def parse_error_text(self, error_text: str) -> List[CompilationError]:
        """Parse the full error text into structured error objects"""
        lines = error_text.strip().split('\n')
        errors = []
        current_template_chain = []
        current_notes = []
        current_candidates = []
        pending_error = None
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Skip make error lines
            if self.make_error_pattern.match(line):
                i += 1
                continue
            
            # Skip empty lines unless we're processing an error
            if not line:
                if pending_error:
                    # End of current error block
                    pending_error.template_chain = current_template_chain.copy()
                    pending_error.notes = current_notes.copy()
                    pending_error.candidates = current_candidates.copy()
                    errors.append(pending_error)
                    
                    # Reset for next error
                    pending_error = None
                    current_template_chain = []
                    current_notes = []
                    current_candidates = []
                i += 1
                continue
            
            # Template instantiation start
            template_match = self.template_instantiation_pattern.match(line)
            if template_match:
                location_str, template_name, template_params = template_match.groups()
                location = self.parse_location(location_str)
                current_template_chain.append(TemplateInstantiation(
                    template_name=template_name,
                    location=location,
                    context=template_params,
                    level=len(current_template_chain)
                ))
            
            # Required from line
            elif "required from" in line:
                required_match = self.required_from_pattern.match(line)
                if required_match:
                    file, line_num, col, context = required_match.groups()
                    location = ErrorLocation(file, int(line_num), int(col))
                    current_template_chain.append(TemplateInstantiation(
                        template_name=f"required from {context}",
                        location=location,
                        context="",
                        level=len(current_template_chain)
                    ))
                else:
                    # Handle other "required from" formats
                    location = ErrorLocation(file="unknown")
                    current_template_chain.append(TemplateInstantiation(
                        template_name=line,
                        location=location,
                        context="",
                        level=len(current_template_chain)
                    ))
            
            # Main error line
            elif "error:" in line:
                error_match = self.error_pattern.match(line)
                if error_match:
                    file, line_num, col, error_msg = error_match.groups()
                    location = ErrorLocation(file, int(line_num), int(col))
                    
                    # If we have a pending error, save it first
                    if pending_error:
                        pending_error.template_chain = current_template_chain.copy()
                        pending_error.notes = current_notes.copy()
                        pending_error.candidates = current_candidates.copy()
                        errors.append(pending_error)
                        current_notes = []
                        current_candidates = []
                    
                    # Create new error
                    pending_error = CompilationError(
                        main_error=error_msg,
                        location=location,
                        error_type=self.classify_error_type(error_msg)
                    )
            
            # Note lines
            elif "note:" in line:
                note_match = self.note_pattern.match(line)
                if note_match:
                    file, line_num, col, note_msg = note_match.groups()
                    location = ErrorLocation(file, int(line_num), int(col))
                    current_notes.append((note_msg, location))
                    
                    # Check if it's a candidate
                    if "candidate" in note_msg:
                        current_candidates.append(note_msg)
                else:
                    # Handle note lines that don't match the pattern
                    candidate_match = self.candidate_pattern.match(line)
                    if candidate_match:
                        current_candidates.append(candidate_match.group(1))
                    else:
                        # Generic note
                        location = ErrorLocation(file="unknown")
                        current_notes.append((line, location))
            
            i += 1
        
        # Don't forget the last error if file doesn't end with blank line
        if pending_error:
            pending_error.template_chain = current_template_chain.copy()
            pending_error.notes = current_notes.copy()
            pending_error.candidates = current_candidates.copy()
            errors.append(pending_error)
        
        return errors

    def generate_html(self, errors: List[CompilationError]) -> str:
        """Generate HTML visualization of the errors"""
        html_content = self._get_html_template()
        
        # Calculate statistics
        error_count = len(errors)
        template_errors = len([e for e in errors if e.template_chain])
        avg_chain_length = sum(len(e.template_chain) for e in errors) / len(errors) if errors else 0
        
        # Generate error cards
        error_cards = []
        for i, error in enumerate(errors):
            error_cards.append(self._generate_error_card(error, i))
        
        return html_content.format(
            error_count=error_count,
            template_errors=template_errors,
            avg_chain_length=avg_chain_length,
            error_cards=''.join(error_cards)
        )

    def _generate_error_card(self, error: CompilationError, index: int) -> str:
        """Generate HTML for a single error card"""
        # Template chain HTML
        template_chain_html = ""
        if error.template_chain:
            template_items = []
            for i, template in enumerate(error.template_chain):
                indent_style = f"margin-left: {template.level * 20}px;"
                template_items.append(f"""
                <div class="template-item" style="{indent_style}">
                    <div class="template-name">{html.escape(template.template_name)}</div>
                    <div class="template-location">{html.escape(template.location.file)}:{template.location.line or '?'}:{template.location.column or '?'}</div>
                    {f'<div class="template-context">{html.escape(template.context)}</div>' if template.context else ''}
                </div>
                """)
            
            template_chain_html = f"""
            <div class="template-chain">
                <h3 class="collapsible">Template Instantiation Chain ({len(error.template_chain)} levels)</h3>
                <div class="collapsible-content">
                    {''.join(template_items)}
                </div>
            </div>
            """
        
        # Notes HTML
        notes_html = ""
        if error.notes:
            note_items = []
            for note_msg, location in error.notes:
                if "candidate" not in note_msg.lower():  # Don't duplicate candidates
                    note_items.append(f"""
                    <div class="note-item">
                        <div class="note-message">{html.escape(note_msg)}</div>
                        <div class="note-location">{html.escape(location.file)}:{location.line or '?'}:{location.column or '?'}</div>
                    </div>
                    """)
            
            if note_items:
                notes_html = f"""
                <div class="notes">
                    <h3>Additional Notes ({len(note_items)})</h3>
                    {''.join(note_items)}
                </div>
                """
        
        # Candidates HTML
        candidates_html = ""
        if error.candidates:
            candidate_items = []
            for candidate in error.candidates:
                candidate_items.append(f'<div class="candidate">{html.escape(candidate)}</div>')
            
            candidates_html = f"""
            <div class="candidates">
                <h3>Available Candidates ({len(error.candidates)})</h3>
                {''.join(candidate_items)}
            </div>
            """
        
        return f"""
        <div class="error-card">
            <div class="error-header">
                <div class="error-type">{error.error_type}</div>
                <div class="error-message">{html.escape(error.main_error)}</div>
                <div class="error-location">📁 {html.escape(error.location.file)}:{error.location.line or '?'}:{error.location.column or '?'}</div>
            </div>
            <div class="error-body">
                {template_chain_html}
                {notes_html}
                {candidates_html}
            </div>
        </div>
        """

    def _get_html_template(self):
        """Get the HTML template"""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>C++ Compilation Errors</title>
    <style>
        body {{
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
            margin: 20px;
            line-height: 1.4;
            background-color: #0d1117;
            color: #e6edf3;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .error-card {{
            border: 1px solid #30363d;
            margin-bottom: 25px;
            padding: 0;
            background-color: #161b22;
            border-radius: 8px;
            overflow: hidden;
        }}
        .error-header {{
            background: linear-gradient(90deg, #21262d, #2d333b);
            padding: 15px;
            border-bottom: 1px solid #30363d;
        }}
        .error-type {{
            font-weight: bold;
            color: #f85149;
            font-size: 0.9em;
            text-transform: uppercase;
            margin-bottom: 8px;
        }}
        .error-message {{
            margin: 8px 0;
            font-weight: bold;
            color: #ff7b72;
            font-size: 1.1em;
            line-height: 1.3;
        }}
        .error-location {{
            color: #8b949e;
            font-size: 0.9em;
            font-family: monospace;
        }}
        .error-body {{
            padding: 20px;
        }}
        .template-chain {{
            margin: 20px 0;
        }}
        .template-item {{
            border-left: 3px solid #1f6feb;
            padding: 12px;
            margin: 8px 0;
            padding-left: 16px;
            background: #0d1117;
            border-radius: 0 6px 6px 0;
            transition: background-color 0.2s;
        }}
        .template-item:hover {{
            background: #161b22;
        }}
        .template-name {{
            font-weight: bold;
            color: #58a6ff;
            margin-bottom: 4px;
        }}
        .template-location {{
            color: #8b949e;
            font-size: 0.85em;
            font-family: monospace;
            margin-bottom: 4px;
        }}
        .template-context {{
            color: #c9d1d9;
            word-break: break-all;
            margin-top: 6px;
            font-size: 0.9em;
            padding: 8px;
            background: #21262d;
            border-radius: 4px;
        }}
        .notes {{
            margin: 20px 0;
        }}
        .note-item {{
            background: #1c2128;
            border: 1px solid #373e47;
            padding: 12px;
            margin: 8px 0;
            border-radius: 6px;
        }}
        .note-message {{
            color: #e6edf3;
            margin-bottom: 4px;
        }}
        .note-location {{
            color: #8b949e;
            font-size: 0.85em;
            font-family: monospace;
        }}
        .candidates {{
            margin-top: 20px;
        }}
        .candidate {{
            background: #2d2107;
            border: 1px solid #9e6a03;
            padding: 12px;
            margin: 8px 0;
            color: #f2cc60;
            border-radius: 6px;
            font-family: monospace;
            word-break: break-all;
        }}
        .summary {{
            background: linear-gradient(135deg, #2d333b, #373e47);
            padding: 20px;
            margin-bottom: 25px;
            border: 1px solid #30363d;
            border-radius: 8px;
        }}
        .collapsible {{
            cursor: pointer;
            user-select: none;
            color: #58a6ff;
            transition: color 0.2s;
        }}
        .collapsible:hover {{
            color: #79c0ff;
        }}
        .collapsible:after {{
            content: ' [click to toggle]';
            color: #8b949e;
            font-size: 0.8em;
        }}
        .collapsible-content.collapsed {{
            display: none;
        }}
        h1, h2, h3 {{
            margin: 15px 0 10px 0;
            color: #e6edf3;
        }}
        h1 {{
            color: #58a6ff;
            border-bottom: 2px solid #21262d;
            padding-bottom: 10px;
        }}
        h3 {{
            color: #79c0ff;
            font-size: 1.1em;
        }}
        
        /* Scrollbar styling */
        ::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        ::-webkit-scrollbar-track {{
            background: #161b22;
        }}
        ::-webkit-scrollbar-thumb {{
            background: #30363d;
            border-radius: 4px;
        }}
        ::-webkit-scrollbar-thumb:hover {{
            background: #484f58;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🛠️ C++ Compilation Error Analysis</h1>
        
        <div class="summary">
            <h2>📊 Summary</h2>
            <p><strong>Total Errors:</strong> {error_count} | <strong>Template-Related:</strong> {template_errors} | <strong>Average Template Chain Length:</strong> {avg_chain_length:.1f}</p>
        </div>
        
        {error_cards}
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            // Handle collapsible sections
            const collapsibles = document.querySelectorAll('.collapsible');
            collapsibles.forEach(function(collapsible) {{
                collapsible.addEventListener('click', function() {{
                    const content = this.nextElementSibling;
                    content.classList.toggle('collapsed');
                }});
            }});
            
            // Auto-collapse long template chains (>3 items)
            const templateChains = document.querySelectorAll('.template-chain');
            templateChains.forEach(function(chain) {{
                const items = chain.querySelectorAll('.template-item');
                if (items.length > 3) {{
                    const header = chain.querySelector('h3');
                    const content = chain.querySelector('.collapsible-content');
                    if (header && content) {{
                        content.classList.add('collapsed');
                    }}
                }}
            }});
        }});
    </script>
</body>
</html>'''


def main():
    parser = ImprovedCppErrorParser()
    
    if len(sys.argv) > 1:
        # Read from file
        input_file = Path(sys.argv[1])
        if not input_file.exists():
            print(f"Error: File {input_file} not found")
            return 1
        
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            error_text = f.read()
        
        output_file = input_file.with_suffix('.html')
    else:
        # Read from stdin
        error_text = sys.stdin.read()
        output_file = Path('cpp_errors.html')
    
    try:
        errors = parser.parse_error_text(error_text)
        
        if not errors:
            print("No compilation errors found in the input")
            return 1
        
        html_output = parser.generate_html(errors)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_output)
        
        print(f"Generated HTML report: {output_file}")
        print(f"Found {len(errors)} compilation errors")
        
        # Print summary of errors found
        for i, error in enumerate(errors):
            print(f"  Error {i+1}: {error.error_type} - {error.main_error[:60]}...")
        
        return 0
        
    except Exception as e:
        print(f"Error processing compilation output: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
