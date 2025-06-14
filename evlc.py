#!/usr/bin/env python3
import subprocess
import os
import argparse
import time
import signal

# Global variable for debug mode
DEBUG_MODE = False

# Global variable to keep track of the VLC process
vlc_process = None

def debug_print(message):
    """Prints a message only if DEBUG_MODE is True."""
    if DEBUG_MODE:
        print(message)

def start_vlc(media_path, media_format, dry_run=False):
    global vlc_process

    # Define VLC options based on format
    vlc_options = []
    if media_format == 'photo':
        vlc_options = ['--play-and-pause', '--no-osd']
    elif media_format == 'video':
        vlc_options = ['--loop', '--no-osd'] 
    elif media_format == 'gif':
        vlc_options = ['--demux=avformat', '--loop', '--no-osd', '--aspect-ratio=4:3', '--crop=16:9']
    else:
        print(f"Error: Unknown format '{media_format}'. Supported formats are 'gif', 'photo', 'video'.")
        return

    # Construct the full VLC command
    command = ['cvlc', media_path] + vlc_options

    debug_print(f"\n--- VLC Command ---")
    debug_print(f"Format: {media_format}")
    debug_print(f"File: {media_path}")
    debug_print(f"Generated Command: {' '.join(command)}")
    debug_print(f"-------------------")

    if not dry_run: # Only execute if dry_run is False
        if vlc_process:
            print("VLC is already running via this script. Please stop it first before starting a new one.")
            return

        debug_print("\nExecuting command...")
        try:
            vlc_process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid)
            debug_print(f"VLC started with PID: {vlc_process.pid}")
            time.sleep(0.5)
        except FileNotFoundError:
            print("Error: `cvlc` command not found. Make sure VLC is installed and in your system's PATH.")
        except Exception as e:
            print(f"An unexpected error occurred while trying to start VLC: {e}")
    else:
        debug_print("\nPerforming a dry run (command not executed).")

def stop_vlc_process():
    global vlc_process

    found_pids = []
    try:
        pgrep_output = subprocess.check_output(['pgrep', 'vlc']).decode('utf-8').strip()
        
        if pgrep_output:
            found_pids = [int(pid) for pid in pgrep_output.split('\n')]
    except subprocess.CalledProcessError:
        debug_print("No 'vlc' processes found by 'pgrep'.") # Debug print
        if vlc_process:
            vlc_process = None
        return
    except FileNotFoundError:
        print("Error: 'pgrep' command not found. Cannot automatically find and kill processes.")
        print("Please ensure 'pgrep' is installed and in your system's PATH.")
        return
    except Exception as e:
        print(f"An unexpected error occurred while trying to find processes with 'pgrep': {e}")
        return

    if not found_pids:
        print("No 'vlc' processes are currently running.") # This is a primary status, keep it visible
        if vlc_process:
            vlc_process = None
        return

    debug_print(f"Found 'vlc' processes with PIDs: {', '.join(map(str, found_pids))}")
    debug_print("Attempting to terminate...")

    killed_count = 0
    for pid in found_pids:
        try:
            os.kill(pid, signal.SIGTERM)
            debug_print(f"Sent SIGTERM to PID {pid}.")
            killed_count += 1
        except ProcessLookupError:
            debug_print(f"PID {pid} not found (already terminated or invalid).")
        except PermissionError:
            print(f"Permission denied to kill PID {pid}. Check user permissions.") # Error message
        except Exception as e:
            print(f"An error occurred while trying to kill PID {pid}: {e}") # Error message

    if killed_count > 0:
        print(f"Successfully sent termination signal to {killed_count} 'vlc' process(es).") # Primary feedback
        if vlc_process:
            vlc_process = None
    else:
        print("No 'vlc' processes were successfully terminated (might be running under different user or already dead).") # Primary feedback

def get_vlc_status():
    global vlc_process
    
    try:
        subprocess.check_output(['pgrep', '-c', 'vlc'], stderr=subprocess.DEVNULL)
        debug_print("At least one 'vlc' process is currently running (found by pgrep).")
    except subprocess.CalledProcessError:
        debug_print("No 'vlc' processes are currently running (not found by pgrep).")
    except FileNotFoundError:
        print("Error: 'pgrep' command not found. Cannot determine status.") # Error message
    except Exception as e:
        print(f"An unexpected error occurred while checking status: {e}") # Error message
    
    if vlc_process and vlc_process.poll() is None:
        debug_print(f"  (Internally tracked VLC process with PID {vlc_process.pid} is active.)")
    elif vlc_process and vlc_process.poll() is not None:
        debug_print(f"  (Internally tracked VLC process with PID {vlc_process.pid} has terminated.)")
        vlc_process = None
    else:
        debug_print("  (No VLC process is currently tracked by this script instance.)")

    # For status command, if no debug info, just print a concise summary
    if not DEBUG_MODE:
        try:
            pgrep_count = int(subprocess.check_output(['pgrep', '-c', 'vlc']).decode('utf-8').strip())
            if pgrep_count > 0:
                print(f"VLC status: {pgrep_count} process(es) running.")
            else:
                print("VLC status: No processes running.")
        except Exception:
            print("VLC status: Unable to determine (pgrep error).")


def main():
    global DEBUG_MODE # Declare global here to modify it

    parser = argparse.ArgumentParser(
        description="Control `cvlc` with simplified commands. Use 'stop' or 'status' as commands, "
                    "or specify format directly for playback.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        'action_or_format',
        help='Media format ("gif", "photo", "video") to play, or a command ("stop", "status").'
    )

    parser.add_argument(
        'file',
        nargs='?',
        type=str,
        help='Path to the media file. Required when playing media.'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='For play commands: print the cvlc command but do not execute it.'
    )

    # --- IMPORTANT CHANGE HERE: Added --debug argument ---
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable verbose debug output.'
    )

    args = parser.parse_args()

    # Set DEBUG_MODE based on the parsed argument
    DEBUG_MODE = args.debug

    # Determine action based on the first argument
    if args.action_or_format in ['gif', 'photo', 'video']:
        media_format = args.action_or_format
        media_file = args.file

        if not media_file:
            parser.error(f"Error: A file path is required when specifying the format '{media_format}'. "
                         f"Usage: evlc {media_format} <file_path>")
        
        start_vlc(media_file, media_format, args.dry_run)

    elif args.action_or_format == 'stop':
        if args.file or args.dry_run: # --dry-run is for play command only
            parser.error("Error: 'stop' command does not take a file path or --dry-run. "
                         "Usage: evlc stop")
        stop_vlc_process()

    elif args.action_or_format == 'status':
        if args.file or args.dry_run: # --dry-run is for play command only
            parser.error("Error: 'status' command does not take a file path or --dry-run. "
                         "Usage: evlc status")
        get_vlc_status()

    else:
        parser.error(f"Error: Unrecognized command or media format: '{args.action_or_format}'. "
                     "Expected 'gif', 'photo', 'video', 'stop', or 'status'.")

if __name__ == "__main__":
    main()
