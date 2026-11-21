
========================================

=== GEMINI gemini-3.5-flash-lite ===
Oto kompleksowa instrukcja użytkowania skryptu, wyjaśnienie plików konfiguracyjnych oraz szczegółowe informacje techniczne (w tym odpowiedź na Twoje pytanie o filtry plików i format `models.cfg`).

### 1. Instrukcja obsługi skryptu dla użytkownika

#### Przygotowanie środowiska (Sourcing)
Zanim uruchomisz skrypt, musisz wgrać zmienne środowiskowe (klucz API oraz ścieżkę do katalogu czatów) do swojej sesji terminala. 

Utwórz plik `my-env.sh` (jeśli jeszcze go nie masz) o zawartości:
```bash
export AI_CHATS_GEMINI_DIR='/home/x/ai-chats/gemini/'
export GEMINI_API_KEY='TWOJ_KLUCZ_API'
```

Przed każdym uruchomieniem skryptu wykonaj w terminalu polecenie `source`:
```bash
source my-env.sh
```
*(Uwaga: Zapis musi być wykonany przez kropkę lub słowo `source` w tej samej sesji powłoki, z której wywołujesz Pythona).*

#### Uruchomienie skryptu
Skrypt wymaga podania nazwy podkatalogu (czatu) w katalogu bazowym `AI_CHATS_GEMINI_DIR`:
```bash
python start.py nazwa_katalogu_czatu
```
*Jeśli podany katalog nie istnieje, skrypt zapyta, czy go utworzyć.*

---

### 2. Znaczenie plików zarządzanych przez użytkownika

* **`models.cfg`** (w katalogu uruchomieniowym skryptu):
  Plik tekstowy definiujący listę modeli AI oraz ich kolejność priorytetową. Modele umieszczone wyżej są traktowane jako pierwsze w mechanizmie *fallback* (przełączania awaryjnego). Możesz go edytować ręcznie (np. w `vim`), dodawać puste linie dla przejrzystości oraz komentarze zaczynające się od `#`.
* **Pliki `chat-*.json`** (w katalogu czatu, np. `/home/x/ai-chats/gemini/nazwa_katalogu/`):
  Automatyczne snapshoty konwersacji. Każda wypowiedź zapisuje się jako nowy plik z unikalnym timestampem (np. `chat-1715000000.json`). Skrypt zawsze automatycznie wykrywa **najnowszy** plik na podstawie najwyższego numeru i wczytuje go jako kontekst dalszej rozmowy.

---

### 3. Dokumentacja wybranych komend wewnątrz skryptu

Podczas aktywnej sesji czatu (po wpisaniu `Ty: `) możesz używać następujących poleceń sterujących:

* **Komenda `%u` (Update):**
  * **Użycie:** Wpisz `%u` i naciśnij Enter.
  * **Działanie:** Odpytuje oficjalne API Google Gemini o świeżą listę dostępnych modeli tekstowych, sortuje je według wewnętrznej heurystyki (stawiając modele Pro/Flash wyżej) i automatycznie nadpisuje plik `models.cfg`. Wyświetla zaktualizowaną listę w terminalu.

* **Komenda `%m <nazwa_modelu>` (Promocja modelu):**
  * **Użycie:** Wpisz np. `%m gemini-2.5-pro` i naciśnij Enter.
  * **Działanie:** Przenosi wskazany model na samą górę pliku `models.cfg` (usuwając jego ewentualne starsze wpisy z niższych pozycji). Sprawia to, że model ten staje się natychmiast modelem domyślnym (*startowym*) dla kolejnych zapytań w tej i następnych sesjach.

* **Komenda `%f` (Wczytanie z pliku):**
  * **Użycie:** Wpisz `%f` i naciśnij Enter.
  * **Działanie:** Pobiera treść zapytania bezpośrednio z pliku `input.txt` znajdującego się w katalogu czatu, zamiast wymagać wpisywania tekstu z klawiatury. Przydatne przy wklejaniu bardzo długich promptów.

* **Komenda `%l` (Lista modeli):**
  * **Użycie:** Wpisz `%l` i naciśnij Enter.
  * **Działanie:** Wyświetla aktualną listę modeli wczytaną z pliku `models.cfg`, oznaczając gwiazdką `*` ten model, który jest aktualnie używany jako domyślny.

* **Komenda `exit`:**
  * **Użycie:** Wpisz `exit` i naciśnij Enter.
  * **Działanie:** Bezpiecznie kończy działanie skryptu.

---

### 4. Dwa pytania

#### Czy pobieranie kontekstu z katalogu uwzględnia pliki inne niż zaczynające się od `chat-`?
**Nie.** Skrypt używa bardzo precyzyjnego wyrażenia regularnego (regex):
`pattern = re.compile(r"^chat-(\d+)\.json$")`

Dzięki temu:
* Pliki takie jak `alamakota.txt`, `raad.txt`, `input.txt` czy kopia robocza `last-chat.json` są **całkowicie ignorowane** przy próbie odnalezienia najnowszego pliku konwersacji (`get_latest_chat_file_by_name`).
* Plik musi zaczynać się dokładnie od słowa `chat-`, po którym musi nastąpić ciąg cyfr (`\d+`) i rozszerzenie `.json`. Żadne inne nazwy ani pliki pomocnicze nie zakłócą mechanizmu wczytywania historii. Użytkownik może swobodnie „żonglować” snapshotami (np. `chat-000.json`, `chat-999.json`) lub trzymać w katalogu dowolne pliki tekstowe/json.

#### Czy w pliku `models.cfg` mogą być puste linie? (Tak dla oka?)
**Tak, jak najbardziej.** Funkcja `load_models_from_cfg()` w skrypcie została napisana tak, że:
1. Odczytuje plik linia po linii.
2. Robi `line.strip()` (obcina spacje).
3. Sprawdza warunek: `if line and not line.startswith('#'):`
Oznacza to, że puste linie, linie zawierające same spacje oraz komentarze zaczynające się od `#` są **w pełni ignorowane**. Możesz śmiało formatować plik `models.cfg` pustymi liniami dla lepszej przejrzystości wzrokowej.

---

========================================
