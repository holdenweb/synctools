"""
CLI integration tests for sync_to and sync_from commands.

These tests invoke the actual CLI commands as subprocesses.
They are marked with @pytest.mark.cli and are skipped by default.
Run with: pytest --run-cli
"""

import pytest
import sys
import os
import subprocess
from pathlib import Path

# Adjust path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from conftest import rsync_available, ssh_available, cli_tests


@cli_tests
class TestCLISyncTo:
    """CLI tests for sync_to command."""
    
    @rsync_available
    def test_cli_sync_to_local(
        self,
        populated_source,
        empty_dest_parent,
        original_cwd,
        verify_sync
    ):
        """Should sync via CLI to local destination."""
        os.chdir(populated_source)
        
        result = subprocess.run(
            ['sync_to', str(empty_dest_parent)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"sync_to failed: {result.stderr}"
        
        # Verify output mentions synchronization
        assert "Synchronizing" in result.stderr
        
        # Verify files were synced
        dest_dir = empty_dest_parent / populated_source.name
        errors = verify_sync(dest_dir)
        assert not errors, f"Sync verification failed: {errors}"
    
    @rsync_available
    def test_cli_sync_to_no_args(self):
        """Should show usage with no arguments."""
        result = subprocess.run(
            ['sync_to'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1
        assert "Usage:" in result.stderr
    
    @rsync_available
    def test_cli_sync_to_nonexistent_dest(self, populated_source, original_cwd):
        """Should report error for nonexistent destination."""
        os.chdir(populated_source)
        
        result = subprocess.run(
            ['sync_to', '/tmp/totally_nonexistent_xyz_123'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1
        assert "does not exist" in result.stderr
    
    @rsync_available
    @ssh_available
    def test_cli_sync_to_remote(
        self,
        populated_source,
        empty_remote_dest_parent,
        remote_host,
        original_cwd,
        verify_sync
    ):
        """Should sync via CLI to remote destination."""
        os.chdir(populated_source)
        
        remote_path = f"{remote_host}:{empty_remote_dest_parent}"
        
        result = subprocess.run(
            ['sync_to', remote_path],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"sync_to failed: {result.stderr}"
        
        # Verify files were synced
        dest_dir = empty_remote_dest_parent / populated_source.name
        errors = verify_sync(dest_dir)
        assert not errors, f"Sync verification failed: {errors}"


@cli_tests
class TestCLISyncFrom:
    """CLI tests for sync_from command."""
    
    @rsync_available
    def test_cli_sync_from_local(
        self,
        populated_source,
        temp_local_dir,
        original_cwd,
        verify_sync
    ):
        """Should sync via CLI from local source."""
        # Create directory to sync into (with different name to avoid conflict)
        dest_dir = temp_local_dir / "cli_dest_for_sync_from"
        dest_dir.mkdir()
        # Create subdirectory matching source name
        sync_target = dest_dir / populated_source.name
        sync_target.mkdir()
        os.chdir(sync_target)
        
        source_parent = populated_source.parent
        
        result = subprocess.run(
            ['sync_from', str(source_parent)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"sync_from failed: {result.stderr}"
        
        # Verify output mentions synchronization
        assert "Synchronizing" in result.stderr
        
        # Verify files were synced
        errors = verify_sync(sync_target)
        assert not errors, f"Sync verification failed: {errors}"
    
    @rsync_available
    def test_cli_sync_from_no_args(self):
        """Should show usage with no arguments."""
        result = subprocess.run(
            ['sync_from'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1
        assert "Usage:" in result.stderr
    
    @rsync_available
    def test_cli_sync_from_nonexistent_source(
        self,
        temp_local_dir,
        original_cwd
    ):
        """Should report error for nonexistent source."""
        current_dir = temp_local_dir / "myproject"
        current_dir.mkdir()
        os.chdir(current_dir)
        
        result = subprocess.run(
            ['sync_from', '/tmp/totally_nonexistent_xyz_123'],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1
        assert "does not exist" in result.stderr
    
    @rsync_available
    @ssh_available
    def test_cli_sync_from_remote(
        self,
        populated_remote_source,
        temp_local_dir,
        remote_host,
        original_cwd,
        verify_sync
    ):
        """Should sync via CLI from remote source."""
        # Create local directory to sync into
        dest_parent = temp_local_dir / "cli_remote_dest"
        dest_parent.mkdir()
        sync_target = dest_parent / populated_remote_source.name
        sync_target.mkdir()
        os.chdir(sync_target)
        
        source_parent = populated_remote_source.parent
        remote_path = f"{remote_host}:{source_parent}"
        
        result = subprocess.run(
            ['sync_from', remote_path],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0, f"sync_from failed: {result.stderr}"
        
        # Verify files were synced
        errors = verify_sync(sync_target)
        assert not errors, f"Sync verification failed: {errors}"


@cli_tests
class TestCLIOutput:
    """Tests for CLI output and messaging."""
    
    @rsync_available
    def test_cli_shows_progress(
        self,
        populated_source,
        empty_dest_parent,
        original_cwd
    ):
        """Should show progress during sync."""
        os.chdir(populated_source)
        
        result = subprocess.run(
            ['sync_to', str(empty_dest_parent)],
            capture_output=True,
            text=True
        )
        
        # Should show rsync command being executed
        assert "Executing:" in result.stderr
        assert "rsync" in result.stderr
    
    @rsync_available
    def test_cli_shows_source_dest(
        self,
        populated_source,
        empty_dest_parent,
        original_cwd
    ):
        """Should display source and destination paths."""
        os.chdir(populated_source)
        
        result = subprocess.run(
            ['sync_to', str(empty_dest_parent)],
            capture_output=True,
            text=True
        )
        
        # Should show source and destination
        assert "FROM:" in result.stderr or "Source" in result.stderr
        assert "TO:" in result.stderr or "Destination" in result.stderr
    
    @rsync_available
    def test_cli_success_message(
        self,
        populated_source,
        empty_dest_parent,
        original_cwd
    ):
        """Should show success message on completion."""
        os.chdir(populated_source)
        
        result = subprocess.run(
            ['sync_to', str(empty_dest_parent)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "✓" in result.stderr or "completed successfully" in result.stderr


@cli_tests
class TestCLIEdgeCases:
    """Tests for CLI edge cases."""
    
    @rsync_available
    def test_cli_handles_special_chars_in_filenames(
        self,
        populated_source,
        empty_dest_parent,
        original_cwd
    ):
        """Should handle filenames with special characters via CLI."""
        os.chdir(populated_source)
        
        result = subprocess.run(
            ['sync_to', str(empty_dest_parent)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        
        dest_dir = empty_dest_parent / populated_source.name
        assert (dest_dir / "file with spaces.txt").exists()
        assert (dest_dir / "file-with-special!@#.txt").exists()
    
    @rsync_available
    def test_cli_interrupt_handling(
        self,
        populated_source,
        empty_dest_parent,
        original_cwd
    ):
        """Test that CLI handles SIGTERM gracefully."""
        # Note: This test is inherently timing-dependent and may be flaky.
        # The sync often completes before we can interrupt it.
        # We mainly verify that termination works without hanging.
        os.chdir(populated_source)
        
        proc = subprocess.Popen(
            ['sync_to', str(empty_dest_parent)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Give it a moment to start
        import time
        time.sleep(0.1)
        
        # Terminate it
        proc.terminate()
        
        try:
            # Wait for termination, with timeout
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # If it doesn't terminate, kill it
            proc.kill()
            proc.wait()
            pytest.fail("Process did not terminate within timeout")
        
        # Process should have terminated (either completed or interrupted)
        # We don't assert the return code because the sync might complete
        # successfully before we can interrupt it
        assert proc.returncode is not None, "Process should have terminated"
