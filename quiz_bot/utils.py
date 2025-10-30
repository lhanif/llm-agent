from typing import List, Callable, Any
import discord
from discord.webhook import WebhookMessage
from functools import wraps
import re
from .database import db

def ensure_user_registered():
    """
    Decorator to ensure user is registered in database before command execution.
    Use this decorator on command methods that need user registration.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            # Get user information from interaction
            user_id = str(interaction.user.id)
            username = interaction.user.name
            
            # Upsert user
            db.upsert_user(user_id, username)
            
            # Call the original function
            return await func(self, interaction, *args, **kwargs)
        return wrapper
    return decorator

async def send_long_message(interaction: discord.Interaction, content: str, chunk_size: int = 1900) -> List[WebhookMessage]:
    """
    Send a long message in chunks through Discord.
    
    Args:
        interaction: Discord interaction object
        content: The message content to send
        chunk_size: Maximum size of each chunk (default: 1900 to allow for markup)
    
    Returns:
        List of sent message objects
    """
    messages = []
    chunks = split_into_chunks(content, chunk_size)
    
    for i, chunk in enumerate(chunks):
        if i == 0:  # First chunk
            msg = await interaction.followup.send(chunk)
        else:  # Subsequent chunks
            msg = await interaction.followup.send(chunk)
        messages.append(msg)
    
    return messages

def split_into_chunks(content: str, chunk_size: int = 1900) -> List[str]:
    """
    Split content into chunks while preserving markdown code blocks and structure.
    
    Args:
        content: The content to split
        chunk_size: Maximum size of each chunk
    
    Returns:
        List of content chunks
    """
    if len(content) <= chunk_size:
        return [content]
        
    chunks = []
    current_chunk = ""
    code_block = False
    code_lang = ""
    
    # Split by lines first to preserve structure
    lines = content.split('\n')
    
    for line in lines:
        # Check for code block markers
        if line.startswith('```'):
            code_block = not code_block
            if code_block:  # Start of code block
                code_lang = line[3:].strip()
            
        # Calculate new chunk size with this line
        new_chunk = current_chunk + ('' if not current_chunk else '\n') + line
        
        if len(new_chunk) > chunk_size:
            # If we're in a code block, we need to close it in this chunk
            # and reopen it in the next chunk
            if code_block:
                current_chunk += '\n```'
                chunks.append(current_chunk)
                current_chunk = f'```{code_lang}\n{line}'
            else:
                chunks.append(current_chunk)
                current_chunk = line
        else:
            current_chunk = new_chunk
            
    # Add the last chunk if there's anything left
    if current_chunk:
        # Make sure to close any open code blocks
        if code_block and not current_chunk.endswith('```'):
            current_chunk += '\n```'
        chunks.append(current_chunk)
        
    return chunks