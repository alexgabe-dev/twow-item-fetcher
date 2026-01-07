import os
import requests
import re
import json
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
BASE_URL = "https://database.turtlecraft.gg"
DATA_DIR = "twow_items"
ITEMS_DIR = os.path.join(DATA_DIR, "items")
ICONS_DIR = os.path.join(DATA_DIR, "icons")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

QUALITY_MAP = {
    "0": "Poor", "1": "Common", "2": "Uncommon", 
    "3": "Rare", "4": "Epic", "5": "Legendary"
}

QUALITY_CSS_MAP = {
    "Poor": "q-poor", "Common": "q-common", "Uncommon": "q-uncommon",
    "Rare": "q-rare", "Epic": "q-epic", "Legendary": "q-legendary"
}

STAT_KEYS = {
    "Stamina": "stamina", "Intellect": "intellect", "Strength": "strength",
    "Agility": "agility", "Spirit": "spirit", "Armor": "armor"
}

ZONES = {
    3429: "Ruins of Ahn'Qiraj", 3428: "Temple of Ahn'Qiraj", 2677: "Blackwing Lair",
    2717: "Molten Core", 3456: "Naxxramas", 2437: "Onyxia's Lair", 309: "Zul'Gurub",
    2057: "Scholomance", 2017: "Stratholme", 1584: "Blackrock Depths",
    1583: "Blackrock Spire", 2557: "Dire Maul", 3703: "Lower Karazhan Halls",
    46: "Burning Steppes", 1377: "Silithus", 41: "Deadwind Pass", 618: "Winterspring", 139: "Eastern Plaguelands"
}

# Try loading extended zones
try:
    with open("zones.json", "r", encoding="utf-8") as f:
        extra_zones = json.load(f)
        for zid, zname in extra_zones.items():
            ZONES[int(zid)] = zname
except: pass

ITEM_NAME_CACHE = {}

# Ensure directories exist
os.makedirs(ITEMS_DIR, exist_ok=True)
os.makedirs(ICONS_DIR, exist_ok=True)

def normalize_stat_key(raw_stat):
    if raw_stat in STAT_KEYS: return STAT_KEYS[raw_stat]
    return raw_stat.lower().replace(" ", "_")

def clean_name(text):
    text = text.replace("\\'", "'").replace('\\"', '"')
    if len(text) > 0 and text[0].isdigit(): return text[1:]
    return text

def get_item_name(item_id):
    if item_id in ITEM_NAME_CACHE: return ITEM_NAME_CACHE[item_id]
    url = f"{BASE_URL}/?item={item_id}"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            title = soup.find('title').text.split(' - ')[0]
            clean = clean_name(title)
            ITEM_NAME_CACHE[item_id] = clean
            return clean
    except: pass
    return f"Item {item_id}"

def parse_tooltip_structured(tooltip_div):
    data = {
        "name": None, "quality": "Common", "css_class": "q-common",
        "binding": None, "slot": None, "armor_type": None, "armor_value": None,
        "stats_normalized": {}, "resistances": {}, "effects": [], 
        "set_bonuses": [], "classes": [], "level_req": None, "raw_text": "",
        "requirements": {
            "reputation": None,
            "class_req": [],
            "unique_equipped": False
        }
    }
    if not tooltip_div: return data
    raw_text = tooltip_div.get_text(separator="\n").strip()
    data["raw_text"] = raw_text
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    if not lines: return data
    data["name"] = lines[0]
    
    name_tag = tooltip_div.find('b')
    if name_tag and name_tag.get('class'):
        q_cls = name_tag['class'][0]
        if q_cls.startswith('q'):
             quality_name = QUALITY_MAP.get(q_cls[1:], "Common")
             data["quality"] = quality_name
             data["css_class"] = QUALITY_CSS_MAP.get(quality_name, "q-common")
    i = 1
    while i < len(lines):
        line = lines[i]
        
        # Requirement Parsing
        rep_match = re.search(r"Requires (.+?) - (Neutral|Friendly|Honored|Revered|Exalted)", line)
        if rep_match:
            data["requirements"]["reputation"] = {
                "faction": rep_match.group(1),
                "level": rep_match.group(2)
            }
        
        if line == "Unique-Equipped":
            data["requirements"]["unique_equipped"] = True
            
        if "Binds when" in line or "Soulbound" in line or line == "Unique":
            data["binding"] = line
        elif line in ["Head", "Neck", "Shoulder", "Back", "Chest", "Shirt", "Tabard", "Wrist", "Hands", "Waist", "Legs", "Feet", "Finger", "Trinket", "Main Hand", "Off Hand", "One-Hand", "Two-Hand", "Ranged", "Relic", "Held In Off-hand", "Projectile", "Wand"]:
            data["slot"] = line
            if i+1 < len(lines):
                next_l = lines[i+1]
                if not next_l.startswith("+") and not "Armor" in next_l and not "Damage" in next_l:
                    data["armor_type"] = next_l
                    i += 1
        elif "Armor" in line and line.split()[0].isdigit():
             match = re.search(r"(\d+)\s+Armor", line)
             if match: 
                 val = int(match.group(1))
                 data["armor_value"] = val
                 data["stats_normalized"]["armor"] = val
        elif line.startswith("+") or line.startswith("-"):
            clean_line = line.replace("+", "").replace("-", "")
            parts = clean_line.split(" ", 1)
            if len(parts) == 2:
                try:
                    val = int(parts[0])
                    raw_stat = parts[1]
                    if "Resistance" in raw_stat:
                        data["resistances"][raw_stat.replace(" Resistance", "").lower()] = val
                    else:
                        data["stats_normalized"][normalize_stat_key(raw_stat)] = val
                except: pass
        elif line.startswith("Requires Level"):
            try: data["level_req"] = int(line.split()[-1])
            except: pass
        elif line.startswith("Classes:"):
            data["classes"] = [c.strip() for c in line.replace("Classes:", "").split(",")]
            data["requirements"]["class_req"] = data["classes"]
        elif line.startswith("Equip:") or line.startswith("Use:") or line.startswith("Chance on hit:"):
            effect_type = line.split(":")[0]
            desc = line.replace(effect_type, "").strip()
            if (not desc or desc == ":") and i+1 < len(lines):
                desc = lines[i+1]
                i += 1
            if desc.startswith(":"): desc = desc[1:].strip()
            data["effects"].append({"type": effect_type, "description": desc})
        elif re.match(r"\(\d+\)\s+Set:", line):
            bonus = line
            if i+1 < len(lines) and not lines[i+1].startswith("("):
                 bonus += " " + lines[i+1]
                 i += 1
            data["set_bonuses"].append(bonus)
        i += 1
    return data

def fetch_full_item_data(item_id):
    url = f"{BASE_URL}/?item={item_id}"
    print(f"   (Downloading from {url}...)")
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200: return None
    html = response.text
    soup = BeautifulSoup(html, 'html.parser')
    
    try: item_name = soup.find('title').text.split(' - ')[0]
    except: item_name = "Unknown Item"

    tooltip_div = soup.find('div', class_='tooltip')
    structured_details = parse_tooltip_structured(tooltip_div)
    if structured_details["name"]: item_name = structured_details["name"]

    icon_match = re.search(r"_\[" + str(item_id) + r"\]=\{icon:\s*'([^']+)'\}", html)
    icon_name = icon_match.group(1) if icon_match else "inv_misc_questionmark"

    sources_data = {}
    listview_pattern = r"id:\s*'([a-z-]+)'.*?data:\s*(\[\{.*?\}\])"
    found_lists = re.findall(listview_pattern, html, re.DOTALL)
    
    for list_id, list_data_raw in found_lists:
        objects = re.split(r"\}\s*,\s*\{", list_data_raw)
        cleaned_list = []
        for obj in objects:
            name_m = re.search(r"name:\s*'((?:[^'\\]|\\.)+)'", obj)
            pct_m = re.search(r"percent:\s*(\d+)", obj)
            loc_m = re.search(r"location:\s*\[(\d+)\]", obj)
            reagents_m = re.search(r"reagents:\s*\[(.*?)\]\]", obj)
            
            if name_m:
                raw_name = clean_name(name_m.group(1))
                if raw_name.startswith("@"): raw_name = raw_name[1:]
                
                entry = {"name": raw_name}
                if pct_m: entry["drop_rate"] = f"{pct_m.group(1)}%"
                if loc_m:
                    zid = int(loc_m.group(1))
                    entry["zone_id"] = zid
                    entry["zone_name"] = ZONES.get(zid, f"Zone {zid}")
                
                if reagents_m:
                    pairs = re.findall(r"\[(\d+),\s*(\d+)\]", reagents_m.group(1))
                    reagent_list = []
                    if pairs:
                        print(f"      (Resolving {len(pairs)} reagent names...)")
                        for r_id, r_count in pairs:
                            r_name = get_item_name(int(r_id))
                            reagent_list.append({
                                "id": int(r_id),
                                "name": r_name,
                                "count": int(r_count)
                            })
                    entry["reagents"] = reagent_list
                    
                cleaned_list.append(entry)
        sources_data[list_id.replace('-', '_')] = cleaned_list

    return {
        "id": item_id, "name": item_name, "icon": icon_name,
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "details": structured_details, "sources": sources_data
    }

def search_items_only(query):
    print(f"🔎 Searching for items named '{query}'...")
    response = requests.get(BASE_URL, params={'search': query}, headers=HEADERS)
    if "item=" in response.url:
        item_id = response.url.split('item=')[1]
        return [{"id": item_id, "name": "Direct Match", "is_direct": True}]
    items_block_match = re.search(r"id:\s*'items'.*?data:\s*(\[\{.*?\}\])", response.text, re.DOTALL)
    results = []
    if items_block_match:
        objects = re.split(r"\}\s*,\s*\{", items_block_match.group(1))
        for obj in objects:
            id_m = re.search(r"id:\s*(\d+)", obj)
            name_m = re.search(r"name:\s*'((?:[^'\\]|\\.)+)'", obj)
            qual_m = re.search(r"quality:\s*(\d+)", obj)
            if id_m and name_m:
                results.append({
                    "id": int(id_m.group(1)),
                    "name": clean_name(name_m.group(1)),
                    "quality": qual_m.group(1) if qual_m else "1",
                    "is_direct": False
                })
    return results

def save_item_to_disk(data):
    # Updated structure: items/{id}.json and icons/{icon}.png
    item_path = os.path.join(ITEMS_DIR, f"{data['id']}.json")
    
    # Check freshness
    if os.path.exists(item_path):
        with open(item_path, 'r', encoding='utf-8') as f:
            old_data = json.load(f)
            last_up = old_data.get('last_updated', '2000-01-01 00:00:00')
            last_date = datetime.strptime(last_up, "%Y-%m-%d %H:%M:%S")
            if datetime.now() - last_date < timedelta(days=30):
                print(f"⚠️  Data for {data['name']} is fresh (updated {last_up}).")
                # Optional: return here to skip overwrite, but we'll overwrite for now
    
    with open(item_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
        
    icon_filename = f"{data['icon'].lower()}.png"
    icon_path = os.path.join(ICONS_DIR, icon_filename)
    if not os.path.exists(icon_path):
        icon_url = f"{BASE_URL}/images/icons/large/{icon_filename}"
        with open(icon_path, 'wb') as f:
            f.write(requests.get(icon_url, headers=HEADERS).content)
            
    print(f"✅ Saved to: {item_path}")

def display_and_save(item_id, display_name_hint):
    print(f"\n🔄 Fetching: {display_name_hint}...")
    full_data = fetch_full_item_data(item_id)
    details = full_data['details']
    print("-" * 40)
    print(f"📜 {details['name']} ({details['quality']})")
    print(f"   {details['slot'] or ''} {details['armor_type'] or ''}")
    if details['stats_normalized']: print(f"   Stats: {details['stats_normalized']}")
    print("-" * 40)
    if full_data['sources'].get('dropped_by'):
         d = full_data['sources']['dropped_by'][0]
         zone_str = f" in {d['zone_name']}" if 'zone_name' in d else ""
         print(f"⚔️  Drops from: {d['name']}{zone_str} ({d.get('drop_rate','?')})")
    elif full_data['sources'].get('created_by'):
         c = full_data['sources']['created_by'][0]
         print(f"⚒️  Created by: {c['name']}")
         if 'reagents' in c and c['reagents']:
             print("   Reagents: " + ", ".join([f"{r['count']}x {r['name']}" for r in c['reagents']]))
    elif full_data['sources'].get('sold_by'):
         print(f"💰 Sold by: {full_data['sources']['sold_by'][0]['name']}")
    elif full_data['sources'].get('reward_from_quest'):
         print(f"📜 Quest Reward: {full_data['sources']['reward_from_quest'][0]['name']}")

    action = input("\n[1] Download  |  [Enter] Cancel: ")
    if action == '1': save_item_to_disk(full_data)

def bulk_fetch():
    print("\n📦 BULK FETCH MODE")
    print("Paste your list of item names below.")
    print("Enter 'END' on a new line to start processing.")
    print("-" * 40)
    
    item_names = []
    while True:
        line = input().strip()
        if line == "END": break
        if line: item_names.append(line)
        
    print(f"\n🚀 Processing {len(item_names)} items...")
    
    for name in item_names:
        print(f"\n🔎 Looking for: {name}")
        results = search_items_only(name)
        
        target_item = None
        
        # 1. Check for exact name match (case-insensitive)
        for res in results:
            if res['name'].lower() == name.lower():
                target_item = res
                break
        
        # 2. If no exact match, but only one result found
        if not target_item and len(results) == 1:
            target_item = results[0]
            
        if target_item:
            print(f"   ✅ Found: {target_item['name']} (ID: {target_item['id']})")
            full_data = fetch_full_item_data(target_item['id'])
            if full_data:
                save_item_to_disk(full_data)
            else:
                print("   ❌ Failed to download data.")
        else:
            if not results:
                print("   ❌ No results found.")
            else:
                print(f"   ⚠️  Ambiguous results ({len(results)} found). Skipping.")

def main():
    while True:
        print("\n" + "="*40)
        print("🐢 TURTLE FORGE ITEM SEARCHER")
        print("="*40)
        print("[1] Search Item")
        print("[2] Bulk Download (Paste List)")
        print("[q] Quit")
        
        choice = input("\nSelect option: ").strip().lower()
        
        if choice == 'q': break
        elif choice == '2':
            bulk_fetch()
            continue
        elif choice == '1':
            pass # Continue to search logic below
        else:
            continue

        query = input("Enter item name (or 'b' to back): ").strip()
        if query.lower() == 'b': continue
        if len(query) < 2: continue
        results = search_items_only(query)
        if not results:
            print("❌ No ITEMS found."); continue
        if len(results) == 1 and results[0].get('is_direct'):
            print(f"🎯 Direct Match Found! ID: {results[0]['id']}")
            display_and_save(results[0]['id'], "Direct Match"); continue 
        
        page, items_per_page, total_items = 0, 20, len(results)
        while True:
            start_idx = page * items_per_page
            end_idx = min(start_idx + items_per_page, total_items)
            print(f"\nFound {total_items} ITEMS (Showing {start_idx+1}-{end_idx}):")
            for i in range(start_idx, end_idx):
                item = results[i]
                q_lbl = QUALITY_MAP.get(item['quality'], "Common")
                print(f"[{i+1}] {item['name']} ({q_lbl}) - ID: {item['id']}")
            if end_idx < total_items: print(f"[n] Next Page ({total_items - end_idx} more)")
            if page > 0: print(f"[p] Previous Page")
            
            sel = input("\nSelect number, (n)ext, (p)rev, or (b)ack to search: ").strip().lower()
            if sel == 'b': break 
            elif sel == 'n' and end_idx < total_items: page += 1; continue
            elif sel == 'p' and page > 0: page -= 1; continue
            if not sel.isdigit(): continue
            idx = int(sel) - 1
            if 0 <= idx < total_items: display_and_save(results[idx]['id'], results[idx]['name'])

if __name__ == "__main__":
    main()