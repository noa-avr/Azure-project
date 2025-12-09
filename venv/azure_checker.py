from azure.identity import AzureCliCredential
from azure.mgmt.web import WebSiteManagementClient
import subprocess
import sys

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


    if __name__ == "__main__":
        print("---Starting Azure checker---")

        client, sub_id = create_client()
        
        if app_list:
            print("\n" + "="*80)
            print("דו\"ח גרסאות App Service")
            print("="*80)

        else:
            # זה הבלוק החדש שיוסיף דיווח ברור
            print("\n" + "#"*80)
            print("ALERT: סריקה הסתיימה ללא תוצאות.")
            print("אחת מהסיבות הבאות ככל הנראה גרמה לכך:")
            print("1. אין לך משאבי App Service במנוי הפעיל.")
            print("2. האימות נכשל (הרשאות, או שגיאה ב-az login).")
            print("#"*80 + "\n")

        printf("Ready to scan App Services using client: {client}")


    


