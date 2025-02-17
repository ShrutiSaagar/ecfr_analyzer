# Python File: prepare_d3_data_stacked.py
import json

def prepare_data_for_d3_stacked(file_path, output_file_path):
    """
    Reads a JSON file, restructures data for a stacked bar chart in D3.js,
    and saves it to a new JSON file. Data is grouped by year, with agencies
    and their counts as stacks.

    Args:
        file_path (str): Path to the input JSON file.
        output_file_path (str): Path to save the output JSON file for D3.js.
    """
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)

        # Group data by year
        yearly_data = {}
        for year, year_data in data.items():
            agencies_list = []
            for agency, agency_data in year_data.items():
                if 'yearly_word_count' in agency_data:
                    agencies_list.append({"name": agency, "count": agency_data['yearly_word_count']})
            yearly_data[year] = agencies_list

        # Convert to list of objects for D3.js
        d3_stacked_data = []
        for year, agencies in yearly_data.items():
            d3_stacked_data.append({"year": year, "agencies": agencies})

        with open(output_file_path, 'w') as outfile:
            json.dump(d3_stacked_data, outfile, indent=2)

        print(f"Successfully prepared stacked data for D3.js and saved to '{output_file_path}'.")

    except FileNotFoundError:
        print(f"Error: Input file '{file_path}' not found.")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{file_path}'.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

# Usage (example - you can modify these paths)
input_file_path = 'monthly_yearly_counts.json'  # Replace with your input file path
output_file_path = 'd3_stacked_data.json'  # Output file for D3.js stacked chart data
prepare_data_for_d3_stacked(input_file_path, output_file_path)
