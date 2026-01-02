import sys
from pathlib import Path

# Import from the same package
from .sync_dirs import (
    check_rsync_available,
    sync_directories,
)
from .file_path import FilePath, LocalFile
from .sync_diff import main as sync_diff_main


def sync_from():
    """Main function for sync_from command."""
    # Check for correct number of arguments
    if len(sys.argv) != 2:
        from_usage()

    remote_parent_path = sys.argv[1]
    
    # Get current directory as LocalFile
    current_dir = LocalFile(str(Path.cwd()))
    current_basename = current_dir.get_name()

    # Check if rsync is available
    if not check_rsync_available():
        prt_error("Error: rsync is not available on this system.")
        sys.exit(1)

    # Create FilePath for remote parent (auto-detects local vs remote)
    remote_parent = FilePath.create(remote_parent_path)
    
    # Validate remote parent directory
    remote_parent.validate("Remote parent directory")

    # Construct the source path (subdirectory with current dir's name)
    source = remote_parent.join(current_basename)
    
    # For remote paths, we could validate the subdirectory exists, but rsync
    # will fail gracefully if it doesn't, so we skip the extra check
    # For local paths, validate the subdirectory exists
    if isinstance(source, LocalFile):
        if not source.exists():
            prt_error(f"Error: Source subdirectory does not exist: {source.for_display()}")
            prt_error(f"Expected to find a subdirectory named '{current_basename}' in {remote_parent.for_display()}")
            sys.exit(1)
        
        if not source.is_dir():
            prt_error(f"Error: Source path is not a directory: {source.for_display()}")
            sys.exit(1)

    prt_error(f"Synchronizing FROM: {source.for_display()}")
    prt_error(f"              TO: {current_dir.for_display()}")
    prt_error("")

    # Perform synchronization: source is subdirectory, destination is parent of current dir
    parent_dir = current_dir.get_parent()
    sync_directories(source, parent_dir)


def from_usage():
    prt_error("Usage: sync_from <remote_parent_dir>")
    prt_error("")
    prt_error(
        "Synchronizes current directory FROM <remote_parent_dir>/$(basename $PWD)",
    )
    prt_error("")
    prt_error("Arguments:")
    prt_error("  remote_parent_dir  Parent directory (local or remote SSH path)")
    prt_error("")
    prt_error("Examples:")
    prt_error("  cd /home/user/myproject")
    prt_error("  sync_from /backup")
    prt_error("  # Syncs FROM /backup/myproject TO current directory")
    prt_error("")
    prt_error("  cd /home/user/myproject")
    prt_error("  sync_from user@server:/backup")
    prt_error("  # Syncs FROM user@server:/backup/myproject TO current directory")
    sys.exit(1)


def sync_to():
    """Main function for sync_to command."""
    # Check for correct number of arguments
    if len(sys.argv) != 2:
        to_usage()
        
    remote_parent_path = sys.argv[1]
    
    # Get current directory as LocalFile
    current_dir = LocalFile(str(Path.cwd()))

    # Check if rsync is available
    if not check_rsync_available():
        prt_error("Error: rsync is not available on this system.")
        sys.exit(1)

    # Create FilePath for remote parent (auto-detects local vs remote)
    remote_parent = FilePath.create(remote_parent_path)
    
    # Validate remote parent directory
    remote_parent.validate("Remote parent directory")

    # Build destination path for display
    destination = remote_parent.join(current_dir.get_name())

    prt_error(f"Synchronizing FROM: {current_dir.for_display()}")
    prt_error(f"              TO: {destination.for_display()}")
    prt_error("")

    # Perform synchronization: source is current directory, destination is remote parent
    sync_directories(current_dir, remote_parent)


def to_usage():
    prt_error("Usage: sync_to <remote_parent_dir>")
    prt_error("")
    prt_error(
        "Synchronizes current directory TO <remote_parent_dir>/$(basename $PWD)",
    )
    prt_error("")
    prt_error("Arguments:")
    prt_error("  remote_parent_dir  Parent directory (local or remote SSH path)")
    prt_error("")
    prt_error("Examples:")
    prt_error("  cd /home/user/myproject")
    prt_error("  sync_to /backup")
    prt_error("  # Syncs FROM current directory TO /backup/myproject")
    prt_error("")
    prt_error("  cd /home/user/myproject")
    prt_error("  sync_to user@server:/backup")
    prt_error("  # Syncs FROM current directory TO user@server:/backup/myproject")
    sys.exit(1)


def prt_error(*args, **kwargs):
    return print(*args, file=sys.stderr, **kwargs)


def sync_diff():
    """Main function for sync_diff command."""
    sync_diff_main()
