"""
Pytest configuration and shared fixtures for synctools tests.
"""

import os
import sys
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Generator, Dict, List
import pytest


# Environment variable to allow testing against a different remote host
REMOTE_HOST = os.environ.get('SYNCTOOLS_REMOTE_HOST', 'localhost')


def check_ssh_available() -> bool:
    """Check if SSH to the remote host is available."""
    try:
        result = subprocess.run(
            ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=5', 
             REMOTE_HOST, 'echo test'],
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def check_rsync_available() -> bool:
    """Check if rsync is available."""
    try:
        result = subprocess.run(
            ['rsync', '--version'],
            capture_output=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


# Skip markers
ssh_available = pytest.mark.skipif(
    not check_ssh_available(),
    reason=f"SSH to {REMOTE_HOST} not available"
)

rsync_available = pytest.mark.skipif(
    not check_rsync_available(),
    reason="rsync not available"
)

# Marker for CLI tests (slow, skipped by default)
cli_tests = pytest.mark.cli


@pytest.fixture(scope="session")
def remote_host() -> str:
    """Return the remote host for SSH testing."""
    return REMOTE_HOST


@pytest.fixture
def temp_local_dir() -> Generator[Path, None, None]:
    """
    Create a temporary local directory for testing.
    
    Yields:
        Path to temporary directory
    """
    temp_dir = Path(tempfile.mkdtemp(prefix='synctools_test_local_'))
    try:
        yield temp_dir
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


@pytest.fixture
def temp_remote_dir(remote_host: str) -> Generator[Path, None, None]:
    """
    Create a temporary remote directory for testing.
    
    This creates a directory in /tmp that can be accessed both:
    - Locally as /tmp/synctools_test_remote_XXXX
    - Remotely as localhost:/tmp/synctools_test_remote_XXXX
    
    Yields:
        Path to temporary directory (local path)
    """
    temp_dir = Path(tempfile.mkdtemp(
        prefix='synctools_test_remote_',
        dir='/tmp'
    ))
    try:
        yield temp_dir
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


@pytest.fixture
def test_file_content() -> Dict[str, str]:
    """
    Standard test file contents for verification.
    
    Returns:
        Dictionary mapping filenames to content
    """
    return {
        'file1.txt': 'This is test file 1\nWith multiple lines\n',
        'file2.txt': 'Test file 2 content',
        'file with spaces.txt': 'Testing spaces in filename',
        'file-with-special!@#.txt': 'Testing special characters',
        'subdir/file3.txt': 'File in subdirectory',
        'subdir/nested/file4.txt': 'File in nested subdirectory',
        'empty_file.txt': '',
    }


@pytest.fixture
def populated_source(temp_local_dir: Path, test_file_content: Dict[str, str]) -> Path:
    """
    Create a populated source directory for testing.
    
    Args:
        temp_local_dir: Temporary directory fixture
        test_file_content: Test file content fixture
    
    Returns:
        Path to populated source directory
    """
    source_dir = temp_local_dir / "source_dir"
    source_dir.mkdir()
    
    for filepath, content in test_file_content.items():
        full_path = source_dir / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
    
    return source_dir


@pytest.fixture
def empty_dest_parent(temp_local_dir: Path) -> Path:
    """
    Create an empty destination parent directory.
    
    Args:
        temp_local_dir: Temporary directory fixture
    
    Returns:
        Path to empty destination parent directory
    """
    dest_parent = temp_local_dir / "dest_parent"
    dest_parent.mkdir()
    return dest_parent


@pytest.fixture
def populated_remote_source(
    temp_remote_dir: Path, 
    test_file_content: Dict[str, str]
) -> Path:
    """
    Create a populated remote source directory for testing.
    
    Args:
        temp_remote_dir: Temporary remote directory fixture
        test_file_content: Test file content fixture
    
    Returns:
        Path to populated source directory (accessible locally and remotely)
    """
    source_dir = temp_remote_dir / "source_dir"
    source_dir.mkdir()
    
    for filepath, content in test_file_content.items():
        full_path = source_dir / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content)
    
    return source_dir


@pytest.fixture
def empty_remote_dest_parent(temp_remote_dir: Path) -> Path:
    """
    Create an empty remote destination parent directory.
    
    Args:
        temp_remote_dir: Temporary remote directory fixture
    
    Returns:
        Path to empty destination parent directory
    """
    dest_parent = temp_remote_dir / "dest_parent"
    dest_parent.mkdir()
    return dest_parent


@pytest.fixture
def original_cwd() -> Generator[Path, None, None]:
    """
    Save and restore the original working directory.
    
    Yields:
        Original working directory path
    """
    original = Path.cwd()
    try:
        yield original
    finally:
        os.chdir(original)


def verify_sync_result(
    dest_dir: Path,
    expected_files: Dict[str, str],
    check_content: bool = True
) -> List[str]:
    """
    Verify that a sync operation produced the expected results.
    
    Args:
        dest_dir: Destination directory to verify
        expected_files: Dict of relative paths to expected content
        check_content: Whether to verify file contents (default: True)
    
    Returns:
        List of error messages (empty if verification passed)
    """
    errors = []
    
    for filepath, expected_content in expected_files.items():
        full_path = dest_dir / filepath
        
        if not full_path.exists():
            errors.append(f"Missing file: {filepath}")
            continue
        
        if not full_path.is_file():
            errors.append(f"Not a file: {filepath}")
            continue
        
        if check_content:
            actual_content = full_path.read_text()
            if actual_content != expected_content:
                errors.append(
                    f"Content mismatch in {filepath}:\n"
                    f"  Expected: {repr(expected_content[:50])}\n"
                    f"  Got: {repr(actual_content[:50])}"
                )
    
    return errors


@pytest.fixture
def verify_sync(test_file_content: Dict[str, str]):
    """
    Fixture providing sync verification function with test_file_content bound.
    
    Returns:
        Verification function
    """
    def _verify(dest_dir: Path, check_content: bool = True) -> List[str]:
        return verify_sync_result(dest_dir, test_file_content, check_content)
    return _verify


# Pytest configuration
def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", 
        "cli: mark test as CLI integration test (slow, skipped by default)"
    )
    config.addinivalue_line(
        "markers",
        "ssh: mark test as requiring SSH access"
    )


def pytest_collection_modifyitems(config, items):
    """Skip CLI tests by default unless --run-cli flag is provided."""
    if not config.getoption("--run-cli", default=False):
        skip_cli = pytest.mark.skip(reason="CLI tests skipped (use --run-cli to run)")
        for item in items:
            if "cli" in item.keywords:
                item.add_marker(skip_cli)


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-cli",
        action="store_true",
        default=False,
        help="Run slow CLI integration tests"
    )
