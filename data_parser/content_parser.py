import xml.etree.ElementTree as ET
import re
import string
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, WordNetLemmatizer # Import WordNetLemmatizer
from collections import Counter
from typing import Dict
import json
import asyncio

# Ensure NLTK resources are downloaded (run this once if you haven't already)
import nltk
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True) # Download wordnet for lemmatizer
nltk.download('omw-1.4', quiet=True) # Download omw-1.4 for wordnet lemmatizer data
class TextProcessor:
    def __init__(self, xml_content: str = None):
        """
        Initializes the TextProcessor with NLTK resources (lemmatizer, stopwords, stemmer).
        These resources are created once per instance to avoid redundant initialization.
        Optionally, initializes with XML content for future processing.

        Args:
            xml_content: Optional XML content as a string to be stored in the instance.
        """
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))
        self.stemmer = PorterStemmer()  # Keeping stemmer instance for potential future use
        self.xml_content = xml_content
        self.word_transformation_map = {}

    def set_xml_content(self, xml_content: str):
        self.xml_content = xml_content
        self.root = ET.fromstring(self.xml_content)
        
    async def extract_content_from_xml(self, path: Dict[str, list]) -> Dict[str, Dict[str, str]]:
        """
        Extracts the text content from the stored XML content based on the specified path dictionary.
        The path dictionary contains keys representing XML attributes and lists of values to match.

        Args:
            path: A dictionary where keys are XML attributes (e.g., 'chapter', 'part') and values are lists of strings to match.

        Returns:
            A dictionary where keys are the matched attribute values and values are dictionaries of text content.
            Returns an empty dictionary if no matches are found or if there's an error parsing XML.
        """
        if not self.xml_content:
            print("No XML content set.")
            return {}

        path_keys = set(path.keys())
        value_sets = {key: set(values) for key, values in path.items()}
        result = {key: {} for key in path_keys} # Initialize result dict correctly

        try:
            for element in self.root.iter():
                if 'TYPE' in element.attrib:
                    type_c = element.attrib['TYPE'].lower()
                    if type_c in path_keys:
                        if 'N' in element.attrib: # Check if 'N' attribute exists
                            n_value = element.attrib['N'] # Get 'N' value safely
                            # print(f"Processing element with TYPE: {type_c}, N: {n_value}") # Debug print
                            if n_value in value_sets[type_c]:
                                text_content = self.get_element_full_text(element)
                                # print('full text')
                                # print(len(text_content))
                                # print(text_content[:200])
                                result[type_c][n_value] = text_content.strip()

        except ET.ParseError as e:
            print(f"XML ParseError: {e}")
            return {}
        except Exception as e:
            print(f"Error extracting content from XML: {e}")
            return None  # Or handle the error as appropriate

        return result

    def get_element_full_text(self, element):
        """
        Recursively extracts all text content from an XML element, including text from
        the element itself and all its descendants.

        Args:
            element: The XML ElementTree Element object.

        Returns:
            A string containing all text content within the element and its descendants,
            concatenated together.
        """
        text = element.text if element.text else "" # Get the element's own text
        for child in element:
            text += self.get_element_full_text(child) # Recursively get text from children
        tail = element.tail if element.tail else "" # Get the element's tail text (text after closing tag)
        return text + tail

    async def aggregate_word_counts(self, text_content: str) -> Dict[str, int]:
        """
        Aggregates the counts of meaningful words from a text string,
        excluding filler words, performing lemmatization, and removing punctuation.
        Removes unnecessary new lines from the text before processing.

        Args:
            text_content: The input text string.

        Returns:
            A dictionary where keys are lemmatized meaningful words and values are their counts.
        """
        if not text_content:
            return {}

        # 0. Remove unnecessary new lines
        text_content = text_content.replace('\n', ' ')

        # 1. Lowercasing
        text_content = text_content.lower()
        print('text_content')
        print(text_content)
        # 2. Remove punctuation
        text_content = text_content.translate(str.maketrans('', '', string.punctuation))
        print(text_content)

        # 3. Tokenization (split into words)
        words = text_content.split()
        print("words")
        print(words)
        # 4. Stop word removal
        filtered_words = [word for word in words if word not in self.stop_words] # Use instance's stop_words

        # 5. Lemmatization
        lemma_words = [self.lemmatizer.lemmatize(word) for word in filtered_words] # Use instance's lemmatizer
        print('lemma_words')
        print(lemma_words)
        
        # 6. Count word frequencies
        word_counts = Counter(lemma_words)
        print('word_counts')
        print(word_counts)
        return dict(word_counts)


    async def aggregate_word_counts_stemming_numeric_filter(self, text_content: str) -> Dict[str, int]: #tuple[Dict[str, int], Dict[str, str]]:
        """
        Aggregates word counts using stemming and filters out numeric and hyphenated numeric words.
        """
        if not text_content:
            return {}, {}

        original_words = text_content.replace('\n', ' ').split()
        processed_words = []

        for original_word in original_words:
            current_word = original_word

            lowercased_word = current_word.lower()
            if lowercased_word != current_word:
                self.word_transformation_map[lowercased_word] = current_word
                current_word = lowercased_word

            punctuation_removed_word = current_word.translate(str.maketrans('', '', string.punctuation))
            if punctuation_removed_word != current_word:
                self.word_transformation_map[punctuation_removed_word] = current_word
                current_word = punctuation_removed_word

            if current_word and current_word not in self.stop_words:
                # --- Stemming instead of Lemmatization ---
                stemmed_word = self.stemmer.stem(current_word) # Apply stemming
                if stemmed_word != current_word:
                    self.word_transformation_map[stemmed_word] = current_word # Map stemmed word to word before stemming
                    current_word = stemmed_word

                if current_word:
                    # --- Efficient Numeric and Hyphenated Number Filter ---
                    if not self.is_numeric_string(current_word) and len(current_word) > 3: # Filter numeric and hyphenated numbers
                        processed_words.append(current_word)

        word_counts = Counter(processed_words)
        filtered_word_counts = dict(word_counts)

        return filtered_word_counts

    def is_numeric_string(self, word: str) -> bool:
        """
        Efficiently checks if a word is purely numeric or a hyphenated number-like word.
        """
        if any(char.isdigit() for char in word):
            return True

        # if '-' in word:
        #     parts = word.split('-')
        #     if any(part.isdigit() for part in parts if part):
        #         return True # It's a hyphenated number-like word

        return False # Not numeric or hyphenated number-like


# Example Usage:
async def main():
    text_processor = TextProcessor() # Create an instance of TextProcessor

    sample_xml = """
    <ROOT>
        <SECTION>
            <TITLE>Section Title</TITLE>
            <P>This is the first paragraph.\n It whale Hurry up contains word what rocket some important words.\n\n</P>
            <P>Here is a second paragraph with more text and different words. Running and runs.</P>
        </SECTION>
        <SECTION>
            <P>Another paragraph in a different section.</P>
        </SECTION>
    </ROOT>
    """
    path_to_content = ".//SECTION/P"

    text_processor.set_xml_content(sample_xml)
    extracted_text = await text_processor.extract_content_from_xml(path_to_content) # Use instance's method
    print("Extracted Text Content:")
    print(extracted_text)

    word_counts = await text_processor.aggregate_word_counts(extracted_text) # Use instance's method
    print("\nAggregated Word Counts (Lemmatized, Class-based):")
    print(json.dumps(word_counts, indent=4))

if __name__ == "__main__":
    asyncio.run(main())