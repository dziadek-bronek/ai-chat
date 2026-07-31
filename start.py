import glob
import os


def get_latest_chat_file(folder_path):
    # Szukamy wszystkich plików .json w wskazanym katalogu
    files = glob.glob(os.path.join(folder_path, "*.json"))
    if not files:
        return None  # Brak plików = start nowej konwersacji
    # Zwracamy plik z najnowszą datą modyfikacji
    return max(files, key=os.path.getmtime)

def prepare_chat_directory(folder_path):
    # Sprawdzamy, czy katalog już istnieje
    if not os.path.exists(folder_path):
        print(f"\n[!] Katalog '{folder_path}' nie istnieje.")
        conf = input("Czy chcesz utworzyć nowy katalog (nowy czat)? [y/N]: ").strip().lower()
        
        if conf == 'y':
            # Tworzy katalog wraz z brakującymi katalogami nadrzędnymi (~/aichats/gemini/)
            os.makedirs(folder_path, exist_ok=True)
            print(f"[+] Utworzono nowy katalog rozmowy: {folder_path}")
            return True
        else:
            print("Anulowano. Skrypt zostanie zamknięty.")
            return False
    return True


if not prepare_chat_directory('/home/dtstgseete/ai-chats/gemini/' + 'test-dir'):
    return

:w

