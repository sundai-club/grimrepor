const fs = require('fs');
const axios = require('axios');
const csv = require('csv-parser');
const path = require('path');

// Define the path to the input and output files
const inputCsvPath = path.join(__dirname, 'paper_repo_info.csv');
const outputJsonPath = path.join(__dirname, 'paper_repo_info.json');

// Function to read requirements.txt from the provided URL
async function fetchRequirements(requirementsUrl) {
  try {
    const response = await axios.get(requirementsUrl);
    return response.data;
  } catch (error) {
    console.error(`Error fetching requirements.txt from ${requirementsUrl}:`, error);
    if (error.response && error.response.status === 403) {
      process.exit(1); // Exit the process with error code 1 if the error is 403
    }
    return ''; // Return empty string if there's an error
  }
}

// Main function to read the CSV, process each row, and save the JSON file
async function processCsvToJson() {
  const results = [];

  // Wrap the CSV reading and processing in a promise
  const csvProcessing = new Promise((resolve, reject) => {
    fs.createReadStream(inputCsvPath)
      .pipe(csv())
      .on('data', (row) => {
        // Check if the requirementsUrl contains "requirements.txt not found"
        if (!row.requirementsUrl.includes('requirements.txt not found')) {
          results.push(row); // Push rows to results for later processing
        }
      })
      .on('end', resolve)
      .on('error', reject);
  });

  await csvProcessing;

  // Process the results by fetching requirements.txt for each row
  const enhancedResults = await Promise.all(
    results.map(async (row) => {
      const requirements = await fetchRequirements(row.requirementsUrl);
      return { ...row, requirements }; // Add the fetched requirements to the row data
    })
  );

  // Save the enhanced results as a JSON file
  fs.writeFileSync(outputJsonPath, JSON.stringify(enhancedResults, null, 2));
  console.log('CSV data successfully processed and saved as JSON.');
}

// Run the main function
processCsvToJson().catch((error) => {
  console.error('Error processing CSV to JSON:', error);
});
