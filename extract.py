import re
import os

# Słownik z jednoznacznymi skrótami (Q = potas, P = sympramol)
DICTIONARY = {
    "L": "sympramol",
    "J": "obudzenie",
    "W": "wstanie",
    "S": "sól 2g w 300g wody",
    "M": "cytrynian magnezu 1.5g w 50g wody",
    "P": "cytrynian potasu 1.5g w 50g wody",
    "N": "żel z ugotowanego siemienia lnianego",
    "F": "kawa i 20g śmietanki 36%",
    "Z": "zakwas buraczany",
    "R": "kreatyna",
    "G": "omega3",
    "K": "witamina K",
    "D": "witamina D",
    "C": "witamina C",
    "Q": "witamina B",
    "T": "olej mct c8",
    "X": "deprexolet - mianseryna 10mg",
    "H": "melatonina",
    "V": "cwiczenia na drabince - podciagniecia i dipy",
    "B": "cynk selen kompleks witamin B"
}

def decompress_diary_from_file(file_path):
    if not os.path.exists(file_path):
        print(f"Błąd: Nie znaleziono pliku '{file_path}'!")
        return

    output_lines = []

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            stripped = line.strip()

            # 1. Puste linie zachowujemy bez zmian
            if not stripped:
                output_lines.append("")
                continue

            # 2. Linie bez formatu godziny (komentarze, dni) przepisujemy dosłownie
            if not re.search(r'\(\d{2,4}\)', stripped):
                output_lines.append(stripped)
                continue

            # 3. Wyciąganie poszczególnych chunków z danej linii
            chunks = re.findall(r'[^;]+?\s*\(\s*\d{2,4}\s*\)\s*;', stripped)

            for chunk in chunks:
                match = re.match(r"([^;]+?)\s*\(\s*(\d{2,4})\s*\)\s*;", chunk.strip())
                if match:
                    body, time = match.groups()
                    body = body.strip()

                    # Formatowanie czasu (np. "09" -> "09:00", "0730" -> "07:30")
                    if len(time) == 2:
                        formatted_time = f"{time}:00"
                    elif len(time) == 4:
                        formatted_time = f"{time[:2]}:{time[2:]}"
                    else:
                        formatted_time = time

                    # Przypadek A: Tekst wewnątrz apostrofów
                    if body.startswith("&") and body.endswith("&"):
                        content = body[1:-1].strip()
                        output_lines.append(f"[{formatted_time}] {content}")

                    # Przypadek B: Wyłącznie wielkie litery (skróty)
                    else:
                        decoded_items = []
                        for char in body:
                            if char in DICTIONARY:
                                decoded_items.append(DICTIONARY[char])

                        if decoded_items:
                            content = ", ".join(decoded_items)
                            output_lines.append(f"[{formatted_time}] {content}")

    return "\n".join(output_lines)

# --- URUCHOMIENIE ---
INPUT_FILE = "blabla.txt"

result = decompress_diary_from_file(INPUT_FILE)
if result:
    print(result)

