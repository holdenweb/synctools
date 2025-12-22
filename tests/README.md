# Synctools Test Suite

Comprehensive test suite for the synctools package, covering both local and remote (SSH) synchronization scenarios.

## Test Structure

```
tests/
├── conftest.py           # Shared fixtures and pytest configuration
├── test_file_path.py     # Unit tests for FilePath classes
├── test_sync_dirs.py     # Integration tests for sync_directories
├── test_commands.py      # Tests for sync_to/sync_from functions
└── test_cli.py           # CLI integration tests (slow)
```

## Running Tests

### Basic Usage

Run all tests (excluding CLI tests):
```bash
pytest
```

Run with verbose output:
```bash
pytest -v
```

Run specific test file:
```bash
pytest tests/test_file_path.py
```

Run specific test class:
```bash
pytest tests/test_file_path.py::TestLocalFile
```

Run specific test:
```bash
pytest tests/test_file_path.py::TestLocalFile::test_get_name
```

### Running CLI Tests

CLI tests are slower and skipped by default. To run them:
```bash
pytest --run-cli
```

Run only CLI tests:
```bash
pytest -m cli --run-cli
```

### Running SSH Tests

SSH tests require SSH access to a remote host (default: localhost). These tests are automatically skipped if SSH is not available.

Run only SSH tests:
```bash
pytest -m ssh
```

### Using a Different Remote Host

By default, tests use `localhost` for SSH testing. To test against a different host:
```bash
export SYNCTOOLS_REMOTE_HOST=myserver.example.com
pytest -m ssh
```

**Note:** The remote host must:
- Be accessible via SSH with key-based authentication (no password prompt)
- Have rsync installed
- Allow creation of temporary directories in `/tmp`

## Test Categories

### Unit Tests (`test_file_path.py`)
- Test FilePath factory method
- Test LocalFile operations (exists, is_dir, mkdir, join, etc.)
- Test SSHFile operations
- Test SSH path pattern detection
- Fast, no external dependencies

### Integration Tests (`test_sync_dirs.py`)
- Test sync_directories with various source/dest combinations:
  - Local → Local
  - Local → Remote
  - Remote → Local
  - Remote → Remote
- Test file content preservation
- Test directory structure preservation
- Test --delete behavior (removing extra files)
- Test handling of special characters in filenames
- Requires rsync

### Command Tests (`test_commands.py`)
- Test sync_to and sync_from functions
- Test directory changing and path resolution
- Test error handling for invalid arguments
- Tests work with mocked sys.argv
- Requires rsync

### CLI Tests (`test_cli.py`)
- Test actual CLI command execution via subprocess
- Test command-line argument parsing
- Test output messages and progress display
- Test interrupt handling
- Slower than other tests (skipped by default)
- Requires rsync and properly installed synctools

## Test Fixtures

### Temporary Directories

- `temp_local_dir`: Temporary local directory
- `temp_remote_dir`: Temporary directory in /tmp (accessible as localhost:/tmp/...)
- `original_cwd`: Saves and restores working directory

### Populated Test Data

- `test_file_content`: Dict of filenames → content for testing
- `populated_source`: Local directory with test files
- `populated_remote_source`: Remote directory with test files
- `empty_dest_parent`: Empty destination parent directory
- `empty_remote_dest_parent`: Empty remote destination parent

### Verification

- `verify_sync`: Function to verify sync results match expected content

## Requirements

### Minimum Requirements
- pytest >= 7.0
- Python >= 3.8

### For Full Test Coverage
- rsync installed and in PATH
- SSH server running (for SSH tests)
- SSH key-based authentication configured (for remote host testing)

## Test Coverage

The test suite covers:

### Acceptance Criteria
✓ Local and remote sources work correctly
✓ Local and remote destinations work correctly
✓ All significant problems are detected and reported

### Known Limitations
⚠ **Remote-to-remote sync**: rsync does not support both source and destination being remote paths (e.g., `host1:/path` to `host2:/path` or even `host:/path1` to `host:/path2`). At least one side must be local. To sync between two remote locations, you need to:
  - Run the sync from one of the remote machines, OR
  - Use a two-step process (sync from remote1 to local, then from local to remote2)

This is a limitation of rsync itself, not synctools.

### Error Detection
✓ Source doesn't exist (local/remote)
✓ Source is not a directory (local/remote)
✓ Destination parent doesn't exist (local/remote)
✓ Destination parent is not a directory (local/remote)
✓ Invalid SSH path format
✓ rsync not available
✓ SSH not available (when needed)

### Functionality
✓ Files are copied correctly
✓ Directory structure is preserved
✓ File contents are preserved
✓ Modified files are updated
✓ Extra files are deleted (--delete flag)
✓ Empty directories are handled
✓ Symlinks are preserved
✓ File permissions are preserved
✓ Special characters in filenames are handled
✓ Spaces in filenames are handled

## Troubleshooting

### SSH Tests Failing

If SSH tests are being skipped:
1. Verify SSH server is running: `sudo systemctl status ssh`
2. Test SSH to localhost: `ssh localhost echo test`
3. If prompted for password, set up key-based auth:
   ```bash
   ssh-keygen -t ed25519  # if you don't have a key
   ssh-copy-id localhost
   ```

### CLI Tests Not Running

CLI tests are skipped by default. Use `--run-cli` flag:
```bash
pytest --run-cli
```

If CLI tests fail:
1. Verify synctools is installed: `pip install -e .`
2. Verify commands are in PATH: `which sync_to sync_from`
3. Check that rsync is available: `which rsync`

### Permission Errors

If you get permission errors on /tmp:
- The test suite creates directories in `/tmp` for remote testing
- Ensure you have write permissions to `/tmp`
- Cleanup happens automatically, but orphaned dirs can be removed:
  ```bash
  rm -rf /tmp/synctools_test_*
  ```

## Contributing

When adding new tests:

1. Add unit tests to `test_file_path.py` for low-level functionality
2. Add integration tests to `test_sync_dirs.py` for sync operations
3. Add command tests to `test_commands.py` for high-level commands
4. Add CLI tests to `test_cli.py` for end-to-end CLI behavior (mark with `@cli_tests`)
5. Mark SSH-dependent tests with `@ssh_available`
6. Mark rsync-dependent tests with `@rsync_available`
7. Update this README if adding new test categories or requirements

## Extra Credit Answer

The quote "First, make it work. Then (if it doesn't work fast enough) make it work faster" is commonly attributed to **Kent Beck**, who expressed similar sentiments in his work on Extreme Programming and Test-Driven Development. The philosophy aligns with his "simplest thing that could possibly work" principle.

A related famous quote is Donald Knuth's "Premature optimization is the root of all evil" (1974), which expresses a similar idea about prioritizing correctness before performance.
