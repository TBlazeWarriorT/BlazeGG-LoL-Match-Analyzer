# 🔥 Blaze GG — LoL Head-to-Head Duel Analytics

Blaze GG is an analytical tool and local web dashboard for **League of Legends** matches powered directly by the official **Riot Games API** and **DataDragon**.

It focuses on granular head-to-head lane comparisons, dynamic duel deltas, jungle objective control, interactive match timelines, and LLM-ready prompt data.

---

## ✨ Features

- **⚔️ Head-to-Head Lane Dueling**:
  - Direct 1v1 comparisons per role (Top, Jungle, Mid, ADC, Support).
  - 2v2 Bot Duo combined analysis and 5v5 Total Team overview.
  - Visual gold delta share bars and gap badges (GAP! 🔥).
- **🏆 Match Podiums & Awards**:
  - Highlights top damage dealers, highest gold earners, damage sponges, MVP visionaries, and jungle thieves.
- **⚡ Multikill Breakdown**:
  - Chronological badges for Triple Kills, Quadra Kills, and Pentakills with victim avatars.
- **⏱️ Interactive Event Timeline**:
  - Filterable match timeline with expandable key moments (Solo kills, objectives, shutdowns, multikills).
- **🌐 Internationalization (i18n)**:
  - Native runtime language switching between **English (en_US)** and **Português (pt_BR)**.
- **🤖 LLM Ready Prompt Box**:
  - One-click copy raw summary prompt structured specifically for LLMs (ChatGPT, Claude, Gemini).
- **🚀 Local Web Hub & Offline Cache**:
  - Fast search with cached match browsing and low-latency rendering.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.10+ (Built-in standard library HTTP server, Threading, Urllib)
- **Frontend**: Pure modern CSS3 (Custom Dark Theme, Flexbox, CSS Grid) & Vanilla JavaScript
- **API & Data**: Official Riot Games API (Match-V5, Account-V1, Summoner-V4) & DataDragon

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10 or higher
- A Riot Games API Key from the [Riot Developer Portal](https://developer.riotgames.com/)

### 2. Installation
Clone the repository and install dependencies:
`ash
git clone https://github.com/your-username/lol-api-analyzer.git
cd lol-api-analyzer
pip install -r requirements.txt
`

### 3. Environment Configuration
Copy .env.example to .env and insert your Riot API key:
`ini
RIOT_API_KEY=RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
DEFAULT_ROUTING=americas
DEFAULT_REGION=br1
`
*(Alternatively, you can paste the API key directly into the Web Hub interface on first launch)*

### 4. Running the Web Hub
Start the local dashboard server:
`ash
# Windows Launcher:
start_hub.bat

# Or using Python:
python app.py
`
Open your browser at [http://localhost:8000](http://localhost:8000).

---

## 📁 Project Structure

`	ext
lol-api-analyzer/
├── app.py                 # Local Web Hub & server entrypoint
├── main.py                # CLI interactive analyzer
├── start_hub.bat          # 1-Click launcher for Windows
├── requirements.txt       # Python dependencies
├── scripts/               # Helper utilities
│   ├── view_last_match.py
│   ├── inspect_timeframe.py
│   └── download_match.py
└── src/
    ├── config.py          # Environment settings & cache paths
    ├── riot_client.py     # Riot Games API client & rate-limiting
    ├── ddragon.py         # DataDragon asset resolver
    ├── event_engine.py    # Match timeline parsing & metrics calculation
    ├── cache_manager.py   # Match JSON storage & local cache management
    ├── i18n.py            # Multilingual dictionary translations
    ├── html_report.py     # Report builder & orchestrator
    ├── report_components/ # Modular HTML renderers (duels, awards, timeline)
    └── static/            # Static styles & client-side scripts
        ├── css/
        │   ├── hub.css
        │   └── report.css
        └── js/
            └── report.js
`

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

## ⚖️ Legal Disclaimer

Blaze GG isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.