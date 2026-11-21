import sys
import os
import re
import json
import time
from pathlib import Path

from google import genai
from google.genai import types
from google.genai import errors as genai_errors


# source .sh file
# example:
#     source my-env.sh
# where my-env.sh content is:
#     export AI_CHATS_GEMINI_DIR='/home/x/ai-chats/gemini/'
#     export GEMINI_API_KEY='ABCDEFGHIJKLMNOPQRSTUVWXYZ'



BASE_DIR=os.environ.get("AI_CHATS_GEMINI_DIR")
MODELS_CONFIG_FILE = os.path.join("models.cfg") if BASE_DIR else "models.cfg"

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


def save_conversation_history(filepath, conv_state, models_history):
    data = []
    for message, mdl in zip(conv_state, models_history):
        txt = ''.join(p.text for p in message.parts if p.text)
        item = {'role': message.role, 'text': txt}
        if mdl:
            item['model'] = mdl
        data.append(item)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_conversation_history(filepath):
    conv_state = []
    models_history = []
    with open(filepath, 'r', encoding='utf-8') as f:
        try:
            raw_data = json.load(f)
        except json.JSONDecodeError:
            return [], []
    for item in raw_data:
        conv_state.append(types.Content(
            role=item["role"],
            parts=[types.Part.from_text(text=item["text"])]
        ))
        models_history.append(item.get('model'))
    return conv_state, models_history


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


STANDARD_NAME = re.compile(r"^gemini-(\d+(?:\.\d+)?)-(pro|flash-lite|flash)(?:-(.+))?$")


def model_rank(name):
    """
    Wyższy klucz = lepszy model. Najpierw modele o standardowej nazwie
    (gemini-X.Y-pro|flash|flash-lite), potem wersja, klasa (pro > flash > lite),
    stabilność (bez preview/exp). Kryptonimy typu 'gemini-4-argon' trafiają na koniec,
    ale nadal można je wybrać ręcznie komendą 'model <nazwa>'.
    """
    m = STANDARD_NAME.match(name)
    if not m:
        return (0, 0.0, 0, 0, 0)
    version = float(m.group(1))
    tier = {"flash-lite": 1, "flash": 2, "pro": 3}[m.group(2)]
    suffix = m.group(3) or ""
    stable = 0 if any(x in suffix for x in ("preview", "exp")) else 1
    alias_penalty = 0 if "latest" in suffix else 1
    return (1, version, tier, stable, alias_penalty)


def ranked_models(client):
    return sorted(list_text_models(client), key=model_rank, reverse=True)

def save_models_to_cfg(candidates):
    """Zapisuje listę modeli do pliku models.cfg jako czysty tekst (jeden na linię)."""
    try:
        with open(MODELS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(candidates) + "\n")
        print(f"[+] Zapisano listę modeli do pliku: {MODELS_CONFIG_FILE}")
    except Exception as e:
        print(f"[!] Nie udało się zapisać pliku {MODELS_CONFIG_FILE}: {e}")


def load_models_from_cfg():
    """Wczytuje listę modeli z pliku tekstowego models.cfg (pomija puste linie i komentarze #)."""
    models = []
    if os.path.exists(MODELS_CONFIG_FILE):
        try:
            with open(MODELS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        models.append(line)
        except Exception as e:
            print(f"[!] Błąd odczytu pliku {MODELS_CONFIG_FILE}: {e}")
    return models


def promote_model_in_cfg(model_name):
    """Przenosi wybrany model na początek pliku models.cfg, usuwając jego ewentualne starsze wystąpienia."""
    lines = []
    if os.path.exists(MODELS_CONFIG_FILE):
        try:
            with open(MODELS_CONFIG_FILE, 'r', encoding='utf-8') as f:
                lines = [line.rstrip('\n') for line in f]
        except Exception as e:
            print(f"[!] Błąd odczytu pliku {MODELS_CONFIG_FILE}: {e}")

    # Usuwamy model_name ze wszystkich linii (jeśli tam był), ignorując puste i komentarze przy porównaniu
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped == model_name or stripped == f"models/{model_name}":
            continue # pomijamy, bo wrzucimy go na samą górę
        cleaned_lines.append(line)

    # Wstawiamy nowy model na samą górę jako aktywny
    new_lines = [model_name] + cleaned_lines

    try:
        with open(MODELS_CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write("\n".join(new_lines) + "\n")
        print(f"[+] Zaktualizowano {MODELS_CONFIG_FILE}: model '{model_name}' trafił na początek.")
    except Exception as e:
        print(f"[!] Nie udało się zapisać pliku {MODELS_CONFIG_FILE}: {e}")

def refresh_and_save_models(client):
    """Pobiera świeżą listę z API i zapisuje do pliku."""
    try:
        candidates = ranked_models(client)
        save_models_to_cfg(candidates)
        return candidates
    except genai_errors.APIError as e:
        print(f"[!] Nie udało się pobrać listy modeli z API: {e}")
        return []


MAX_ATTEMPTS = 334          # ile modeli maksymalnie próbujemy na jedno pytanie
REQUEST_TIMEOUT_MS = 90_000  # timeout pojedynczego zapytania (90 s)
failed_models = {}        # model -> kod błędu, pomijane do końca sesji


def generate_with_fallback(client, candidates, start_model, contents):
    """
    Próbuje start_model, a przy błędzie (limit, model niedostępny, przeciążenie)
    przechodzi do kolejnych kandydatów - maksymalnie MAX_ATTEMPTS.
    Modele, które już zawiodły w tej sesji, są pomijane. Zwraca (response, użyty_model).
    """
    order = [start_model] + [m for m in candidates if m != start_model]
    order = order[:MAX_ATTEMPTS]
    if "gemini-3.5-flash-lite" not in order:
        order.append("gemini-3.5-flash-lite")

    last_error = None
    for i, model in enumerate(order, 1):
        print(f"[{i}/{len(order)}] próba: {model} ...", flush=True)
        t0 = time.time()
        try:
            response = client.models.generate_content(
                model=model, contents=contents,
                config=types.GenerateContentConfig(
                    http_options=types.HttpOptions(timeout=REQUEST_TIMEOUT_MS)),
            )
            return response, model
        except genai_errors.APIError as e:
            last_error = e
            code = getattr(e, "code", None)
            failed_models[model] = code
            print(f"[!] {model}: błąd {code} po {time.time() - t0:.1f}s - {str(getattr(e, 'message', e))[:150]}")
            if code in (400, 401):
                raise  # zły klucz lub zapytanie - zmiana modelu nie pomoże
        except Exception as e:  # timeout sieciowy itp.
            last_error = e
            failed_models[model] = type(e).__name__
            print(f"[!] {model}: {type(e).__name__} po {time.time() - t0:.1f}s")
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

# Wstępny zapis domyślnej listy modeli do pliku, jeśli go nie ma
if not os.path.exists(MODELS_CONFIG_FILE):
    refresh_and_save_models(client)

start_model = ''
current_model = ''

print("[+] Komendy: '%l' (lista z cfg), '%u' (update odśwież z API), '%m <nazwa>' (promocja modelu na pierwsze miejsce), '%f' (tekst z input.txt), 'exit'")

while True:
    latest_chat_file_name = get_latest_chat_file_by_name(chat_path)
    print(f'chat file to load conversation: {latest_chat_file_name}\n')

    conv_state, models_history = ([],[]) if latest_chat_file_name is None else load_conversation_history(latest_chat_file_name)

    user_input = input("\nTy: ")
    cmd = user_input.strip().lower()

    # Zawsze ładujemy kandydatów z pliku na start pętli (uwzględnia edycję w VIM)
    candidates = load_models_from_cfg()
    if not candidates:
        candidates = ["gemini-3.5-flash-lite"]
    if candidates:
        print("[+] kandydaci " + ", ".join(candidates[:6]))
        
    # Ustalamy start_model z pliku (lub zmiennej środowiskowej)
    start_model = os.environ.get("GEMINI_MODEL") or candidates[0]
    current_model = start_model

    if cmd == 'exit':
        print("[+] Zakończono sesję.")
        break

    if cmd == '%l':
        print("Aktualna lista modeli (z pliku models.cfg):")
        for m in candidates:
            print(f"  {'*' if m == current_model else ' '} {m}")
        continue

    if cmd == '%u':
        # Pobieranie z API i nadpisywanie pliku models.cfg na żądanie użytkownika
        candidates = refresh_and_save_models(client)
        if not candidates:
            # Fallback na plik gdyby API niedomagało
            candidates = load_models_from_cfg()
            
        print("Dostępne modele (od najlepszego wg heurystyki):")
        for m in candidates:
            print(f"  {'*' if m == current_model else ' '} {m}")
        continue

    if cmd.startswith('%m '):
        target_model = user_input.strip().split(None, 1)[1].replace("models/", "")
        
        # Modyfikujemy plik models.cfg zgodnie z wymaganiem
        promote_model_in_cfg(target_model)
        
        # Ponieważ na początku kolejnej iteracji pętli (lub od razu tutaj) 
        # plik jest czytany, model natychmiast stanie się startowym.
        continue

    if cmd == '%f':
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
    models_history.append(None)

    # Pobieranie listy modeli z pliku lokalnego w pętli (zamiast z API)
    if not candidates:
        candidates = [start_model] # Awaryjnie

    try:
        response, used_model = generate_with_fallback(client, candidates, start_model, conv_state)
    except KeyboardInterrupt:
        print("\n[!] Przerwano (Ctrl+C).")
        continue
    except Exception as e:
        print(f"[!] Nie udało się uzyskać odpowiedzi: {e}")
        continue  # nic nie zapisujemy - tura użytkownika nie trafia do historii

    if used_model != current_model:
        current_model = used_model
        print(f"[+] Przełączono na działający model: {used_model}")

    answer = response.text
    if not answer:
        reason = response.candidates[0].finish_reason if response.candidates else "brak kandydatów"
        answer = f"[System: Model zwrócił pustą odpowiedź. Powód: {reason}]"

    print("===========================================")
    print(f"\nGemini({current_model})\n{answer}")
    print("===========================================")

    conv_state.append(types.Content(
        role="model",
        parts=[types.Part.from_text(text=answer)]
    ))
    models_history.append(current_model)

    timestamp = int(time.time())
    filepath = os.path.join(chat_path, f"chat-{timestamp}.json")
    save_conversation_history(filepath, conv_state, models_history)
    print(f'saved to {filepath}\n')
    print("===========================================")

