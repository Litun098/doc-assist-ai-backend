"""
Script to update all instances of direct client creation to use the connection manager.
This script modifies the codebase to use the connection manager for external service connections.
"""
import os
import re
import logging
from typing import List, Dict, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Patterns to search for
SUPABASE_PATTERN = r"service_supabase\s*=\s*create_client\(\s*supabase_url=settings\.SUPABASE_URL,\s*supabase_key=settings\.SUPABASE_SERVICE_KEY\s*\)"
WEAVIATE_PATTERN = r"self\.weaviate_client\s*=\s*weaviate\.connect_to_weaviate_cloud\(\s*cluster_url=weaviate_url,\s*auth_credentials=Auth\.api_key\(settings\.WEAVIATE_API_KEY\),\s*skip_init_checks=True,\s*additional_config=AdditionalConfig\(\s*timeout=Timeout\(init=\d+\)\s*\)\s*\)"

# Replacements
SUPABASE_REPLACEMENT = "service_supabase = connection_manager.get_supabase_client(\"service\")"
WEAVIATE_REPLACEMENT = "self.weaviate_client = connection_manager.get_weaviate_client()"

def find_files(directory: str, extensions: List[str]) -> List[str]:
    """
    Find all files with the given extensions in the directory.
    
    Args:
        directory: Directory to search in
        extensions: List of file extensions to look for
        
    Returns:
        List of file paths
    """
    file_paths = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                file_paths.append(os.path.join(root, file))
    return file_paths

def update_file(file_path: str, patterns: List[Tuple[str, str]]) -> int:
    """
    Update a file by replacing patterns with replacements.
    
    Args:
        file_path: Path to the file
        patterns: List of (pattern, replacement) tuples
        
    Returns:
        Number of replacements made
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        total_replacements = 0
        new_content = content
        
        for pattern, replacement in patterns:
            # Count matches
            matches = re.findall(pattern, content)
            if matches:
                # Replace matches
                new_content = re.sub(pattern, replacement, new_content)
                total_replacements += len(matches)
                logger.info(f"Found {len(matches)} matches for pattern in {file_path}")
        
        if total_replacements > 0:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(new_content)
            logger.info(f"Updated {file_path} with {total_replacements} replacements")
        
        return total_replacements
    except Exception as e:
        logger.error(f"Error updating {file_path}: {str(e)}")
        return 0

def add_import_to_file(file_path: str, import_statement: str) -> bool:
    """
    Add an import statement to a file if it doesn't already exist.
    
    Args:
        file_path: Path to the file
        import_statement: Import statement to add
        
    Returns:
        True if the import was added, False otherwise
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Check if the import already exists
        if import_statement in content:
            return False
        
        # Find a good place to add the import
        lines = content.split('\n')
        import_index = 0
        
        # Look for the last import statement
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_index = i + 1
        
        # Insert the import statement
        lines.insert(import_index, import_statement)
        
        # Write the updated content
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write('\n'.join(lines))
        
        logger.info(f"Added import to {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error adding import to {file_path}: {str(e)}")
        return False

def main():
    """Main function."""
    logger.info("Updating connections in codebase...")
    
    # Find Python files
    python_files = find_files('app', ['.py'])
    
    # Patterns to replace
    patterns = [
        (SUPABASE_PATTERN, SUPABASE_REPLACEMENT),
        (WEAVIATE_PATTERN, WEAVIATE_REPLACEMENT)
    ]
    
    # Import statement to add
    import_statement = "from app.utils.connection_manager import connection_manager"
    
    # Update files
    total_files_updated = 0
    total_replacements = 0
    
    for file_path in python_files:
        replacements = update_file(file_path, patterns)
        if replacements > 0:
            total_files_updated += 1
            total_replacements += replacements
            # Add import statement
            add_import_to_file(file_path, import_statement)
    
    logger.info(f"Updated {total_files_updated} files with {total_replacements} replacements")

if __name__ == "__main__":
    main()
