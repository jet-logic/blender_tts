# Blender VSE Text-to-Speech Narration Add-on

Generate voiceover narration from **text strips** directly in the **Video Sequence Editor (VSE)** — no external tools needed.

🔊 Offline TTS | 🔄 Auto-sync | 🧹 Cleanup | 💾 Cached audio

## Features

- Generate narration via `pyttsx3`
- Unique ID links text to audio
- Auto-save to `~/.cache/blender_narrations`
- Refresh narration after editing text
- Cleanup unused audio files
- Copy audio path to clipboard

---

### 🐧 Linux Users: Additional Step

Make sure you have `espeak` installed:

```bash
sudo apt install espeak libespeak1
```

## 🔧 Installation: Required Dependency

This add-on uses **text-to-speech (TTS)** via the `pyttsx3` library, which is **not bundled with Blender**. You must install it once into Blender’s Python environment.

### Option 1: Install from Blender’s Scripting Tab (Easiest)

1. Open Blender
2. Go to the **Scripting** workspace
3. In the **Python Console**, paste and run this code:

```python
import subprocess
import sys

# Install pyttsx3
subprocess.run([sys.executable, "-m", "pip", "install", "pyttsx3"])
```

### Option 2: Command Line (Advanced)

If you prefer the terminal, run this command (adjust path to your Blender version):

#### Linux/macOS:

```bash
/path/to/blender/4.0/python/bin/python3.10 -m pip install pyttsx3
```

#### Windows:

```cmd
"C:\Program Files\Blender Foundation\Blender 4.0\4.0\python\bin\python.exe" -m pip install pyttsx3
```

> 💡 Tip: Replace `4.0` with your Blender version.

---

### Option 3: Use `--python-expr` to Install `pyttsx3`

#### 🔧 Command (One-Liner)

```bash
blender --background --python-expr "import subprocess, sys; subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyttsx3'])"
```

#### 💡 Breakdown

| Part                  | Purpose                                               |
| --------------------- | ----------------------------------------------------- |
| `blender`             | Calls Blender (must be in `PATH`, or use full path)   |
| `--background`        | Runs without opening UI                               |
| `--python-expr "..."` | Executes the Python code inside Blender's environment |
| `sys.executable`      | Points to **Blender’s Python**, not system Python     |
| `pip install pyttsx3` | Installs the package into Blender’s Python            |

---

### 🖥️ OS-Specific Tips

#### 1. **If `blender` is in your PATH** (Linux/macOS/Windows with setup)

```bash
blender --background --python-expr "import subprocess, sys; subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyttsx3'])"
```

#### 2. **If not in PATH — Use Full Path**

##### 🖥️ Windows

```cmd
"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe" --background --python-expr "import subprocess, sys; subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyttsx3'])"
```

##### 🍏 macOS

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background --python-expr "import subprocess, sys; subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyttsx3'])"
```

##### 🐧 Linux (installed via package)

```bash
blender --background --python-expr "import subprocess, sys; subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyttsx3'])"
```

Or if using a downloaded version:

```bash
~/blender-4.0-linux-x64/blender --background --python-expr "import subprocess, sys; subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyttsx3'])"
```

---

### ✅ Verify It Worked

Run this command to test:

```bash
blender --background --python-expr "import pyttsx3; print('✅ pyttsx3 installed successfully!')"
```

If you see the success message — you're good!
