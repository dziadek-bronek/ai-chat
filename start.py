import glob
import os
import json
import time
from pathlib import Path


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
    return max(files, key=lambda f: f.name)



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
    conv_state = []
    """
    Wczytuje historię z pliku JSON i konwertuje ją na format obiektów Google.
    Format pliku JSON to lista słowników: [{"role": "user"|"model", "text": "treść"}, ...]

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
    """

    return conv_state


if not prepare_chat_directory('/home/dtstgseete/ai-chats/gemini/' + 'test-dir'):
    exit



i = 0
go = True

while go == True:
    i = i + 1


    latest_chat_file_name = get_latest_chat_file_by_name('/home/dtstgseete/ai-chats/gemini/' + 'test-dir')

    print(f'latest chat file name: {latest_chat_file_name}\n')



    if None == latest_chat_file_name:
        conv_state = []
    else:
        conv_state = load_conversation_history(latest_chat_file_name)

    print(f'conv_state on start {conv_state}\n')

    # user_input = input("\nTy: ")

    user_input = f'q{i}'

    new_user_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_input)]
    )
    conv_state.append(new_user_message)

    answer = f'a{i}'

    new_user_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_input)]
    )
    conv_state.append(new_user_message)

    # if user_input.strip().lower() == 'exit':


    print(f'conv_state on start {conv_state}\n')



    timestamp = int(time.time())
    init_filepath = os.path.join('/home/dtstgseete/ai-chats/gemini/' + 'test-dir/', f"chat_{timestamp}.json")

    print(f'{init_filepath}\n')




    go = False

