import glob
import os
import json
import time
from pathlib import Path


import os
from google import genai
from google.genai import types


def get_latest_chat_file(folder_path):
    # Szukamy wszystkich plików .json w wskazanym katalogu
    files = glob.glob(os.path.join(folder_path, "*.json"))
    if not files:
        return None  # Brak plików = start nowej konwersacji
    # Zwracamy plik z najnowszą datą modyfikacji
    return max(files, key=os.path.getmtime)





def get_latest_chat_file_by_name(folder_path):
    directory = Path(folder_path)
    files = list(directory.glob("*.json"))

    if not files:
        return None

    # Sortujemy leksykalnie na podstawie samej nazwy pliku
    return str(max(files, key=lambda f: f.name))

def prepare_chat_directory(folder_path):
    # Sprawdzamy, czy katalog już istnieje
    if not os.path.exists(folder_path):
        print(f"\n[!] Katalog '{folder_path}' nie istnieje.")
        conf = input("Czy chcesz utworzyć nowy katalog (nowy czat)? [y/N]: ").strip().lower()
        
        if conf == 'y':
            # Tworzy katalog wraz z brakującymi katalogami nadrzędnymi (~/aichats/gemini/)
            os.makedirs(folder_path, exist_ok=True)

            new_conversation = True

            print(f"[+] Utworzono nowy katalog rozmowy: {folder_path}\n")
            
            return True
        else:
            print("Anulowano. Skrypt zostanie zamknięty.")
            return False
    return True



def save_conversation_history(filepath, conv_state):
    """
    Wyciąga tekst z obiektów Google i zapisuje całą historię do nowego pliku JSON.
    """

    raw_data_to_save = []

    for message in conv_state:
        # Wyciągamy rolę ("user" lub "model")
        role = message.role

        # Łączymy tekst ze wszystkich części (parts) wiadomości w jeden ciąg
        text_parts = [part.text for part in message.parts if part.text]
        full_text = "".join(text_parts)

        # Tworzymy prosty słownik do zrzucenia do pliku
        raw_data_to_save.append({
            "role": role,
            "text": full_text
        })

    # Zapisujemy do pliku z zachowaniem polskich znaków (ensure_ascii=False)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(raw_data_to_save, f, ensure_ascii=False, indent=2)




def load_conversation_history(filepath):
    """
    Wczytuje historię z pliku JSON i konwertuje ją na format obiektów Google.
    Format pliku JSON to lista słowników: [{"role": "user"|"model", "text": "treść"}, ...]
    """
    conv_state = []

    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            raw_data = json.load(f)
        except json.JSONDecodeError:
            # Obsługa sytuacji, gdyby plik był całkowicie pusty/uszkodzony
            return []

    for item in raw_data:
        # Tworzymy oficjalny obiekt wiadomości Google dla każdej tury z pliku
        google_message = types.Content(
            role=item["role"],
            parts=[types.Part.from_text(text=item["text"])]
        )
        conv_state.append(google_message)

    return conv_state






def read_input_source(folder_path = './'):
    """
    Sprawdza, czy w katalogu czatu istnieje plik input.txt z treścią.
    Jeśli tak - zwraca jego zawartość i czyści plik.
    Jeśli nie - zwraca None (sygnał do przejścia na klawiaturę).
    """
    input_filepath = os.path.join(folder_path, "input.txt")

    print(input_filepath)
    
    # 1. Jeśli plik istnieje, sprawdzamy jego zawartość
    if os.path.exists(input_filepath):
        with open(input_filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            
        if content:
            print(f"[+] Wykryto zapytanie z pliku input.txt ({len(content)} znaków).")
            
            return content
            
    return ''







if not prepare_chat_directory('/home/dtstgseete/ai-chats/gemini/' + 'test-dir2'):
    exit()

# Inicjalizacja klienta Google GenAI (pobiera klucz z .bashrc)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


i = 0
go = True

while go == True:
    i = i + 1

    latest_chat_file_name = get_latest_chat_file_by_name('/home/dtstgseete/ai-chats/gemini/' + 'test-dir2')

    print(f'latest chat file name: {latest_chat_file_name}\n')


    if None == latest_chat_file_name:
        conv_state = []
    else:
        conv_state = load_conversation_history(latest_chat_file_name)

    print(f'conv_state loaded {conv_state}\n')

    # Próba odczytu z pliku input.txt
    user_input = input("\nTy: ")


    user_input_strip_lower = user_input.strip().lower()
    if user_input.strip().lower() == 'f':
        print('czytanie z pliku\n')
        user_input = read_input_source()
        user_input_strip_lower = user_input.strip().lower()

    if user_input_strip_lower == '':
        user_input = input("\nBrak pliku input.txt albo pusty")
        continue
                
    if user_input_strip_lower == 'exit':
        print("[+] Zakończono sesję.")
        break
                
    new_json_entry = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_input)]
    )

    conv_state.append(new_json_entry)

    print("\nGemini myśli...")
    response = client.models.generate_content(
        # model="gemini-3.6-flash",
        model="gemini-3.5-flash-lite",
        contents=conv_state  # Tutaj przekazujemy całą dotychczasową rozmowę
    )
    
    # 5. Wyświetlamy odpowiedź w terminalu
    print(f"\nGemini: {response.text}")



    """
            model_string = ""
            
            # 1. Sprawdzamy czy Google nie zablokowało odpowiedzi (Filtry bezpieczeństwa)
            if response.candidates and response.candidates[0].finish_reason.name in ["SAFETY", "BLOCKLIST", "OTHER"]:
                model_string = f"[System: Odpowiedź zablokowana przez filtry Google. Powód: {response.candidates[0].finish_reason.name}]"
            
            # 2. Jeśli odpowiedź przeszła pomyślnie, bezpiecznie wyciągamy czysty tekst z części składowych
            elif response.candidates and response.candidates[0].content.parts:
                # Łączymy wszystkie fragmenty tekstowe, odrzucając puste lub inne obiekty
                text_chunks = [part.text for part in response.candidates[0].content.parts if part.text]
                model_string = "".join(text_chunks)
            
            # 3. Zabezpieczenie na wypadek całkowicie pustego obiektu z serwera
            if not model_string:
                model_string = "[System: Model zwrócił pustą odpowiedź lub błąd wewnętrzny.]"
            
            # Wyświetlamy bezpieczny, oczyszczony string w terminalu
            print(f"\nGemini: {model_string}")
            
            # Zapisujemy do lokalnej historii poprawnie sformatowany obiekt string
            new_model_message = types.Content(
                role="model",
                parts=[types.Part.from_text(text=model_string)]
            )
            conv_state.append(new_model_message)



    """




    new_json_entry = types.Content(
        role="model",
        parts=[types.Part.from_text(text=response.text)]
    )


    conv_state.append(new_json_entry)

    print(f'conv_state to write {conv_state}\n')

    timestamp = int(time.time())
    init_filepath = os.path.join('/home/dtstgseete/ai-chats/gemini/' + 'test-dir2/', f"chat_{timestamp}.json")

    save_conversation_history(init_filepath, conv_state)

    print(f'{init_filepath}\n')

    if i == 5:
        go = False

