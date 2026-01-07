# 🐢 Turtle Forge Item Searcher

A powerful command-line tool for fetching, parsing, and archiving item data from the **Turtle WoW Database**. 

Built for developers and data hoarders who need structured JSON data and icons for items from the Turtle WoW expansion.

## ✨ Features

- **🔍 Interactive Search**: Search for items directly from your terminal.
- **📄 Structured Data**: Scrapes and parses raw HTML into clean, usable JSON.
  - Extracts stats, armor, weapon speeds, and damage.
  - Parses complex tooltips (Set bonuses, "Chance on hit", Class requirements).
  - Resolves item sources (Drops, Crafting recipes + Reagents, Vendors, Quests).
- **🖼️ Asset Downloading**: Automatically downloads high-quality item icons.
- **📂 Local Caching**: Saves data to a structured local directory (`twow_items/`) to avoid re-fetching.
- **⚡ Smart Parsing**: Normalizes stat names and quality levels for consistent consumption by other apps.

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- Internet connection (to reach `database.turtlecraft.gg`)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/twowdb.git
   cd twowdb
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## 🛠️ Usage

Run the fetcher script:

```bash
python twowdb-fetch.py
```

1. **Enter an item name** (e.g., "Thunderfury").
2. **Browse the list** of results and select the one you want.
3. **Preview** the item details in the console.
4. **Press `1`** to download the JSON data and icon.

## 📂 Data Structure

Downloaded data is organized in the `twow_items` directory:

```text
twow_items/
├── items/           # JSON files named by Item ID (e.g., 19019.json)
└── icons/           # PNG images named by icon name (e.g., inv_sword_39.png)
```

### Example JSON Output
```json
{
    "id": 19019,
    "name": "Thunderfury, Blessed Blade of the Windseeker",
    "quality": "Legendary",
    "details": {
        "slot": "One-Hand",
        "stats_normalized": {
            "agility": 5,
            "stamina": 8
        },
        "effects": [
            {
                "type": "Chance on hit",
                "description": "Blasts your enemy with lightning..."
            }
        ]
    },
    "sources": {
        "reward_from_quest": [ ... ]
    }
}
```

## ⚠️ Disclaimer

This tool is an unofficial scraper for educational and personal use. Please respect the bandwidth of `database.turtlecraft.gg` and do not use this tool to aggressively hammer their servers.

---
*Happy looting!* 🐢

**Made by Alex Gabe**
