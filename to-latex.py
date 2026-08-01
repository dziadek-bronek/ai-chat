#!/usr/bin/env python3
import json
import sys
from typing import List, Dict

class GeminiJsonToLatex:
    def __init__(self):
        # Słownik mapowania podstawowych znaków specjalnych LaTeX
        self.latex_escapes = {
            '_': r'\_',
            '#': r'\#',
            '$': r'\$',
            '%': r'\%',
            '&': r'\&',
            '{': r'\{',
            '}': r'\}',
            '^': r'\textasciicircum{}',
            '~': r'\textasciitilde{}',
        }

    def _escape_line(self, line: str) -> str:
        """Ucieka znaki specjalne w pojedynczej linii tekstu."""
        # Najpierw backslash, aby uniknąć uciekania wielokrotnego
        escaped = line.replace('\\', r'\textbackslash{}')
        for char, replacement in self.latex_escapes.items():
            escaped = escaped.replace(char, replacement)
        return escaped

    def process_text_field(self, raw_text: str) -> str:
        """Przetwarza pole tekstowe wiadomości, obsługując bloki kodu (maszyna stanów)."""
        lines = raw_text.split('\n')
        processed_lines = []
        in_code_block = False

        for line in lines:
            # Sprawdzenie znaczników bloków kodu Markdown (np. ```json)
            if line.strip().startswith('```'):
                if not in_code_block:
                    in_code_block = True
                    processed_lines.append(r'\begin{verbatim}')
                else:
                    in_code_block = False
                    processed_lines.append(r'\end{verbatim}')
                continue

            if in_code_block:
                # Wewnątrz bloku kodu dodajemy linię w stanie surowym
                processed_lines.append(line)
            else:
                # W zwykłym tekście uciekamy znaki specjalne
                processed_lines.append(self._escape_line(line))

        return '\n'.join(processed_lines)









    def generate_latex_document(self, conversation: List[Dict[str, str]]) -> str:
        """Generuje pełną strukturę dokumentu LaTeX z poprawną preambułą."""
        preamble = (
            "\\documentclass[10pt,a4paper]{article}\n\n"
            "% 1. Kodowanie i języki\n"
            "\\usepackage[T1]{fontenc}\n"
            "\\usepackage[utf8]{inputenc}\n"
            "\\usepackage[polish]{babel}\n\n"
            "% 2. Font o stałej szerokości (Monospaced) dla CAŁEGO dokumentu\n"
            "\\usepackage{inconsolata}\n"
            "\\renewcommand{\\familydefault}{\\ttdefault}\n\n"
            "% 3. Marginesy - maksymalne upakowanie tekstu (0.5 cala)\n"
            "\\usepackage[margin=0.5in]{geometry}\n\n"
            "% 4. Interlinia i formatowanie akapitów\n"
            "\\linespread{0.9}\n"
            "\\setlength{\\parindent}{0pt}\n"
            "\\setlength{\\parskip}{4pt}\n\n"
            "% 5. Kolory do wizualnego rozróżnienia ról\n"
            "\\usepackage{xcolor}\n"
            "\\definecolor{rulecolor}{gray}{0.7}\n\n"
            "% 6. Proste makra do oznaczania nadawcy (poprawione definicje)\n"
            "\\newcommand{\\UserTurn}{\\textbf{[USER]}\\par\\medskip}\n"
            "\\newcommand{\\ModelTurn}{\\textbf{[GEMINI]}\\par\\medskip}\n"
            "\\newcommand{\\Separator}{\\par\\vspace{4pt}\\noindent{\\color{rulecolor}\\rule{\\linewidth}{0.4pt}}\\par\\vspace{6pt}}\n\n"
            "\\begin{document}\n"
        )

        body_elements = []
        for message in conversation:
            role = message.get("role", "user")
            text_raw = message.get("text", "")

            processed_text = self.process_text_field(text_raw)

            if role == "user":
                turn_header = "\\UserTurn\n"
            else:
                turn_header = "\\ModelTurn\n"

            body_elements.append(f"{turn_header}{processed_text}\n\\Separator\n")

        footer = "\\end{document}\n"

        return preamble + "".join(body_elements) + footer





























    def convert_file(self, input_json_path: str, output_tex_path: str):
        """Główna metoda ładująca plik i zapisująca wynik."""
        try:
            with open(input_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            latex_code = self.generate_latex_document(data)
            
            with open(output_tex_path, 'w', encoding='utf-8') as f:
                f.write(latex_code)
                
            print(f"[OK] Pomyślnie wygenerowano plik: {output_tex_path}")
        except Exception as e:
            print(f"[BŁĄD] Wystąpił problem podczas konwersji: {e}", file=sys.stderr)
















if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Użycie: python3 script.py <plik_wejsciowy.json> <plik_wyjsciowy.tex>")
        sys.exit(1)
        
    parser = GeminiJsonToLatex()
    parser.convert_file(sys.argv[1], sys.argv[2])













