# Run the Mahsool AI backend on my Windows laptop

The website is on Vercel. It sends questions to your laptop through ngrok, at
`https://resident-coil-delusion.ngrok-free.dev`. When the laptop (or the script) is off, the website
says: "Mahsool AI is resting right now. Please try again later."

You need: your **Groq API key** and your **ngrok account** (free). The first start takes about
30 minutes (downloads). After that, starting takes about 2 minutes.

---

## Step 1. Install three programs (one time)

1. **Python 3.11**: https://www.python.org/downloads/release/python-3119/ → "Windows installer
   (64-bit)". When the installer opens, **tick "Add python.exe to PATH"** at the bottom, then click
   "Install Now".
2. **Git**: https://git-scm.com/download/win → install with all the default options.
3. **ngrok**: https://ngrok.com/download → Windows → download the ZIP, open it, and move
   `ngrok.exe` to `C:\ngrok\`. Then add `C:\ngrok` to PATH: Start menu → type "environment" →
   "Edit the system environment variables" → "Environment Variables…" → under "User variables"
   select **Path** → Edit → New → `C:\ngrok` → OK, OK, OK.

Already have another Python (for example 3.14)? Keep it. Install 3.11 next to it; the script always
uses 3.11 through the Python launcher (`py -3.11`).

Close all PowerShell windows and open a new one (Start menu → "PowerShell"). Check:

```
py -3.11 --version
git --version
ngrok version
```

You should see `Python 3.11.x`, a git version, and an ngrok version. (`py --list` shows all your
Python versions.)

## Step 2. Connect ngrok to your account (one time)

Log in to https://dashboard.ngrok.com → "Your Authtoken" → copy it. In PowerShell:

```
ngrok config add-authtoken PASTE_YOUR_TOKEN_HERE
```

## Step 3. Get the code (one time)

```
cd $HOME
git clone https://github.com/hamzabilal000/mahsool.ai.git
cd mahsool.ai
```

## Step 4. Allow scripts (one time)

Windows blocks scripts by default. Allow your own scripts:

```
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Type `Y` and press Enter.

## Step 5. Start Mahsool AI

```
cd $HOME\mahsool.ai
.\scripts\run_local.ps1
```

The first time it:
1. makes a Python environment (`.venv`) and installs the libraries (10-20 minutes),
2. installs the search index (1 minute; no 30-minute re-index),
3. asks for your **GROQ_API_KEY**. Paste it and press Enter (the text stays hidden; that is
   normal). It is saved in the file `.env` on your laptop only. Git never uploads it.
4. opens a **second window for ngrok** and starts the backend in this window. The first start
   also downloads the AI models (~3 GB).

It is ready when you see `Application startup complete`. **Keep both windows open.**

Next time, run the same two commands. It skips the installs and just starts.

## Step 6. Check that it works

Open a **new** PowerShell window:

```
cd $HOME\mahsool.ai
.\scripts\run_local.ps1 -Check
```

Good result:

```
backend (local):  OK
public (ngrok):   OK  https://resident-coil-delusion.ngrok-free.dev
```

Then open the website on Vercel and ask a question, for example "What is the tax on bank profit
for a non-filer?".

## Stop

- Press **Ctrl+C** in the backend window.
- Close the **ngrok** window.

The website then shows the "resting" message.

## Update to the newest version

Stop it first (see above). Then:

```
cd $HOME\mahsool.ai
git pull
.\scripts\run_local.ps1
```

The script installs new libraries or a new index by itself when they changed.

## Good to know

- **Sleep:** when the laptop sleeps, the website stops working. Settings → System → Power →
  "When plugged in, put my device to sleep after" → **Never**. Keep the charger connected.
- **Change the Groq key:** open `.env` in Notepad (`notepad .env`), change the `GROQ_API_KEY=` line,
  save, and start again.
- **Daily limit:** the free Groq tier gives about 60 new answers a day for all visitors together,
  and 10 new questions per visitor. Repeated questions come from the cache and are free.
- **Questions and feedback** are saved on your laptop in `data\mahsool.db`.
- **Problems?** Read the backend window for red error text. "Python 3.11 is not installed" →
  install Python 3.11 (Step 1); your other Python can stay. "ngrok is not installed" → Step 1.3. ngrok says "authentication failed"
  → Step 2 again.

## Ubuntu instead of Windows

Install `python3.11 python3.11-venv git` and ngrok (https://ngrok.com/download → Linux), run
`ngrok config add-authtoken YOUR_TOKEN`, clone the repo, then:

```
bash scripts/run_local.sh          # start (first time installs everything)
bash scripts/run_local.sh --check  # check
```

Ctrl+C stops the backend and ngrok together.
