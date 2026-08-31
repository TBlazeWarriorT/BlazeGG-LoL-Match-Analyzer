# 🔥 Blaze GG — League of Legends Match Analyzer

Blaze GG is a local match analysis dashboard for League of Legends powered by the official Riot Games API and DataDragon.

Instead of broad macro summaries, it focuses on lane matchups, damage breakdowns, and detailed post-game duel stats.

---

## Our Unique Features

- **Lane Deaths vs. External Deaths**  
  Separates deaths conceded directly to lane opponent(s) (1v1 or 2v2 bot) from deaths caused by roaming, ganks, or teamfights.

- **Granular Damage Breakdown**  
  Interactive damage pills with hover/pin to view exact physical, magic, and true damage dealt, alongside damage taken, self-mitigated damage, and healing.

- **AI-Ready Match Summary**  
  One-click copy of a structured, factual text summary of the entire match, formatted for pasting directly into LLMs (ChatGPT, Claude) for analysis or coaching.

- **Match Podiums & Multikills**  
  Highlights top performers across key metrics (damage, gold, mitigation) and lists multikills with timestamps and victims.

- **Event Timeline**  
  Chronological feed of match events, including solo kills, objectives, shutdowns, and multikills AND detailed stats at the approx. time of each kill.

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

## 📄 License & Terms (TL;DR)

This project is **Source-Available & Creator-Protected**:
- ✅ **Allowed**: Personal local usage, study, experimentation, and submitting Pull Requests / contributions.
- ❌ **Prohibited**: Public re-hosting, SaaS deployment, forks operated as competing public web services, or commercial use while the official project is active.
- 🔄 **Continuity**: If the official project is permanently shut down and abandoned (no active official service and no repository maintenance for 12+ consecutive months), the license automatically converts to open-source (AGPLv3/MIT) for community continuity.

See the full [LICENSE](LICENSE) for details.

---

## Legal Disclaimer

Blaze GG isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.
