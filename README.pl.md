# World Clock Overlay

Mały, półprzezroczysty overlay z zegarami świata dla Windows.

World Clock Overlay to lekki system widgetów desktopowych dla Windows. Aplikacja obsługuje wiele niezależnych okien zegarów, które można rozmieścić w dowolnych miejscach i na różnych monitorach, a także tray, autostart, wyszukiwalną listę miast, edytowalne strefy czasowe, kompaktowe skalowanie i dwa półprzezroczyste motywy dopasowane do jasnego lub ciemnego tła.

## Funkcje

- przezroczyste okno bez ramki
- always-on-top
- zaokrąglone rogi
- ikona tray z opcją pokaż / ukryj
- przeciąganie lewym przyciskiem myszy
- zmiana rozmiaru przez uchwyt w prawym dolnym rogu
- skalowanie kółkiem myszy
- wiele niezależnych okien zegarów
- nielimitowana liczba aktywnych zegarów
- scrollowalna i przeszukiwalna lista miast
- każdy zegar można przesuwać i zmieniać jego rozmiar niezależnie
- zegary można rozmieścić na różnych monitorach
- wybór miast z menu aplikacji
- edytowalny `config.json`
- przeładowanie konfiguracji bez zmiany kodu
- zapis pozycji i rozmiaru okna
- snap do prawego dolnego rogu
- przełączanie 24h / 12h
- przełączanie sekund
- dwa półprzezroczyste motywy:
- `Black`
- `White`
- autostart Windows przez `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- build EXE przez PyInstaller

## Wymagania

- Windows
- Python 3.11+

## Technologie

- Python
- PySide6
- `zoneinfo`
- `tzdata`
- PyInstaller

## Pliki projektu

- `app.py` - główna aplikacja
- `config.json` - lokalna konfiguracja
- `requirements.txt` - zależności Pythona
- `run_dev.bat` - uruchomienie w trybie developerskim
- `build.bat` - ręczny build EXE
- `install.bat` - przygotowanie venv, instalacja zależności, build EXE i opcjonalny autostart
- `uninstall.bat` - usunięcie autostartu z Windows
- `README.md` - dokumentacja po angielsku
- `README.pl.md` - dokumentacja po polsku

## Szybki start

1. Zainstaluj Python 3.11 lub nowszy.
2. Otwórz folder projektu.
3. Uruchom:

```bat
install.bat
```

4. Po zakończeniu buildu uruchom:

```bat
dist\WorldClockOverlay.exe
```

W trybie developerskim użyj:

```bat
run_dev.bat
```

## Output buildu

Plik wykonywalny pojawia się tutaj:

```text
dist\WorldClockOverlay.exe
```

## Obsługa

- lewy przycisk myszy: przeciąganie overlayu
- kółko myszy: skalowanie widgetu
- uchwyt w prawym dolnym rogu: zmiana rozmiaru
- prawy klik: menu kontekstowe
- klik na ikonę tray: pokaż / ukryj wszystkie zegary

## Menu kontekstowe

- `Select clocks...`
- `Show / Hide seconds`
- `Switch 24h / 12h`
- `Reload config`
- `Snap to bottom-right`
- `Theme: Black`
- `Theme: White`
- `Save position`
- `Close this clock`
- `Exit`

## Menu tray

- `Show all`
- `Hide all`
- `Select clocks...`
- `Reload config`
- `Theme: Black`
- `Theme: White`
- `Exit`

## Konfiguracja

Aplikacja używa lokalnego pliku `config.json` obok źródeł albo obok EXE po buildzie.

Możesz w nim:

- włączać i wyłączać miasta
- zmieniać przezroczystość
- zmieniać format czasu
- włączać lub wyłączać sekundy
- ustawiać domyślny motyw
- kontrolować snap do rogu
- zapisywać niezależną pozycję i rozmiar dla każdego zegara

Przykład:

```json
{
  "display": {
    "show_seconds": false,
    "use_24h": true,
    "theme": "black"
  }
}
```

Dostępne wartości motywu:

- `"black"`
- `"white"`

## Autostart

`install.bat` może dodać wpis dla bieżącego użytkownika Windows do:

```text
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
```

`uninstall.bat` usuwa ten wpis.

## Uwagi

- aplikacja nie integruje się natywnie z obszarem systemowego zegara na pasku zadań Windows
- działa jako lekki floating overlay, który wizualnie zachowuje się jak jeden lub wiele dodatkowych zegarów przy pasku zadań
- dane stref czasowych są lokalne i nie wymagają internetu

## Licencja

Projekt jest udostępniony na licencji MIT. Szczegóły znajdują się w pliku `LICENSE`.
