import json
from typing import List, Dict
from config.base import settings
from db.db import get_db 
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

import asyncio
from models.models import Agency
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Session = sessionmaker(settings.DATABASE_URL, class_=AsyncSession, expire_on_commit=False)

def prepare_title_path_maps(agency_docs_list: List[Dict]) -> Dict[int, Dict[str, List[str]]]:
    """
    Prepares a dictionary mapping title numbers to a dictionary of path types and their lists of paths,
    based on the agency's document paths.

    Args:
        agency_docs_list: A list of dictionaries, where each dictionary represents
                          a document path and contains 'title' (int) and other path type keys
                          (e.g., 'chapter', 'subtitle', 'category') with their path values (str or int).
                          Example: [{"title": 2, "chapter": "XV"}, {"title": 2, "subtitle": 1}]

    Returns:
        A dictionary where keys are title numbers (integers).
        Values are dictionaries, where keys are path types (strings like "chapter", "subtitle")
        and values are lists of path values (strings or ints, converted to strings for JSON)
        associated with that path type for the title.
        Example: {2: {"chapter": ["XV", "VVX"], "subtitle": ["1", "2"]}, 20: {"chapter": ["III"]}, 48: {"chapter": ["23"], "subtitle": ["3"]}}
    """
    title_path_map: Dict[int, Dict[str, List[str]]] = {}

    for doc_path in agency_docs_list:
        title_number = doc_path.get("title")

        if title_number is not None:
            if not isinstance(title_number, int):
                try:
                    title_number = int(title_number)
                except ValueError:
                    print(f"Warning: Invalid title number '{title_number}' found. Skipping path entry: {doc_path}")
                    continue

            if title_number not in title_path_map:
                title_path_map[title_number] = {}

            for path_type, path_value in doc_path.items():
                if path_type != "title" and path_value is not None: # Process all keys except 'title' as path types
                    path_type_str = str(path_type) # Ensure path_type is a string (for dictionary key)
                    path_value_str = str(path_value) # Convert path value to string for JSON consistency

                    if path_type_str not in title_path_map[title_number]:
                        title_path_map[title_number][path_type_str] = []
                    if path_value_str not in title_path_map[title_number][path_type_str]:
                        title_path_map[title_number][path_type_str].append(path_value_str)
        else:
            print(f"Warning: Document path entry missing 'title'. Skipping: {doc_path}")

    return title_path_map

def store_path_map_as_json(path_map: Dict[int, List[str]], filepath: str):
    """
    Stores the title-path map dictionary as a JSON file.

    Args:
        path_map: The dictionary mapping title numbers to chapter paths, as created by prepare_title_path_maps.
        filepath: The path to the JSON file where the map should be stored.
    """
    try:
        with open(filepath, 'w') as f:
            json.dump(path_map, f, indent=4)  # Use indent for pretty formatting (optional)
        print(f"Path map successfully stored in JSON format at: {filepath}")
    except Exception as e:
        print(f"Error storing path map as JSON to {filepath}: {e}")



async def fetch_agencies_from_db(session: AsyncSession) -> List[Agency]:
    """
    Fetches all agency records from the database using SQLAlchemy and the Agency model.

    Args:
        session: An SQLAlchemy AsyncSession object.

    Returns:
        A list of Agency objects fetched from the database.
        Returns an empty list if there are no agencies or if an error occurs.
    """
    try:
        query = select(Agency)  # Construct a SELECT query for the Agency model
        result = await session.execute(query)  # Execute the query asynchronously
        agencies: List[Agency] = result.scalars().all()  # Get all Agency objects from the result
        logging.info(f"Successfully fetched {len(agencies)} agency records from the database.")
        return agencies
    except Exception as e:
        logging.error(f"Error fetching agency records from the database: {e}")
        return []  # Return an empty list in case of error

async def main():
    """
    Example usage function to fetch and print agency names.
    """
    async for session in get_db(): 
        agencies = await fetch_agencies_from_db(session)
        if agencies:
            print("Fetched Agencies:")
            agency_docs_list = []
            for agency in agencies:
                print(f"- Agency ID: {agency.id}, Name: {agency.name}") 
                print(agency.docs)
                docs = agency.docs
                agency_docs_list.extend(docs)
            path_map = prepare_title_path_maps(agency_docs_list)
            print("Prepared Path Map:")
            print(json.dumps(path_map, indent=4))

            json_filepath = "title_path_map.json"
            store_path_map_as_json(path_map, json_filepath)
        else:
            print("No agencies found or error occurred while fetching.")

if __name__ == "__main__":
    asyncio.run(main())