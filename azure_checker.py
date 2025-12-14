from azure.identity import AzureCliCredential
from azure.mgmt.web import WebSiteManagementClient
import subprocess
import sys


# ----------------------------------------------------
# Apgrade rules dictionary
# Key: Runtime version (SDK identifier)
# Value: Status and recommendation
# ----------------------------------------------------
UPGRADE_RULES = {
    "NODE|14": {"status": "EOL Soon/Outdated", "recommendation": "Upgrade to Node 20 LTS (or 18 LTS)"},
    "NODE|16": {"status": "Outdated", "recommendation": "Upgrade to Node 20 LTS"},
    "DOTNETCORE|3.1": {"status": "EOL (End of Life)", "recommendation": "Upgrade to .NET 6 or 8 LTS"},
    "PYTHON|3.8": {"status": "EOL Soon", "recommendation": "Upgrade to Python 3.11 or 3.12"},
    "PHP|7.4": {"status": "EOL (End of Life)", "recommendation": "Upgrade to PHP 8.2 or higher"},
    "JAVA|8": {"status": "Very Outdated", "recommendation": "Upgrade to Java 17 LTS"},
    "ASP": {"status": "EOL/Unsupported", "recommendation": "Migrate to modern .NET"}
}


# ----------------------------------------------------
# Check the Runtime against the rules
# ----------------------------------------------------
def check_runtime_status(runtime_str):
    """Check the Runtime status against the rules."""
    
    # Convert the input to uppercase to ensure uniform case checking
    runtime_str_upper = runtime_str.upper() 
    
    for obsolete_version, rule in UPGRADE_RULES.items():
        # Check if the obsolete version appears in the current runtime string
        if obsolete_version in runtime_str_upper:
            # If we found a match (obsolete version), return the status and recommendation
            return rule['status'], rule['recommendation']
            
    # If the loop completed and no match was found, assume the version is up to date
    return "Up-to-Date / Unchecked", "N/A"



# Reading the subscription ID from the Azure CLI
def get_subscription_ID():

    try:
            subID = subprocess.check_output("az account show --query id -o tsv", shell=True, text=True).strip()

            if not subID:
                raise ValueError("No subscription ID found")

            return subID

    except FileNotFoundError:
        print("Azure CLI not found. Please install Azure CLI and try again.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to retrieve Subscription ID. Please ensure you ran 'az login' and set an active subscription.")
        print(f"Details: {e}")
        sys.exit(1)


# Creating the Azure client
def create_client():

    # Getting the subscription ID
    sub_id = get_subscription_ID()

    # Reading the credential from the Azure CLI
    credential = AzureCliCredential()

    # Creating the client
    client = WebSiteManagementClient(credential, sub_id)

    print(f"Azure client created successfully for subscription: {sub_id}")

    return client, sub_id

# Getting the app list of the subscription

def get_app_service_data(client):
    
    app_data = [] # List to collect the final data
    
    try:
        # 1. Get the basic list of resources
        all_apps = client.web_apps.list() 
        all_apps_list = list(all_apps) # Convert the iterator to a list
        app_count = len(all_apps_list)
        print(f"DEBUG: Successfully fetched list of App Services. Scanning {app_count} apps...")
        
        # 2. Loop through each App Service found
        for app in all_apps_list:
            
            # Initialize default variables
            current_runtime = "Unknown Stack / Not configured"
            status = "N/A"
            recommendation = "N/A"
            
            try:
                # *************************************************************
                # Step 1: Get the configuration object (additional call)
                # *************************************************************
                config = client.web_apps.get_configuration(
                    # **Fix: Use the correct field name**
                    resource_group_name=app.resource_group_name, 
                    name=app.name
                )
                
                # *************************************************************
                # Step 2: Get the version (Runtime Stack)
                # *************************************************************
                if config.linux_fx_version:
                    current_runtime = config.linux_fx_version
                elif config.net_framework_version:
                    current_runtime = config.net_framework_version

                # *************************************************************
                # Step 3: Apply the logic rules (check_runtime_status)
                # *************************************************************
                if current_runtime != "Unknown Stack / Not configured":
                    status, recommendation = check_runtime_status(current_runtime) 
                
            except Exception as e:
                # Handle errors within the loop
                status = "ERROR: Config Read Failed"
                recommendation = f"Check permissions or resource status: {e.__class__.__name__}"
            
            # Add the data to the final report
            app_data.append({
                "Name": app.name,
                "Resource Group": app.resource_group_name,
                "Current Runtime": current_runtime,
                "Status": status,
                "Recommendation": recommendation
            })
            
    except Exception as e:
        # Error message if the list() completely fails
        print(f"FATAL ERROR: Failed during App Service listing. Details: {e.__class__.__name__}: {e}")
        return []

    return app_data


if __name__ == "__main__":
    print("---Starting Azure checker---")

    client, sub_id = create_client()

    app_list = get_app_service_data(client)
    
    if app_list:
        print("\n" + "="*120)
        print("App Service Runtime Status Report - EOL Check")
        print("="*120)
        
        # Print the report headers
        print(f"{'App Name':<30} | {'Runtime':<20} | {'Status':<30} | {'Recommendation':<35}")
        print("-" * 120)

        # Print the data
        for item in app_list:
            print(f"{item['Name']:<30} | {item['Current Runtime']:<20} | {item['Status']:<30} | {item['Recommendation']:<35}")
        
        print("="*120)

    else:
        print("\n" + "#"*80)
        print("ALERT: Scan completed without results. (No App Services Found)")
        print(f"The active subscription ({sub_id}) does not contain any App Service resources.")
        print("#"*80 + "\n")
    


