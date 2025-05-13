# Homelab Deal Finder

A web application designed to help you find the best deals on homelab hardware on eBay. The application searches for listings based on your configured criteria, performs detailed data extraction (CPU, RAM, Storage), integrates with PassMark for performance scores, uses idle power data for energy cost estimation, and calculates a comprehensive Total Cost of Ownership (TCO). Results are presented via a sortable and filterable web interface.

## Features

-   **On-Demand eBay Search**: Fetches current hardware deals from eBay based on keywords, category, and maximum price configured in `config.yaml`.
-   **Detailed Data Extraction**: Attempts to parse CPU model, RAM size, and storage capacity from listing titles.
-   **PassMark Score Integration**: Looks up CPU performance scores from `passmark.txt` to provide a quantitative performance metric.
-   **Idle Power Data Integration**: Uses CPU idle power consumption data from `idlepower.txt` for energy cost calculations.
-   **Comprehensive TCO Calculation**: Evaluates deals based on:
    -   Purchase price.
    -   Estimated 5-year energy cost (configurable lifespan, kWh cost, and per-CPU idle power).
    -   Estimated shipping costs (configurable, differentiated for 'T' series CPUs).
    -   Estimated flat costs for RAM or storage upgrades if the listing is below configurable minimums (`required_ram_gb`, `required_storage_gb`).
-   **Configurable TCO Assumptions**: All TCO parameters (lifespan, kWh cost, shipping estimates, RAM/Storage requirements & flat upgrade costs) are configurable via `config.yaml`.
-   **Performance per TCO Dollar**: Calculates a score based on PassMark performance relative to the calculated TCO.
-   **Web Interface**: View, sort, and filter listings by various attributes including price, TCO, performance, CPU model, RAM, storage, and free shipping status.
-   **Dockerized Deployment**: Easy to deploy using Docker and Docker Compose, with an SQLite database for any necessary persistent storage (though currently, data is fetched on demand).

![Screenshot of my application's main interface](./homelab-shopper-screenshot.png)

## Quick Start

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd homelab-deal-finder
    ```

2.  **Set up Secrets using `.env` file:**
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the newly created `.env` file and fill in your actual eBay API credentials and a Flask secret key:
        ```
        EBAY_CLIENT_ID="YourEbayClientID"
        EBAY_CLIENT_SECRET="YourEbayClientSecret"
        SECRET_KEY="YourSecureRandomStringForFlask"
        FLASK_ENV="development" # Or "production"
        ```
    This `.env` file is used by Docker Compose to set environment variables within the container. It should not be committed to version control.

3.  **Prepare Configuration and Data Files:**
    *   Copy `config.yaml.example` to `config.yaml`.
        ```bash
        cp config.yaml.example config.yaml
        ```
    *   **Review `config.yaml`**:
        *   The eBay API credentials (`app_id`, `cert_id`) and Flask `secret_key` in `config.yaml` are configured to use placeholders (e.g., `${EBAY_CLIENT_ID}`). These will be automatically populated from the environment variables set by the `.env` file when running with Docker Compose.
        *   Customize search keywords, category ID, and max price.
    *   **Create/Verify Data Files**:
        *   `passmark.txt`: Ensure this file exists and contains CPU benchmark scores. The expected format per line is: `CPU Name\tScore` (tab-separated). Example: `Intel Core i5-9500T\t7000`
        *   `idlepower.txt`: Ensure this file exists and contains CPU idle power consumption data in Watts. The first line is treated as a header and skipped. Subsequent lines should be: `CPU Name\tIdle Power (Watts)` (tab-separated). Example: `Intel Core i5-9500T\t3.5`

4.  **Run with Docker:**
    ```bash
    docker-compose up --build
    ```

5.  **Access the web interface** at `http://localhost:5000`.

## Configuration (`config.yaml`)

The primary configuration is done through `config.yaml`:

-   **`database`**:
    -   `url`: SQLAlchemy database URL (defaults to SQLite).
-   **`ebay`**:
    -   `app_id`: Your eBay API Application ID (placeholder `${EBAY_CLIENT_ID}` loads from `.env` via Docker Compose).
    -   `cert_id`: Your eBay API Certificate ID (placeholder `${EBAY_CLIENT_SECRET}` loads from `.env` via Docker Compose).
    -   `sandbox`: `true` or `false` (use `false` for live eBay data).
-   **`search`**:
    -   `keywords`: Comma-separated list of search terms (e.g., "ThinkCentre Tiny, OptiPlex Micro, N100").
    -   `category_id`: eBay category ID for searches.
    -   `max_price`: Maximum listing price to consider.
-   **`logging`**:
    -   Configuration for logging level, file, size, etc.
-   **`security`**:
    -   `secret_key`: Flask secret key (placeholder `${SECRET_KEY}` loads from `.env` via Docker Compose).
    -   Session cookie settings.
-   **`app`**:
    -   Flask app settings (debug, host, port, workers, timeout).
    -   **`tco_assumptions`**:
        -   `kwh_cost`: Cost per kWh (e.g., `0.14`).
        -   `lifespan_years`: Assumed operational lifespan for energy calculation (e.g., `5`).
        -   `shipping_cost_t_cpu`: Estimated shipping for CPUs ending in 'T' if not free (e.g., `10`).
        -   `shipping_cost_non_t_cpu`: Estimated shipping for other CPUs if not free (e.g., `35`).
        -   `required_ram_gb`: Minimum desired RAM in GB (e.g., `16`).
        -   `ram_upgrade_flat_cost`: Flat cost to add if RAM is below `required_ram_gb` (e.g., `30`).
        -   `required_storage_gb`: Minimum desired storage in GB (e.g., `120`).
        -   `storage_upgrade_flat_cost`: Flat cost to add if storage is below `required_storage_gb` (e.g., `15`).

### Data Files

-   **`passmark.txt`**:
    -   Format: `CPU Name\tScore` (tab-separated)
    -   Example: `Intel Core i7-8700T\t9123`
-   **`idlepower.txt`**:
    -   Format: `CPU Name\tIdle Power (Watts)` (tab-separated)
    -   The first line is skipped (assumed to be a header).
    -   Example: `Intel Core i7-8700T\t10`

## Project Structure

```
homelab-deal-finder/
├── src/
│   ├── web_app.py          # Main Flask web application, includes TCO logic
│   ├── config.py           # Configuration loading utility
│   └── ebay_api.py         # eBay API communication and token management
├── templates/
│   └── index.html          # Main HTML template for the web interface
├── data/                   # Default location for SQLite database (if used by web_app.py)
├── logs/                   # Default location for application logs
├── config.yaml             # Main application configuration
├── passmark.txt            # CPU benchmark scores data file
├── idlepower.txt           # CPU idle power consumption data file
├── docker-compose.yml      # Docker Compose configuration
├── Dockerfile              # Dockerfile for building the application image
└── requirements.txt        # Python dependencies
```

## Development

1.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # or `venv\Scripts\activate` on Windows
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set up Secrets for Local Development:**
    *   Ensure you have a `.env` file as described in the "Quick Start" section (copy `.env.example` to `.env` and edit it).
    *   When running locally (not with Docker), your shell needs to load these variables. You can do this by:
        *   Sourcing the `.env` file if your shell supports it (e.g., `set -a; source .env; set +a` for bash/zsh).
        *   Or, ensure the `python-dotenv` package is installed (`pip install python-dotenv`) and your application loads it at startup (this project's `config.py` is set up to do this).
        *   Alternatively, manually export them in your current terminal session:
            ```bash
            export EBAY_CLIENT_ID="YourEbayClientID"
            export EBAY_CLIENT_SECRET="YourEbayClientSecret"
            export SECRET_KEY="YourSecureRandomStringForFlask"
            export FLASK_ENV="development"
            ```

4.  **Run the Flask development server:**
    ```bash
    flask run # (or python src/web_app.py if __main__ is configured)
    ```

## License

This project is licensed under the GNU Affero General Public License v3.0.
See the [LICENSE](LICENSE) file for details.

