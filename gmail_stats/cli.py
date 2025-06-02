import click
import logging
from typing import Dict, Optional, List
from collections import OrderedDict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from . import get_sender_counts
from .sender import GmailSender
from .thread import GmailThread

console = Console()

def sort_senders(senders: Dict[str, GmailSender], sort_by: str = 'messages') -> List[tuple]:
    """Sort senders by different criteria.
    
    Args:
        senders: Dict of GmailSender objects
        sort_by: Criteria to sort by ('messages', 'threads', or 'unread_threads')
        
    Returns:
        List of (email, count) tuples sorted by the specified criteria
    """
    if sort_by == 'messages':
        return sorted(senders.items(), key=lambda x: x[1].message_count, reverse=True)
    elif sort_by == 'threads':
        return sorted(senders.items(), key=lambda x: len(x[1].threads), reverse=True)
    elif sort_by == 'unread_threads':
        return sorted(senders.items(), 
                     key=lambda x: sum(1 for t in x[1].threads if 'UNREAD' in t.labels), 
                     reverse=True)
    else:
        raise ValueError(f"Invalid sort criteria: {sort_by}")

def display_sender_table(senders: Dict[str, GmailSender], sort_by: str = 'messages') -> None:
    """Display a table of senders and their counts.
    
    Args:
        senders: Dict of GmailSender objects
        sort_by: Criteria to sort by ('messages', 'threads', or 'unread_threads')
    """
    sorted_senders = sort_senders(senders, sort_by)
    
    table = Table(title=f"Senders sorted by {sort_by.replace('_', ' ')}", box=box.ROUNDED)
    table.add_column("Sender", style="cyan")
    table.add_column("Messages", justify="right", style="green")
    table.add_column("Total Threads", justify="right", style="blue")
    table.add_column("Unread Threads", justify="right", style="yellow")
    
    for email, sender in sorted_senders:
        unread_count = sum(1 for t in sender.threads if 'UNREAD' in t.labels)
        table.add_row(
            email,
            str(sender.message_count),
            str(len(sender.threads)),
            str(unread_count)
        )
    
    console.print(table)

def display_sender_details(sender: GmailSender) -> None:
    """Display detailed information about a sender."""
    console.print(Panel(f"[bold cyan]{sender.sender}[/bold cyan]", title="Sender Details"))
    
    # Add summary statistics
    unread_count = sum(1 for t in sender.threads if 'UNREAD' in t.labels)
    console.print(f"[bold]Total Messages:[/bold] {sender.message_count}")
    console.print(f"[bold]Total Threads:[/bold] {len(sender.threads)}")
    console.print(f"[bold]Unread Threads:[/bold] {unread_count}")
    console.print()
    
    table = Table(box=box.ROUNDED)
    table.add_column("Thread ID", style="dim")
    table.add_column("Subject", style="yellow")
    table.add_column("Labels", style="green")
    table.add_column("Status", style="magenta")
    
    for thread in sender.threads:
        is_unread = 'UNREAD' in thread.labels
        status = "[red]Unread[/red]" if is_unread else "[green]Read[/green]"
        labels = ", ".join(thread.labels)
        table.add_row(thread.thread_id, thread.subject, labels, status)
    
    console.print(table)

@click.group()
def cli():
    """Gmail Statistics CLI - Analyze your Gmail inbox."""
    pass

@cli.command()
@click.option('--sort-by', 
              type=click.Choice(['messages', 'threads', 'unread_threads']),
              default='messages',
              help='Sort criteria for senders')
def list(sort_by: str):
    """List all senders with their message and thread counts."""
    try:
        _, sender_threads = get_sender_counts()
        if sender_threads:
            display_sender_table(sender_threads, sort_by)
        else:
            console.print("[yellow]No messages found.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

@cli.command()
@click.argument('sender_email')
def show(sender_email: str):
    """Show detailed information about a specific sender."""
    try:
        _, sender_threads = get_sender_counts()
        if sender_email in sender_threads:
            display_sender_details(sender_threads[sender_email])
        else:
            console.print(f"[yellow]No messages found from {sender_email}[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

@cli.command()
@click.option('--sort-by', 
              type=click.Choice(['messages', 'threads', 'unread_threads']),
              default='messages',
              help='Sort criteria for senders')
def interactive(sort_by: str):
    """Start an interactive session to explore your Gmail data."""
    try:
        _, sender_threads = get_sender_counts()
        if not sender_threads:
            console.print("[yellow]No messages found.[/yellow]")
            return

        while True:
            display_sender_table(sender_threads, sort_by)
            console.print("\n[bold]Options:[/bold]")
            console.print("1. Enter sender email to see details")
            console.print("2. Type 's' to change sort criteria")
            console.print("3. Type 'q' to quit")
            
            choice = click.prompt("\nEnter your choice", type=str)
            
            if choice.lower() == 'q':
                break
            elif choice.lower() == 's':
                sort_by = click.prompt(
                    "Sort by",
                    type=click.Choice(['messages', 'threads', 'unread_threads']),
                    default=sort_by
                )
            elif choice in sender_threads:
                display_sender_details(sender_threads[choice])
                click.pause()
            else:
                console.print("[yellow]Invalid choice. Please try again.[/yellow]")
                
    except Exception as e:
        console.print(f"[red]Error: {str(e)}[/red]")

def main():
    """Main entry point for the CLI."""
    cli() 