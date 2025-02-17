import json

def restructure_data_option2_from_json(filepath):
    """
    Reads data from a JSON file in the original format and restructures it
    into Option 2 data format.

    Args:
        filepath (str): The path to the JSON file.

    Returns:
        list or None: A list of dictionaries in Option 2 format, or None if
                      the file is not found or there's an error loading JSON.
    """
    try:
        with open(filepath, 'r') as f:
            original_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found at {filepath}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in {filepath}")
        return None

    restructured_data = []
    for year, agencies_data in original_data.items():
        for agency, agency_data in agencies_data.items():
            top_words_dict = agency_data.get("top_10_words", {}) # Get top_10_words or default to empty dict
            top_words_list = []
            for word, frequency in top_words_dict.items():
                top_words_list.append({"word": word, "frequency": frequency})

            agency_year_object = {
                "year": year,
                "agency": agency,
                "top_words": top_words_list
            }
            restructured_data.append(agency_year_object)

    return restructured_data

# Example usage:
if __name__ == "__main__":
    json_file_path = 'top_10_words.json'  # Replace 'your_data.json' with the actual file path
    restructured_data_option2 = restructure_data_option2_from_json(json_file_path)
    if restructured_data_option2:
        with open('agency_chart_data.json', 'w') as outfile:
            json.dump(restructured_data_option2, outfile, indent=2)
