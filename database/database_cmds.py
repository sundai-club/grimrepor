import os
import sys
import re
import subprocess
import pandas as pd
import requests
import json
import mysqlx
import asyncio
from multiprocessing import Pool, Manager
from functools import partial
import math
from datetime import datetime
from bs4 import BeautifulSoup
from dotenv import load_dotenv

"""
To run:
./setup/create_venv.sh
./setup/mysql_setup.sh
source venv/bin/activate
(venv) python3 database/database_cmds.py
"""

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(ROOT)

from utils.decorators import timeit

load_dotenv()

# Database configuration
DATABASE_NAME = os.getenv('DATABASE_NAME') or "grimrepor_db"
MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_PORT = int(os.getenv('MYSQL_PORT', 33060))

TABLE_NAME = "papers_and_code"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
OS = sys.platform


def is_mysql_installed() -> bool:
    """Check if MySQL server and client are installed"""
    if OS == "linux":
        try:
            # Check MySQL client
            client_check = subprocess.run(['dpkg', '-l', 'mysql-client'],
                capture_output=True, check=False)
            # Check MySQL server
            server_check = subprocess.run(['dpkg', '-l', 'mysql-server'],
                capture_output=True, check=False)
            return client_check.returncode == 0 and server_check.returncode == 0
        except Exception as e:
            print(f"Error checking MySQL installation: {e}")
            return False
    elif OS == "darwin":
        try:
            result = subprocess.run(['brew', 'list', 'mysql'],
                capture_output=True, check=False)
            return result.returncode == 0
        except Exception as e:
            print(f"Error checking MySQL installation: {e}")
            return False
    return False

def launch_server() -> bool:
    if OS == "linux":
        try:
            subprocess.run(['sudo', 'systemctl', 'start', 'mysql'], check=True)
            print("MySQL server started successfully on Linux.\n")
            return True
        except Exception as e:
            print(f"Error starting MySQL server on Linux: {str(e)}")
            return False
    elif OS == 'darwin':
        try:
            subprocess.run(['brew', 'services', 'start', 'mysql'], check=True)
            print("MySQL server started successfully on macOS.\n")
            return True
        except Exception as e:
            print(f"Error starting MySQL server on macOS: {str(e)}")
            return False
    else:
        print("Unsupported OS")
        return False

def is_mysql_running() -> bool:
    """Check if MySQL server is running"""
    run_check = f"mysqladmin ping -u {MYSQL_USER} --password={MYSQL_PASSWORD}"
    try:
        subprocess.run(run_check.split(), capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def login_server() -> bool:
    login_cmd = f"mysql -u {MYSQL_USER} --password={MYSQL_PASSWORD} -e 'SELECT 1;'"
    try:
        subprocess.run(login_cmd, shell=True, check=True)
        print(f"Successfully logged into MySQL server as {escape_value(MYSQL_USER)}@{escape_value(MYSQL_HOST)}")
    except subprocess.CalledProcessError as e:
        print(f"Error logging into MySQL server: {e}")
        return False
    return True

def initialize_mysql() -> bool:
    """
    This needs to be run to ensure MySQL is installed and running
    """
    env_path = os.path.join(ROOT, '.env')
    if not os.path.exists(env_path):
        print(f".env file not found at {env_path}")

    if OS != 'linux' and OS != 'darwin':
        raise Exception('Unsupported OS')

    if not is_mysql_installed():
        print("MySQL is not installed. Please run database/mysql_setup.sh to install MySQL.")
        sys.exit(1)
    else:
        print("MySQL is installed.")

    if not launch_server():
        print("Error launching MySQL server")
        sys.exit(1)
    else:
        print("MySQL server has been launched.")

    if not is_mysql_running():
        print("Failed to start MySQL server. Check system logs")
        sys.exit(1)
    else:
        print("MySQL server is running.")

    if not login_server():
        print("Failed to login to MySQL server.")
        sys.exit(1)
    else:
        print("Logged into MySQL server.")

    print("MySQL server is ready for use.")
    return True

def create_session(db_name: str = None) -> object:
    """
    create mysql server session
    can create a database without giving db_name
    and call later with db_name to connect to the database
    returns the session object (open connection)
    """
    conn_params = {
        "host": MYSQL_HOST,
        "port": MYSQL_PORT,
        "user": MYSQL_USER,
        "password": MYSQL_PASSWORD
    }

    try:
        session = mysqlx.get_session(**conn_params)
        schema = None
        if db_name:
            schema = session.get_schema(db_name)
            if not schema.exists_in_database():
                create_db(db_name)
                schema = session.get_schema(db_name)
            # WARNING: we intentionally select the database for the session
            # this will propagate to chained functions but not to new sessions
            session.sql(f"USE {db_name}").execute()  # Ensure the database is selected

        print(f"Successfully connected to MySQL as '{conn_params['user']}'@'{conn_params['host']}'")
        return session, schema
    except mysqlx.InterfaceError as e:
        print(f"InterfaceError: {e}")
    except mysqlx.ProgrammingError as e:
        print(f"ProgrammingError: {e}")
    except mysqlx.DatabaseError as e:
        print(f"DatabaseError: {e}")
    except Exception as e:
        print(f"Error connecting to mysql as '{conn_params['user']}'@'{conn_params['host']}'\n{str(e)}")
    sys.exit(1)

def create_db(db_name: str = "grimrepor_db") -> bool:
    """
    create a new database
    ok if the database already exists
    """
    session = None
    try:
        session, _ = create_session()
    except Exception as e:
        print(f"Error creating session: {str(e)}")
        return False

    try:
        session.sql(f"CREATE DATABASE IF NOT EXISTS {db_name}").execute()
        print(f"Database '{db_name}' is active.")
        return True
    except mysqlx.DatabaseError as e:
        if "schema exists" in str(e).lower():
            print(f"Database {db_name} already exists.")
            return True
    except Exception as e:
        print(f"Error creating database: {str(e)}")
        return False
    finally:
        session.close()

def show_databases() -> bool:
    session = None
    try:
        session, _ = create_session()
    except Exception as e:
        print(f"Error creating session: {str(e)}")
        return False

    try:
        print(f"\nDatabases: {session.get_schemas()}\n")
        if session:
            session.close()
        return True
    except Exception as e:
        print(f"Error showing databases: {str(e)}")
        return False
    finally:
        if session: session.close()

def show_all_tables(db_name: str = "grimrepor_db") -> bool:
    """
    show all tables in the database
    """
    session, schema = create_session(db_name)
    if not session: return False
    try:
        print(f"Tables in {db_name = }\n")
        _ = [ print(f'  {table.get_name()}') for table in schema.get_tables() ]
        print()
        session.close()
        return True
    except Exception as e:
        print(f"Error showing tables: {str(e)}")
        return False
    finally:
        session.close()

def show_table_columns(table_name: str, db_name: str = "grimrepor_db") -> bool:
    session, _ = create_session(db_name)
    if not session: return False
    print(f"\nColumns in table '{table_name}'\n")
    try:
        result = session.sql(f"SHOW COLUMNS FROM {table_name}").execute()
        for col in result.fetch_all():
            print(f'  {col}')
        print()
        return True
    except Exception as e:
        print(f"Error showing table columns: {str(e)}")
        return False
    finally:
        session.close()

def show_table_contents(table_name: str, db_name: str = "grimrepor_db", limit_num: int = None) -> bool:
    """
    SELECT * FROM table_name;
    option to limit the number of rows returned
    shows all columns
    """
    session, schema = create_session(db_name)
    if not session: return False

    try:
        print(f"Contents of {table_name}\n")
        result = None
        try:
            if limit_num is None:
                result = schema.get_table(table_name).select().execute()
            else:
                result = schema.get_table(table_name).select().limit(limit_num).execute()
        except Exception as e:
            print(f"Error selecting from table: {str(e)}")
            return False

        for row in result.fetch_all():
            print(row)
        return True

    except Exception as e:
        print(f"Error showing table contents: {str(e)}")
        return False
    finally:
        session.close()

def drop_table(table_name: str, db_name: str = "grimrepor_db") -> bool:
    """
    drop a table from the database
    be careful with this command as it will delete a table
    """
    session, _ = create_session(db_name)
    try:
        session.sql("SET FOREIGN_KEY_CHECKS = 0").execute()  # Disable foreign key checks
        session.sql(f"DROP TABLE IF EXISTS {table_name}").execute()
        print(f"Table {table_name} dropped successfully.")
        return True
        session.sql("SET FOREIGN_KEY_CHECKS = 1").execute()  # Re-enable foreign key checks
    except Exception as e:
        print(f"Error dropping table: {str(e)}")
        return False
    finally:
        if session: session.close()

def drop_all_tables(db_name: str = "grimrepor_db") -> bool:
    """
    drop all of the tables
    find all the tables in the database
    then drop them one by one
    """
    ans = input("Are you sure you want to drop all tables? (y/n): ")
    if ans.lower() != 'y':
        print("Tables not dropped.")
        return False

    session, schema = create_session(db_name)
    if not session: return False

    try:
        tables = schema.get_tables()
        session.sql("SET FOREIGN_KEY_CHECKS = 0").execute()  # Disable foreign key checks
        for table in tables:
            table_name = table.get_name()
            session.sql(f"DROP TABLE IF EXISTS {table_name}").execute()
            print(f"Table {table_name} dropped successfully.")
        session.sql("SET FOREIGN_KEY_CHECKS = 1").execute()  # Re-enable foreign key checks
        return True
    except Exception as e:
        print(f"Error dropping tables: {str(e)}")
        return False
    finally:
        session.close()

def delete_data_from_table(table_name: str, db_name: str = "grimrepor_db") -> bool:
    """
    delete all data from a table
    keep column headers
    """
    session, _ = create_session(db_name)
    if not session: return False

    try:
        session.sql(f"TRUNCATE TABLE {table_name}").execute()
        print(f"Data deleted from table {table_name}.")
        return True
    except Exception as e:
        print(f"Error deleting data from table: {str(e)}")
        return False
    finally:
        session.close()

def escape_value(value):
    """
    helper function to prepare data for SQL table insertion
    """
    if value is None:
        return 'NULL'
    # escape single quotes and backslashes
    return "'" + str(value).replace("'", "''").replace("\\", "\\\\") + "'"

def process_chunk_json(chunk, shared_counts, lock, table_name, db_name):
    session, schema = create_session(db_name)
    if not session: return False

    local_inserted = 0
    local_skipped = 0

    try:
        for row in chunk:
            if isinstance(row, str):
                try:
                    row = json.loads(row)
                except json.JSONDecodeError:
                    local_skipped += 1
                    continue

            if not row.get('paper_url_abs'):
                local_skipped += 1
                continue
            elif re.match(r"http[s]{0,1}://.+/http[s]{0,1}-github.com", row.get('repo_url')):
                local_skipped += 1
                continue

            values = [
                escape_value(row.get('paper_title')),
                escape_value(row.get('paper_arxiv_id')),
                escape_value(row.get('paper_url_abs')),
                escape_value(row.get('paper_url')),
                escape_value(row.get('repo_url')),
            ]

            insert_cmd = f"""
            INSERT INTO {table_name} (
                paper_title, paper_arxiv_id, paper_arxiv_url, paper_pwc_url, github_url
            ) VALUES (
                {values[0]}, {values[1]}, {values[2]}, {values[3]}, {values[4]}
            )"""

            try:
                session.sql(insert_cmd).execute()
                session.commit()
                local_inserted += 1

            except Exception:
                local_skipped += 1
                continue

        # Update shared counters with lock
        with lock:
            shared_counts['inserted'] += local_inserted
            shared_counts['skipped'] += local_skipped

    finally:
        session.close()

def print_row_count(db_name, table_name):
    while True:
        time.sleep(10)  # Print row count every 10 seconds
        session, _ = create_session(db_name)
        try:
            result = session.sql(f"SELECT COUNT(*) FROM {table_name}").execute()
            row_count = result.fetch_one()[0]
            print(f"Total rows in {table_name}: {row_count}")
        except Exception as e:
            print(f"Error fetching row count: {str(e)}")
        finally:
            session.close()

def convert_to_mysql_date(iso_datetime):
    """
    Convert ISO 8601 datetime (e.g., '2018-05-30T01:01:19Z') to MySQL DATE format ('2018-05-30').
    """
    try:
        # Parse the ISO 8601 datetime string
        dt = datetime.strptime(iso_datetime, "%Y-%m-%dT%H:%M:%SZ")
        # Return in MySQL-compatible DATE format
        return dt.strftime("%Y-%m-%d")
    except Exception as e:
        print(f"Error converting datetime value: {iso_datetime} - {str(e)}")
        return None

def extract_owner_repo(github_url):
    """
    Extract owner and repository name from the GitHub URL.
    helper function for populate_table_github_api
    """
    regex = r"github\.com\/([^\/]+)\/([^\/]+)"
    match = re.search(regex, github_url)
    if match:
        return match.groups()
    return None

def get_contributors(owner, repo):
    """
    Fetch contributors from the GitHub repository.
    helper function for populate_table_github_api
    """
    contributors_url = f"https://api.github.com/repos/{owner}/{repo}/contributors"

    # Get GitHub token from environment variable
    try:
        headers = {}
        if GITHUB_TOKEN:
            headers['Authorization'] = f'token {GITHUB_TOKEN}'
        else:
            print(f"Warning: No GitHub token found. Rate limits will be strict.")

        response = requests.get(contributors_url, headers=headers)

        # Check rate limits from response headers
        rate_limit = response.headers.get('X-RateLimit-Remaining', 'N/A')
        rate_reset = response.headers.get('X-RateLimit-Reset', 'N/A')
        if rate_reset != 'N/A':
            reset_time = datetime.fromtimestamp(int(rate_reset)).strftime('%Y-%m-%d %H:%M:%S')
        else:
            reset_time = 'N/A'

        if response.status_code == 403:
            if rate_limit == '0':
                print(f"\nGitHub API rate limit exceeded!")
                print(f"Rate limit will reset at: {reset_time}")
            else:
                print(f"\nRepository {owner}/{repo} access forbidden (403)")
                print(f"This might be a private repository or the token might not have sufficient permissions")
            return None
        elif response.status_code == 404:
            print(f"\nRepository {owner}/{repo} not found (404)")
            print(f"The repository might have been deleted or renamed")
            return None
        elif response.status_code == 200:
            contributors = [contributor['login'] for contributor in response.json()]
            if not contributors:
                print(f"\nNo contributors found for {owner}/{repo}")
                return None
            return ', '.join(contributors)
        else:
            print(f"\nError fetching contributors for {owner}/{repo}")
            print(f"Status code: {response.status_code}")
            print(f"Remaining API calls: {rate_limit}")
            print(f"Rate limit resets at: {reset_time}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"\nNetwork error fetching contributors for {owner}/{repo}")
        print(f"Error: {str(e)}")
        return None
    except Exception as e:
        print(f"\nUnexpected error fetching contributors for {owner}/{repo}")
        print(f"Error: {str(e)}")
        return None

def get_last_commit_date(owner, repo, file_path):
    """
    Fetch the last commit date for a specific file in a GitHub repository.
    """
    try:
        for branch in ['main', 'master']:
            commits_url = f"https://api.github.com/repos/{owner}/{repo}/commits?path={file_path}&sha={branch}&per_page=1"
            response = requests.get(commits_url, headers={'Authorization': f'token {GITHUB_TOKEN}'})
            if response.status_code == 200:
                commit_data = response.json()
                if commit_data:
                    return convert_to_mysql_date(commit_data[0].get('commit', {}).get('author', {}).get('date', None))
        return None  # No valid commit date found
    except Exception as e:
        print(f"Error fetching last commit date for {file_path} in {owner}/{repo}: {str(e)}")
        return None

def get_file_content(file_url):
    """
    Fetch the content of a file from the given URL.
    Prioritize raw user content; fallback to alternative paths if raw URL fails.
    """
    try:
        # Convert GitHub blob URL to raw URL if necessary
        raw_file_url = (
            file_url.replace('github.com', 'raw.githubusercontent.com')
                    .replace('/blob/', '/')
            if 'github.com' in file_url and '/blob/' in file_url
            else file_url
        )

        # Attempt to fetch raw file content
        response = requests.get(raw_file_url)
        if response.status_code == 200:
            return response.text

        # If raw URL fails, fallback to the original blob URL
        response = requests.get(file_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            code_element = soup.find('table', {'class': 'highlight'}) or soup.find('pre')
            if code_element:
                return code_element.get_text()

        # If all attempts fail, try common alternative branches for raw content
        if 'github.com' in file_url:
            parts = file_url.split('github.com/')[1].split('/')
            owner, repo = parts[0], parts[1]
            req_files = ['requirements.txt']
            branches = ['main', 'master']

            for branch in branches:
                for req_file in req_files:
                    alt_raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{req_file}"
                    alt_response = requests.get(alt_raw_url)
                    if alt_response.status_code == 200:
                        return alt_response.text
        return None

    except Exception as e:
        print(f"Error fetching file content from {file_url}: {str(e)}")
        return None


class Table:
    def __init__(self, table_name: str, db_name: str = "grimrepor_db"):
        self.table_name = table_name
        self.db_name = db_name
        # database has to work before creating tables
        # create_db(db_name=db_name)

    def create_table_full(self) -> bool:
        """
        create a table in the database
        note that in create session, the database is selected

        Unique constraints are necessary because there are 283 instances of these exact fields:
            "paper_url": "https://paperswithcode.com/paper/a-neural-algorithm-of-artistic-style",
            "paper_title": "A Neural Algorithm of Artistic Style",
            "paper_arxiv_id": "1508.06576",
            "paper_url_abs": "http://arxiv.org/abs/1508.06576v2",
            "paper_url_pdf": "http://arxiv.org/pdf/1508.06576v2.pdf",

        all with different "repo_url" values (github's associated)
        """
        session, schema = create_session(self.db_name)
        if not session:
            return False

        create_table_cmd = f"""
        CREATE TABLE IF NOT EXISTS {self.table_name} (
            id INT AUTO_INCREMENT PRIMARY KEY,

            paper_title VARCHAR(255) NOT NULL UNIQUE,
            paper_arxiv_id VARCHAR(255) DEFAULT NULL UNIQUE,
            paper_arxiv_url VARCHAR(255) DEFAULT NULL UNIQUE,
            paper_pwc_url VARCHAR(255) DEFAULT NULL UNIQUE,
            github_url VARCHAR(255) DEFAULT NULL UNIQUE,

            contributors VARCHAR(255) DEFAULT NULL,
            build_sys_type VARCHAR(255) DEFAULT NULL,
            deps_file_url VARCHAR(255) DEFAULT NULL UNIQUE,
            deps_file_content_orig MEDIUMTEXT,
            deps_last_commit_date DATE DEFAULT NULL,

            build_status_orig VARCHAR(255) DEFAULT NULL,
            deps_file_content_edited MEDIUMTEXT,
            build_status_edited VARCHAR(255) DEFAULT NULL,
            datetime_latest_build DATETIME DEFAULT NULL,
            num_build_attempts INT DEFAULT 0,
            py_valid_versions VARCHAR(255) DEFAULT NULL,

            github_fork_url VARCHAR(255) DEFAULT NULL UNIQUE,
            pushed_to_fork BOOLEAN DEFAULT FALSE,
            pull_request_made BOOLEAN DEFAULT FALSE,
            tweet_posted BOOLEAN DEFAULT FALSE,
            tweet_url VARCHAR(255) DEFAULT NULL UNIQUE
        );"""
        try:
            # Check if the table exists
            table_exists = False
            tables = schema.get_tables()
            for table in tables:
                if table.get_name() == self.table_name:
                    table_exists = True
                    break

            if table_exists:
                print(f"Table {self.table_name} already exists.")
                return True

            # Create the table if it does not exist
            session.sql(create_table_cmd).execute()
            print(f"Table {self.table_name} created successfully.")
            return True
        except Exception as e:
            print(f"Error creating table: {str(e)}")
            return False
        finally:
            session.close()

    @timeit
    def populate_table_from_papers_and_code_json_sequential(self, row_limit: int = None) -> bool:
        """
        populate the table with data from data/links-between-papers-and-code.json
        sample:
        {
            "paper_url": "https://paperswithcode.com/paper/attngan-fine-grained-text-to-image-generation",
            "paper_title": "AttnGAN: Fine-Grained Text to Image Generation with Attentional Generative Adversarial Networks",
            "paper_arxiv_id": "1711.10485",
            "paper_url_abs": "http://arxiv.org/abs/1711.10485v1",
            "paper_url_pdf": "http://arxiv.org/pdf/1711.10485v1.pdf",
            "repo_url": "https://github.com/bprabhakar/text-to-image",
            "is_official": false,
            "mentioned_in_paper": false,
            "mentioned_in_github": false,
            "framework": "pytorch"
        },
        fill these fields of the table:
        paper_title VARCHAR(255) NOT NULL UNIQUE,
        paper_arxiv_id VARCHAR(255) DEFAULT NULL UNIQUE,
        paper_arxiv_url VARCHAR(255) DEFAULT NULL UNIQUE,
        paper_pwc_url VARCHAR(255) NOT NULL UNIQUE,
        github_url VARCHAR(255) NOT NULL,

        # db_column : json_col
        # 'paper_title' : 'paper_title',
        # 'paper_arxiv_id' : 'paper_arxiv_id',
        # 'paper_arxiv_url' : 'paper_url_abs',
        # 'paper_pwc_url' : 'paper_url',
        # 'github_url' : 'repo_url'

        Not all rows are inserted due to unique and not null constraints
        clashes mainly on paper_url, paper_arxiv_id
        Rows inserted: 185013 of 272525
        """
        session, schema = create_session(self.db_name)
        if not session: return False

        file_loc = os.path.join(ROOT, "data", "links-between-papers-and-code.json")
        data = None
        with open(file_loc, 'r', encoding='ascii') as f:
            data = json.load(f)
        if not data:
            print("JSON file not read in correctly")
            return False

        table = schema.get_table(self.table_name)
        rows_inserted, rows_skipped = 0, 0

        try:
            for idx, row in enumerate(data):
                if row_limit and idx >= row_limit: break

                # convert string to dict if needed
                if isinstance(row, str):
                    try:
                        row = json.loads(row)
                    except json.JSONDecodeError as e:
                        print(f"Error parsing row #{idx}: {str(e)}")
                        continue

                if not row.get('paper_url_abs'):
                    print(f"Skipping row #{idx}: Missing required paper_pwc_url")
                    rows_skipped += 1
                    continue
                elif re.match(r"http[s]{0,1}://.+/http[s]{0,1}-github.com", row.get('repo_url')):
                    # skip repos with multiple http[s] occurences inside
                    # retrieving raw github file content can fail
                    # "repo_url":
                    # "https://github.com/NateKoenig/https-github.com-Kautenja-a-neural-algorithm-of-artistic-style",
                    rows_skipped += 1
                    continue

                values = [
                    escape_value(row.get('paper_title')),
                    escape_value(row.get('paper_arxiv_id')),
                    escape_value(row.get('paper_url_abs')),
                    escape_value(row.get('paper_url')),
                    escape_value(row.get('repo_url')),
                ]
                insert_update_cmd = f"""
                INSERT INTO {self.table_name} (
                    paper_title, paper_arxiv_id, paper_arxiv_url, paper_pwc_url, github_url
                ) VALUES (
                    {values[0]}, {values[1]}, {values[2]}, {values[3]}, {values[4]}
                )"""
                try:
                    session.sql(insert_update_cmd).execute()
                    session.commit()
                    rows_inserted += 1
                    if rows_inserted % 10000 == 0:
                        print(f"-- Rows inserted: {rows_inserted} --")

                except Exception as e:
                    print(f"Error inserting row #{idx}: {str(e)}")
                    rows_skipped += 1
                    continue

            if row_limit:
                print(f"Rows inserted: {rows_inserted}, Rows skipped: {rows_skipped} of attempted {row_limit}")
            else:
                print(f"Rows inserted: {rows_inserted}, Rows skipped: {rows_skipped} of attempted {len(data)}")
            print(f"Total rows in table: {table.count()}")
        except Exception as e:
            print(f"Error populating table: {str(e)}")
            return False
        finally:
            session.close()
        return True

    @timeit
    def populate_table_from_papers_and_code_json_parallel(self, row_limit: int = None) -> bool:
        print("Attempting to popualte table from JSON file in parallel mode...")
        file_loc = os.path.join(ROOT, "data", "links-between-papers-and-code.json")
        try:
            with open(file_loc, 'r', encoding='ascii') as f:
                data = json.load(f)
            if not data:
                print("JSON file not read in correctly")
                return False
        except Exception as e:
            print(f"Error reading JSON file: {str(e)}")
            return False

        data = data[:row_limit] if row_limit else data

        # Calculate chunk size and number of processes
        num_processes = min(os.cpu_count(), 16)
        chunk_size = math.ceil(len(data) / num_processes)
        chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

        # Shared counters and lock
        manager = Manager()
        shared_counts = manager.dict()
        shared_counts['inserted'] = 0
        shared_counts['skipped'] = 0
        lock = manager.Lock()

        # Process chunks in parallel
        with Pool(processes=num_processes) as pool:
            pool.map(
                partial(process_chunk_json,
                    shared_counts=shared_counts,
                    lock=lock,
                    table_name=self.table_name,
                    db_name=self.db_name),
                chunks
            )

        # Print final statistics
        print(f"Rows inserted: {shared_counts['inserted']}, "
            f"Rows skipped: {shared_counts['skipped']} "
            f"of attempted {len(data)}")

        return True

    @timeit
    def populate_table_from_github_repo_sequential(self, row_limit: int = None) -> bool:
        """
        Populate additional columns in the table using GitHub repository data.
        This includes:

        build_sys_type ['Not found', 'pip', 'conda']
        deps_file_url  f"https://raw.githubusercontent.com/{owner}/{repo}/{main,master}/{requirements.txt,env.yml,environment.yml}"
        deps_file_content_orig  module0==1.0.2 module0==2.3.4
        contributors  github_username1, github_username2
        requirements_last_commit_date  'YYYY-MM-DD'

        if build_sys_type == "Not found" then the other fields are left NULL
        """
        # TODO: optimize speed
        session, schema = create_session(self.db_name)
        if not session: return False

        rows_updated, rows_skipped = 0, 0
        table = schema.get_table(self.table_name)

        try:
            # Fetch all rows from the table
            # avoid rechecking rows where the build_sys_type has been populated (previously hit this section)
            rows = table.select('github_url, paper_title').where('build_sys_type IS NULL').execute().fetch_all()
            rows = rows[:row_limit] if row_limit else rows

            for row in rows:
                github_url = row[0]  # Now correctly points to github_url
                paper_title = row[1]  # Now correctly points to paper_title

                if github_url:
                    owner_repo = extract_owner_repo(github_url)
                    if owner_repo:
                        owner, repo = owner_repo

                        # Determine the requirements.txt file URL
                        prefix = "https://raw.githubusercontent.com"
                        builds_and_paths = {
                        'pip':
                        [
                            f"{prefix}/{owner}/{repo}/main/requirements.txt",
                            f"{prefix}/{owner}/{repo}/master/requirements.txt"
                        ],
                        'conda':
                        [
                            f"{prefix}/{owner}/{repo}/main/environment.yml",
                            f"{prefix}/{owner}/{repo}/master/environment.yml",
                            f"{prefix}/{owner}/{repo}/main/env.yml",
                            f"{prefix}/{owner}/{repo}/master/env.yml"
                        ]}
                        deps_file_content_orig, deps_file_url, deps_last_commit_date = None, None, None
                        build_sys_type = "Not found"
                        for build_sys, deps_files in builds_and_paths.items():
                            for deps_file_path in deps_files:
                                content = self.get_file_content(deps_file_path)
                                if content:
                                    deps_file_content_orig = content
                                    deps_file_url = deps_file_path
                                    build_sys_type = build_sys
                                    break

                        # Determine build system type
                        # hinge upon value of build_sys_type for future table queries
                        # default sql update table if we don't find a requirements file
                        update_cmd = f"""
                        UPDATE {self.table_name}
                        SET build_sys_type = {escape_value(build_sys_type)}
                        WHERE paper_title = {escape_value(paper_title)}
                        """

                        # we found a requirements file, so fetch additional info from repo
                        if build_sys_type != "Not found":
                            # Fetch last commit date for the requirements file
                            if deps_file_url:
                                deps_last_commit_date = self.get_last_commit_date(
                                    owner, repo, 'requirements.txt'
                                )

                            # Get contributors
                            contributors = get_contributors(owner, repo)
                            if contributors and len(contributors) > 255:
                                contributors = contributors[:252] + '...'

                            # Escape all values for SQL
                            escaped_values = {
                                'build_sys_type': escape_value(build_sys_type),
                                'deps_file_url': escape_value(deps_file_url),
                                'deps_file_content_orig': escape_value(deps_file_content_orig),
                                'contributors': escape_value(contributors),
                                'deps_last_commit_date': escape_value(deps_last_commit_date),
                                'paper_title': escape_value(paper_title)
                            }
                            # overwrite default command if fields can be scraped
                            update_cmd = f"""
                            UPDATE {self.table_name}
                            SET build_sys_type = {escaped_values['build_sys_type']},
                                deps_file_url = {escaped_values['deps_file_url']},
                                deps_file_content_orig = {escaped_values['deps_file_content_orig']},
                                contributors = {escaped_values['contributors']},
                                deps_last_commit_date = {escaped_values['deps_last_commit_date']}
                            WHERE paper_title = {escaped_values['paper_title']};
                            """

                        try:
                            session.sql(update_cmd).execute()
                            rows_updated += 1
                            if rows_updated % 100 == 0:
                                print(f"-- Rows updated: {rows_updated} --\n")

                        except Exception as e:
                            rows_skipped += 1
                            print(f"Error updating row for {paper_title}: {str(e)}")
                            continue

            print(f"Total rows updated with additional info: {rows_updated}")
            print(f"Rows skipped: {rows_skipped}\n")
            if row_limit:
                print(f"(Limited to {row_limit} rows)")
            return True

        except Exception as e:
            print(f"Error populating additional info: {str(e)}")
            return False
        finally:
            session.close()


if __name__ == '__main__':
    row_limit_parse = 1000
    row_limit_view = 10

    # make sure mysql is installed and running
    initialize_mysql()
    create_db(db_name=DATABASE_NAME) # do once
    show_databases()
    show_all_tables(db_name=DATABASE_NAME)
    drop_all_tables(db_name=DATABASE_NAME) # for testing

    # have function to populate the table from each data source
    # FIND      first 5 cols from 'links-between-papers-and-code.json'
    # QUALIFY   next 5 columns web scraping the git repo
    # BUILD     venv build and see if reqs install correctly
    # FIX       update reqs, find python compat version(s)
    # PUBLISH   git fork, git clone, git push, git pull request, tweet
    # # import function into another file to do the cell updates...

    papers_and_code = Table(table_name=TABLE_NAME, db_name=DATABASE_NAME)
    papers_and_code.create_table_full()
    show_table_columns(table_name=TABLE_NAME, db_name=DATABASE_NAME)
    # 185,000 new rows of 272,000 possible \/
    # sequential took 158 seconds on M3 Max MBP with 14 cores, 96GB RAM
    # sequential took 459 seconds on 2x Xeon E5-2699 v4 server with 44 cores, 256GB RAM
    # papers_and_code.populate_table_from_papers_and_code_json_sequential()
    # parallel took 23 seconds on M3 Max MBP with 14 cores, 96GB RAM
    # parallel took 40 seconds on 2x Xeon E5-2699 v4 server with 44 cores, 256GB RAM
    papers_and_code.populate_table_from_papers_and_code_json_parallel()
    show_table_contents(table_name=TABLE_NAME, db_name=DATABASE_NAME, limit_num=row_limit_view)

    # given the 5000 github api call limit per hour, row limit is set here
    # 1000 insertions
    # took 1075 seconds on M3 Max MBP
    # took 920 seconds on 2x Xeon E5-2699 v4 server
    papers_and_code.populate_table_from_github_repo_sequential(row_limit=row_limit_parse)
    # TODO: parallelize github fetching code
    show_table_contents(table_name=TABLE_NAME, db_name=DATABASE_NAME, limit_num=row_limit_view)

    # build, fix, publish columns not filled in with this script (yet)

    show_all_tables(db_name=DATABASE_NAME)


"""
use a .env file at the root of the project see (.env.example) with the following:
MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, GITHUB_TOKEN, DATABASE_NAME
(venv) python3 database/database_cmds.py
"""
