# Pet Persona AI

An AI/ML system that generates unique pet personalities and "voices" for cats and dogs using breed baselines from Wikipedia, YouTube-derived content, and user-specific data (questionnaires, stories, photos/videos).

## Features

- **Breed Baseline Profiles**: Automatically ingest personality traits from Wikipedia and YouTube for any dog or cat breed
- **Personalized Pet Profiles**: Combine breed data with questionnaires, stories, and media to create unique personalities
- **Voice Generation**: Create consistent "voice" profiles with style guides, example phrases, and personality quirks
- **Interactive Chat**: Talk to your pet via text or voice (microphone input with speech-to-text)
- **Continual Learning**: Pet personalities update as you add more content over time

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/pet-persona-ai.git
cd pet-persona-ai

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -e .

# For voice chat features
pip install -e ".[voice]"

# For development
pip install -e ".[dev]"
```

### Configuration

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
```

Edit `.env` to add:
- `YOUTUBE_API_KEY`: Required for YouTube ingestion ([Get one here](https://console.cloud.google.com/apis/credentials))

### Basic Usage

```bash
# Initialize the database
pet-persona init-db

# Ingest breed data from Wikipedia
pet-persona ingest-wikipedia --species dog --breeds "Golden Retriever,Labrador Retriever"

# Create a pet
pet-persona create-pet --user-id myuser --pet-json examples/pet_profile.json

# Add stories about your pet
pet-persona add-story --pet-id <PET_ID> --text "Today Buddy learned a new trick!"

# Update personality based on all data
pet-persona update-personality --pet-id <PET_ID>

# Generate voice profile
pet-persona generate-voice --pet-id <PET_ID> --out data/outputs/voice.json

# Start chatting!
pet-persona chat --pet-id <PET_ID>
```

### Run the Demo

```bash
chmod +x scripts/demo.sh
./scripts/demo.sh
```

## CLI Commands

### Ingestion

```bash
# Ingest Wikipedia data for specific breeds
pet-persona ingest-wikipedia --species dog --breeds "Golden Retriever,Poodle"

# Ingest all starter breeds
pet-persona ingest-wikipedia --species dog --all
pet-persona ingest-wikipedia --species cat --all

# Ingest YouTube data (requires API key)
pet-persona ingest-youtube --species dog --breed "Golden Retriever" --max-results 10
```

### Pet Management

```bash
# Create a pet from JSON file
pet-persona create-pet --user-id USER_ID --pet-json path/to/pet.json

# List all pets
pet-persona list-pets
pet-persona list-pets --user-id USER_ID

# Add stories/notes about your pet
pet-persona add-story --pet-id PET_ID --text "Story text here"
pet-persona add-story --pet-id PET_ID --file path/to/story.txt

# Add media (photos/videos)
pet-persona add-media --pet-id PET_ID --path /path/to/photo.jpg
```

### Personality & Voice

```bash
# Update personality from all data
pet-persona update-personality --pet-id PET_ID

# Generate voice profile
pet-persona generate-voice --pet-id PET_ID
pet-persona generate-voice --pet-id PET_ID --out output.json

# View detailed report
pet-persona report --pet-id PET_ID
```

### Chat

```bash
# Text chat
pet-persona chat --pet-id PET_ID
pet-persona chat --pet-id PET_ID --debug  # Show evidence and intent info
pet-persona chat --pet-id PET_ID --playful  # More expressive responses

# Voice chat (requires voice dependencies)
pet-persona voice-chat --pet-id PET_ID
pet-persona voice-chat --pet-id PET_ID --no-tts  # Text outputonly
```

## Architecture

### Personality System

Personalities are represented as **trait vectors** based on the [MIT Ideonomy traits list](https://ideonomy.mit.edu/), adapted for pets:

- Each trait has a score (0-1) and confidence level
- Evidence snippets link traits to source content
- Traits are extracted using keyword/phrase lexicons

### Data Flow

```
┌─────────────────┐     ┌─────────────────┐
│   Wikipedia     │     │    YouTube      │
│   Breed Data    │     │   Videos/Meta   │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
    ┌────────────────────────────────┐
    │      Trait Extraction          │
    │   (Lexicon + Pattern Match)    │
    └────────────────┬───────────────┘
                     │
                     ▼
    ┌────────────────────────────────┐
    │       Breed Baseline           │
    │    (TraitVector + Sources)     │
    └────────────────┬───────────────┘
                     │
    ┌────────────────┴───────────────┐
    │                                │
    ▼                                ▼
┌──────────┐                 ┌──────────────┐
│Questionnaire│              │ User Stories │
│ Responses   │              │   & Media    │
└──────┬─────┘               └──────┬───────┘
       │                            │
       └────────────┬───────────────┘
                    │
                    ▼
    ┌────────────────────────────────┐
    │    Personality Blending        │
    │  (Weighted + Time Decay)       │
    └────────────────┬───────────────┘
                     │
                     ▼
    ┌────────────────────────────────┐
    │      Voice Generation          │
    │   (Templates + Trait Rules)    │
    └────────────────┬───────────────┘
                     │
                     ▼
    ┌────────────────────────────────┐
    │       Conversation             │
    │   (Intent + Retrieval + Gen)   │
    └────────────────────────────────┘
```

### Continual Learning

Each time you add content or run `update-personality`, the system:

1. Combines breed baseline with user-specific data
2. Applies time decay to older personality snapshots
3. Creates a new versioned snapshot
4. Keeps history for comparison

## Voice Chat Setup

Voice features require additional dependencies:

```bash
pip install -e ".[voice]"
```

### Dependencies

- **sounddevice**: Microphone capture
- **faster-whisper**: Speech-to-text (local, CPU-friendly)
- **pyttsx3**: Text-to-speech (uses system TTS)
- **scipy**: Audio file handling

### OS-Specific Notes

**macOS**:
- Grant microphone permission when prompted
- Works out of the box with system voices

**Linux**:
- Install portaudio: `sudo apt-get install portaudio19-dev`
- For TTS: `sudo apt-get install espeak`

**Windows**:
- Should work out of the box with Windows voices

## API Key Setup

### YouTube Data API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the YouTube Data API v3
4. Create credentials (API Key)
5. Add to `.env`: `YOUTUBE_API_KEY=your_key_here`

**Rate Limits**: The default configuration limits requests to stay within free tier quotas. Adjust in `.env` if needed.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pet_persona

# Run specific test file
pytest tests/test_traits.py
```

## Project Structure

```
pet_persona_ai/
├── src/pet_persona/
│   ├── cli.py              # Command-line interface
│   ├── config.py           # Configuration management
│   ├── db/                 # Database models and repository
│   ├── traits/             # Trait catalog, lexicon, scorer
│   ├── ingest/             # Wikipedia and YouTube ingestion
│   ├── profile/            # Questionnaire, media, personality updater
│   ├── voice/              # Voice generation templates
│   ├── retrieval/          # Embeddings and vector store
│   ├── conversation/       # Chat responder, intent, memory, safety
│   └── speech/             # STT and TTS modules
├── tests/                  # Test suite
├── examples/               # Example JSON files
├── scripts/                # Demo and utility scripts
└── data/                   # Data storage (created at runtime)
```

## Limitations & Next Steps

### Current Limitations

- **No GPU Required**: All operations run on CPU
- **Rule-Based Responses**: Chat uses templates rather than LLM generation
- **Basic Vision**: Media tagging is a placeholder (no actual vision model)
- **English Only**: Optimized for English content

### Future Improvements

- [ ] LLM-based response generation (pluggable interface ready)
- [ ] Vision model for photo/video tagging
- [ ] Better transcript support for YouTube
- [ ] ML-based intent classification
- [ ] Multi-language support
- [ ] Web/mobile interfaces

## Privacy & Compliance

- All processing happens locally by default
- Voice input is processed on-device (faster-whisper)
- No data sent to external services except API calls for ingestion
- YouTube ingestion uses official Data API
- Wikipedia uses their public API with rate limiting

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## Support

- Issues: https://github.com/your-org/pet-persona-ai/issues
- Documentation: This README and inline code comments
