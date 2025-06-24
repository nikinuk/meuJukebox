#!/bin/bash

# --- Variable Configuration ---
CUSTOMER_ID="felipane"
CLIENT_ID="tbd"
CLIENT_SECRET="tbd"

# --- Fixed Configuration ---
PROJECT_ID="jukebox-446711"
REGION="southamerica-east1"  # Consistent region for Cloud Run and Cloud SQL
DATABASE_INSTANCE="jukebox" # Your Cloud SQL instance name
ACCESS_TOKEN="none"          
REFRESH_TOKEN="none"         
EXPIRES_AT="none"
JUKE_LIST="none"
LIKES="{}"
JUKE_LIST2="{}"
ICN="jukebox-446711:southamerica-east1:jukebox"
DB_NAME="postgres"

# --- Auto configuration
INSTANCE=$CUSTOMER_ID
IMAGE_NAME="gcr.io/$PROJECT_ID/login" # Your container image
REDIRECT_URI="https://$INSTANCE-hrbec6un6a-rj.a.run.app/callback"
CANONICAL_URL="https://$INSTANCE-hrbec6un6a-rj.a.run.app"

# --- 1. Create Cloud SQL User (Optional but Recommended) ---
# Create a dedicated database user for each customer for better security.
# Uncomment these lines if you want per-customer users:
PASSWORD=$(openssl rand -base64 12) # Generate a strong password
gcloud sql users create $CUSTOMER_ID --instance=$DATABASE_INSTANCE --password=$PASSWORD --host=%  
DB_USER=$CUSTOMER_ID

# --- 2. Deploy to Cloud Run ---
gcloud builds submit --tag $IMAGE_NAME .  # Build the image (if needed, you can skip if already built)

gcloud run deploy $INSTANCE \
    --image=$IMAGE_NAME \
    --platform=managed \
    --set-env-vars="REDIRECT_URI=$REDIRECT_URI,ACCESS_TOKEN=$ACCESS_TOKEN,REFRESH_TOKEN=$REFRESH_TOKEN,EXPIRES_AT=$EXPIRES_AT,JUKE_LIST=$JUKE_LIST,LIKES=$LIKES,CLIENT_ID=$CLIENT_ID,CLIENT_SECRET=$CLIENT_SECRET,JUKE_LIST2=$JUKE_LIST2,ICN=$ICN,DB_USER=$DB_USER,DB_PASS=$PASSWORD,DB_NAME=$DB_NAME,INSTANCE=$INSTANCE" \
    --add-cloudsql-instances="$PROJECT_ID:$REGION:$DATABASE_INSTANCE" \
    --allow-unauthenticated # Or configure authentication as needed

# --- 3. Test the Deployment (Optional) ---
#echo "Service URL: https://$SERVICE_NAME-$REGION-$PROJECT_ID.a.run.app"
# You can add a curl command here to test the service

echo "Deployment complete for customer: $INSTANCE"
echo "--------------------------------------------"
gcloud run services describe $INSTANCE --region=southamerica-east1

# Path to user access Python script
PYTHON_SCRIPT="./jukebox_inspiria/user_setup.py"
python "$PYTHON_SCRIPT" "$CUSTOMER_ID"