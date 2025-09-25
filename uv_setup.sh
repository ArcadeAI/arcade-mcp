#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script configuration
REQUIRED_PYTHON_VERSION="3.11"
VENV_NAME=".venv"
PROJECT_ROOT=$(pwd)
INTERACTIVE_MODE=true

echo -e "${BLUE}=== UV Python Environment Setup ===${NC}"
echo -e "${BLUE}Project: ${PROJECT_ROOT}${NC}"
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to compare version strings
version_ge() {
    [ "$(printf '%s\n' "$1" "$2" | sort -V | head -n1)" = "$2" ]
}

# Function to ask for confirmation
confirm() {
    local prompt="$1"
    local default="${2:-y}"
    local response

    if [ "$default" = "y" ]; then
        prompt="${prompt} [Y/n]: "
    else
        prompt="${prompt} [y/N]: "
    fi

    while true; do
        echo -ne "${CYAN}${prompt}${NC}"
        read -r response
        response=${response:-$default}
        response=$(echo "$response" | tr '[:upper:]' '[:lower:]')

        if [[ "$response" =~ ^(yes|y)$ ]]; then
            return 0
        elif [[ "$response" =~ ^(no|n)$ ]]; then
            return 1
        else
            echo -e "${RED}Please answer yes/no (y/n)${NC}"
        fi
    done
}

# Ask if user wants to run in interactive mode
if confirm "Do you want to run in interactive mode? (You'll be asked to confirm each step)" "y"; then
    INTERACTIVE_MODE=true
    echo -e "${GREEN}Running in interactive mode${NC}\n"
else
    INTERACTIVE_MODE=false
    echo -e "${YELLOW}Running in automatic mode (all steps will be executed)${NC}\n"
fi

# Step 1: Check if uv is installed
echo -e "${YELLOW}1. Checking uv installation...${NC}"
if ! command_exists uv; then
    echo -e "${RED}✗ uv is not installed${NC}"

    if [ "$INTERACTIVE_MODE" = true ]; then
        if confirm "Would you like to install uv?" "y"; then
            echo -e "${YELLOW}Installing uv...${NC}"
        else
            echo -e "${RED}Cannot proceed without uv. Exiting.${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}Installing uv...${NC}"
    fi

    # Install uv based on the system
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command_exists brew; then
            brew install uv
        else
            curl -LsSf https://astral.sh/uv/install.sh | sh
        fi
    else
        # Linux and others
        curl -LsSf https://astral.sh/uv/install.sh | sh
    fi

    # Add to PATH if not already there
    if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
        export PATH="$HOME/.local/bin:$PATH"
    fi

    echo -e "${GREEN}✓ uv installed successfully${NC}"
else
    echo -e "${GREEN}✓ uv is installed ($(uv --version))${NC}"
fi

# Step 2: Check Python 3.11 availability
echo -e "\n${YELLOW}2. Checking Python ${REQUIRED_PYTHON_VERSION} availability...${NC}"

# First check if uv can find Python 3.11
if uv python find 3.11 >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Python 3.11 is available via uv${NC}"
    PYTHON_PATH=$(uv python find 3.11)
    echo -e "  Found at: ${PYTHON_PATH}"
else
    echo -e "${RED}✗ Python 3.11 not found${NC}"

    if [ "$INTERACTIVE_MODE" = true ]; then
        if confirm "Would you like to install Python 3.11 via uv?" "y"; then
            echo -e "${YELLOW}Installing Python 3.11...${NC}"
            uv python install 3.11
            PYTHON_PATH=$(uv python find 3.11)
            echo -e "${GREEN}✓ Python 3.11 installed successfully${NC}"
        else
            echo -e "${RED}Cannot proceed without Python 3.11. Exiting.${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}Installing Python 3.11 via uv...${NC}"
        uv python install 3.11
        PYTHON_PATH=$(uv python find 3.11)
        echo -e "${GREEN}✓ Python 3.11 installed successfully${NC}"
    fi
fi

# Step 3: Create or verify virtual environment
echo -e "\n${YELLOW}3. Setting up virtual environment...${NC}"

if [ -d "$VENV_NAME" ]; then
    echo -e "${YELLOW}Virtual environment already exists. Checking Python version...${NC}"

    # Check if the existing venv has the correct Python version
    if [ -f "$VENV_NAME/bin/python" ]; then
        VENV_PYTHON_VERSION=$("$VENV_NAME/bin/python" --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
        if [ "$VENV_PYTHON_VERSION" != "$REQUIRED_PYTHON_VERSION" ]; then
            echo -e "${RED}✗ Existing venv uses Python $VENV_PYTHON_VERSION (required: $REQUIRED_PYTHON_VERSION)${NC}"

            if [ "$INTERACTIVE_MODE" = true ]; then
                if confirm "Would you like to recreate the virtual environment with Python $REQUIRED_PYTHON_VERSION?" "y"; then
                    echo -e "${YELLOW}Recreating virtual environment...${NC}"
                    rm -rf "$VENV_NAME"
                    uv venv --python 3.11
                    echo -e "${GREEN}✓ Virtual environment recreated with Python 3.11${NC}"
                else
                    echo -e "${YELLOW}Keeping existing virtual environment with Python $VENV_PYTHON_VERSION${NC}"
                    echo -e "${RED}Warning: This may cause compatibility issues!${NC}"
                fi
            else
                echo -e "${YELLOW}Recreating with Python $REQUIRED_PYTHON_VERSION...${NC}"
                rm -rf "$VENV_NAME"
                uv venv --python 3.11
                echo -e "${GREEN}✓ Virtual environment recreated with Python 3.11${NC}"
            fi
        else
            echo -e "${GREEN}✓ Virtual environment uses correct Python version ($VENV_PYTHON_VERSION)${NC}"
        fi
    else
        echo -e "${RED}✗ Virtual environment seems corrupted${NC}"

        if [ "$INTERACTIVE_MODE" = true ]; then
            if confirm "Would you like to recreate the virtual environment?" "y"; then
                echo -e "${YELLOW}Recreating virtual environment...${NC}"
                rm -rf "$VENV_NAME"
                uv venv --python 3.11
                echo -e "${GREEN}✓ Virtual environment recreated${NC}"
            else
                echo -e "${RED}Cannot proceed with corrupted virtual environment. Exiting.${NC}"
                exit 1
            fi
        else
            echo -e "${YELLOW}Recreating...${NC}"
            rm -rf "$VENV_NAME"
            uv venv --python 3.11
            echo -e "${GREEN}✓ Virtual environment recreated${NC}"
        fi
    fi
else
    if [ "$INTERACTIVE_MODE" = true ]; then
        if confirm "Would you like to create a new virtual environment with Python 3.11?" "y"; then
            echo -e "${YELLOW}Creating virtual environment...${NC}"
            uv venv --python 3.11
            echo -e "${GREEN}✓ Virtual environment created${NC}"
        else
            echo -e "${RED}Cannot proceed without virtual environment. Exiting.${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}Creating new virtual environment with Python 3.11...${NC}"
        uv venv --python 3.11
        echo -e "${GREEN}✓ Virtual environment created${NC}"
    fi
fi

# Step 4: Install dependencies
echo -e "\n${YELLOW}4. Installing project dependencies...${NC}"

# Check if pyproject.toml exists
if [ -f "pyproject.toml" ]; then
    if [ "$INTERACTIVE_MODE" = true ]; then
        if confirm "Would you like to install dependencies from pyproject.toml?" "y"; then
            echo -e "${YELLOW}Installing dependencies...${NC}"
            uv sync
            echo -e "${GREEN}✓ Dependencies installed${NC}"
        else
            echo -e "${YELLOW}Skipping dependency installation${NC}"
            echo -e "${RED}Warning: You'll need to run 'uv sync' manually later${NC}"
        fi
    else
        echo -e "${YELLOW}Installing dependencies from pyproject.toml...${NC}"
        uv sync
        echo -e "${GREEN}✓ Dependencies installed${NC}"
    fi
else
    echo -e "${YELLOW}No pyproject.toml found. Skipping dependency installation.${NC}"
fi

# Step 5: Configure VS Code
echo -e "\n${YELLOW}5. Configuring VS Code...${NC}"

CONFIGURE_VSCODE=true
if [ "$INTERACTIVE_MODE" = true ]; then
    if [ -f ".vscode/settings.json" ]; then
        echo -e "${YELLOW}VS Code settings already exist${NC}"
        if confirm "Would you like to overwrite existing VS Code settings?" "n"; then
            CONFIGURE_VSCODE=true
        else
            CONFIGURE_VSCODE=false
            echo -e "${YELLOW}Keeping existing VS Code settings${NC}"
        fi
    else
        if confirm "Would you like to configure VS Code settings?" "y"; then
            CONFIGURE_VSCODE=true
        else
            CONFIGURE_VSCODE=false
            echo -e "${YELLOW}Skipping VS Code configuration${NC}"
        fi
    fi
fi

if [ "$CONFIGURE_VSCODE" = true ]; then
    # Create .vscode directory if it doesn't exist
    mkdir -p .vscode

    # Create VS Code settings
    cat > .vscode/settings.json << EOF
{
    "python.defaultInterpreterPath": "${PROJECT_ROOT}/${VENV_NAME}/bin/python",
    "python.terminal.activateEnvironment": true,
    "python.terminal.activateEnvInCurrentTerminal": true,
    "python.envFile": "\${workspaceFolder}/.env",
    "python.venvPath": "${PROJECT_ROOT}",
    "python.venvFolders": ["${VENV_NAME}"],
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": false,
    "python.linting.flake8Enabled": false,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "ruff",
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.organizeImports": "explicit",
            "source.fixAll": "explicit"
        }
    },
    "ruff.path": ["${PROJECT_ROOT}/${VENV_NAME}/bin/ruff"]
}
EOF

    echo -e "${GREEN}✓ VS Code settings created/updated${NC}"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    if [ "$INTERACTIVE_MODE" = true ]; then
        if confirm "Would you like to create an .env file?" "y"; then
            echo "# Environment variables for the project" > .env
            echo -e "${GREEN}✓ Created .env file${NC}"
        else
            echo -e "${YELLOW}Skipping .env file creation${NC}"
        fi
    else
        echo "# Environment variables for the project" > .env
        echo -e "${GREEN}✓ Created .env file${NC}"
    fi
fi

# Step 6: Create activation helper script
echo -e "\n${YELLOW}6. Creating activation helper...${NC}"

CREATE_HELPER=true
if [ "$INTERACTIVE_MODE" = true ]; then
    if [ -f "activate.sh" ]; then
        echo -e "${YELLOW}Activation helper script already exists${NC}"
        if confirm "Would you like to overwrite the existing activate.sh?" "n"; then
            CREATE_HELPER=true
        else
            CREATE_HELPER=false
            echo -e "${YELLOW}Keeping existing activation helper${NC}"
        fi
    else
        if confirm "Would you like to create an activation helper script (activate.sh)?" "y"; then
            CREATE_HELPER=true
        else
            CREATE_HELPER=false
            echo -e "${YELLOW}Skipping activation helper creation${NC}"
        fi
    fi
fi

if [ "$CREATE_HELPER" = true ]; then
    cat > activate.sh << 'EOF'
#!/bin/bash
# Quick activation script for the virtual environment

if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "Virtual environment activated!"
    echo "Python: $(which python) ($(python --version))"
    echo "To deactivate, run: deactivate"
else
    echo "Error: Virtual environment not found. Run ./uv_setup.sh first."
    exit 1
fi
EOF

    chmod +x activate.sh
    echo -e "${GREEN}✓ Created activate.sh helper script${NC}"
fi

# Step 7: Display final instructions
echo -e "\n${GREEN}=== Setup Complete! ===${NC}"
echo -e "\n${BLUE}To activate the virtual environment in your terminal:${NC}"
echo -e "  ${YELLOW}source ${VENV_NAME}/bin/activate${NC}"
echo -e "\n${BLUE}Or use the helper script:${NC}"
echo -e "  ${YELLOW}source ./activate.sh${NC}"

echo -e "\n${BLUE}For VS Code:${NC}"
echo -e "  1. Open VS Code in this directory: ${YELLOW}code .${NC}"
echo -e "  2. When prompted, select the Python interpreter from ${YELLOW}${VENV_NAME}/bin/python${NC}"
echo -e "  3. Or press ${YELLOW}Cmd+Shift+P${NC} and search for 'Python: Select Interpreter'"

echo -e "\n${BLUE}Current environment info:${NC}"
echo -e "  Python version required: ${YELLOW}>=${REQUIRED_PYTHON_VERSION}, <3.11${NC}"
echo -e "  Virtual environment: ${YELLOW}${PROJECT_ROOT}/${VENV_NAME}${NC}"
echo -e "  Python executable: ${YELLOW}${PROJECT_ROOT}/${VENV_NAME}/bin/python${NC}"

# Check if we're in an activated environment
if [ -n "$VIRTUAL_ENV" ]; then
    echo -e "\n${GREEN}✓ Virtual environment is currently activated${NC}"
else
    echo -e "\n${YELLOW}! Virtual environment is not activated in this shell${NC}"
fi

# Add to .gitignore if not already there
if [ -f ".gitignore" ]; then
    if ! grep -q "^${VENV_NAME}$" .gitignore; then
        if [ "$INTERACTIVE_MODE" = true ]; then
            if confirm "Would you like to add ${VENV_NAME} and activate.sh to .gitignore?" "y"; then
                echo -e "\n# Virtual environment" >> .gitignore
                echo "${VENV_NAME}" >> .gitignore
                echo "activate.sh" >> .gitignore
                echo -e "${GREEN}✓ Added ${VENV_NAME} to .gitignore${NC}"
            fi
        else
            echo -e "\n# Virtual environment" >> .gitignore
            echo "${VENV_NAME}" >> .gitignore
            echo "activate.sh" >> .gitignore
            echo -e "${GREEN}✓ Added ${VENV_NAME} to .gitignore${NC}"
        fi
    fi
fi

# Summary of actions taken
echo -e "\n${BLUE}=== Setup Summary ===${NC}"
echo -e "${GREEN}✓ Completed Steps:${NC}"
[ -n "$(command -v uv)" ] && echo -e "  • uv is installed and available"
[ -d "$VENV_NAME" ] && echo -e "  • Virtual environment created/verified"
[ -f "$VENV_NAME/bin/python" ] && echo -e "  • Python $($VENV_NAME/bin/python --version 2>&1 | cut -d' ' -f2) configured"
[ -f ".vscode/settings.json" ] && [ "$CONFIGURE_VSCODE" = true ] && echo -e "  • VS Code settings configured"
[ -f "activate.sh" ] && [ "$CREATE_HELPER" = true ] && echo -e "  • Activation helper created"
[ -f ".env" ] && echo -e "  • .env file created"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo -e "  1. Activate the virtual environment: ${CYAN}source ${VENV_NAME}/bin/activate${NC}"
echo -e "  2. If you skipped dependency installation: ${CYAN}uv sync${NC}"
echo -e "  3. Open VS Code and select the Python interpreter if needed"
