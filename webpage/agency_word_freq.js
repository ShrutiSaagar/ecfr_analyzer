document.addEventListener('DOMContentLoaded', () => {
    const dataUrl = 'agency_chart_data.json';
    const agencyFilter = d3.select('#agency-filter');
    const wordFilter = d3.select('#word-filter');
    const agencyList = d3.select('#agency-list');
    const wordList = d3.select('#word-list');
    const selectedAgenciesDiv = d3.select('#selected-agencies');
    const selectedWordsDiv = d3.select('#selected-words');
    const stackedBarChartDiv = d3.select('#stacked-bar-chart');
    const barChartDiv = d3.select('#bar-chart');
    const wordCloudChartDiv = d3.select('#word-cloud-chart');
    const agencyWordCountDiv = d3.select('#agency-word-count');
    const leastWordCountAgenciesDiv = d3.select('#least-agency-summary'); 
    const totalWordsSummaryH1Div = d3.select('#total-words-summary-h1');
    const tooltipDiv = d3.select('#chart-tooltip');
    const resetButton = d3.select('#reset-button');

    let allData = [];
    let allAgencies = [];
    let allWords = [];
    let selectedAgencies = ['all'];
    let selectedWords = [];
    let filteredAgencies = [];
    let filteredWords = [];
    let initialTopAgencies = [];
    const defaultTopCount = 20;
    const extendedTopCount = 40;

    // Update the color palette
    const materialColors = {
        summary: [
            '#3498db',
            '#2ecc71',
            '#9b59b6',
            '#e67e22'
        ],
        primary: ['#1976D2', '#0097A7', '#388E3C', '#FFA000', '#E64A19'],
        secondary: ['#42A5F5', '#00BCD4', '#66BB6A', '#FFB300', '#FF7043'],
        accent: ['#2196F3', '#00ACC1', '#4CAF50', '#FFC107', '#F4511E']
    };

    // --- Helper Functions ---
    const getAgencies = (data) => {
        return [...new Set(data.map(d => d.agency))].sort();
    };

    const getAllWords = (data) => {
        const words = new Set();
        data.forEach(item => {
            item.top_words.forEach(wordData => {
                words.add(wordData.word);
            });
        });
        return [...words].sort();
    };

    const filterData = () => {
        let filtered = allData;
        if (!selectedAgencies.includes('all')) {
            filtered = filtered.filter(d => selectedAgencies.includes(d.agency));
        }
        return filtered;
    };

    // Define all update functions first
    const updateSelectedAgencies = () => {
        selectedAgenciesDiv.selectAll('*').remove();
        selectedAgencies.forEach(agency => {
            selectedAgenciesDiv.append('span')
                .attr('class', 'selected-tag')
                .html(`${agency} <span class="remove-tag">×</span>`)
                .on('click', () => {
                    const index = selectedAgencies.indexOf(agency);
                    if (index > -1) {
                        selectedAgencies.splice(index, 1);
                        if (selectedAgencies.length === 0) selectedAgencies = ['all'];
                        updateSelectedAgencies();
                        updateCharts();
                    }
                });
        });
    };

    const updateSelectedWords = () => {
        selectedWordsDiv.selectAll('*').remove();
        selectedWords.forEach(word => {
            selectedWordsDiv.append('span')
                .attr('class', 'selected-tag')
                .html(`${word} <span class="remove-tag">×</span>`)
                .on('click', () => {
                    const index = selectedWords.indexOf(word);
                    if (index > -1) {
                        selectedWords.splice(index, 1);
                        updateSelectedWords();
                        updateCharts();
                    }
                });
        });
    };

    const updateAgencyList = () => {
        const searchTerm = agencyFilter.property('value').toLowerCase();
        filteredAgencies = ['all', ...allAgencies.filter(agency =>
            agency.toLowerCase().includes(searchTerm)
        )];

        const items = agencyList.selectAll('.filter-item')
            .data(filteredAgencies);

        items.enter()
            .append('div')
            .merge(items)
            .attr('class', d => `filter-item${selectedAgencies.includes(d) ? ' selected' : ''}`)
            .text(d => d)
            .on('click', (event, d) => {
                if (d === 'all') {
                    selectedAgencies = ['all'];
                } else {
                    const index = selectedAgencies.indexOf('all');
                    if (index > -1) selectedAgencies.splice(index, 1);

                    const agencyIndex = selectedAgencies.indexOf(d);
                    if (agencyIndex > -1) {
                        selectedAgencies.splice(agencyIndex, 1);
                    } else {
                        selectedAgencies.push(d);
                    }

                    if (selectedAgencies.length === 0) selectedAgencies = ['all'];
                }

                updateSelectedAgencies();
                updateCharts();
            });

        items.exit().remove();
    };

    const updateWordList = () => {
        const searchTerm = wordFilter.property('value').toLowerCase();
        filteredWords = allWords.filter(word =>
            word.toLowerCase().includes(searchTerm)
        );

        const items = wordList.selectAll('.filter-item')
            .data(filteredWords);

        items.enter()
            .append('div')
            .merge(items)
            .attr('class', d => `filter-item${selectedWords.includes(d) ? ' selected' : ''}`)
            .text(d => d)
            .on('click', (event, d) => {
                const index = selectedWords.indexOf(d);
                if (index > -1) {
                    selectedWords.splice(index, 1);
                } else {
                    selectedWords.push(d);
                }
                updateSelectedWords();
                updateCharts();
            });

        items.exit().remove();
    };

    // --- Summary Chart Functions ---
    const createAgencyWordCountChart = (data) => {
        agencyWordCountDiv.selectAll('*').remove();

        if (!data || data.length === 0) {
            agencyWordCountDiv.append('text').text("No data available");
            return;
        }

        const margin = { top: 30, right: 0, bottom: 60, left: 60 }; // Reduced right margin
        const width = Math.min(agencyWordCountDiv.node().getBoundingClientRect().width - margin.left - margin.right, 400);
        const height = 200;

        const svg = agencyWordCountDiv.append('svg')
            .attr('width', width + margin.left + margin.right)
            .attr('height', height + margin.top + margin.bottom)
            .append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        // Calculate total word count per agency
        const agencyCounts = d3.rollup(data,
            v => d3.sum(v[0].top_words, w => w.frequency),
            d => d.agency
        );

        const sortedAgencies = Array.from(agencyCounts)
            .sort(([, a], [, b]) => b - a);

        const displayCount = selectedAgencies.length > 1 && selectedAgencies[0] !== 'all' ? extendedTopCount : defaultTopCount;
        const topAgenciesForChart = sortedAgencies.slice(0, displayCount);

        const x = d3.scaleBand()
            .domain(topAgenciesForChart.map(d => d[0]))
            .range([0, width])
            .padding(0.1);

        const y = d3.scaleLinear()
            .domain([0, d3.max(topAgenciesForChart, d => d[1])])
            .nice()
            .range([height, 0]);

        svg.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(x))
            .selectAll('text')
            .style('text-anchor', 'end')
            .attr('dx', '-.8em')
            .attr('dy', '.15em')
            .attr('transform', 'rotate(-45)');

        svg.append('g')
            .call(d3.axisLeft(y));

        svg.selectAll('rect')
            .data(topAgenciesForChart)
            .enter()
            .append('rect')
            .attr('x', d => x(d[0]))
            .attr('y', d => y(d[1]))
            .attr('width', x.bandwidth())
            .attr('height', d => height - y(d[1]))
            .attr('fill', materialColors.summary[0])
            .on('mouseover', (event, d) => {
                const agencyData = allData.find(ad => ad.agency === d[0]);
                tooltipDiv.transition().duration(200).style('opacity', .9);
                tooltipDiv.html(`${agencyData.agency}<br>Total words: ${d[1]}`)
                    .style('left', (event.pageX + 10) + 'px')
                    .style('top', (event.pageY - 15) + 'px');
            })
            .on('mouseout', () => {
                tooltipDiv.transition().duration(500).style('opacity', 0);
            });

        svg.append('text')
            .attr('x', width / 2)
            .attr('y', -10)
            .attr('text-anchor', 'middle')
            .style('font-size', '14px')
            .text(`Total Word Count by Agency (Top ${displayCount})`);
    };


    const createBarChart = (data) => {
        barChartDiv.selectAll('*').remove();

        if (!data || data.length === 0) {
            barChartDiv.append('text')
                .attr('x', 20)
                .attr('y', 20)
                .text("No data available");
            return;
        }

        const margin = { top: 30, right: 0, bottom: 60, left: 60 }; // Reduced right margin
        const width = Math.min(barChartDiv.node().getBoundingClientRect().width - margin.left - margin.right, 400);
        const height = 200;

        const svg = barChartDiv.append('svg')
            .attr('width', width + margin.left + margin.right)
            .attr('height', height + margin.top + margin.bottom)
            .append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        // Aggregate word frequencies across agencies for top words
        const wordFrequencies = {};
        data.forEach(agencyData => {
            agencyData.top_words.forEach(wordInfo => {
                wordFrequencies[wordInfo.word] = (wordFrequencies[wordInfo.word] || 0) + wordInfo.frequency;
            });
        });

        const sortedWords = Object.entries(wordFrequencies)
            .sort(([, a], [, b]) => b - a);

        const displayCount = selectedWords.length > 0 ? extendedTopCount : defaultTopCount;
        const topWordsForChart = sortedWords.slice(0, displayCount);


        const x = d3.scaleBand()
            .domain(topWordsForChart.map(d => d[0]))
            .range([0, width])
            .padding(0.1);

        const y = d3.scaleLinear()
            .domain([0, d3.max(topWordsForChart, d => d[1])])
            .nice()
            .range([height, 0]);

        svg.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(x))
            .selectAll('text')
            .style('text-anchor', 'end')
            .attr('dx', '-.8em')
            .attr('dy', '.15em')
            .attr('transform', 'rotate(-45)');

        svg.append('g')
            .call(d3.axisLeft(y));

        svg.selectAll('rect')
            .data(topWordsForChart)
            .enter()
            .append('rect')
            .attr('x', d => x(d[0]))
            .attr('y', d => y(d[1]))
            .attr('width', x.bandwidth())
            .attr('height', d => height - y(d[1]))
            .attr('fill', materialColors.summary[1]);

        svg.append('text')
            .attr('x', width / 2)
            .attr('y', -10)
            .attr('text-anchor', 'middle')
            .style('font-size', '14px')
            .text(`Top Word Count Summary (Top ${displayCount} Words)`);
    };


    const createLeastWordCountAgenciesChart = (data) => {
        leastWordCountAgenciesDiv.selectAll('*').remove();

        if (!data || data.length === 0) {
            leastWordCountAgenciesDiv.append('text').text("No data available");
            return;
        }

        const margin = { top: 30, right: 5, bottom: 60, left: 60 }; // Reduced right margin
        const width = Math.min(leastWordCountAgenciesDiv.node().getBoundingClientRect().width - margin.left - margin.right, 400);
        const height = 200;

        const svg = leastWordCountAgenciesDiv.append('svg')
            .attr('width', width + margin.left + margin.right)
            .attr('height', height + margin.top + margin.bottom)
            .append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        // Aggregate top word frequencies across all agencies

        // Calculate total word count per agency
        const agencyCounts = d3.rollup(data,
            v => d3.sum(v[0].top_words, w => w.frequency),
            d => d.agency
        );

        // Sort agencies by word count in ascending order (least to most)
        const sortedAgencies = Array.from(agencyCounts)
            .sort(([, a], [, b]) => a - b); // Changed to ascending sort for least word counts

        const displayCount = selectedWords.length > 0 ? extendedTopCount : defaultTopCount;
        const topWordsForChart = sortedAgencies.slice(0, displayCount);


        const x = d3.scaleBand()
            .domain(topWordsForChart.map(d => d[0]))
            .range([0, width])
            .padding(0.1);

        const y = d3.scaleLinear()
            .domain([0, d3.max(topWordsForChart, d => d[1])])
            .nice()
            .range([height, 0]);

        svg.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(x))
            .selectAll('text')
            .style('text-anchor', 'end')
            .attr('dx', '-.8em')
            .attr('dy', '.15em')
            .attr('transform', 'rotate(-45)');

        svg.append('g')
            .call(d3.axisLeft(y));

        svg.selectAll('rect')
            .data(sortedAgencies.slice(0, displayCount))
            .enter()
            .append('rect')
            .attr('x', d => x(d[0]))
            .attr('y', d => y(d[1]))
            .attr('width', x.bandwidth())
            .attr('height', d => height - y(d[1]))
            .attr('fill', materialColors.summary[2]);
        svg.append('text')
            .attr('x', width / 2)
            .attr('y', -10)
            .attr('text-anchor', 'middle')
            .style('font-size', '14px')
            .text(`Agencies with Least Word Counts (Bottom ${displayCount})`); // Updated chart title
        };


    const createTotalWordsSummaryChart = (data) => {
        totalWordsSummaryH1Div.selectAll('*').remove();

        if (!data || data.length === 0) {
            totalWordsSummaryH1Div.text("No data available");
            return;
        }

        const totalWords = d3.sum(data, agencyData => d3.sum(agencyData.top_words, word => word.frequency));

        totalWordsSummaryH1Div.append('span')
            .style('font-size', '0.8em')
            .style('font-weight', 'bold')
            .text(`(Total Words Analyzed: ${d3.format(".3s")(totalWords)})`);
    };


    const createStackedBarChart = (data) => {
        stackedBarChartDiv.selectAll('*').remove();

        if (selectedWords.length > 30) {
            stackedBarChartDiv.append('text')
                .attr('x', 20)
                .attr('y', 20)
                .text("Cannot display stacked bar chart with more than 30 words selected. Please reduce word selection.");
            return;
        }
        // If no words are selected, do not display the chart
        if (selectedWords.length === 0) return;
        if (!data || data.length === 0) {
            stackedBarChartDiv.append('text')
                .attr('x', 20)
                .attr('y', 20)
                .text("No data available");
            return;
        }

        const margin = { top: 30, right: 70, bottom: 60, left: 60 };
        const width = stackedBarChartDiv.node().getBoundingClientRect().width - margin.left - margin.right;
        const height = stackedBarChartDiv.node().getBoundingClientRect().height - margin.top - margin.bottom;

        const svg = stackedBarChartDiv.append('svg')
            .attr('width', width + margin.left + margin.right)
            .attr('height', height + margin.top + margin.bottom)
            .append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);

        // Get top agencies by word count for initial display and ordering
        const agencyWordCounts = d3.rollup(allData,
            v => d3.sum(v[0].top_words, w => w.frequency),
            d => d.agency
        );
        let sortedAgencies = Array.from(agencyWordCounts)
            .sort(([, a], [, b]) => b - a); // Sort ascending for ordering in chart

        const agenciesForChart = selectedAgencies.includes('all') ? sortedAgencies.slice(-30).map(d => d[0]) : selectedAgencies;
        sortedAgencies.sort(([, a], [, b]) => b - a);

        const orderedAgenciesForChart = sortedAgencies.slice(-30).map(d => d[0]);

        // Filter data to only include agencies for the chart
        const dataForChart = data.filter(d => orderedAgenciesForChart.includes(d.agency));


        const allWordsInAgency = [...new Set(data.flatMap(d => d.top_words.map(w => w.word)))];

        // Use selectedWords for the chart, if words are selected
        let wordsForChart = selectedWords.length > 0 ? selectedWords : [];

        if (wordsForChart.length === 0) {
            return; // If no words selected after filter, exit to avoid empty chart
        }

        const stackData = wordsForChart.map(word => {
            const entry = { word };
            dataForChart.forEach(agencyData => {
                const wordInfo = agencyData.top_words.find(w => w.word === word);
                entry[agencyData.agency] = wordInfo ? wordInfo.frequency : 0;
            });
            return entry;
        });

        const stack = d3.stack()
            .keys(orderedAgenciesForChart);

        const series = stack(stackData);

        const x = d3.scaleBand()
            .domain(wordsForChart)
            .range([0, width])
            .padding(0.1);

        const y = d3.scaleLinear()
            .domain([0, d3.max(series, d => d3.max(d, d => d[1]))]).nice()
            .range([height, 0]);

        const color = d3.scaleOrdinal()
            .domain(orderedAgenciesForChart)
            .range(materialColors.primary);

        svg.append('g')
            .selectAll('g')
            .data(series)
            .enter().append('g')
            .attr('fill', d => color(d.key))
            .selectAll('rect')
            .data(d => d)
            .enter().append('rect')
            .attr('x', d => x(d.data.word))
            .attr('y', d => y(d[1]))
            .attr('height', d => y(d[0]) - y(d[1]))
            .attr('width', x.bandwidth())
            .on('mouseover', (event, d) => {
                tooltipDiv.transition().duration(200).style('opacity', .9);
                tooltipDiv.html(`${d.data.word}<br>${d.key}: ${d[1] - d[0]} occurrences`)
                    .style('left', (event.pageX + 10) + 'px')
                    .style('top', (event.pageY - 15) + 'px');
            })
            .on('mouseout', () => {
                tooltipDiv.transition().duration(500).style('opacity', 0);
            });


        svg.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(x))
            .selectAll('text')
            .style('text-anchor', 'end')
            .attr('dx', '-.8em')
            .attr('dy', '.15em')
            .attr('transform', 'rotate(-45)');

        svg.append('g')
            .call(d3.axisLeft(y));

        // Legend
        const legend = svg.append("g")
            .attr("class", "legend")
            .attr("transform", `translate(${width + 20}, 20)`);

        legend.selectAll("rect")
            .data(orderedAgenciesForChart)
            .enter().append("rect")
            .attr("class", "legend-rect")
            .attr("x", 0)
            .attr("y", (d, i) => i * 20)
            .attr("width", 15)
            .attr("height", 15)
            .style("fill", color);

        legend.selectAll("text")
            .data(orderedAgenciesForChart)
            .enter().append("text")
            .attr("class", "legend-text")
            .attr("x", 20)
            .attr("y", (d, i) => i * 20 + 8)
            .text(d => d);

        if (wordsForChart.length > 0) {
            svg.append('text')
                .attr('x', width / 2)
                .attr('y', -10)
                .attr('text-anchor', 'middle')
                .style('font-size', '14px')
                .text('Word Frequency by Agency (Stacked - Top 30 Agencies)');
        }
    };

    d3.json("agency_name.json").then(function(data) {
        agencyNameData = data; // Assign loaded data to the global variable
        const agencyListDiv = d3.select("#agency-help-list");
        for (const shortName in data) {
            const fullName = data[shortName];
            agencyListDiv.append("div")
                .attr("class", "agency-item")
                .html(`
                    <span class="agency-short-name">${shortName}</span>
                    <span class="agency-full-name">${fullName}</span>
                `);
        }
    });

    function filterAgencyHelp() {
        const searchInput = document.getElementById('agency-help-search');
        const filterValue = searchInput.value.toLowerCase();
        const agencyListItems = document.querySelectorAll('#agency-help-list .agency-item');

        agencyListItems.forEach(item => {
            const shortName = item.querySelector('.agency-short-name').textContent.toLowerCase();
            const fullName = item.querySelector('.agency-full-name').textContent.toLowerCase();

            if (shortName.includes(filterValue) || fullName.includes(filterValue)) {
                item.style.display = ''; // Show the item
            } else {
                item.style.display = 'none'; // Hide the item
            }
        });
    }

    // const createWordCloudChart = (data) => {
    //     wordCloudChartDiv.selectAll('*').remove();

    //     if (!data || data.length === 0) {
    //         wordCloudChartDiv.append('text')
    //             .attr('x', 20)
    //             .attr('y', 20)
    //             .text("No data available");
    //         return;
    //     }

    //     const wordsForCloud = [];
    //     data.forEach(agencyData => {
    //         agencyData.top_words.forEach(wordInfo => {
    //             wordsForCloud.push({text: wordInfo.word, size: Math.sqrt(wordInfo.frequency)});
    //         });
    //     });

    //     const layout = d3.layout.cloud()
    //         .size([wordCloudChartDiv.node().getBoundingClientRect().width - 20, wordCloudChartDiv.node().getBoundingClientRect().height - 20])
    //         .words(wordsForCloud)
    //         .padding(5)
    //         .rotate(() => 0)
    //         .fontSize(d => d.size)
    //         .on("end", drawWordCloud);

    //     layout.start();

    //     function drawWordCloud(words) {
    //         wordCloudChartDiv.append("svg")
    //             .attr('width', layout.size()[0])
    //             .attr('height', layout.size()[1])
    //             .append("g")
    //             .attr("transform", `translate(${layout.size()[0] / 2},${layout.size()[1] / 2})`)
    //             .selectAll("text")
    //             .data(words)
    //             .enter().append("text")
    //             .style("font-size", d => d.size + 'px')
    //             .style("fill", (_, i) => materialColors.accent[i % materialColors.accent.length])
    //             .attr("text-anchor", "middle")
    //             .attr("transform", d => `translate(${[d.x, d.y]})rotate(${d.rotate})`)
    //             .text(d => d.text);
    //     }

    //     wordCloudChartDiv.append('text')
    //         .attr('x', wordCloudChartDiv.node().getBoundingClientRect().width / 2)
    //         .attr('y', 20)
    //         .attr('text-anchor', 'middle')
    //         .style('font-size', '14px')
    //         .text('Word Cloud of Top Words');
    // };


    // --- Update Charts ---
    const updateCharts = () => {
        const filteredData = filterData();
        createAgencyWordCountChart(filteredData);
        createBarChart(filteredData);
        createLeastWordCountAgenciesChart(filteredData);
        createTotalWordsSummaryChart(filteredData);
        createStackedBarChart(filteredData);
        // createWordCloudChart(filteredData);
    };

    // --- Event Handlers ---
    agencyFilter.on('input', updateAgencyList);
    wordFilter.on('input', updateWordList);

    resetButton.on('click', () => {
        selectedAgencies = ['all'];
        selectedWords = [];
        agencyFilter.property('value', '');
        wordFilter.property('value', '');
        updateAgencyList();
        updateWordList();
        updateSelectedAgencies();
        updateSelectedWords();
        updateCharts();
    });

    // --- Data Loading and Initialization ---
    d3.json(dataUrl).then(data => {
        allData = data;
        allAgencies = getAgencies(data);
        allWords = getAllWords(data);
        filteredAgencies = ['all', ...allAgencies];
        filteredWords = allWords;

        // Calculate total word count for each agency to determine top agencies
        const agencyWordCounts = d3.rollup(allData,
            v => d3.sum(v[0].top_words, w => w.frequency),
            d => d.agency
        );
        initialTopAgencies = Array.from(agencyWordCounts)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 40)
            .map(d => d[0]);


        updateAgencyList();
        updateWordList();
        updateSelectedAgencies();
        updateSelectedWords();
        updateCharts();
    }).catch(error => {
        console.error("Error loading data:", error);
        // Handle error
    });
});
