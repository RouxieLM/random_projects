from urllib.request import Request, urlopen
import os, time, json, random, re

# === Constants for URLs and file paths ===
MAIN_SECTIONS_URL = "https://gate.skin.club/apiv2/main-sections"
ODDS_URL = "https://gate.skin.club/apiv2/odds/"
HEADERS = {'User-Agent': 'Mozilla/5.0'}  # Required to mimic a browser request
CACHE_TIME_HOURS = 2  # How long to cache downloaded data before refreshing

# === Constants for filtering specific test case and simulation ===
TESTED_SECTION = "Crazy Moves"
TESTED_CASE = "Who\u2019s crazy?"
TESTED_CASE_COUNT = 1000

# === Dynamic filenames based on case and section ===
safe_case = re.sub(r'\W+', '_', TESTED_CASE.lower())
safe_section = re.sub(r'\W+', '_', TESTED_SECTION.lower())

MAIN_SECTIONS_FILE = f"data/main_sections.json"
ODDS_FILE = f"data/odds_{safe_case}.json"
FILTERED_ODDS_FILE = f"data/filtered_odds_{safe_case}.json"
RESULTS_FILE = f"results/results_{safe_case}.txt"

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
    # Ensure results folder exists
    os.makedirs("results", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    # -- Step 1: Download or reuse cached main_sections file
    if os.path.exists(MAIN_SECTIONS_FILE):
        mtime_in_hours = check_file_mtime(MAIN_SECTIONS_FILE)
        if mtime_in_hours > CACHE_TIME_HOURS:
            request_json(MAIN_SECTIONS_URL, MAIN_SECTIONS_FILE)
        else:
            print(MAIN_SECTIONS_FILE, "has been updated within the last 2 hours, skipping request to skin.club API\n")
    else:
        request_json(MAIN_SECTIONS_URL, MAIN_SECTIONS_FILE)

    # -- Step 2: Extract UID and case price for the specific test case
    with open(MAIN_SECTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    found_uid = None
    for section in data.get("data"):
        if section.get("name") == TESTED_SECTION:
            for case in section.get("cases"):
                if case.get("title") == TESTED_CASE:
                    found_uid = case.get("last_successful_generation").get("uid")
                    case_price = case.get("price")
                    break

    formatted_case_price = float(f"{case_price / 100:.2f}")

    # -- Step 3: Build odds URL using the found UID
    odds_url = f"{ODDS_URL}{found_uid}/contents"

    # -- Step 4: Download or reuse cached odds file
    if os.path.exists(ODDS_FILE):
        mtime_in_hours = check_file_mtime(ODDS_FILE)
        if mtime_in_hours > CACHE_TIME_HOURS:
            request_json(odds_url, ODDS_FILE)
        else:
            print(ODDS_FILE, "has been updated within the last 2 hours, skipping request to skin.club API\n")
    else:
        request_json(odds_url, ODDS_FILE)

    # -- Step 5: Parse and clean odds data
    with open(ODDS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    filtered_odds_json = {}
    for item in data["data"]:
        raw_name = item["item"]["market_hash_name"]
        price = item["fixed_price"]
        chance = float(item["chance_percent"])

        # Strip special characters and emojis
        clean_name = raw_name.encode("ascii", "ignore").decode().strip()
        formatted_price = float(f"{price / 100:.2f}")

        filtered_odds_json[clean_name] = {
            "price": formatted_price,
            "chance": chance
        }

    # -- Step 6: Save cleaned odds to file
    with open(FILTERED_ODDS_FILE, "w", encoding="utf-8") as f:
        json.dump(filtered_odds_json, f, indent=2)

    # -- Step 7: Prepare lists for simulation
    items_list = []
    chances_list = []
    for item in filtered_odds_json:
        items_list.append(item)
        chances_list.append(filtered_odds_json[item]["chance"])

    # -- Step 8: Run simulation and track profit
    results_list = []
    profitable_drops_list = []
    for _ in range(TESTED_CASE_COUNT):
        result = random.choices(items_list, weights=chances_list, k=1)[0]
        results_list.append(result)
        if filtered_odds_json[result]["price"] > formatted_case_price:
            profitable_drops_list.append(result)

    # -- Step 9: Save results
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results_list, f, indent=2)

    profit = 0
    for item in results_list:
        profit += filtered_odds_json[item]["price"]
    spendings = formatted_case_price * TESTED_CASE_COUNT

    expected_return = 0
    for item, data_entry in filtered_odds_json.items():
        expected_return += (data_entry["chance"] / 100) * data_entry["price"]

    expected_profit = expected_return - formatted_case_price
    return_ratio = (expected_return / formatted_case_price) * 100

    results_data = {
        "summary": {
            "cases_opened": TESTED_CASE_COUNT,
            "case_name": TESTED_CASE,
            "case_price": formatted_case_price,
            "total_spent": round(spendings, 2),
            "total_earned": round(profit, 2),
            "net_profit": round(profit - spendings, 2),
            "expected_return": round(expected_return, 2),
            "expected_profit": round(expected_profit, 2),
            "return_ratio_percent": round(return_ratio, 2)
        },
        "drops": results_list
    }

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results_data, f, indent=2)

    # -- Step 10: Print simulation results
    print("You opened", TESTED_CASE_COUNT, TESTED_CASE, "cases.")
    print("You spent", float(f"{spendings:.2f}"), "$")
    print("You earned", float(f"{profit:.2f}"), "$\n")
    print("Profits:", f"{profit - spendings:.2f}", "$\n")

    print(f"\nExpected return per '{TESTED_CASE}' case: {expected_return:.2f} $")
    print(f"Expected profit per case: {expected_profit:.2f} $")
    print(f"Return ratio: {return_ratio:.2f}%\n")

# === Run the script ===
if __name__ == "__main__":
    main()
