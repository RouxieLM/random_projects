from urllib.request import Request, urlopen
import os, time, json, random, re

# === Constants for URLs and file paths ===
MAIN_SECTIONS_URL = "https://gate.skin.club/apiv2/main-sections"
ODDS_URL = "https://gate.skin.club/apiv2/odds/"
HEADERS = {'User-Agent': 'Mozilla/5.0'}  # Required to mimic a browser request
MAIN_SECTIONS_FILE = "main_sections.json"
ODDS_FILE = "odds.json"
FILTERED_ODDS_FILE = "filtered_odds.json"
CACHE_TIME_HOURS = 2  # How long to cache downloaded data before refreshing
RESULTS_FILE = "results.txt"

# === Constants for filtering specific test case and simulation ===
TESTED_SECTION = "By type"
TESTED_CASE = "M9 Bayonet Knives"
TESTED_CASE_COUNT = 10000

# === Helper: check how old a cached file is ===
def check_file_mtime(file):
    now = time.time()
    file_mtime = os.stat(file).st_mtime
    mtime_in_hours = (now - file_mtime) / 3600
    return mtime_in_hours

# === Helper: request JSON data from a URL and save it to a file ===
def request_json(url, file):
    req = Request(url, headers=HEADERS)
    with urlopen(req) as response:
        json_data = json.load(response)
    with open(file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)

# === Main logic ===
def main():
    # -- Step 1: Check if main_sections.json is cached and fresh
    if os.path.exists(MAIN_SECTIONS_FILE):
        mtime_in_hours = check_file_mtime(MAIN_SECTIONS_FILE)
        if mtime_in_hours > CACHE_TIME_HOURS:
            request_json(MAIN_SECTIONS_URL, MAIN_SECTIONS_FILE)
        else:
            print(MAIN_SECTIONS_FILE, "has been updated within the last 2 hours, skipping request to skin.club API\n")
    else:
        request_json(MAIN_SECTIONS_URL, MAIN_SECTIONS_FILE)

    # -- Step 2: Load JSON and find UID for the test case
    with open(MAIN_SECTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    found_uid = None
    for section in data.get("data"):
        if section.get("name") == TESTED_SECTION:
            for case in section.get("cases"):
                if case.get("title") == TESTED_CASE:
                    # Get the UID needed to request the odds for this specific case
                    found_uid = case.get("last_successful_generation").get("uid")
                    break

    # -- Step 3: Build the odds URL from the UID
    odds_url = f"{ODDS_URL}{found_uid}/contents"

    # -- Step 4: Download or skip odds file depending on cache freshness
    if os.path.exists(ODDS_FILE):
        mtime_in_hours = check_file_mtime(ODDS_FILE)
        if mtime_in_hours > CACHE_TIME_HOURS:
            request_json(odds_url, ODDS_FILE)
        else:
            print(ODDS_FILE, "has been updated within the last 2 hours, skipping request to skin.club API\n")
    else:
        request_json(odds_url, ODDS_FILE)

    # -- Step 5: Parse odds JSON and clean item names
    with open(ODDS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    filtered_odds_json = {}
    for item in data["data"]:
        raw_name = item["item"]["market_hash_name"]
        chance = float(item["chance_percent"])

        # Clean item names to avoid unicode/emoji issues (e.g., "★ M9 Bayonet")
        clean_name = raw_name.encode("ascii", "ignore").decode().strip()

        filtered_odds_json[clean_name] = chance

    # -- Step 6: Save cleaned odds to a separate JSON file
    with open(FILTERED_ODDS_FILE, "w", encoding="utf-8") as f:
        json.dump(filtered_odds_json, f, indent=2)

    # -- Step 7: Load cleaned data and prepare for simulation
    with open(FILTERED_ODDS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    items_list = []
    chances_list = []
    for item in data:
        items_list.append(item)
        chances_list.append(data.get(item))

    # -- Step 8: Simulate TESTED_CASE_COUNT number of case openings
    results_list = []
    i = 0
    for _ in range(TESTED_CASE_COUNT):
        result = random.choices(items_list, weights=chances_list, k=1)[0]
        if re.search(r"M9", result):  # Filter for knife drops
            i += 1
            results_list.append(result)

    # -- Step 9: Save all knife drops to results file
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results_list, f, indent=2)

    # -- Step 10: Print knife drop rate
    drop_rate = (i / TESTED_CASE_COUNT) * 100
    print("Chances of dropping a knife, tested on", TESTED_CASE_COUNT, "cases:", drop_rate, "%")

# === Run the script ===
if __name__ == "__main__":
    main()
