import json
from collections import defaultdict

def process_word_frequencies(input_filename="word_statistics.json"):
    """
    Processes a JSON file containing word frequencies, aggregates them by agency and title,
    and ensures all words are present for each year with summed frequencies.
    Saves the results to two new JSON files.

    Args:
        input_filename (str): The name of the input JSON file.
    """

    try:
        with open(input_filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file '{input_filename}'.")
        return

    agency_word_counts = defaultdict(lambda: {"agency_dn": "", "years": defaultdict(lambda: defaultdict(int))})
    title_word_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    all_words = set()
    all_years_agency = defaultdict(set) # To track years per agency
    all_years_title = defaultdict(set)  # To track years per title

    # 1. Collect all unique words and years
    for record in data:
        agency = record.get("agency")
        title = record.get("title")
        version_date_str = record.get("versionDate")
        word_frequencies = record.get("wordFrequencies", {})
        if word_frequencies:
            all_words.update(word_frequencies.keys())
        if agency and version_date_str:
            year = version_date_str[:4]
            all_years_agency[agency].add(year)
        if title and version_date_str:
            year = version_date_str[:4]
            all_years_title[title].add(year)

    # 2. Initialize output structures with all words for each year
    for agency in all_years_agency:
        for year in all_years_agency[agency]:
            for word in all_words:
                agency_word_counts[agency]["years"][year][word] = 0 # Initialize to 0
    for title in all_years_title:
        for year in all_years_title[title]:
            for word in all_words:
                title_word_counts[title][year][word] = 0 # Initialize to 0


    # 3. Sum up word frequencies from input data
    for record in data:
        agency = record.get("agency")
        agency_dn = record.get("agency_dn")
        title = record.get("title")
        version_date_str = record.get("versionDate")
        word_frequencies = record.get("wordFrequencies", {})

        if agency and version_date_str and word_frequencies:
            year = version_date_str[:4]
            agency_word_counts[agency]["agency_dn"] = agency_dn if agency_dn else agency_word_counts[agency]["agency_dn"]
            for word, count in word_frequencies.items():
                agency_word_counts[agency]["years"][year][word] += count

        if title and version_date_str and word_frequencies:
            year = version_date_str[:4]
            for word, count in word_frequencies.items():
                title_word_counts[title][year][word] += count

    # 4. Convert defaultdict to dict for JSON serialization
    agency_output = {agency: {"agency_dn": data["agency_dn"], "years": dict(data["years"])} for agency, data in agency_word_counts.items()}
    title_output = {title: dict(years) for title, years in title_word_counts.items()}


    with open("agency_word_frequencies.json", 'w') as agency_file:
        json.dump(agency_output, agency_file, indent=2)
    print("Agency word frequencies saved to 'agency_word_frequencies.json'")

    with open("title_word_frequencies.json", 'w') as title_file:
        json.dump(title_output, title_file, indent=2)
    print("Title word frequencies saved to 'title_word_frequencies.json'")

if __name__ == "__main__":
    process_word_frequencies()
