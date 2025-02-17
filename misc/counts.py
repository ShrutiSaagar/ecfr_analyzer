import json

def process_json_file(input_filename="year_agency_top_words.json"):
    """
    Reads a JSON file, processes it to extract monthly/yearly word counts and top 10 words,
    and returns two JSON strings.

    Args:
        input_filename (str): The name of the input JSON file.

    Returns:
        tuple: A tuple containing two JSON strings:
               - JSON with monthly and yearly word counts.
               - JSON with top 10 words for each agency in each year.
    """

    try:
        with open(input_filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        return "Error: Input file not found.", "Error: Input file not found."
    except json.JSONDecodeError:
        return "Error: Invalid JSON format in input file.", "Error: Invalid JSON format in input file."

    monthly_yearly_counts_data = {}
    top_10_words_data = {}

    for year, year_data in data.items():
        monthly_yearly_counts_data[year] = {}
        top_10_words_data[year] = {}
        for agency, agency_data in year_data.items():
            monthly_yearly_counts_data[year][agency] = {
                "monthly_word_counts": agency_data.get("monthly_word_counts", {}),
                "yearly_word_count": agency_data.get("yearly_word_count", 0)
            }

            top_words = agency_data.get("top_words", {})
            sorted_top_words = sorted(top_words.items(), key=lambda item: item[1], reverse=True)
            top_10_words_dict = dict(sorted_top_words[:10]) # Take top 10 or fewer if less than 10 words
            top_10_words_data[year][agency] = {
                "top_10_words": top_10_words_dict
            }

    monthly_yearly_counts_json = json.dumps(monthly_yearly_counts_data, indent=2)
    top_10_words_json = json.dumps(top_10_words_data, indent=2)

    return monthly_yearly_counts_json, top_10_words_json

if __name__ == "__main__":
    monthly_yearly_json, top_10_words_json = process_json_file()

    if "Error:" in monthly_yearly_json:
        print(monthly_yearly_json)
    else:
        with open("monthly_yearly_counts.json", "w") as f:
            f.write(monthly_yearly_json)
        with open("top_10_words.json", "w") as f:
            f.write(top_10_words_json)
        print("JSON files have been saved successfully.")

    if "Error:" in monthly_yearly_json:
        print(monthly_yearly_json)
    else:
        print("Monthly and Yearly Word Counts JSON:")
        print(monthly_yearly_json)
        print("\nTop 10 Words JSON:")
        print(top_10_words_json)
