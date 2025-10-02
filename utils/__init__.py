def normalize_path_for_ffmpeg(path: str) -> str:
    """
    Normalize file paths for FFMPEG compatibility on Windows.
    
    On Windows, FFMPEG has issues with backslash path separators,
    so we convert them to forward slashes for video processing operations.
    
    Args:
        path: The file path to normalize
        
    Returns:
        Normalized path with forward slashes
    """
    return path.replace('\\', '/')


def normalize_path_for_os(path: str) -> str:
    """
    Normalize file paths for OS file operations.
    
    Converts forward slashes back to backslashes on Windows for
    file system operations like moving, copying, deleting files.
    
    Args:
        path: The file path to normalize
        
    Returns:
        Path with OS-appropriate separators
    """
    import os
    return path.replace('/', os.sep)
