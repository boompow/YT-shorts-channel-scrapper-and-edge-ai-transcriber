import os
import sys
import json
import argparse
import time
from datetime import datetime
from dotenv import load_dotenv

# Force console standard output and error to use UTF-8 on Windows to prevent UnicodeEncodeError with emojis
if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')  # type: ignore
    except Exception:
        pass
if sys.stderr.encoding.lower() != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')  # type: ignore
    except Exception:
        pass


# Import local modules
import config
from scraper import scrape_shorts_list
from transcriber import download_audio_for_short, transcribe_audio_with_whisper, load_whisper_model

# Import Rich elements for a stunning Terminal UI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich import box

console = Console()

def load_state(json_path):
    """Loads the database state from the JSON file."""
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            console.print(f"[bold red]Error reading state file {json_path}: {e}. Starting fresh.[/bold red]")
    return []

def save_state(state, json_path):
    """Saves the database state to the JSON file."""
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        console.print(f"[bold red]Error saving state file {json_path}: {e}[/bold red]")

def merge_states(old_state, new_state):
    """
    Merges newly scraped shorts with existing ones.
    Preserves transcription progress for already known shorts.
    """
    old_map = {item['id']: item for item in old_state}
    merged = []
    
    # Keep existing ones if they are in the new list, or add new ones
    for item in new_state:
        video_id = item['id']
        if video_id in old_map:
            # Preserve existing transcription data
            merged.append(old_map[video_id])
        else:
            # New short discovered
            merged.append(item)
            
    # Include completed shorts that might no longer be in the channel's top feed
    # (keeps our database from losing historical data)
    new_ids = {item['id'] for item in new_state}
    for video_id, old_item in old_map.items():
        if video_id not in new_ids and old_item.get('status') == 'completed':
            merged.append(old_item)
            
    return merged

def export_transcripts_txt(state, txt_path):
    """Regenerates the transcripts.txt file using all completed transcriptions."""
    try:
        completed_items = [item for item in state if item.get('status') == 'completed' and item.get('transcript')]
        
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(f"================================================================================\n")
            f.write(f"               YOUTUBE SHORTS TRANSCRIPTIONS EXPORT - {len(completed_items)} VIDEOS\n")
            f.write(f"               Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"================================================================================\n\n")
            
            for item in completed_items:
                f.write(f"================================================================================\n")
                f.write(f"Title: {item.get('title')}\n")
                f.write(f"URL: {item.get('url')}\n")
                f.write(f"Transcribed At: {item.get('transcribed_at')}\n")
                f.write(f"--------------------------------------------------------------------------------\n")
                f.write(f"{item.get('transcript').strip()}\n")
                f.write(f"================================================================================\n\n")
    except Exception as e:
        console.print(f"[bold red]Error exporting transcripts to txt: {e}[/bold red]")

def display_welcome_banner(channel, json_path, txt_path, model_size, device):
    """Displays a beautiful title banner."""
    banner_content = (
        f"[bold cyan]YouTube Channel:[/bold cyan] {channel}\n"
        f"[bold cyan]State Database (JSON):[/bold cyan] [green]{json_path}[/green]\n"
        f"[bold cyan]Transcript Output (TXT):[/bold cyan] [green]{txt_path}[/green]\n"
        f"[bold cyan]Whisper Model:[/bold cyan] {model_size} ([yellow]{device}[/yellow])"
    )
    console.print(
        Panel(
            banner_content,
            title="[bold magenta]🚀 YT Shorts Scraper & Local Transcriber[/bold magenta]",
            subtitle="Powered by Faster-Whisper & yt-dlp",
            border_style="cyan",
            box=box.ROUNDED
        )
    )

def main():
    # Load environment variables from .env
    load_dotenv()
    
    channel_env = os.getenv("YOUTUBE_CHANNEL")
    
    parser = argparse.ArgumentParser(description="Scrape and transcribe YouTube Shorts using local Faster-Whisper.")
    parser.add_argument("-c", "--channel", required=channel_env is None, default=channel_env,
                        help="YouTube channel handle (e.g. '@username') or URL (defaults to YOUTUBE_CHANNEL from .env)")
    parser.add_argument("-d", "--delay", type=float, default=config.DEFAULT_DELAY_SECONDS, 
                        help=f"Delay between downloads in seconds (default: {config.DEFAULT_DELAY_SECONDS}s)")
    parser.add_argument("-f", "--force-scrape", action="store_true", 
                        help="Force a new scrape of the channel even if a state file exists")
    parser.add_argument("-o", "--output-json", default=config.DEFAULT_JSON_OUTPUT, 
                        help=f"Path to state JSON database (default: {config.DEFAULT_JSON_OUTPUT})")
    parser.add_argument("-t", "--output-txt", default=config.DEFAULT_TXT_OUTPUT, 
                        help=f"Path to transcripts TXT output (default: {config.DEFAULT_TXT_OUTPUT})")
    parser.add_argument("-m", "--model", default=config.WHISPER_MODEL,
                        choices=["tiny", "base", "small", "medium"],
                        help=f"Whisper model size (default: {config.WHISPER_MODEL})")
    
    args = parser.parse_args()
    
    # 1. Load local Whisper model
    with console.status("[bold yellow]Loading Faster-Whisper model (first run downloads it automatically)...[/bold yellow]", spinner="aesthetic"):
        try:
            model, resolved_device = load_whisper_model(
                model_size=args.model,
                device=config.WHISPER_DEVICE,
                compute_type=config.WHISPER_COMPUTE_TYPE
            )
        except Exception as e:
            console.print(f"[bold red]Failed to load Whisper model: {e}[/bold red]")
            sys.exit(1)
    console.print(f"[bold green]✓ Whisper model '{args.model}' loaded on {resolved_device.upper()}.[/bold green]")

    display_welcome_banner(args.channel, args.output_json, args.output_txt, args.model, resolved_device)
    
    # 2. Check and Load State
    state = load_state(args.output_json)
    
    # Determine if we need to scrape
    should_scrape = args.force_scrape or len(state) == 0
    
    if should_scrape:
        with console.status(f"[bold yellow]Scraping Shorts list from {args.channel}...[/bold yellow]", spinner="aesthetic"):
            try:
                scraped_shorts = scrape_shorts_list(args.channel)
                state = merge_states(state, scraped_shorts)
                save_state(state, args.output_json)
                console.print(f"[bold green]✓ Scraped {len(scraped_shorts)} Shorts. Saved list to {args.output_json}.[/bold green]")
            except Exception as e:
                console.print(f"[bold red]Scraping failed: {e}[/bold red]")
                if len(state) == 0:
                    console.print("[bold red]No existing state. Exiting.[/bold red]")
                    sys.exit(1)
                else:
                    console.print("[bold yellow]Proceeding using existing cached state database.[/bold yellow]")
    else:
        console.print(f"[bold blue]ℹ Loaded cached state from {args.output_json} containing {len(state)} shorts.[/bold blue]")

    # 3. Analyze work to do
    pending_items = [item for item in state if item.get('status') == 'pending']
    completed_items = [item for item in state if item.get('status') == 'completed']
    
    total_count = len(state)
    pending_count = len(pending_items)
    completed_count = len(completed_items)
    
    # Print status summary
    summary_table = Table(box=box.SIMPLE, show_header=False, width=50)
    summary_table.add_row("Total Shorts:", f"[bold cyan]{total_count}[/bold cyan]")
    summary_table.add_row("Transcribed:", f"[bold green]{completed_count}[/bold green]")
    summary_table.add_row("Pending:", f"[bold yellow]{pending_count}[/bold yellow]")
    console.print(Panel(summary_table, title="[bold]Processing Status[/bold]", border_style="blue", expand=False))
    
    if pending_count == 0:
        console.print("[bold green]🎉 All Shorts have already been transcribed! Exporting final output...[/bold green]")
        export_transcripts_txt(state, args.output_txt)
        sys.exit(0)
        
    # 4. Transcription Process Loop
    console.print("\n[bold yellow]Starting transcription loop. Press Ctrl+C at any time to pause safely.[/bold yellow]\n")
    
    processed_this_run = 0
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=40),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            overall_task = progress.add_task("[magenta]Overall Progress[/magenta]", total=pending_count)
            
            for idx, item in enumerate(pending_items):
                video_id = item['id']
                title = item['title']
                url = item['url']
                
                # Truncate title for UI display
                display_title = title if len(title) <= 35 else title[:32] + "..."
                progress.update(overall_task, description=f"[cyan]Processing: {display_title}[/cyan]")
                
                # Step A: Download Audio
                progress.print(f"[blue]→ [{idx+1}/{pending_count}] Downloading audio for '{display_title}'...[/blue]")
                try:
                    audio_path = download_audio_for_short(video_id, url, config.DOWNLOADS_DIR)
                except Exception as e:
                    progress.print(f"[bold red]❌ Failed to download audio for {video_id}: {e}[/bold red]")
                    progress.advance(overall_task)
                    continue
                    
                # Step B: Local Transcription
                progress.print(f"[blue]→ Transcribing audio locally with Whisper...[/blue]")
                try:
                    transcript_text = transcribe_audio_with_whisper(model, audio_path)
                    
                    # Save transcription to state
                    item['status'] = 'completed'
                    item['transcript'] = transcript_text
                    item['transcribed_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Persist state after each successful transcription
                    save_state(state, args.output_json)
                    export_transcripts_txt(state, args.output_txt)
                    
                    progress.print(f"[bold green]✓ Successfully transcribed '{display_title}'![/bold green]")
                    processed_this_run += 1
                except Exception as e:
                    progress.print(f"[bold red]❌ Failed to transcribe {video_id}: {e}[/bold red]")
                
                progress.advance(overall_task)
                
                # Step C: Small delay between downloads (polite to YouTube)
                if idx < pending_count - 1 and args.delay > 0:
                    time.sleep(args.delay)
                    
    except KeyboardInterrupt:
        console.print("\n[bold orange3]⚠ Execution paused by user (KeyboardInterrupt). Saving progress...[/bold orange3]")
        save_state(state, args.output_json)
        export_transcripts_txt(state, args.output_txt)
        console.print("[bold green]Progress saved successfully. Run the command again to resume anytime![/bold green]")
        sys.exit(0)
        
    # Final Recap
    console.print(f"\n[bold green]🏁 Finished! Transcribed {processed_this_run} shorts during this run.[/bold green]")
    console.print(f"[bold green]Combined transcripts saved to: [underline]{args.output_txt}[/underline][/bold green]")

if __name__ == '__main__':
    main()
