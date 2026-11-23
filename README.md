# Sabre Bubble HUD

A small always-on-top timer for EVE Online interdictor (Sabre) pilots. It tracks the three warp
disruption probes (bubbles) in your launcher and the reload, so you can see at a glance when each
bubble runs out and when the launcher is loaded again.

![platform](https://img.shields.io/badge/platform-Windows-blue)

## What it does

- Press your launch hotkey (default **F2**) each time you launch a bubble. Three bars count each one down.
- After the third launch the launcher cycles and then reloads; the fourth bar shows the reload timer.
- **Ctrl+R** (or the button) starts a reload early if you only launched one or two.
- Bubble type is switchable: Standard (120 s) or Surgical (180 s).
- Bars turn red for the last 15 seconds.

It only **listens** for your hotkey and **reads** the title of the window that has focus. It never sends
keystrokes or clicks to the game, and it does not touch the EVE client, so one key press still means one
action in game.

## Download

Grab `sabre_hud.exe` from the [latest release](../../releases/latest). No install needed: put it in its own
folder (e.g. `C:\EVE Tools\SabreHUD\`) and run it. Its settings file, `sabre_config.json`, is saved
next to the exe.

Windows SmartScreen or your antivirus may warn about it, because the app is unsigned and watches the
keyboard (that is how it sees your hotkey). If you would rather not trust the exe, run it from source
(below) and read the code: it is a single file.

## Using it

- **Move**: left-click and drag anywhere on the dark box.
- **Everything else**: right-click the widget.
  - *Set Launch Hotkey* to rebind the launch key.
  - *Link Specific EVE Pilot* locks the hotkey to one client (handy when multiboxing): choose it, then
    click that client within 3 seconds.
  - *Filter: Any EVE Client* (default) or *All Windows* (no filter).
  - *Reset* gives you a full, loaded launcher again.
  - *Create Desktop Shortcut* puts a shortcut on your Desktop.
- Hotkeys only count while an EVE window (title starting `EVE - `) is focused, unless you pick *All Windows*.
- Use EVE in Fixed Window or Windowed mode so the overlay can sit on top of it.

## Run from source

Needs Windows and Python 3.10 or newer.

```powershell
pip install -r requirements.txt
python sabre_hud.py
```

## Build the exe

```powershell
pip install pyinstaller
pyinstaller sabre_hud.spec
```

The exe appears in `dist\`.

## Privacy

Everything stays on your PC. The only file it writes is `sabre_config.json` (hotkey, window position,
settings) next to the program. It makes no network connections.

## Licence

MIT, see [LICENSE](LICENSE). Not affiliated with CCP Games. EVE Online is a trademark of CCP hf.
