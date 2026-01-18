import asyncio
import sys
import logging
import os
from dotenv import load_dotenv
load_dotenv()

from claude_agent_sdk import query, ClaudeAgentOptions, tool, create_sdk_mcp_server
from tools import run_video_pipeline

# Suppress verbose logging for cleaner CLI output
logging.getLogger("azure").setLevel(logging.WARNING)
logging.getLogger("claude_agent_sdk").setLevel(logging.WARNING)
logging.getLogger("tools").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

sys.stdout.reconfigure(encoding='utf-8')

# ANSI color codes for terminal
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    DIM = '\033[2m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def create_progress_callback():
    """Create a callback function for pipeline progress updates."""
    def callback(step, total, status, detail=""):
        if status == "started":
            print(f"\n    {Colors.DIM}[{step}/{total}]{Colors.RESET} {detail}", end='', flush=True)
        elif status == "done":
            print(f" {Colors.GREEN}✓{Colors.RESET}", flush=True)
    return callback

# Single unified tool for the entire video pipeline
@tool(
    "video_pipeline",
    "Process a video file: upload to cloud, transcribe, translate Hindi to English, and generate editor script. Returns all outputs saved to /output folder.",
    {"file_path": str}
)
async def video_pipeline_tool(args):
    """Run the complete video processing pipeline"""
    try:
        progress_callback = create_progress_callback()
        result = run_video_pipeline(args['file_path'], progress_callback=progress_callback)

        # Build response
        steps = ", ".join(result["steps_completed"])

        response = f"""Pipeline Complete!

**Steps completed:** {steps}

**Files saved:**"""

        if "hindi_file" in result:
            response += f"\n- Hindi transcript: {result['hindi_file']}"
        if "english_file" in result:
            response += f"\n- English transcript: {result['english_file']}"
        if "editor_file" in result:
            response += f"\n- Editor script: {result['editor_file']}"
        if "english_audio_file" in result:
            response += f"\n- English audio: {result['english_audio_file']}"

        response += f"\n\n**Cloud URLs (share with editor):**"
        if "azure_url" in result:
            response += f"\n- Video: {result['azure_url']}"
        if "english_transcript_url" in result:
            response += f"\n- Transcript: {result['english_transcript_url']}"
        if "editor_script_url" in result:
            response += f"\n- Editor Notes: {result['editor_script_url']}"
        if "english_audio_url" in result:
            response += f"\n- English Audio: {result['english_audio_url']}"

        response += f"""

---
**ENGLISH TRANSCRIPT:**
{result.get('english_transcript', 'N/A')}

---
**EDITOR SCRIPT:**
{result.get('editor_script', 'N/A')}"""

        return {"content": [{"type": "text", "text": response}]}

    except Exception as e:
        return {"content": [{"type": "text", "text": f"Pipeline failed: {str(e)}"}]}

# Create MCP server with single tool
mcp_server = create_sdk_mcp_server(
    name="video",
    version="1.0.0",
    tools=[video_pipeline_tool]
)

# System prompt
SYSTEM_PROMPT = """You are a video processing CLI tool.

Your main capability is the video_pipeline tool which:
1. Uploads video to Azure cloud storage
2. Transcribes audio (Hindi speech-to-text)
3. Translates transcript to English
4. Generates an editor script with B-roll suggestions, cuts, etc.
5. Saves all outputs to /output folder

When the user wants to process a video, use the video_pipeline tool.
After the pipeline completes, ALWAYS include all cloud URLs in your reply so the user can easily share them with their editor.
Be concise and helpful."""

# Streaming input (required for MCP)
async def message_generator(user_input):
    yield {
        "type": "user",
        "message": {"role": "user", "content": user_input}
    }

def print_header():
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'=' * 50}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}  Video Pipeline Agent{Colors.RESET}")
    print(f"{Colors.CYAN}{'=' * 50}{Colors.RESET}")
    print(f"\n{Colors.DIM}Usage:{Colors.RESET}")
    print(f"  {Colors.GREEN}process <file>{Colors.RESET} - Run full video pipeline")
    print(f"  {Colors.GREEN}exit{Colors.RESET}           - Quit")
    print()

async def main():
    print_header()

    conversation_history = []

    while True:
        try:
            user_input = input(f"{Colors.BOLD}You:{Colors.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{Colors.DIM}Goodbye!{Colors.RESET}")
            break

        if user_input.lower() == 'exit':
            print(f"\n{Colors.DIM}Goodbye!{Colors.RESET}")
            break
        if not user_input:
            continue

        conversation_history.append(f"User: {user_input}")
        full_prompt = "\n".join(conversation_history)

        print(f"\n{Colors.CYAN}Agent:{Colors.RESET} ", end='', flush=True)

        agent_response = ""
        tool_in_progress = False

        async for message in query(
            prompt=message_generator(full_prompt),
            options=ClaudeAgentOptions(
                model="claude-haiku-4-5-20251001",
                system_prompt=SYSTEM_PROMPT,
                mcp_servers={"video": mcp_server},
                include_partial_messages=True,
                allowed_tools=[
                    "Glob",
                    "Bash",
                    "mcp__video__video_pipeline"
                ]
            )
        ):
            msg_type = type(message).__name__

            if msg_type == "StreamEvent":
                event = message.event
                if event.get("type") == "content_block_delta":
                    delta = event.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            if tool_in_progress:
                                print()
                                print(f"{Colors.CYAN}Agent:{Colors.RESET} ", end='')
                                tool_in_progress = False
                            print(text, end='', flush=True)
                            agent_response += text

            elif msg_type == "AssistantMessage" and hasattr(message, 'content') and message.content:
                for block in message.content:
                    if hasattr(block, 'name'):
                        tool_name = block.name.replace('mcp__video__', '')
                        print(f"\n{Colors.YELLOW}  ⚡ Running {tool_name}...{Colors.RESET}", flush=True)
                        tool_in_progress = True

        if agent_response:
            conversation_history.append(f"Agent: {agent_response}")

        print()

if __name__ == "__main__":
    asyncio.run(main())
