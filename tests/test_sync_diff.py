"""
Tests for sync_diff command.

Tests the directory comparison functionality for both local and remote paths.
"""

import pytest
import sys
import os
import time
from pathlib import Path
from unittest.mock import patch

# Adjust path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from synctools.sync_diff import (
    FileStatus,
    FileInfo,
    ComparisonResult,
    get_local_file_info,
    list_local_files,
    compare_files,
    main as sync_diff_main
)
from synctools.file_path import FilePath, LocalFile
from synctools import sync_diff
from conftest import rsync_available, ssh_available


class TestFileInfo:
    """Tests for FileInfo operations."""
    
    def test_file_info_creation(self):
        """Should create FileInfo with correct attributes."""
        info = FileInfo(
            path="test.txt",
            size=1024,
            mtime=1234567890.0
        )
        
        assert info.path == "test.txt"
        assert info.size == 1024
        assert info.mtime == 1234567890.0
        assert info.exists is True


class TestLocalFileOperations:
    """Tests for local file information gathering."""
    
    def test_get_local_file_info_exists(self, temp_local_dir):
        """Should get info for existing file."""
        test_file = temp_local_dir / "test.txt"
        test_file.write_text("test content")
        
        info = get_local_file_info(temp_local_dir, "test.txt")
        
        assert info is not None
        assert info.path == "test.txt"
        assert info.size > 0
        assert info.mtime > 0
    
    def test_get_local_file_info_missing(self, temp_local_dir):
        """Should return None for missing file."""
        info = get_local_file_info(temp_local_dir, "nonexistent.txt")
        assert info is None
    
    def test_get_local_file_info_directory(self, temp_local_dir):
        """Should return None for directory."""
        subdir = temp_local_dir / "subdir"
        subdir.mkdir()
        
        info = get_local_file_info(temp_local_dir, "subdir")
        assert info is None
    
    def test_list_local_files(self, temp_local_dir):
        """Should list all files recursively."""
        # Create test structure
        (temp_local_dir / "file1.txt").write_text("content1")
        (temp_local_dir / "file2.txt").write_text("content2")
        subdir = temp_local_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content3")
        
        files = list_local_files(temp_local_dir)
        
        assert len(files) == 3
        assert "file1.txt" in files
        assert "file2.txt" in files
        assert str(Path("subdir") / "file3.txt") in files


class TestComparisonLogic:
    """Tests for file comparison logic."""
    
    def test_compare_identical_directories(self, temp_local_dir):
        """Should show all files as SAME when identical."""
        # Create source
        source_dir = temp_local_dir / "source"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content")
        
        # Create identical dest
        dest_dir = temp_local_dir / "dest"
        dest_dir.mkdir()
        (dest_dir / "file1.txt").write_text("content")
        
        # Make mtimes the same
        mtime = time.time()
        os.utime(source_dir / "file1.txt", (mtime, mtime))
        os.utime(dest_dir / "file1.txt", (mtime, mtime))
        
        results = compare_files(source_dir, LocalFile(str(dest_dir)))
        
        assert len(results) == 1
        assert results[0].status == FileStatus.SAME
    
    def test_compare_newer_local(self, temp_local_dir):
        """Should show NEWER when local file is newer."""
        # Create files with different mtimes
        source_dir = temp_local_dir / "source"
        source_dir.mkdir()
        dest_dir = temp_local_dir / "dest"
        dest_dir.mkdir()
        
        # Create dest file first (older)
        dest_file = dest_dir / "file.txt"
        dest_file.write_text("content")
        old_time = time.time() - 100  # 100 seconds ago
        os.utime(dest_file, (old_time, old_time))
        
        # Create source file now (newer)
        source_file = source_dir / "file.txt"
        source_file.write_text("content")
        
        results = compare_files(source_dir, LocalFile(str(dest_dir)))
        
        assert len(results) == 1
        assert results[0].status == FileStatus.NEWER
    
    def test_compare_older_local(self, temp_local_dir):
        """Should show OLDER when local file is older."""
        # Create files with different mtimes
        source_dir = temp_local_dir / "source"
        source_dir.mkdir()
        dest_dir = temp_local_dir / "dest"
        dest_dir.mkdir()
        
        # Create source file first (older)
        source_file = source_dir / "file.txt"
        source_file.write_text("content")
        old_time = time.time() - 100
        os.utime(source_file, (old_time, old_time))
        
        # Create dest file now (newer)
        dest_file = dest_dir / "file.txt"
        dest_file.write_text("content")
        
        results = compare_files(source_dir, LocalFile(str(dest_dir)))
        
        assert len(results) == 1
        assert results[0].status == FileStatus.OLDER
    
    def test_compare_local_only(self, temp_local_dir):
        """Should show LOCAL_ONLY for files only in source."""
        source_dir = temp_local_dir / "source"
        source_dir.mkdir()
        dest_dir = temp_local_dir / "dest"
        dest_dir.mkdir()
        
        (source_dir / "local_only.txt").write_text("content")
        
        results = compare_files(source_dir, LocalFile(str(dest_dir)))
        
        assert len(results) == 1
        assert results[0].status == FileStatus.LOCAL_ONLY
        assert results[0].path == "local_only.txt"
    
    def test_compare_remote_only(self, temp_local_dir):
        """Should show REMOTE_ONLY for files only in dest."""
        source_dir = temp_local_dir / "source"
        source_dir.mkdir()
        dest_dir = temp_local_dir / "dest"
        dest_dir.mkdir()
        
        (dest_dir / "remote_only.txt").write_text("content")
        
        results = compare_files(source_dir, LocalFile(str(dest_dir)))
        
        assert len(results) == 1
        assert results[0].status == FileStatus.REMOTE_ONLY
        assert results[0].path == "remote_only.txt"
    
    def test_compare_conflict(self, temp_local_dir):
        """Should show CONFLICT when mtimes same but sizes differ."""
        source_dir = temp_local_dir / "source"
        source_dir.mkdir()
        dest_dir = temp_local_dir / "dest"
        dest_dir.mkdir()
        
        # Create files with same mtime but different content
        (source_dir / "file.txt").write_text("short")
        (dest_dir / "file.txt").write_text("much longer content")
        
        mtime = time.time()
        os.utime(source_dir / "file.txt", (mtime, mtime))
        os.utime(dest_dir / "file.txt", (mtime, mtime))
        
        results = compare_files(source_dir, LocalFile(str(dest_dir)))
        
        assert len(results) == 1
        assert results[0].status == FileStatus.CONFLICT
    
    def test_compare_multiple_files(self, temp_local_dir):
        """Should handle multiple files with different statuses."""
        source_dir = temp_local_dir / "source"
        source_dir.mkdir()
        dest_dir = temp_local_dir / "dest"
        dest_dir.mkdir()
        
        # Create various scenarios
        # SAME
        (source_dir / "same.txt").write_text("content")
        (dest_dir / "same.txt").write_text("content")
        mtime = time.time()
        os.utime(source_dir / "same.txt", (mtime, mtime))
        os.utime(dest_dir / "same.txt", (mtime, mtime))
        
        # LOCAL_ONLY
        (source_dir / "local.txt").write_text("content")
        
        # REMOTE_ONLY
        (dest_dir / "remote.txt").write_text("content")
        
        results = compare_files(source_dir, LocalFile(str(dest_dir)))
        
        assert len(results) == 3
        statuses = {r.path: r.status for r in results}
        assert statuses["same.txt"] == FileStatus.SAME
        assert statuses["local.txt"] == FileStatus.LOCAL_ONLY
        assert statuses["remote.txt"] == FileStatus.REMOTE_ONLY


class TestSyncDiffCommand:
    """Tests for sync_diff command interface."""
    
    def test_sync_diff_usage_no_args(self, capsys):
        """Should show usage with no arguments."""
        with patch.object(sys, 'argv', ['sync_diff']):
            with pytest.raises(SystemExit) as exc_info:
                sync_diff()
        
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Usage:" in captured.err
    
    def test_sync_diff_local_to_local(
        self,
        temp_local_dir,
        original_cwd,
        capsys
    ):
        """Should compare local directories."""
        # Create source with some files
        source_dir = temp_local_dir / "myproject"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")
        
        # Create dest parent with matching directory
        dest_parent = temp_local_dir / "backup"
        dest_parent.mkdir()
        dest_dir = dest_parent / "myproject"
        dest_dir.mkdir()
        (dest_dir / "file1.txt").write_text("content1")
        (dest_dir / "file3.txt").write_text("content3")
        
        # Make file1 have same mtime
        mtime = time.time()
        os.utime(source_dir / "file1.txt", (mtime, mtime))
        os.utime(dest_dir / "file1.txt", (mtime, mtime))
        
        # Change to source and run diff
        os.chdir(source_dir)
        
        with patch.object(sys, 'argv', ['sync_diff', str(dest_parent)]):
            sync_diff()
        
        captured = capsys.readouterr()
        assert "Summary:" in captured.err
        assert "LOCAL_ONLY" in captured.err or "REMOTE_ONLY" in captured.err
    
    def test_sync_diff_dest_not_exists(
        self,
        temp_local_dir,
        original_cwd,
        capsys
    ):
        """Should error if dest subdirectory doesn't exist."""
        source_dir = temp_local_dir / "myproject"
        source_dir.mkdir()
        
        dest_parent = temp_local_dir / "backup"
        dest_parent.mkdir()
        # Note: backup/myproject does NOT exist
        
        os.chdir(source_dir)
        
        with patch.object(sys, 'argv', ['sync_diff', str(dest_parent)]):
            with pytest.raises(SystemExit):
                sync_diff()
        
        captured = capsys.readouterr()
        assert "does not exist" in captured.err
    
    def test_sync_diff_verbose_flag(
        self,
        temp_local_dir,
        original_cwd,
        capsys
    ):
        """Should show detailed output with --verbose flag."""
        # Create simple setup
        source_dir = temp_local_dir / "myproject"
        source_dir.mkdir()
        (source_dir / "file.txt").write_text("content")
        
        dest_parent = temp_local_dir / "backup"
        dest_parent.mkdir()
        dest_dir = dest_parent / "myproject"
        dest_dir.mkdir()
        (dest_dir / "file.txt").write_text("content")
        
        mtime = time.time()
        os.utime(source_dir / "file.txt", (mtime, mtime))
        os.utime(dest_dir / "file.txt", (mtime, mtime))
        
        os.chdir(source_dir)
        
        with patch.object(sys, 'argv', ['sync_diff', '--verbose', str(dest_parent)]):
            sync_diff()
        
        captured = capsys.readouterr()
        assert "Detailed Comparison:" in captured.err


@pytest.mark.ssh
class TestSyncDiffRemote:
    """Tests for sync_diff with remote directories."""
    
    @ssh_available
    def test_sync_diff_with_remote(
        self,
        temp_local_dir,
        temp_remote_dir,
        remote_host,
        original_cwd,
        capsys
    ):
        """Should compare local with remote directory."""
        # Create local directory
        source_dir = temp_local_dir / "myproject"
        source_dir.mkdir()
        (source_dir / "file1.txt").write_text("content1")
        (source_dir / "file2.txt").write_text("content2")
        
        # Create remote directory
        remote_parent = temp_remote_dir / "backup"
        remote_parent.mkdir()
        remote_dir = remote_parent / "myproject"
        remote_dir.mkdir()
        (remote_dir / "file1.txt").write_text("content1")
        (remote_dir / "file3.txt").write_text("content3")
        
        os.chdir(source_dir)
        
        remote_path = f"{remote_host}:{remote_parent}"
        
        with patch.object(sys, 'argv', ['sync_diff', remote_path]):
            sync_diff()
        
        captured = capsys.readouterr()
        assert "Summary:" in captured.err
        # Should detect file2 (local only) and file3 (remote only)
        assert "LOCAL_ONLY" in captured.err or "REMOTE_ONLY" in captured.err
