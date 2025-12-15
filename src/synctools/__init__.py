import sys
from pathlib import Path

# Import from the same package
from .sync_dirs import (
    validate_directory,
    check_rsync_available,
    sync_directories,
)

def sync_from():
    """Main function for sync_from command."""
    # Check for correct number of arguments
    if len(sys.argv) != 2:
        from_usage()

    remote_parent_path = sys.argv[1]
    current_dir = Path.cwd()
    current_basename = current_dir.name
    parent_dir = current_dir.parent

    # Check if rsync is available
    if not check_rsync_available():
        prt_error("Error: rsync is not available on this system.")
        sys.exit(1)

    # Validate remote parent directory
    remote_parent = validate_directory(remote_parent_path, "Remote parent directory")

    # Construct the source path (remote subdirectory)
    source = remote_parent / current_basename

    # Validate that the source subdirectory exists
    if not source.exists():
        prt_error(
            f"Error: Source subdirectory does not exist: {source}"
        )
        prt_error(
            f"Expected to find a subdirectory named '{current_basename}' in {remote_parent}",
        )
        sys.exit(1)

    if not source.is_dir():
        prt_error(f"Error: Source path is not a directory: {source}")
        sys.exit(1)

    prt_error(f"Synchronizing FROM: {source.resolve()}")
    prt_error(f"              TO: {current_dir.resolve()}")
    prt_error("")

    # Perform synchronization: source is remote subdirectory, destination is parent of current dir
    sync_directories(source, parent_dir)

def from_usage():
    prt_error("Usage: sync_from <remote_parent_dir>")
    prt_error("")
    prt_error(
        "Synchronizes current directory FROM <remote_parent_dir>/$(basename $PWD)",
    )
    prt_error("")
    prt_error("Example:")
    prt_error("  cd /home/user/myproject")
    prt_error("  sync_from /backup")
    prt_error("  # Syncs FROM /backup/myproject TO current directory")
    sys.exit(1)

def sync_to():
    """Main function for sync_to command."""
    # Check for correct number of arguments
    if len(sys.argv) != 2:
        to_usage()
    remote_parent_path = sys.argv[1]
    current_dir = Path.cwd()

    # Check if rsync is available
    if not check_rsync_available():
        prt_error("Error: rsync is not available on this system.")
        sys.exit(1)

    # Validate remote parent directory
    remote_parent = validate_directory(remote_parent_path, "Remote parent directory")

    prt_error(f"Synchronizing FROM: {current_dir.resolve()}")
    prt_error(
        f"              TO: {remote_parent.resolve()}/{current_dir.name}",
    )
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
    prt_error("Example:")
    prt_error("  cd /home/user/myproject")
    prt_error("  sync_to /backup")
    prt_error("  # Syncs FROM current directory TO /backup/myproject")
    sys.exit(1)

def prt_error(*args, **kwargs):
    return print(*args, file=sys.stderr, **kwargs)
