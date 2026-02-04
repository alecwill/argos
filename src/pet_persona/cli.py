"""Command-line interface for Pet Persona AI."""

import json
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from pet_persona.config import get_settings
from pet_persona.db import init_db, get_session, Repository
from pet_persona.utils.logging import setup_logging, get_logger

app = typer.Typer(
    name="pet-persona",
    help="AI system for generating unique pet personalities and voices",
    add_completion=False,
)

console = Console()
logger = get_logger(__name__)


def init_app():
    """Initialize the application."""
    settings = get_settings()
    setup_logging(settings.log_level)
    init_db()


# ============================================================================
# Ingestion Commands
# ============================================================================


@app.command("ingest-wikipedia")
def ingest_wikipedia(
    species: str = typer.Option(..., "--species", "-s", help="Species: dog or cat"),
    breeds: str = typer.Option(
        None, "--breeds", "-b", help="Comma-separated breed names"
    ),
    all_breeds: bool = typer.Option(
        False, "--all", "-a", help="Ingest all starter breeds"
    ),
):
    """Ingest breed data from Wikipedia."""
    init_app()

    from pet_persona.ingest import WikipediaIngester, STARTER_DOG_BREEDS, STARTER_CAT_BREEDS

    ingester = WikipediaIngester()

    if all_breeds:
        breed_list = STARTER_DOG_BREEDS if species == "dog" else STARTER_CAT_BREEDS
    elif breeds:
        breed_list = [b.strip() for b in breeds.split(",")]
    else:
        console.print("[red]Error: Specify --breeds or --all[/red]")
        raise typer.Exit(1)

    console.print(f"[bold]Ingesting {len(breed_list)} {species} breeds from Wikipedia...[/bold]")

    baselines = ingester.ingest_breeds(breed_list, species)

    console.print(f"\n[green]Successfully ingested {len(baselines)} breeds![/green]")
    for baseline in baselines:
        console.print(f"  • {baseline.breed_name}: {len(baseline.extracted_traits)} traits")


@app.command("ingest-youtube")
def ingest_youtube(
    species: str = typer.Option(..., "--species", "-s", help="Species: dog or cat"),
    breed: str = typer.Option(..., "--breed", "-b", help="Breed name"),
    max_results: int = typer.Option(10, "--max-results", "-n",help="Max videos to fetch"),
):
    """Ingest breed data from YouTube."""
    init_app()

    from pet_persona.ingest import YouTubeIngester

    ingester = YouTubeIngester()

    console.print(f"[bold]Ingesting YouTube data for {breed}...[/bold]")

    sources = ingester.ingest_breed(breed, species, max_results=max_results)

    if sources:
        scores = ingester.score_sources(sources)
        console.print(f"\n[green]Ingested {len(sources)} videos, extracted {len(scores)} traits[/green]")
    else:
        console.print("[yellow]No videos ingested. Check your YOUTUBE_API_KEY.[/yellow]")


# ============================================================================
# Pet Management Commands
# ============================================================================


@app.command("create-pet")
def create_pet(
    user_id: str = typer.Option(..., "--user-id", "-u", help="User ID"),
    pet_json: Path = typer.Option(..., "--pet-json", "-p", help="Path to pet JSON file"),
):
    """Create a new pet from JSON file."""
    init_app()

    with open(pet_json, "r") as f:
        pet_data = json.load(f)

    with get_session() as session:
        repo = Repository(session)

        # Get or create user
        user = repo.get_or_create_user(user_id)

        # Create pet
        pet = repo.create_pet(
            user_id=user.id,
            name=pet_data["name"],
            species=pet_data["species"],
            breed=pet_data["breed"],
            age=pet_data.get("age"),
            sex=pet_data.get("sex"),
        )

        # Handle questionnaire responses if present
        if "questionnaire_responses" in pet_data:
            repo.update_pet_questionnaire(pet.id, pet_data["questionnaire_responses"])

        console.print(f"\n[green]Created pet: {pet.name}[/green]")
        console.print(f"  Pet ID: {pet.id}")
        console.print(f"  Species: {pet.species}")
        console.print(f"  Breed: {pet.breed}")


@app.command("add-story")
def add_story(
    pet_id: str = typer.Option(..., "--pet-id", "-p", help="Pet ID"),
    text: str = typer.Option(None, "--text", "-t", help="Storytext"),
    file: Path = typer.Option(None, "--file", "-f", help="Pathto story text file"),
):
    """Add a story/note about a pet."""
    init_app()

    if text:
        story_text = text
    elif file:
        story_text = file.read_text()
    else:
        console.print("[red]Error: Specify --text or --file[/red]")
        raise typer.Exit(1)

    with get_session() as session:
        repo = Repository(session)

        pet = repo.get_pet(pet_id)
        if not pet:
            console.print(f"[red]Pet not found: {pet_id}[/red]")
            raise typer.Exit(1)

        doc = repo.create_document(
            pet_id=pet_id,
            doc_type="user_story",
            title=f"Story for {pet.name}",
            content=story_text,
        )

        console.print(f"[green]Added story for {pet.name}[/green]")
        console.print(f"  Document ID: {doc.id}")


@app.command("add-media")
def add_media(
    pet_id: str = typer.Option(..., "--pet-id", "-p", help="Pet ID"),
    path: Path = typer.Option(..., "--path", help="Path to media file"),
):
    """Add media (photo/video) for a pet."""
    init_app()

    from pet_persona.profile import MediaProcessor

    processor = MediaProcessor()
    metadata = processor.process_file(path)

    if not metadata:
        console.print("[red]Failed to process media file[/red]")
        raise typer.Exit(1)

    with get_session() as session:
        repo = Repository(session)

        pet = repo.get_pet(pet_id)
        if not pet:
            console.print(f"[red]Pet not found: {pet_id}[/red]")
            raise typer.Exit(1)

        doc = repo.create_document(
            pet_id=pet_id,
            doc_type="media_metadata",
            title=path.name,
            content=f"Media file: {path.name}",
            metadata=metadata.to_dict(),
        )

        console.print(f"[green]Added media for {pet.name}[/green]")
        console.print(f"  Type: {metadata.file_type}")
        console.print(f"  Document ID: {doc.id}")


# ============================================================================
# Personality Commands
# ============================================================================


@app.command("update-personality")
def update_personality(
    pet_id: str = typer.Option(..., "--pet-id", "-p", help="Pet ID"),
):
    """Update pet personality from all available data."""
    init_app()

    from pet_persona.profile import PersonalityUpdater

    console.print("[bold]Updating personality...[/bold]")

    updater = PersonalityUpdater()
    trait_vector = updater.update_personality(pet_id)

    console.print(f"\n[green]Personality updated with {len(trait_vector.traits)} traits![/green]")

    # Show top traits
    top_traits = trait_vector.get_top_traits(n=5)
    table = Table(title="Top Personality Traits")
    table.add_column("Trait", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Confidence", justify="right")

    for trait in top_traits:
        table.add_row(
            trait.trait_name,
            f"{trait.score:.2f}",
            f"{trait.confidence:.2f}",
        )

    console.print(table)


@app.command("generate-voice")
def generate_voice(
    pet_id: str = typer.Option(..., "--pet-id", "-p", help="Pet ID"),
    out: Path = typer.Option(None, "--out", "-o", help="OutputJSON path"),
):
    """Generate voice profile for a pet."""
    init_app()

    from pet_persona.voice import VoiceGenerator
    from pet_persona.profile import SnapshotManager

    with get_session() as session:
        repo = Repository(session)

        pet = repo.get_pet(pet_id)
        if not pet:
            console.print(f"[red]Pet not found: {pet_id}[/red]")
            raise typer.Exit(1)

        # Get trait vector
        snapshot_manager = SnapshotManager(repo)
        trait_vector = snapshot_manager.get_trait_vector(pet_id)

        if not trait_vector:
            console.print("[yellow]No personality snapshot found. Run update-personality first.[/yellow]")
            raise typer.Exit(1)

        # Generate voice profile
        generator = VoiceGenerator(seed=42)  # Deterministic for consistency
        voice_profile = generator.generate(
            trait_vector=trait_vector,
            species=pet.species,
            name=pet.name,
            age=pet.age,
        )

        # Save to database
        repo.create_voice_profile(pet_id, voice_profile)

        # Save to file if specified
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
            with open(out, "w") as f:
                json.dump(voice_profile.model_dump(), f, indent=2)
            console.print(f"[green]Voice profile saved to: {out}[/green]")

        # Display profile
        console.print(Panel(voice_profile.persona_summary, title=f"{pet.name}'s Voice"))

        console.print("\n[bold]Style Guide:[/bold]")
        for rule in voice_profile.style_guide[:5]:
            console.print(f"  • {rule}")

        console.print("\n[bold]Example Phrases:[/bold]")
        for phrase in voice_profile.example_phrases:
            console.print(f'  "{phrase}"')


@app.command("report")
def report(
    pet_id: str = typer.Option(..., "--pet-id", "-p", help="Pet ID"),
):
    """Show detailed report for a pet."""
    init_app()

    from pet_persona.profile import SnapshotManager

    with get_session() as session:
        repo = Repository(session)

        pet = repo.get_pet(pet_id)
        if not pet:
            console.print(f"[red]Pet not found: {pet_id}[/red]")
            raise typer.Exit(1)

        console.print(Panel(f"[bold]{pet.name}[/bold]\n{pet.species.title()} - {pet.breed}", title="Pet Report"))

        # Show personality
        snapshot_manager = SnapshotManager(repo)
        trait_vector = snapshot_manager.get_trait_vector(pet_id)

        if trait_vector:
            console.print("\n[bold]Top Traits:[/bold]")
            for trait in trait_vector.get_top_traits(n=5):
                bar = "█" * int(trait.score * 10)
                console.print(f"  {trait.trait_name:15} {bar} {trait.score:.2f}")

                if trait.evidence:
                    console.print(f"    Evidence: {trait.evidence[0][:60]}...")

        # Show voice profile
        voice_profile = repo.get_current_voice_profile(pet_id)
        if voice_profile:
            console.print(f"\n[bold]Voice:[/bold] {voice_profile.persona_summary[:100]}...")

        # Show documents
        documents = repo.get_documents_by_pet(pet_id)
        if documents:
            console.print(f"\n[bold]Documents:[/bold] {len(documents)} total")
            for doc in documents[:3]:
                console.print(f"  • {doc.doc_type}: {doc.title}")


# ============================================================================
# Chat Commands
# ============================================================================


@app.command("chat")
def chat(
    pet_id: str = typer.Option(..., "--pet-id", "-p", help="Pet ID"),
    session_id: Optional[str] = typer.Option(None, "--session-id", "-s", help="Session ID"),
    debug: bool = typer.Option(False, "--debug", "-d", help="Show debug info"),
    playful: bool = typer.Option(False, "--playful", help="Enable playful mode"),
):
    """Start an interactive chat session with a pet."""
    init_app()

    from pet_persona.conversation import PetResponder

    try:
        responder = PetResponder(pet_id=pet_id, playful_mode=playful)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    # Create session if not provided
    if not session_id:
        with get_session() as session:
            repo = Repository(session)
            conv_session = repo.create_conversation_session(pet_id)
            session_id = conv_session.id

    pet_name = responder._pet_name
    pet_breed = responder._pet_breed
    console.print(Panel(
        f"Chatting with [bold]{pet_name}[/bold] the {pet_breed}\n"
        f"Type 'quit' or 'exit' to end the conversation.",
        title="Pet Chat"
    ))

    while True:
        try:
            user_input = console.input("\n[bold cyan]You:[/bold cyan] ")
        except (KeyboardInterrupt, EOFError):
            break

        if user_input.lower() in ("quit", "exit", "bye"):
            response = responder.respond("goodbye", session_id=session_id)
            console.print(f"\n[bold green]{pet_name}:[/bold green] {response['response']}")
            break

        if not user_input.strip():
            continue

        result = responder.respond(user_input, session_id=session_id, debug=debug)

        console.print(f"\n[bold green]{pet_name}:[/bold green] {result['response']}")

        if debug and "evidence" in result:
            console.print(f"  [dim]Intent: {result.get('intent', 'unknown')}[/dim]")
            if result["evidence"]:
                console.print(f"  [dim]Evidence: {result['evidence'][0][:50]}...[/dim]")

    console.print("\n[dim]Chat session ended.[/dim]")


@app.command("voice-chat")
def voice_chat(
    pet_id: str = typer.Option(..., "--pet-id", "-p", help="Pet ID"),
    no_tts: bool = typer.Option(False, "--no-tts", help="Disable spoken output"),
    device: Optional[int] = typer.Option(None, "--device", "-d", help="Audio device ID"),
    language: str = typer.Option("en", "--language", "-l", help="Language code"),
    debug: bool = typer.Option(False, "--debug", help="Show debug info"),
):
    """Start a voice chat session with a pet."""
    init_app()

    from pet_persona.conversation import PetResponder
    from pet_persona.speech import MicrophoneListener
    from pet_persona.speech.stt import get_stt
    from pet_persona.speech.tts import get_tts

    # Initialize components
    try:
        responder = PetResponder(pet_id=pet_id)
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    mic = MicrophoneListener(device=device)
    stt = get_stt(language=language)
    tts = get_tts() if not no_tts else None

    if not mic.is_available:
        console.print("[red]Microphone not available. Install sounddevice.[/red]")
        raise typer.Exit(1)

    if not stt.is_available:
        console.print("[yellow]STT not available. Install faster-whisper for voice input.[/yellow]")

    # Create session
    with get_session() as session:
        repo = Repository(session)
        conv_session = repo.create_conversation_session(pet_id)
        session_id = conv_session.id

    pet_name = responder._pet_name
    console.print(Panel(
        f"Voice chatting with [bold]{pet_name}[/bold]\n"
        f"Press Enter to record, or type 'quit' to exit.",
        title="Voice Chat"
    ))

    while True:
        try:
            cmd = console.input("\n[bold]Press Enter to speak (or type 'quit'):[/bold] ")
        except (KeyboardInterrupt, EOFError):
            break

        if cmd.lower() in ("quit", "exit", "bye"):
            break

        # Record audio
        audio_path = mic.record_until_silence()
        if not audio_path:
            console.print("[yellow]Recording failed[/yellow]")
            continue

        # Transcribe
        transcription = stt.transcribe(audio_path)
        if not transcription:
            console.print("[yellow]Transcription failed[/yellow]")
            continue

        console.print(f"\n[cyan]You said:[/cyan] {transcription}")

        # Generate response
        result = responder.respond(transcription, session_id=session_id, debug=debug)
        response_text = result["response"]

        console.print(f"\n[bold green]{pet_name}:[/bold green] {response_text}")

        # Speak response
        if tts and tts.is_available:
            tts.speak(response_text)

        # Cleanup temp file
        audio_path.unlink(missing_ok=True)

    console.print("\n[dim]Voice chat session ended.[/dim]")


# ============================================================================
# Utility Commands
# ============================================================================


@app.command("init-db")
def init_database():
    """Initialize the database."""
    setup_logging("INFO")
    init_db()
    console.print("[green]Database initialized successfully![/green]")


@app.command("list-pets")
def list_pets(
    user_id: Optional[str] = typer.Option(None, "--user-id", "-u", help="Filter by user ID"),
):
    """List all pets."""
    init_app()

    with get_session() as session:
        repo = Repository(session)

        if user_id:
            pets = repo.get_pets_by_user(user_id)
        else:
            from sqlmodel import select
            from pet_persona.db.models import Pet
            pets = list(session.exec(select(Pet)).all())

        if not pets:
            console.print("[yellow]No pets found.[/yellow]")
            return

        table = Table(title="Pets")
        table.add_column("ID", style="dim")
        table.add_column("Name", style="cyan")
        table.add_column("Species")
        table.add_column("Breed")
        table.add_column("Age")

        for pet in pets:
            table.add_row(
                pet.id[:8] + "...",
                pet.name,
                pet.species,
                pet.breed,
                str(pet.age) if pet.age else "-",
            )

        console.print(table)


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
