import sys
import os
import re
import json
import time
from pathlib import Path

from google import genai
from google.genai import types
from google.genai import errors as genai_errors

BASE_DIR = '/home/dtstgseete/ai-chats/gemini/'

# Modele pomijane przy automatycznym wyborze (obrazy, audio, embeddingi itp.)
EXCLUDE_KEYWORDS = ("image", "live", "tts", "audio", "embedding", "robotics",
                    "computer-use", "learnlm", "aqa", "veo", "imagen")


def get_latest_chat_file_by_name(folder_path):
    directory = Path(folder_path)
    files = list(directory.glob("*.json"))
    if not files:
        return None
    # Sortujemy leksykalnie na podstawie samej nazwy pliku
    return str(max(files, key=lambda f: f.name))


def prepare_chat_directory(folder_path):
    if not os.path.exists(folder_path):
        print(f"\n[!] Katalog '{folder_path}' nie istnieje.")
        conf = input("Czy chcesz utworzyć nowy katalog (nowy czat)? [y/N]: ").strip().lower()
        if conf == 'y':
            os.makedirs(folder_path, exist_ok=True)
            print(f"[+] Utworzono nowy katalog rozmowy: {folder_path}\n")
            return True
        print("Anulowano. Skrypt zostanie zamknięty.")
        return False
    return True


def save_conversation_history(filepath, conv_state):
    raw_data_to_save = []
    for message in conv_state:
        text_parts = [part.text for part in message.parts if part.text]
        raw_data_to_save.append({"role": message.role, "text": "".join(text_parts)})
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(raw_data_to_save, f, ensure_ascii=False, indent=2)


def load_conversation_history(filepath):
    conv_state = []
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            raw_data = json.load(f)
        except json.JSONDecodeError:
            return []
    for item in raw_data:
        conv_state.append(types.Content(
            role=item["role"],
            parts=[types.Part.from_text(text=item["text"])]
        ))
    return conv_state


def read_input_source(folder_path='./'):
    input_filepath = os.path.join(folder_path, "input.txt")
    print(input_filepath)
    if os.path.exists(input_filepath):
        with open(input_filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        if content:
            print(f"[+] Wykryto zapytanie z pliku input.txt ({len(content)} znaków).")
            return content
    return ''


# ---------------------------------------------------------------------------
# Wybór modelu
# ---------------------------------------------------------------------------

def list_text_models(client):
    """Zwraca nazwy modeli dostępnych dla Twojego klucza, które obsługują generateContent."""
    names = []
    for m in client.models.list():
        name = m.name.replace("models/", "")
        actions = getattr(m, "supported_actions", None) or []
        if "generateContent" not in actions:
            continue
        if not name.startswith("gemini"):
            continue
        if any(k in name for k in EXCLUDE_KEYWORDS):
            continue
        names.append(name)
    return names


def model_rank(name):
    """Im wyższy klucz, tym lepszy model: najpierw wersja, potem klasa (pro > flash > lite), potem stabilność."""
    ver = re.search(r"gemini-(\d+(?:\.\d+)?)", name)
    version = float(ver.group(1)) if ver else 0.0
    if "flash-lite" in name or "lite" in name:
        tier = 1
    elif "flash" in name:
        tier = 2
    elif "pro" in name:
        tier = 3
    else:
        tier = 0
    stable = 0 if any(x in name for x in ("preview", "exp")) else 1
    alias_penalty = 0 if "latest" in name else 1
    return (version, tier, stable, alias_penalty)


def ranked_models(client):
    return sorted(list_text_models(client), key=model_rank, reverse=True)


def generate_with_fallback(client, candidates, start_model, contents):
    """
    Próbuje start_model, a przy błędzie (model niedostępny, limit, przeciążenie)
    przechodzi do kolejnych kandydatów. Zwraca (response, użyty_model).
    """
    order = [start_model] + [m for m in candidates if m != start_model]
    last_error = None
    for model in order:
        try:
            response = client.models.generate_content(model=model, contents=contents)
            return response, model
        except genai_errors.APIError as e:
            last_error = e
            code = getattr(e, "code", None)
            print(f"[!] Model {model} zwrócił błąd {code}: {getattr(e, 'message', e)}")
            if code in (400, 401):
                # zły klucz lub zapytanie - zmiana modelu nie pomoże
                raise
            print("[!] Próbuję kolejny model...")
    raise last_error


# ---------------------------------------------------------------------------
# Start
# ---------------------------------------------------------------------------

if len(sys.argv) != 2:
    print("Błąd: Konieczne jest podanie dokładnie jednego argumentu.")
    print("Użycie: python start.py <nazwa_katalogu_czatu>")
    sys.exit(1)

chat_dir = sys.argv[1]
print(f"Pobrany argument: {chat_dir}")

chat_path = BASE_DIR + chat_dir + '/'
if not prepare_chat_directory(chat_path):
    sys.exit()

# Klucz pobierany ze zmiennej środowiskowej (.bashrc)
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Wybór modelu: GEMINI_MODEL z env, a jeśli go nie ma - najlepszy dostępny
try:
    candidates = ranked_models(client)
except genai_errors.APIError as e:
    print(f"[!] Nie udało się pobrać listy modeli: {e}")
    candidates = []

current_model = os.environ.get("GEMINI_MODEL") or (candidates[0] if candidates else "gemini-3.5-flash-lite")
print(f"[+] Model: {current_model}")
print("[+] Komendy: 'models' (lista), 'model <nazwa>' (zmiana), 'f' (z input.txt), 'exit'")

while True:
    latest_chat_file_name = get_latest_chat_file_by_name(chat_path)
    print(f'chat file to load conversation: {latest_chat_file_name}\n')

    conv_state = [] if latest_chat_file_name is None else load_conversation_history(latest_chat_file_name)

    user_input = input("\nTy: ")
    cmd = user_input.strip().lower()

    if cmd == 'exit':
        print("[+] Zakończono sesję.")
        break

    if cmd == 'models':
        try:
            candidates = ranked_models(client)
        except genai_errors.APIError as e:
            print(f"[!] Błąd listowania modeli: {e}")
            continue
        print("Dostępne modele (od najlepszego wg heurystyki):")
        for m in candidates:
            print(f"  {'*' if m == current_model else ' '} {m}")
        continue

    if cmd.startswith('model '):
        current_model = user_input.strip().split(None, 1)[1].replace("models/", "")
        print(f"[+] Model zmieniony na: {current_model}")
        continue

    if cmd == 'f':
        print('czytanie z pliku\n')
        user_input = read_input_source()
        if user_input.strip() == '':
            print("\nBrak pliku input.txt albo pusty")
            continue

    print(f"\nuser_input:\n{user_input}")

    conv_state.append(types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_input)]
    ))

    print(f"\nGemini ({current_model}) myśli...")
    try:
        response, used_model = generate_with_fallback(client, candidates, current_model, conv_state)
    except genai_errors.APIError as e:
        print(f"[!] Nie udało się uzyskać odpowiedzi: {e}")
        continue  # nic nie zapisujemy - tura użytkownika nie trafia do historii

    if used_model != current_model:
        print(f"[+] Przełączono na działający model: {used_model}")
        current_model = used_model

    answer = response.text
    if not answer:
        reason = response.candidates[0].finish_reason if response.candidates else "brak kandydatów"
        answer = f"[System: Model zwrócił pustą odpowiedź. Powód: {reason}]"

    print("===========================================")
    print(f"\nGemini:\n{answer}")
    print("===========================================")

    conv_state.append(types.Content(
        role="model",
        parts=[types.Part.from_text(text=answer)]
    ))

    timestamp = int(time.time())
    filepath = os.path.join(chat_path, f"chat_{timestamp}.json")
    save_conversation_history(filepath, conv_state)
    print(f'saved to {filepath}\n')
    print("===========================================")
