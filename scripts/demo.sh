#!/bin/bash
# Pet Persona AI Demo Script
# This script demonstrates the full pipeline from ingestion to chat.

set -e

echo "================================================"
echo "Pet Persona AI - Demo Script"
echo "================================================"
echo ""

# Change to project directory
cd "$(dirname "$0")/.."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install package
echo "Installing package..."
pip install -e . -q

# Initialize database
echo ""
echo "Step 1: Initializing database..."
pet-persona init-db

# Ingest Wikipedia data for Golden Retriever
echo ""
echo "Step 2: Ingesting breed data from Wikipedia..."
pet-persona ingest-wikipedia --species dog --breeds "Golden Retriever"

# Create a sample pet
echo ""
echo "Step 3: Creating a sample pet..."
pet-persona create-pet --user-id demo_user --pet-json examples/pet_profile.json

# Get the pet ID (we'll capture it from the output)
PET_ID=$(python3 -c "
from pet_persona.db import get_session, Repository, init_db
init_db()
with get_session() as session:
    repo = Repository(session)
    pets = repo.get_pets_by_user('demo_user')
    if pets:
        print(pets[0].id)
")

if [ -z "$PET_ID" ]; then
    echo "Error: Could not find pet ID"
    exit 1
fi

echo "Pet ID: $PET_ID"

# Add a story about the pet
echo ""
echo "Step 4: Adding a story about the pet..."
pet-persona add-story --pet-id "$PET_ID" --text "Buddy went to the dog park today and made three new friends! He played fetch for hours and came home tired but happy. He's the friendliest dogat the park."

# Update personality
echo ""
echo "Step 5: Updating personality based on all data..."
pet-persona update-personality --pet-id "$PET_ID"

# Generate voice profile
echo ""
echo "Step 6: Generating voice profile..."
mkdir -p data/outputs
pet-persona generate-voice --pet-id "$PET_ID" --out data/outputs/voice_buddy.json

# Show report
echo ""
echo "Step 7: Showing pet report..."
pet-persona report --pet-id "$PET_ID"

# Start chat
echo ""
echo "================================================"
echo "Demo complete! Starting chat session..."
echo "Type 'quit' to exit."
echo "================================================"
echo ""

pet-persona chat --pet-id "$PET_ID"

echo ""
echo "Demo finished. Voice profile saved to: data/outputs/voice_buddy.json"
