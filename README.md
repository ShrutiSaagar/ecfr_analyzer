# eCFR Word Watcher: Unveiling Trends in Regulatory Language

[![Project Status](https://img.shields.io/badge/Status-Complete-brightgreen.svg)](https://img.shields.io/badge/Status-Complete-brightgreen.svg)

Have you ever wondered how the language of federal regulations changes over time?  Or which words are catching the eye of different government agencies?  "eCFR Word Watcher" is a project that dives into the Electronic Code of Federal Regulations (eCFR) to do just that!

Adding some screenshots to show off the work, because some basic html catches more attention than amazing scalable software and design in the backend! Phew!
![alt text](<Screenshot 2025-02-16 at 8.39.17 PM.png>)![alt text](<Screenshot 2025-02-16 at 8.45.06 PM.png>)
**In simple terms, this project helps you explore:**

* **Word Count Evolution:** How the length of regulations associated with different agencies has changed year by year. Are regulations getting longer or shorter?
* **Word Frequency Trends:** Which words are popping up more often in eCFR titles related to specific agencies. Are there new buzzwords emerging in certain regulatory areas?  Has a word that was rarely used suddenly become commonplace?

Think of it as a time-lapse for regulatory language, allowing you to spot trends and shifts in focus across different government bodies.

## What's Under the Hood? (Technical Details)

This project is all about data analysis, powered by the publicly available eCFR API (kudos to them for making this data accessible!). Here's a breakdown of how it works:

### 1. Data Source: The eCFR API (and a bit of API wrangling)

Firstly thanks to [eCFR API](https://www.ecfr.gov/developers/documentation/api/v1).  This API provides access to the wealth of data within the Electronic Code of Federal Regulations. 

Initially, figuring out how to effectively navigate this API felt like trying to find your way through a regulatory maze itself!  But after some... let's just say, *painstaking* effort, the project was set up to pull the necessary information.

### 2. Data Acquisition Strategy: Metadata over Megabytes

My first thought was to download all the XML data for every regulation and store it.  Imagine a digital dragon hoarding XML!  However, realizing that the focus was on word frequency and trends, not necessarily the full document content for now, I opted for a more streamlined approach.  I didn't wan to store these huge XML files in S3 (and potentially incurring minor costs over time!) only to not use them later,  the project focuses on extracting metadata – specifically, the titles of regulations and their associated agency information across different versions and dates.

Turns out, even the metadata is substantial!  The eCFR versioning system is quite detailed, leading to a large number of records.  It's not just about amendments; there's more to the versioning story than meets the eye.  But, the key insight was that we can fetch the full titles for their version dates alone. So, the strategy became to identify the available dates for each title and process them and store them in our DB.

### 3.  Facing the Data Deluge: Size Matters!

Before diving deep, it was crucial to understand the scale of the data.  A quick check revealed that some title XML files could be surprisingly large, ranging from 30-50MB!  This meant processing everything locally wasn't going to cut it.  A back-of-the-envelope calculation (yes, even using Excel for a bit!) helped estimate the total data size to be around 180GB.  Time to bring in the cloud!

### 4. Building an Asynchronous Processing Pipeline: Cloud Power to the Rescue

To handle this volume of data efficiently, especially without melting my laptop, an asynchronous processing pipeline was built using AWS.  Why AWS?  Familiarity and a pre-existing PostgreSQL database setup made it a natural choice.

Here's the pipeline in a nutshell:

* **Containerized Processors:**  The core data processing logic was packaged into Docker containers. This allowed for easy scaling and deployment in the cloud.
* **ECS Workers:** These containers were deployed as workers in AWS ECS (Elastic Container Service).  Think of them as little data-crunching robots running in parallel.
* **Job Queuing:**  A queueing system was implemented to manage the processing tasks. This ensures that work is distributed evenly among the workers and handles potential API rate limits gracefully.

Building this pipeline was... *painstaking* (again, that word!).  There was a lot of R&D involved in figuring out:

* **Rate Limiting and Concurrency:**  How many concurrent API requests could be made without getting blocked? How many ECS tasks and concurrent requests per task could the database handle?  Tuning wait times and request frequencies was crucial to play nicely with the eCFR API and the database.
* **API Latency:**  Unexpectedly, the API response times sometimes became quite slow, likely due to their infrastructure limitations.  This required increasing API timeouts in the code to prevent premature connection closures.
* **Error Handling and Requeuing:**  Intermittent job failures were a reality.  Implementing a requeuing mechanism helped to process most of the data, even if some larger titles required multiple retries.  However, the truly massive titles sometimes struggled, hinting at potential connection issues or timeouts on the API side.

### 5.  Word Wrangling: Stemming for Sanity

Once the data was flowing in, the next step was to process the text.  To keep things efficient and focus on the core meaning of words, stemming was used. Stemming reduces words to their root form (e.g., "running," "ran," "runs" all become "run"). This helps group similar words together and speeds up analysis.  Mappings of stemmed words to their original forms were also stored to allow for readable display later on.

### 6. Data Aggregation and Visualization: Making Sense of the Words

The final stage was to aggregate the processed data and present it in a way that's easy to understand and explore in a browser. This involved:

* **Agency-Word Frequency Maps:** Creating mappings to link title content to agencies, enabling analysis at the agency level.
* **Data Aggregation for Visualization:**  A lot of "patchwork" processing was needed to massage the data into a browser-digestible format.  Two main views were created:
    * **Total Word Count Trends:**  Visualizing how the total word count of regulations associated with each agency has changed over the years.
    * **Top Word Trends:**  Identifying the top 10 most frequent words for each agency and year to show word usage trends.  With around 350 agencies, this aggregation was another performance bottleneck to tackle.
* **Interactive Charts with d3.js:**  d3.js was used to create interactive charts for visualizing the data. These charts include filtering options and a searchable legend to make exploration easier.

## Getting Started (Running Locally)

**Backend:** The python files to queue, process and fetch data can be run individually provided the configurations are set in your .env file. Or you can choose to run them by creating different Dockerfiles for them. I've used Postgres DB and the corresponding connection strings, please change as needed.

Frontend: Want to explore the data and visualizations yourself? Here's how to get started:

1. **Run a local server:**  You'll need a simple web server to serve the HTML and data files in the webpage folder.  Python's built-in `http.server` is a quick option: `python -m http.server` in the project directory.
2. **Explore the data:** The data used for visualization (as of February 15th) is included in the repository alongside the webpage.  You can start exploring the trends right away!

## Code and Data Notes

* **Data Snapshot:** The data included in this repository is a snapshot as of **February 15th, 2025**.  To get the latest data, you would need to re-run the data acquisition and processing pipeline.
* **Accessory Files:**  misc/final_pack.py file was the fine tuned version of pack.py which helped aggregate the count data for all the words in versions for the agencies and later process them with other scripts as needed. The repository also includes those accessory files and scripts used for data processing, fine-tuning, and analysis just for reference purposes. These might be helpful if you want to dive deeper or extend the project later.
* **Code Style:**  A small disclaimer:  In the interest of getting things done and exploring quickly, you might find some inconsistencies in the codebase.  You might see a mix of SQLAlchemy and raw SQL queries.  Sometimes, speed trumps perfect consistency!

### Observations and concluding remarks
* The word count data in 2021-23 went a bit down during covid and picked back up, sadly the lawmakers are back to make more troublesome laws I guess. Laws are needed but we know it is no longer a law when there are reports saying Chicago city is planning to reduce the speed limit because they aren't getting enough money in fines!
* The webpage itself is pretty simple and put together hurriedly, it is hosted on my site http://shrutisaagar.com/ecfr/index.html . Feel free to check it out but please don't do intrusion testing or start DDOSing it because I'm a poor dev. Please forgive the shortcuts and bypasses in the html, js and css parts of the webpage.

##  Contribute and Connect

Feel free to explore the code and data!  Any feedback, comments, or suggestions are very welcome.  I'm also happy to discuss my learnings and findings in more detail if you find this project interesting or useful.

Enjoy exploring the world of regulatory language!
