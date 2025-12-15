# Azure EOL Runtime Checker (App Service & AKS)

## Project Overview

This Python utility is designed to help Cloud Operations and Security teams identify outdated and End-of-Life (EOL) runtimes within their Azure App Service and Azure Kubernetes Service (AKS) resources across a subscription.

The script automatically connects to the Azure CLI, scans App Services (Linux/Windows) and AKS Clusters, and compares their detected runtime versions against predefined upgrade rules. The result is a clean, actionable report in both the command line and a persistent CSV file.

### Key Features:

* **Automated Authentication:** Uses the existing Azure CLI login credentials.
* **Multi-Resource Scanning:** Checks both Azure App Services and AKS Clusters.
* **Actionable Reporting:** Generates a **Status** (e.g., EOL, Outdated) and **Recommendation** (e.g., Upgrade to Node 20 LTS).
* **Persistent Output:** Saves the comprehensive report to an `azure_runtime_report.csv` file.

## Prerequisites

Before running the checker, ensure you have the following installed on your machine:

1.  **Python 3.x:** (Used to run the script).
2.  **Azure CLI:** (Used for authentication and subscription management).

## Getting Started

Follow these steps to set up and run the Azure EOL Checker.

### Step 1: Clone the Repository

Clone the project from your Git repository and navigate into the directory:

```bash
git clone [YOUR_REPOSITORY_ADDRESS]
cd azure-eol-checker-project
Step 2: Install Dependencies
It is highly recommended to use a Python virtual environment (venv).

Create and Activate Virtual Environment:

Bash

python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
Install Required Libraries: Install the necessary packages (these are the three core Azure SDK packages used):

Bash

pip install azure-identity azure-mgmt-web azure-mgmt-containerservice
Step 3: Authenticate with Azure CLI
The script relies on the active login session of your Azure CLI. You may need to refresh your token due to MFA policies.

Login Interactively: This command will open a browser window for you to complete the login process, including Multi-Factor Authentication (MFA).

Bash

az login
Verify/Set Subscription (If you have multiple subscriptions): Ensure you are targeting the correct subscription for the scan:

Bash

# Set the desired subscription by ID or Name:
az account set --subscription "YOUR_TARGET_SUBSCRIPTION_ID_OR_NAME"
Step 4: Run the Checker
Execute the main script file (azure_checker.py or azure_checker_complete.py).

Bash

python azure_checker.py
Step 5: Review the Report
Upon completion, the tool will provide two outputs:

Terminal Output: A formatted table displaying the resource type, name, version, status, and recommendation.

CSV File: A detailed report named azure_runtime_report.csv will be generated in the same directory, which can be easily imported into Excel or other reporting tools.

Contribution and Future Enhancements
The current checker supports App Services and AKS. You can extend the project by adding support for other Azure resources like Azure SQL, Azure Functions, or VMs.
