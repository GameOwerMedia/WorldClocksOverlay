# World Clock Overlay

Lekki, przezroczysty overlay z zegarami stref czasowych dla Windows.

Wyswietla sie przy pasku zadan lub jako niezalezne okna na dowolnym monitorze. Zbudowany w Pythonie z PySide6, pakowany do pojedynczego `.exe`.

![World Clock Overlay](docs/screenshots/line-window.png)

## Funkcje

- Przezroczyste, bezramkowe widgety always-on-top
- Dwa tryby: poziomy **pasek** lub niezalezne **okna**
- 100+ miast ze wszystkich glownych stref czasowych
- Wyszukiwarka miast z indywidualnym wyborem trybu
- Przeciaganie, skalowanie kolkiem myszy, zmiana rozmiaru
- Zapis pozycji i rozmiaru kazdego okna miedzy sesjami
- Ikona w zasobniku systemowym z przelaczaniem widocznosci
- Ciemny i jasny motyw z przezroczystoscia
- Format 24h/12h i opcjonalne sekundy
- Dziala w pelni offline, dane stref czasowych sa lokalne

## Szybki start

**Wymagania:** Windows, Python 3.11+

```bat
install.bat
```

Uruchom:

```bat
dist\WorldClockOverlay.exe
```

Tryb developerski:

```bat
run_dev.bat
```

## Sterowanie

| Wejscie | Akcja |
|---|---|
| Lewy przycisk + przeciaganie | Przesuwanie okna |
| Kolko myszy | Skalowanie |
| Uchwyt w prawym dolnym rogu | Zmiana rozmiaru |
| Prawy przycisk | Menu kontekstowe |
| Klik na ikone tray | Pokaz/ukryj wszystkie zegary |

## Konfiguracja

Ustawienia sa przechowywane w `config.json` obok pliku wykonywalnego (lub plikow zrodlowych w trybie dev). Zmiany z poziomu UI zapisuja sie automatycznie.

Mozna tez edytowac plik recznie:

```json
{
  "window": {
    "opacity": 0.82,
    "always_on_top": true
  },
  "display": {
    "show_seconds": false,
    "use_24h": true,
    "theme": "black"
  }
}
```

Motywy: `"black"`, `"white"`

## Jak to dziala

Kazde miasto moze byc ustawione w jednym z trzech trybow:

- **Off** - niewyswietlane
- **Line window** - dodane do wspolnego poziomego paska
- **Separate window** - niezalezny plywajacy zegar

Oba tryby mozna laczyc dowolnie. Pasek jako kompaktowy towarzysz przy taskbarze, osobne okna na konkretnych monitorach.

## Struktura projektu

| Plik | Opis |
|---|---|
| `app.py` | Kod zrodlowy aplikacji |
| `config.json` | Domyslna konfiguracja |
| `requirements.txt` | Zaleznosci Pythona |
| `install.bat` | Przygotowanie srodowiska i build EXE |
| `build.bat` | Samodzielny skrypt budowania |
| `run_dev.bat` | Uruchomienie ze zrodel |
| `uninstall.bat` | Skrypt czyszczacy |

## Technologie

- Python 3.11+
- PySide6
- `zoneinfo` + `tzdata`
- PyInstaller

## Uwagi

- To plywajacy overlay, nie natywne rozszerzenie paska zadan.
- Dane stref czasowych sa lokalne. Brak dostepu do sieci.

## Licencja

Licencja MIT. Zobacz [LICENSE](LICENSE).
