require('dotenv').config(); // Load environment variables from .env
const axios = require('axios');
const fs = require('fs');
const path = require('path');
const csvWriter = require('csv-write-stream');

// Retrieve the GitHub personal access token from the .env file
const GITHUB_ACCESS_TOKEN = process.env.GITHUB_ACCESS_TOKEN;

// Helper function to extract owner and repository name from repo_url
function extractOwnerRepo(repoUrl) {
  const regex = /github\.com\/([^\/]+)\/([^\/]+)/;
  const match = repoUrl.match(regex);
  if (match) {
    const owner = match[1];
    const repo = match[2];
    return { owner, repo };
  }
  throw new Error("Invalid GitHub repository URL");
}

// Function to make authenticated GitHub API requests
async function makeGitHubRequest(url) {
  return axios.get(url, {
    headers: {
      'Authorization': `token ${GITHUB_ACCESS_TOKEN}`,
      'Accept': 'application/vnd.github.v3+json'
    }
  });
}

// Function to get the timestamp of the last commit to a specific file
async function getLastCommitDateForFile(owner, repo, filePath, branch) {
  try {
    const commitsUrl = `https://api.github.com/repos/${owner}/${repo}/commits?path=${filePath}&per_page=1&sha=${branch}`;
    const commitsResponse = await makeGitHubRequest(commitsUrl);
    const lastCommitDate = commitsResponse.data[0]?.commit?.author?.date || null;
    return lastCommitDate;
  } catch (error) {
    console.error(`Error fetching last commit for ${filePath}:`, error.message);
    return null;
  }
}

// Function to get GitHub repository data
async function getRepoDataFromUrl(repoUrl) {
  try {
    const { owner, repo } = extractOwnerRepo(repoUrl);
    const apiUrl = `https://api.github.com/repos/${owner}/${repo}`;

    // Get repository information
    const repoResponse = await makeGitHubRequest(apiUrl);
    const repoData = repoResponse.data;
    const defaultBranch = repoData.default_branch;

    // Get the list of repository contents
    const contentsUrl = `${apiUrl}/contents?ref=${defaultBranch}`;
    const contentsResponse = await makeGitHubRequest(contentsUrl);
    const contentsData = contentsResponse.data;

    // Detect README file
    const readmeFiles = ['README.md', 'README.txt', 'README.rst', 'README'];
    const readmeFile = readmeFiles.find(filename => contentsData.some(file => file.name.toLowerCase() === filename.toLowerCase()));
    const readmeExists = readmeFile ? `https://raw.githubusercontent.com/${owner}/${repo}/${defaultBranch}/${readmeFile}` : 'README not found';

    // Detect requirements.txt and get its last commit timestamp
    const requirementsFile = contentsData.find(file => file.name.toLowerCase() === 'requirements.txt');
    const requirementsExists = requirementsFile ? `https://raw.githubusercontent.com/${owner}/${repo}/${defaultBranch}/requirements.txt` : 'requirements.txt not found';

    let requirementsLastCommitDate = null;
    if (requirementsFile) {
      requirementsLastCommitDate = await getLastCommitDateForFile(owner, repo, 'requirements.txt', defaultBranch);
    }

    // Get prominent language
    const languagesUrl = `${apiUrl}/languages`;
    const languagesResponse = await makeGitHubRequest(languagesUrl);
    const languagesData = languagesResponse.data;
    const mostProminentLanguage = Object.keys(languagesData)[0] || 'No language detected';

    // Get number of stars and last commit date
    const stars = repoData.stargazers_count;
    const commitsUrl = `${apiUrl}/commits?per_page=1`;
    const commitsResponse = await makeGitHubRequest(commitsUrl);
    const lastCommitDate = commitsResponse.data[0]?.commit?.author?.date || 'No commits found';

    // Get contributors
    const contributorsUrl = `${apiUrl}/contributors`;
    const contributorsResponse = await makeGitHubRequest(contributorsUrl);
    const contributors = contributorsResponse.data.map(contributor => contributor.html_url);

    // Return repo information
    return {
      readmeUrl: readmeExists,
      requirementsUrl: requirementsExists,
      requirementsLastCommitDate: requirementsLastCommitDate || 'None',
      mostProminentLanguage,
      stars,
      lastCommitDate,
      contributors: contributors.join(', '),
    };
  } catch (error) {
    console.error('Error fetching repo data:', error.message);
    if (error.response && error.response.status === 403) {
      process.exit(1); // Exit the process with error code 1 if the error is 403
    }
    return null;
  }
}

// Function to process papers and save to CSV
async function processPapersAndSaveToCSV(offset = 0) {
  try {
    // Load the JSON file containing paper data
    const filePath = path.join(__dirname, 'links-between-papers-and-code.json');
    const paperDataList = JSON.parse(fs.readFileSync(filePath, 'utf8'));

    // Check if offset is valid
    if (offset >= paperDataList.length) {
      console.log('Offset exceeds the number of papers. Nothing to process.');
      return;
    }

    // Initialize the CSV writer
    const writer = csvWriter({ headers: ['paper_title', 'paper_url', 'paper_arxiv_id', 'repo_url', 'is_official', 'framework', 'readmeUrl', 'requirementsUrl', 'requirementsLastCommitDate', 'mostProminentLanguage', 'stars', 'lastCommitDate', 'contributors'] });
    const csvFilePath = path.join(__dirname, 'paper_repo_info.csv');
    writer.pipe(fs.createWriteStream(csvFilePath, { flags: 'a' })); // Append mode

    // Total papers and processing counter
    const totalPapers = paperDataList.length;
    let processedCount = 0;

    // Iterate over the paper data list starting from the offset
    for (let i = offset; i < paperDataList.length; i++) {
      const paperData = paperDataList[i];

      if (paperData.repo_url) {
        // Fetch repo information
        const repoInfo = await getRepoDataFromUrl(paperData.repo_url);

        if (repoInfo) {
          // Merge paper data with repo info and write to CSV
          const mergedData = {
            paper_title: paperData.paper_title,
            paper_url: paperData.paper_url,
            paper_arxiv_id: paperData.paper_arxiv_id,
            repo_url: paperData.repo_url,
            is_official: paperData.is_official,
            framework: paperData.framework,
            ...repoInfo,
          };
          writer.write(mergedData);
        }
      }

      // Log progress
      processedCount++;
      console.log(`Processed ${processedCount + offset} of ${totalPapers} papers.`);
    }

    // End the writer
    writer.end();
    console.log('All papers processed and saved to CSV.');
  } catch (error) {
    console.error('Error processing papers:', error.message);
  }
}

// Start the process with an offset
const offset = process.argv[2] ? parseInt(process.argv[2], 10) : 0; // Get offset from command line argument, default to 0
processPapersAndSaveToCSV(2442);
