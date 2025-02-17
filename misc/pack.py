from sqlalchemy import create_engine, text
import json
import asyncio
import os
import copy
from datetime import datetime
from typing import List, Dict
from db.db import get_db 
from data_parser.job_queue import DataProcessor
from collections import defaultdict


async def fetch_word_statistics(title_agency_map, title_name_map): 
    word_stats_list = [] 
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
                print("No data found within the specified timestamp range.")
                return []
            with open('word_transformation_map.json', 'r') as f:
                word_transformation_map = json.load(f)
            for row in rows:
                title_number, version_date, type, code, word_statistics = row
                title = title_number
                title_number = str(title_number)
                if title_number in title_agency_map:
                    if type in title_agency_map[title_number]:
                        if code in title_agency_map[title_number][type]:
                            agencies = title_agency_map[title_number][type][code]
                            for agency in agencies:
                                top_words = dict(sorted(word_statistics.items(), key=lambda item: item[1], reverse=True)[:10])
                                top_tr_words = {}
                                for word in top_words:
                                    if word in word_transformation_map:
                                        transformed_word = next((w for w in word_transformation_map[word] if any(c.isupper() for c in w) and '.' not in w), word_transformation_map[word][0])
                                        top_tr_words[transformed_word] = top_words[word]
                                word_stats_list.append({
                                    "agency": agency['sn'],
                                    "agency_dn": agency['dn'],
                                    "title": title_number,
                                    "type": type,
                                    "code": code,
                                    "title_name": title_name_map[title],
                                    "versionDate": version_date.isoformat(),
                                    "wordFrequencies": top_tr_words
                                })
            return word_stats_list
        except Exception as error:
            print("Error while fetching data:", error)
            return None 

def process_word_statistics_json(input_filename="word_statistics.json", transformation_map_filename='word_transformation_map.json'):
    """
    Processes a JSON file containing word statistics, aggregates them by year, agency, and title,
    and saves the results to two new JSON files.

    Args:
        input_filename (str): The name of the input JSON file (word_statistics.json).
        transformation_map_filename (str): Filename for word transformation map (word_transformation_map.json).
    """
    year_agency_word_counts = defaultdict(lambda: defaultdict(lambda: {"agency_dn": "", "wordFrequencies": defaultdict(int)}))
    year_title_word_counts = defaultdict(lambda: defaultdict(lambda: {"title_name": "", "wordFrequencies": defaultdict(int)}))
    word_transformation_map = {}

    try:
        with open(transformation_map_filename, 'r') as f:
            word_transformation_map = json.load(f)
    except FileNotFoundError:
        print(f"Warning: {transformation_map_filename} not found. Using words without transformation.")
    except json.JSONDecodeError:
        print(f"Warning: Invalid JSON in {transformation_map_filename}. Using words without transformation.")

    try:
        with open(input_filename, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.")
        return None, None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file '{input_filename}'.")
        return None, None

    for record in data:
        agency = record.get("agency")
        agency_dn = record.get("agency_dn")
        title_number_str = record.get("title") # Assuming title in json is already string
        title_name = record.get("title_name")
        version_date_str = record.get("versionDate")
        word_statistics = record.get("wordFrequencies", {})
        version_year = version_date_str[:4] 
        transformed_word_stats = {}

        if word_statistics:
            for word, count in word_statistics.items():
                transformed_word = word
                if word in word_transformation_map:
                    transformed_word = next((w for w in word_transformation_map[word] if any(c.isupper() for c in w) and '.' not in w), word_transformation_map[word][0])
                transformed_word_stats[transformed_word] = transformed_word_stats.get(transformed_word, 0) + count

        if agency:
            year_agency_word_counts[version_year][agency]["agency_dn"] = agency_dn
            for word, count in transformed_word_stats.items():
                year_agency_word_counts[version_year][agency]["wordFrequencies"][word] += count

        if title_number_str:
            year_title_word_counts[version_year][title_number_str]["title_name"] = title_name
            for word, count in transformed_word_stats.items():
                year_title_word_counts[version_year][title_number_str]["wordFrequencies"][word] += count

    return year_agency_word_counts, year_title_word_counts


def prepare_title_agency_maps(agency_docs_list: List[Dict]) -> Dict[int, Dict[str, List[str]]]:
    """
    Args:
        Example: [{"title": 2, "agency_id": "A1", "chapter": "XV"}, {"title": 2, "agency_id": "A2", "subtitle": 1}]

    Returns:
        Example: {2: {"chapter": ["A1"], "subtitle": ["A2"]}, 20: {"chapter": ["A3"]}, 48: {"chapter": ["A4"], "subtitle": ["A5"]}}
    """
    title_agency_map: Dict[int, Dict[str, List[str]]] = {}

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
                if path_type not in ["title", "agency_id"] and path_value is not None: # Process all keys except 'title' and 'agency_id' as path types
                    path_type_str = str(path_type) 
                    path_value_str = str(path_value)
                    if path_type_str not in title_agency_map[title_number]:
                        title_agency_map[title_number][path_type_str] = {}
                    if path_value_str not in title_agency_map[title_number][path_type_str]:
                        title_agency_map[title_number][path_type_str][path_value_str] = []
                    if agency_id not in title_agency_map[title_number][path_type_str][path_value_str]:
                        title_agency_map[title_number][path_type_str][path_value_str].append({
                            'id': agency_id,
                            'sn': agency_sn,
                            'dn': agency_dn
                        })
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
            existing_data = []

        if not isinstance(existing_data, list):
            existing_data = []

        updated_data = existing_data + data
        with open(filename, 'w') as f:
            json.dump(updated_data, f, indent=2)
            
async def create_title_agency_map():
    async for session in get_db(): 
        processor = DataProcessor(session)
        agencies = await processor.fetch_agencies()
        agency_docs_list_agg = []
        for agency in agencies:
            agency_docs_list = agency.docs
            # print(agency_docs_list)
            for doc in agency_docs_list:
                doc['agency_id'] = str(agency.id)
                doc['agency_dn'] = agency.display_name
                if agency.short_name:
                    doc['agency_sn'] = agency.short_name
                else:
                    doc['agency_sn'] = ''.join([word[0] for word in agency.display_name.split() if word[0].isupper()])
                # print(doc)
                agency_docs_list_agg.append(doc)
        # print(agency_docs_list_agg)
        title_agency_map = prepare_title_agency_maps(agency_docs_list_agg)
        append_to_json_file(title_agency_map, 'title_agency_map.json')
    
async def main():
    
    # with open('titles.json', 'r') as f:
    #     titles_data = json.load(f)
    # title_name_map = {title['number']: title['name'] for title in titles_data['titles']}
    
    # output_filename = "word_statistics.json"
    # with open('title_agency_map.json', 'r') as f:
    #     title_agency_map = json.load(f)
    # word_statistics_data = await fetch_word_statistics(title_agency_map, title_name_map)

    # if word_statistics_data is not None:
    #     append_to_json_file(word_statistics_data, output_filename)
    # else:
    #     print("Failed to fetch word statistics. JSON file not updated.")
    
    year_agency, year_title = process_word_statistics_json()
    append_to_json_file(year_agency, 'agency.json')
    append_to_json_file(year_title, 'title.json')

if __name__ == "__main__":
    print('main')
    asyncio.run(main())