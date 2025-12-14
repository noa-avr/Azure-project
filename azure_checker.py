from azure.identity import AzureCliCredential
from azure.mgmt.web import WebSiteManagementClient
import subprocess
import sys


# ----------------------------------------------------
# כללי שדרוג מומלצים (מילון נתונים ידני)
# מפתח: גרסת Runtime מיושנת (המזהה של ה-SDK)
# ערך: סטטוס והמלצה
# ----------------------------------------------------
UPGRADE_RULES = {
    "NODE|14": {"status": "EOL Soon/Outdated", "recommendation": "Upgrade to Node 20 LTS (או 18 LTS)"},
    "NODE|16": {"status": "Outdated", "recommendation": "Upgrade to Node 20 LTS"},
    "DOTNETCORE|3.1": {"status": "EOL (End of Life)", "recommendation": "Upgrade to .NET 6 או 8 LTS"},
    "PYTHON|3.8": {"status": "EOL Soon", "recommendation": "Upgrade to Python 3.11 או 3.12"},
    "PHP|7.4": {"status": "EOL (End of Life)", "recommendation": "Upgrade to PHP 8.2 or higher"},
    "JAVA|8": {"status": "Very Outdated", "recommendation": "Upgrade to Java 17 LTS"},
    "ASP": {"status": "EOL/Unsupported", "recommendation": "Migrate to modern .NET"}
}


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

def get_app_list(client):
    
    app_data = []

    try:
        all_apps = client.web_apps.list()

        #DEBUG:
        app_count = sum(1 for _ in all_apps)
        print(f"Found {app_count} apps in the subscription")
        
        all_apps = client.web_apps.list()

        for app in all_apps:
            app_data.append({
                "name": app.name,
                "resource_group": app.resource_group,
                "runtime": app.runtime,
            })

    except Exception as e:
        print(f"Error: Failed to retrieve App List. Please ensure you have the necessary permissions. Details: {e}")
        return []

    return app_data


if __name__ == "__main__":
    print("---Starting Azure checker---")

    client, sub_id = create_client()

    app_list = get_app_list(client)
    
    if app_list:
        print("\n" + "="*80)
        print("דו\"ח גרסאות App Service")
        print("="*80)

    else:
        print("\n" + "#"*80)
        print("ALERT: סריקה הסתיימה ללא תוצאות. (No App Services Found)")
        print(f"המנוי הפעיל ({sub_id}) לא מכיל משאבי App Service.")
        print("#"*80 + "\n")

    


