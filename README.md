# Aura AI Assistant

<div align="center">
  <h1>Aura AI Assistant</h1>
  <p><strong>Personal Intelligent Desktop AI Assistant for Kalai</strong></p>
  <p>Voice-First Automation · Contextual Intelligence · Desktop Workflows</p>
</div>

---

## 🌟 Overview

**Aura** is a premium Windows desktop AI assistant crafted for **Kalai**. It pairs hands-free voice control with system automation, document authoring, browser automation, and multi-model AI reasoning.

## ✨ Features

- 🎙️ **Voice-First AI & Live Streaming**:
  - Wake words: *"Hey Aura"*, *"Aura"*, *"Ok Aura"*, *"Hello"*
  - High-speed microphone streaming with instant interruption (barge-in)
  - Edge-TTS natural voice output
- 🧠 **Dual AI Engine**:
  - Google Gemini 2.5 Flash native live audio preview & content generation
  - OpenRouter fallback (LLaMA 3.3, Nemotron, Qwen, MiniMax)
- 🖥️ **Windows Desktop Automation**:
  - Open applications (*"Open Chrome"*, *"Launch Spotify"*, *"Open Edge"*)
  - Control volume, mute, display brightness
  - Process monitor & RAM hog detection (*"Who is eating my RAM?"*, *"Kill process"*)
- 🌐 **Full Browser Automation**:
  - Playwright automated navigation, form-filling, clicking, screenshots, and web search
- 📄 **Autonomous Document Generation**:
  - Presentation generation (`.pptx`) with custom themes
  - Excel workbook & budget spreadsheets (`.xlsx`)
  - Word documents (`.docx`) & PDF creation
- 📁 **Smart Desktop Organizer**:
  - Declutters Desktop & Downloads folders into organized categories with 1-click rollback
- 📱 **Mobile Connect & Remote Control**:
  - QR Code mobile pairing via local WebSocket gateway
- 🛡️ **Self-Healing Code Engine**:
  - AST safety sandbox with Boot Sentry to automatically recover from errors

---

## 🚀 How to Launch Aura

### Option 1: Desktop Shortcut
Double-click the **Aura AI** shortcut on your Desktop.

### Option 2: Quick Batch Script
Run `start_aura.bat` in `D:\Kalai\Assistant`:
```cmd
D:\Kalai\Assistant\start_aura.bat
```

### Option 3: Terminal Command
```powershell
cd D:\Kalai\Assistant
python main.py
```

---

## ⚙️ Configuration

- **Identity**: `config/identity.json`
  - Assistant: **Aura**
  - Owner: **Kalai**
- **API Keys**: Managed automatically in `AppData\Local\AuraAI\config\api_keys.json` (Gemini & OpenRouter pre-configured)
