from sqlalchemy import text
import json
import asyncio
import os
from collections import defaultdict
from typing import List, Dict
from db.db import get_db
from data_parser.job_queue import DataProcessor


async def fetch_word_statistics(title_agency_map, title_name_map):
    year_agency_word_counts = defaultdict(lambda: defaultdict(lambda: {
        "agency_dn": "",
        "top_words": {},
        "monthly_word_counts": defaultdict(int),
        "yearly_word_count": 0
    }))

    async for session in get_db():
        try:
            query = text("""
                SELECT
                    vwc.title_number,
                    vwc.version_date,
                    vwc.type,
                    vwc.code,
                    vwc.word_statistics
                FROM
                    version_word_counts vwc;
            """)
            results = await session.execute(query)
            rows = results.fetchall()

            if not rows:
                print("No data found in version_word_counts table.")
                return year_agency_word_counts

            with open('word_transformation_map.json', 'r') as f:
                word_transformation_map = json.load(f)

            for row in rows:
                title_number, version_date, type, code, word_statistics = row
                title = title_number
                title_number_str = str(title_number)
                version_year = str(version_date.year)
                version_month = str(version_date.month).zfill(2) # Month with leading zero
                transformed_word_stats = {}
                total_words_in_record = 0 # Calculate total words for each record

                if word_statistics:
                    for word, count in word_statistics.items():
                        total_words_in_record += count # Sum up words in this record
                        transformed_word = word
                        if word in word_transformation_map:
                            transformed_word = next((w for w in word_transformation_map[word] if any(c.isupper() for c in w) and '.' not in w), word_transformation_map[word][0])
                        transformed_word_stats[transformed_word] = transformed_word_stats.get(transformed_word, 0) + count

                    if title_number_str in title_agency_map:
                        if type in title_agency_map[title_number_str]:
                            if code in title_agency_map[title_number_str][type]:
                                agencies = title_agency_map[title_number_str][type][code]
                                for agency_data in agencies:
                                    agency_sn = agency_data['sn']
                                    agency_dn = agency_data['dn']

                                    # Initialize agency entry if not present for the year
                                    if not year_agency_word_counts[version_year][agency_sn]["agency_dn"]:
                                        year_agency_word_counts[version_year][agency_sn]["agency_dn"] = agency_dn

                                    # Aggregate word frequencies
                                    for word, count in transformed_word_stats.items():
                                        year_agency_word_counts[version_year][agency_sn]["top_words"][word] = year_agency_word_counts[version_year][agency_sn]["top_words"].get(word, 0) + count

                                    # Aggregate monthly word counts
                                    year_agency_word_counts[version_year][agency_sn]["monthly_word_counts"][version_month] += total_words_in_record

                                    # Aggregate yearly word count
                                    year_agency_word_counts[version_year][agency_sn]["yearly_word_count"] += total_words_in_record

            # Get top 100 words for each agency and year
            for year_data in year_agency_word_counts.values():
                for agency_data in year_data.values():
                    sorted_words = sorted(agency_data["top_words"].items(), key=lambda item: item[1], reverse=True)[:100]
                    agency_data["top_words"] = dict(sorted_words) # Replace with top 100

            return year_agency_word_counts

        except Exception as error:
            print("Error while fetching data:", error)
            return defaultdict(lambda: defaultdict(lambda: {
                "agency_dn": "",
                "top_words": {},
                "monthly_word_counts": defaultdict(int),
                "yearly_word_count": 0
            }))


def prepare_title_agency_maps(agency_docs_list: List[Dict]) -> Dict[int, Dict[str, List[str]]]:
    """
    Args:
        Example: [{"title": 2, "agency_id": "A1", "chapter": "XV"}, {"title": 2, "agency_id": "A2", "subtitle": 1}]

    Returns:
        Example: {2: {"chapter": ["A1"], "subtitle": ["A2"]}, 20: {"chapter": ["A3"]}, 48: {"chapter": ["A4"], "subtitle": ["A5"]}}
    """
    title_agency_map: Dict[int, Dict[str, Dict[str, List[Dict]]]] = {}

    if not agency_docs_list:
        print("Warning: agency_docs_list is empty or None.")
        return title_agency_map  # Return empty map if no docs

    for doc_path in agency_docs_list:
        title_number = doc_path.get("title")
        agency_id = doc_path.get("agency_id")
        agency_sn = doc_path.get("agency_sn")
        agency_dn = doc_path.get("agency_dn")

        if title_number is not None and agency_id is not None:
            if not isinstance(title_number, int):
                try:
                    title_number = int(title_number)
                except ValueError:
                    print(f"Warning: Invalid title number '{title_number}' found. Skipping path entry: {doc_path}")
                    continue

            if title_number not in title_agency_map:
                title_agency_map[title_number] = {}

            for path_type, path_value in doc_path.items():
                if path_type not in ["title", "agency_id", "agency_sn", "agency_dn"] and path_value is not None: # Process all keys except 'title' and 'agency_id' as path types
                    path_type_str = str(path_type)
                    path_value_str = str(path_value)
                    if path_type_str not in title_agency_map[title_number]:
                        title_agency_map[title_number][path_type_str] = {}
                    if path_value_str not in title_agency_map[title_number][path_type_str]:
                        title_agency_map[title_number][path_type_str][path_value_str] = []
                    agency_info = {'id': agency_id, 'sn': agency_sn, 'dn': agency_dn}
                    if agency_info not in title_agency_map[title_number][path_type_str][path_value_str]: # Check if agency already exists
                        title_agency_map[title_number][path_type_str][path_value_str].append(agency_info)
        else:
            print(f"Warning: Document path entry missing 'title' or 'agency_id'. Skipping: {doc_path}")

    return title_agency_map


def append_to_json_file(data, filename="word_statistics.json"):
    if not os.path.exists(filename):
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
    else:
        try:
            with open(filename, 'r') as f:
                existing_data = json.load(f)
        except json.JSONDecodeError:
            existing_data = {} # Initialize as dict to handle year-agency structure

        if not isinstance(existing_data, dict): # Check if existing data is a dict
            existing_data = {}

        # Assuming data is year -> agency -> data_dict
        for year, agency_data in data.items():
            if year not in existing_data:
                existing_data[year] = defaultdict(dict) # Initialize year if not present
            for agency_sn, agency_info in agency_data.items():
                 existing_data[year][agency_sn] = agency_info # Directly overwrite/update agency data

        with open(filename, 'w') as f:
            json.dump(existing_data, f, indent=2)


async def create_title_agency_map():
    async for session in get_db():
        processor = DataProcessor(session)
        agencies = await processor.fetch_agencies()
        agency_docs_list_agg = []
        for agency in agencies:
            agency_docs_list = agency.docs
            for doc in agency_docs_list:
                doc['agency_id'] = str(agency.id)
                doc['agency_dn'] = agency.display_name
                if agency.short_name:
                    doc['agency_sn'] = agency.short_name
                else:
                    doc['agency_sn'] = ''.join([word[0] for word in agency.display_name.split() if word[0].isupper()])
                agency_docs_list_agg.append(doc)
        title_agency_map = prepare_title_agency_maps(agency_docs_list_agg)
        append_to_json_file(title_agency_map, 'title_agency_map.json')


async def main():
    with open('title_name_map.json', 'r') as f:
        title_name_map = json.load(f)

    with open('title_agency_map.json', 'r') as f:
        title_agency_map = json.load(f)

    year_agency_word_counts = await fetch_word_statistics(title_agency_map, title_name_map)

    if year_agency_word_counts:
        # Convert defaultdicts to regular dicts for JSON serialization before saving
        agency_output = {
            year: {
                agency: dict(agency_data) for agency, agency_data in agency_year_data.items()
            }
            for year, agency_year_data in year_agency_word_counts.items()
        }

        save_filename = 'year_agency_top_words.json'
        append_to_json_file(agency_output, save_filename)
        print(f"Yearly agency top words with monthly and yearly counts saved to '{save_filename}'")

    else:
        print("Failed to fetch and process word statistics.")


if __name__ == "__main__":
    print('main')
    asyncio.run(main())
