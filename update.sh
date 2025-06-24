#!/bin/bash

# --- Configuration ---
PROJECT_ID="jukebox-446711"

# --- Input Parameters ---
INSTANCE="$1"
IMAGE_NAME="gcr.io/$PROJECT_ID/login" # Your container image

gcloud builds submit --tag $IMAGE_NAME .  # Build the image (if needed, you can skip if already built)

gcloud run deploy $INSTANCE --image=$IMAGE_NAME --platform=managed

echo "Deployment complete for customer: $INSTANCE"