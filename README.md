# Blaze GG — League of Legends Match Analyzer

Blaze GG is a local match analysis dashboard for League of Legends powered by the official Riot Games API and DataDragon.

Instead of broad macro summaries, it focuses on lane matchups, damage breakdowns, and detailed post-game duel stats.

---

## Key Differentiators

- **Lane Deaths vs. External Deaths**: Separates deaths conceded directly to lane opponent(s) (1v1 or 2v2 bot) from deaths caused by roaming, ganks, or teamfights.
- **Granular Damage Breakdown**: Interactive damage pills with hover/pin to view exact physical, magic, and true damage dealt, alongside damage taken, self-mitigated damage, and healing.
- **AI-Ready Match Summary**: One-click copy of a structured, factual text summary of the entire match, formatted for pasting directly into LLMs (ChatGPT, Claude) for analysis or coaching.
- **Match Podiums & Multikills**: Highlights top performers across key metrics (damage, gold, mitigation) and lists multikills with timestamps and victims.

---

## Features

- **Head-to-Head Lane Matchups**: Direct Blue vs. Red comparisons per role (Top, Jungle, Mid, Bot, Support) with 5m/10m/15m/20m gold and level deltas.
- **Bot Lane Duo View**: Combined 2v2 dueling stats for ADC + Support.
- **Event Timeline**: Chronological feed of match events (solo kills, objectives, shutdowns, multikills).
- **Language Switcher**: Instant switching between English (US) and Portuguese (BR).
- **Local Cache**: Match data is cached locally as JSON for instant reloading.

---

## Setup & Running

### 1. Requirements
- Python 3.10+
- A Riot Games API Key from the [Riot Developer Portal](https://developer.riotgames.com/)

### 2. Installation
```bash
git clone https://github.com/your-username/lol-api-analyzer.git
cd lol-api-analyzer
pip install -r requirements.txt
```

### 3. Running the App
On Windows:
```bash
start_hub.bat
```

Or run directly with Python:
```bash
python app.py
```

Then open `http://localhost:8000` in your browser. You can paste your Riot API key directly into the settings on the web interface.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Legal Disclaimer

Blaze GG isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.