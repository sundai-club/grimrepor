setup/mysql_setup.sh#!/bin/bash

set -e
echo

# git large file system installation
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Installing Git LFS for Linux..."
    sudo apt-get update
    sudo apt-get install git-lfs
    git lfs install
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Installing Git LFS for macOS..."
    brew update
    brew install git-lfs
    git lfs install
else
    echo "Unsupported operating system"
    exit 1
fi
# Pull LFS files after installation
git lfs pull

if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    if ! command -v mysql &> /dev/null; then
        echo "Installing MySQL on macOS..."
        brew install mysql
        brew services start mysql
    fi
else
    # Linux (Ubuntu/Debian)
    if ! command -v mysql &> /dev/null; then
        echo "Installing MySQL on Linux..."
        sudo apt update
        sudo apt install -y mysql-server mysql-client
        sudo systemctl start mysql
        echo "Setting up MySQL..."
    fi
fi

# get root path
ROOT=$(dirname $(dirname $(realpath $0)))

# Load environment variables
if [ ! -f "$ROOT/.env" ]; then
    echo ".env file not found at $ROOT/.env"
    exit 1
else
    . "$ROOT"/.env
fi

# Check if MySQL is running
if ! mysqladmin ping &> /dev/null; then
    echo "MySQL is not running. Exiting..."
    exit 1
fi

# check if password variable is set
if [ -z "$MYSQL_ROOT_PASSWORD" ]; then
    echo "MYSQL_ROOT_PASSWORD is not set in .env file. Exiting..."
    exit 1
fi

# Secure MySQL setup
echo "Securing MySQL installation..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    mysql -u root << EOF
ALTER USER '$MYSQL_USER'@'$MYSQL_HOST' IDENTIFIED BY '$MYSQL_PASSWORD';
FLUSH PRIVILEGES;
EOF
else
    sudo mysql << EOF
ALTER USER '$MYSQL_USER'@'$MYSQL_HOST' IDENTIFIED WITH mysql_native_password BY '$MYSQL_PASSWORD';
FLUSH PRIVILEGES;
EOF
fi

echo; echo
echo "MySQL setup complete."
echo "You can now run"
echo "(venv) python3 database/database_cmds.py"
echo "to create the database and tables."
echo
