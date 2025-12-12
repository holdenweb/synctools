#!/usr/bin/env python3
"""
Directory Synchronization Script using rsync.

Usage:
    python sync_dirs.py <source_dir> <destination_parent_dir>

This script synchronizes the source directory to a subdirectory of the destination
parent directory. The subdirectory will have the same name as the source directory.

Example:
    python sync_dirs.py /home/user/documents /backup
    
    This will sync /home/user/documents to /backup/documents/
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List


def validate_directory(path: str, arg_name: str) -> Path:
    """
    Validate that a path exists and is a directory.
    
    Args:
        path: Path string to validate
        arg_name: Name of the argument (for error messages)
    
    Returns:
        Path object if valid
    
    Raises:
        SystemExit: If validation fails
    """
    path_obj = Path(path)
    
    if not path_obj.exists():
        print(f"Error: {arg_name} does not exist: {path}", file=sys.stderr)
        sys.exit(1)
    
    if not path_obj.is_dir():
        print(f"Error: {arg_name} is not a directory: {path}", file=sys.stderr)
        sys.exit(1)
    
    return path_obj


def check_rsync_available() -> bool:
    """
    Check if rsync is available on the system.
    
    Returns:
        True if rsync is available, False otherwise
    """
    try:
        result = subprocess.run(
            ["rsync", "--version"],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def build_rsync_command(source: Path, destination: Path) -> List[str]:
    """
    Build the rsync command with appropriate options.
    
    Args:
        source: Source directory path
        destination: Destination directory path
    
    Returns:
        List of command arguments for subprocess
    """
    # rsync options:
    # -a: archive mode (recursive, preserves permissions, times, symlinks, etc.)
    # -v: verbose output
    # -h: human-readable output
    # --progress: show progress during transfer
    # --delete: delete files in destination that don't exist in source
    # --stats: show file transfer statistics
    
    command = [
        "rsync",
        "-avh",
        "--progress",
        "--delete",
        "--stats",
        str(source) + "/",  # Trailing slash ensures contents are synced, not the dir itself
        str(destination) + "/"
    ]
    
    return command


def sync_directories(source: Path, dest_parent: Path) -> None:
    """
    Synchronize source directory to a subdirectory of dest_parent.
    
    Args:
        source: Source directory to sync from
        dest_parent: Parent directory where subdirectory will be created/synced
    """
    # Get the name of the source directory
    source_name = source.name
    
    # Build the full destination path
    destination = dest_parent / source_name
    
    # Create destination directory if it doesn't exist
    destination.mkdir(parents=True, exist_ok=True)
    
    print(f"Source directory: {source.resolve()}", file=sys.stderr)
    print(f"Destination directory: {destination.resolve()}", file=sys.stderr)
    print(f"\nSynchronizing...\n", file=sys.stderr)
    
    # Build rsync command
    command = build_rsync_command(source, destination)
    
    # Show the command being executed
    print(f"Executing: {' '.join(command)}\n", file=sys.stderr)
    
    try:
        # Run rsync with real-time output
        result = subprocess.run(
            command,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            print(f"\n✓ Synchronization completed successfully!", file=sys.stderr)
        else:
            print(f"\n✗ rsync exited with code {result.returncode}", file=sys.stderr)
            sys.exit(result.returncode)
            
    except KeyboardInterrupt:
        print(f"\n\nSynchronization interrupted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\nError during synchronization: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main function to handle command line arguments and orchestrate sync."""
    # Check arguments
    if len(sys.argv) != 3:
        print("Usage: python sync_dirs.py <source_dir> <destination_parent_dir>", file=sys.stderr)
        print("\nArguments:", file=sys.stderr)
        print("  source_dir              Source directory to synchronize", file=sys.stderr)
        print("  destination_parent_dir  Parent directory for the synchronized copy", file=sys.stderr)
        print("\nExample:", file=sys.stderr)
        print("  python sync_dirs.py /home/user/documents /backup", file=sys.stderr)
        print("  → Syncs to /backup/documents/", file=sys.stderr)
        sys.exit(1)
    
    source_path = sys.argv[1]
    dest_parent_path = sys.argv[2]
    
    # Check if rsync is available
    if not check_rsync_available():
        print("Error: rsync is not available on this system.", file=sys.stderr)
        print("Please install rsync:", file=sys.stderr)
        print("  Ubuntu/Debian: sudo apt-get install rsync", file=sys.stderr)
        print("  macOS: brew install rsync (or use built-in version)", file=sys.stderr)
        print("  Windows: Install via WSL, Cygwin, or msys2", file=sys.stderr)
        sys.exit(1)
    
    # Validate directories
    source = validate_directory(source_path, "Source directory")
    dest_parent = validate_directory(dest_parent_path, "Destination parent directory")
    
    # Perform synchronization
    sync_directories(source, dest_parent)


if __name__ == "__main__":
    main()
