# {{ toolkit_name }}

{{ toolkit_description }}

## Creating your new toolkit repo

1. Run `arcade new` and answer all the questions
2. Navigate to your new toolkit directory:
   ```bash
   cd {{ toolkit_name }}
   ```
3. Initialize git repository:
   ```bash
   git init
   ```
4. Create a new repository in Github with the same name as your new toolkit
   > Note: Don't create a README, LICENSE or .gitignore when creating the repository because `arcade new` has already created these files for you.
5. Add remote and push your code:
   ```bash
   git remote add origin https://github.com/{{ toolkit_author_name }}/{{ toolkit_name }}.git
   git branch -M main
   git add .
   git commit -m "Initial commit"
   git push -u origin main
   ```

## Publishing to PyPi

### Generating a PyPi API Key

1. Log into your PyPi account
2. Navigate to your Account settings and add an API token
3. Copy the token
4. In your Github repository:
   - Go to Settings > Secrets and variables > Actions
   - Click "New repository secret"
   - Name your secret `PYPI_TOKEN`
   - Paste your API Token into the Secret field

### Creating a Release

1. Navigate to your Github repository and click on Releases
2. Create a new tag that corresponds to the version in your toolkit's `pyproject.toml` file
   > Note: This will be 0.0.1 for your first release

## How to install the toolkit:
1. Run `make install` from the root of the repository

## How to run tests:
1. Run `make test` from the root of the repository

## How to run evals:
1. [Install the Arcade Engine Locally](https://docs.arcade-ai.com/home/install/local)
2. Install extra dependencies needed for evals:
   ```bash
   pip install 'arcade-ai[fastapi,evals]'
   ```
3. Log into Arcade AI:
   ```bash
   arcade login
   ```
4. Start the Arcade Engine and Worker:
   ```bash
   arcade dev
   ```
5. In a separate terminal, navigate to the `evals` directory:
   ```bash
   cd evals
   ```
5. Run the evals:
   ```bash
   arcade evals --host localhost --details
   ```
