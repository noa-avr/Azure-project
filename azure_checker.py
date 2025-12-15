from azure.identity import AzureCliCredential
from azure.mgmt.web import WebSiteManagementClient
import subprocess
import sys
import csv
from azure.mgmt.containerservice import ContainerServiceClient


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
# AKS Upgrade rules dictionary
# Key: Kubernetes version (Major.Minor)
# Value: Status and recommendation
# ----------------------------------------------------
AKS_UPGRADE_RULES = {
    # Examples of supported versions that are not EOL
    "1.26": {"status": "EOL Soon", "recommendation": "Upgrade to Kubernetes 1.28/1.29 (or higher LTS)."},
    "1.27": {"status": "Near EOL", "recommendation": "Upgrade to Kubernetes 1.28/1.29 (or higher LTS)."},
    "1.28": {"status": "Supported", "recommendation": "N/A"},
    "1.29": {"status": "Supported", "recommendation": "N/A"},
    # Examples of versions that are no longer supported
    "1.25": {"status": "EOL (End of Life)", "recommendation": "URGENT: Upgrade to 1.28/1.29+."},
    "1.24": {"status": "EOL (End of Life)", "recommendation": "URGENT: Upgrade to 1.28/1.29+."},
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



# ----------------------------------------------------
# Check the AKS Version against the rules
# ----------------------------------------------------
def check_aks_version(version_str):
    """Check the AKS Kubernetes version status against the rules."""
    
    # Kubernetes versions are checked by Major.Minor (e.g. 1.28)
    # We try to extract only the first two parts.
    try:
        parts = version_str.split('.')
        # If a valid version is found, take only the first two parts
        version_prefix = f"{parts[0]}.{parts[1]}" 
    except:
        # If the format is not valid, return Unknown
        version_prefix = "Unknown" 

    # Check against the rules
    if version_prefix in AKS_UPGRADE_RULES:
        rule = AKS_UPGRADE_RULES[version_prefix]
        return version_prefix, rule['status'], rule['recommendation']
        
    # If no match is found, assume the version is supported and up to date
    return version_prefix, "Supported / Unchecked", "N/A"



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
    web_client = WebSiteManagementClient(credential, sub_id)
    aks_client = ContainerServiceClient(credential, sub_id) # AKS client
    
    print(f"Azure client created successfully for subscription: {sub_id}")

    return web_client, aks_client, sub_id


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


# ----------------------------------------------------
# Get the AKS cluster list of the subscription
# ----------------------------------------------------
def get_aks_data(aks_client):
    
    aks_data = [] # List to collect the final data
    
    try:
        # 1. Get the list of all AKS clusters in the subscription
        all_clusters = aks_client.managed_clusters.list()
        all_clusters_list = list(all_clusters)
        cluster_count = len(all_clusters_list)
        print(f"DEBUG: Successfully fetched list of AKS Clusters. Scanning {cluster_count} clusters...")
        
        # 2. Loop through each cluster found
        for cluster in all_clusters_list:
            
            # Get the data directly from the cluster object
            cluster_version = cluster.kubernetes_version
            
            # Apply the logic rules (check_aks_version)
            version_prefix, status, recommendation = check_aks_version(cluster_version) 
            
            # Add the data to the final report
            aks_data.append({
                "Type": "AKS Cluster",
                "Name": cluster.name,
                "Resource Group": cluster.resource_group_name,
                "Current Version": cluster_version,
                "Status": status,
                "Recommendation": recommendation
            })
            
    except Exception as e:
        # Error message if the list() completely fails
        print(f"FATAL ERROR: Failed during AKS Cluster listing. Details: {e.__class__.__name__}: {e}")
        return []

    return aks_data
    


# ----------------------------------------------------
# Save the report to a CSV file
# ----------------------------------------------------
def save_report_to_csv(data_list):
    """Save the list of application data to a CSV file."""
    
    file_name = "app_service_report.csv"
    
    # If the list is empty, there is nothing to save
    if not data_list:
        print(f"INFO: No data to save. Skipping save to {file_name}")
        return

    # The keys (Fields) of our dictionary will be used as the column headers in the CSV
    field_names = ["Name", "Resource Group", "Current Runtime", "Status", "Recommendation"]

    try:
        # Open the file for writing (w)
        # newline='' prevents extra spaces between lines in CSV files
        with open(file_name, 'w', newline='', encoding='utf-8') as csvfile:
            # Create an object that knows how to write dictionaries into the CSV
            writer = csv.DictWriter(csvfile, fieldnames=field_names)
            
            # Write the column headers in the first row
            writer.writeheader()
            
            # Write all the rows from our list
            writer.writerows(data_list)
        
            print(f"\n✅ Report saved successfully to file: {file_name}")
        
    except Exception as e:
        print(f"ERROR: Failed to save the CSV. Details: {e}")


if __name__ == "__main__":
    print("---Starting Azure checker---")

    # Call the clients
    web_client, aks_client, sub_id = create_client() 

    # Scan the App Services
    app_service_list = get_app_service_data(web_client)
    
    # Scan the AKS Clusters
    aks_list = get_aks_data(aks_client)
    
    # Combine all the results into a single list
    combined_list = app_service_list + aks_list
    
    # ----------------------------------------------------
    # Print the combined report
    # ----------------------------------------------------
    if combined_list:
        print("\n" + "="*140)
        # Change the report name to a more general one
        print("דו\"ח אבטחת גרסאות Azure (App Service & AKS)") 
        print("="*140)
        
        # Add the 'Type' column to the table
        print(f"{'Type':<15} | {'Name':<30} | {'Resource Group':<20} | {'Current Version':<15} | {'Status':<30} | {'Recommendation':<25}")
        print("-" * 140)

        # Loop through the combined list
        for item in combined_list:
            print(f"{item.get('Type', 'App Service'):<15} | {item['Name']:<30} | {item['Resource Group']:<20} | {item['Current Version']:<15} | {item['Status']:<30} | {item['Recommendation']:<25}")
        
        print("="*140)

    else:
        print("\n" + "#"*80)
        print("ALERT: Scan completed with no results. (No App Services or AKS Clusters Found)")
        print(f"The active subscription ({sub_id}) does not contain any App Services or AKS clusters.")
        print("#"*80 + "\n")
        
    # *************************************************************
    # Save the combined report to a CSV file
    # *************************************************************
    # Pass the combined_list to the save function
    save_report_to_csv(combined_list)
    


