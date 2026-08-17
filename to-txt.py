# python3.12 to-txt.py dieta-dziennik.json 24 > dieta-dziennik.txt && vim dieta-dziennik.txt
import sys

def formatuj_json_do_tekstu(sciezka_pliku, msg_to_skip):
    try:
        with open(sciezka_pliku, 'r', encoding='utf-8') as f:
            dane = json.load(f)
        
        # Jeśli JSON to słownik z listą pod jakimś kluczem, dostosuj poniższą linię,
        # np. wiadomosci = dane.get('history', dane)
        wiadomosci = dane if isinstance(dane, list) else dane.get('messages', dane)

        i = 0;
        for msg in wiadomosci:
            if i < msg_to_skip:
                i = i + 1
                continue
            rola = msg.get('role', 'unknown').upper()
            tresc = msg.get('text', '').strip()
            
            # Zamiana nazwy roli na czytelniejszą
            if rola == 'MODEL':
                rola = 'GEMINI'
                
            print(f"=== {rola} ===")
            print(tresc)
            print("-" * 40)
            print() # Dodatkowa pusta linia dla czytelności
            i = i + 1
            
    except FileNotFoundError:
        print(f"Błąd: Plik '{sciezka_pliku}' nie istnieje.", file=sys.stderr)
    except json.JSONDecodeError:
        print("Błąd: Niepoprawny format pliku JSON.", file=sys.stderr)
    except Exception as e:
        print(f"Wystąpił błąd: {e}", file=sys.stderr)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Użycie: python formatuj_czat.py <sciezka_do_pliku.json>")
    else:
        if len(sys.argv) == 2:
            formatuj_json_do_tekstu(sys.argv[1], 0)
        else:
            formatuj_json_do_tekstu(sys.argv[1], int(sys.argv[2]))
