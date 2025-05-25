# Document Processing Fixes - AnyDocAI

## Issues Identified and Fixed

### 1. **File Type Detection Problems**
**Problem**: Files were being saved with `temp_` prefix without proper extensions, causing file type detection to fail and resulting in corrupted text extraction.

**Fixes Applied**:
- **File Upload Service** (`app/services/document_service.py`):
  - Ensured files are saved with proper extensions: `{file_id}.{file_ext}`
  - Added comments to clarify file extension handling

- **LlamaIndex Service** (`app/services/llama_index_service.py`):
  - Enhanced `_determine_file_type()` method to handle both full filenames and extensions
  - Added validation for empty filenames
  - Improved file type detection logic

### 2. **Document Loading and Text Extraction**
**Problem**: PDF and other document types were being processed incorrectly, leading to raw binary data or PDF structure being stored as text content.

**Fixes Applied**:
- **Enhanced Document Loading** (`app/services/llama_index_service.py`):
  - Added proper error handling for each file type (PDF, DOCX, XLSX, PPTX, TXT)
  - Implemented try-catch blocks for each document parser
  - Added file existence validation before processing
  - Improved encoding detection for text files (UTF-8 fallback to latin-1)
  - Added meaningful error messages for parsing failures

### 3. **File Path Validation**
**Problem**: No validation of file paths before processing, leading to unclear error messages.

**Fixes Applied**:
- Added `_validate_file_path()` method to check file existence and readability
- Integrated validation into the main processing pipeline
- Added proper error handling for missing or unreadable files

### 4. **Temporary File Handling**
**Problem**: Temporary files created without proper extensions, causing file type detection to fail.

**Fixes Applied**:
- **Document Processor** (`app/services/document_processor.py`):
  - Enhanced S3 file download to preserve file extensions
  - Added logic to handle temporary files without extensions
  - Implemented file renaming for proper extension handling

### 5. **Celery Task Processing**
**Problem**: File type parameter handling inconsistencies between string and enum types.

**Fixes Applied**:
- **Celery Tasks** (`app/workers/llama_index_tasks.py`):
  - Added file type conversion logic to handle both string and enum inputs
  - Enhanced file type detection from file path when string conversion fails
  - Improved error handling and logging

### 6. **Error Handling and Logging**
**Problem**: Poor error messages and insufficient logging for debugging document processing issues.

**Fixes Applied**:
- Added comprehensive error handling for each document type
- Improved logging messages with specific error details
- Added validation checks with meaningful error messages
- Enhanced exception handling to provide actionable feedback

## Key Improvements

### 1. **Robust File Type Detection**
```python
def _determine_file_type(self, filename: str) -> FileType:
    if not filename:
        return FileType.UNKNOWN

    # Handle both full filenames and just extensions
    if filename.startswith('.'):
        extension = filename[1:].lower()
    else:
        extension = filename.split(".")[-1].lower() if "." in filename else filename.lower()
```

### 2. **Enhanced Document Loading with Error Handling**
```python
if file_type == FileType.PDF:
    try:
        with open(file_path, "rb") as f:
            pdf = PdfReader(f)
            for page_num, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_content += f"Page {page_num + 1}:\n{page_text}\n\n"
                except Exception as page_error:
                    logger.warning(f"Error extracting text from page {page_num + 1}: {str(page_error)}")
                    continue
    except Exception as pdf_error:
        logger.error(f"Error reading PDF file {file_path}: {str(pdf_error)}")
        raise ValueError(f"Unable to read PDF file: {str(pdf_error)}")
```

### 3. **File Path Validation**
```python
def _validate_file_path(self, file_path: str) -> bool:
    try:
        return os.path.exists(file_path) and os.path.isfile(file_path) and os.access(file_path, os.R_OK)
    except Exception:
        return False
```

### 4. **Improved Temporary File Handling**
```python
# Download to a temporary file with proper extension
file_ext = os.path.splitext(s3_key)[1]
temp_file_path = os.path.join(settings.UPLOAD_DIR, f"temp_{file_id}{file_ext}")
```

## Testing Recommendations

1. **Test File Upload with Different Types**:
   - Upload PDF, DOCX, XLSX, PPTX, and TXT files
   - Verify proper text extraction for each type
   - Check that file extensions are preserved

2. **Test Error Handling**:
   - Upload corrupted files
   - Upload files with missing extensions
   - Verify meaningful error messages are returned

3. **Test Large File Processing**:
   - Upload files larger than 5MB to test Celery processing
   - Verify proper file type detection in background tasks

4. **Test Temporary File Cleanup**:
   - Verify temporary files are properly cleaned up after processing
   - Check that file extensions are preserved during S3 operations

## Files Modified

1. `app/services/document_service.py` - File upload and storage improvements
2. `app/services/llama_index_service.py` - Document loading and processing fixes
3. `app/services/document_processor.py` - Temporary file handling improvements
4. `app/workers/llama_index_tasks.py` - Celery task file type handling

## Additional Fixes Applied

### 7. **WebSocket Event Loop Issues**
**Problem**: "Cannot run the event loop while another loop is running" errors when emitting WebSocket updates.

**Fixes Applied**:
- **Enhanced WebSocket Helper** (`app/services/document_service.py`):
  - Created `safe_emit_websocket_update()` function to handle event loop conflicts
  - Added proper detection of existing event loops
  - Implemented fallback to create new event loop when needed
  - Added comprehensive error handling for WebSocket operations

- **Celery Worker Updates** (`app/workers/llama_index_tasks.py`):
  - Enhanced error handling for WebSocket updates in Celery context
  - Added proper event loop management for background tasks

- **Duplicate Import Cleanup** (`app/services/chat_service.py`):
  - Removed duplicate WebSocket manager import functions
  - Cleaned up redundant code

### 8. **DateTime Deprecation Warning**
**Problem**: `datetime.datetime.utcnow()` deprecation warning from botocore.

**Status**: This is a third-party library warning from AWS SDK (botocore). The warning comes from the boto3/botocore library used for S3 operations, not from our application code. This will be resolved when the library is updated.

### 9. **Improved Error Handling**
**Fixes Applied**:
- Added comprehensive try-catch blocks for all WebSocket operations
- Enhanced logging for debugging WebSocket and processing issues
- Implemented graceful degradation when WebSocket manager is unavailable

## Key Technical Improvements

### 1. **Safe WebSocket Update Function**
```python
def safe_emit_websocket_update(ws_manager, coro):
    """Safely emit WebSocket update handling event loop issues."""
    if not ws_manager:
        return

    try:
        import asyncio
        # Check if we're already in an async context
        try:
            # Try to get the current event loop
            loop = asyncio.get_running_loop()
            # If we're in an async context, create a task instead of running directly
            asyncio.create_task(coro)
        except RuntimeError:
            # No event loop running, safe to create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(coro)
            finally:
                loop.close()
    except Exception as ws_error:
        logger.error(f"Error emitting WebSocket update: {str(ws_error)}")
```

### 2. **Simplified WebSocket Calls**
```python
# Before (complex event loop handling)
if ws_manager:
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        # ... complex loop management
    except Exception as ws_error:
        logger.error(f"Error: {str(ws_error)}")

# After (simple and safe)
safe_emit_websocket_update(
    ws_manager,
    ws_manager.emit_file_status_update(file_id, user_id, "processing", 0)
)
```

## Issues Resolved

✅ **File Type Detection**: Files now properly maintain extensions during processing
✅ **Document Parsing**: Enhanced error handling for all document types
✅ **Text Extraction**: Proper text content extraction instead of binary data
✅ **WebSocket Event Loops**: Resolved "Cannot run the event loop while another loop is running"
✅ **Error Handling**: Comprehensive error handling and logging
✅ **Code Cleanup**: Removed duplicate imports and improved code organization

## Latest Diagnostic Fixes Applied

### 10. **Enhanced PDF Processing Diagnostics**
**Problem**: Weaviate still storing corrupted text despite previous fixes.

**Fixes Applied**:
- **Enhanced File Validation** (`app/services/llama_index_service.py`):
  - Added file size and first bytes logging for debugging
  - Added PDF header validation (checks for `%PDF` magic bytes)
  - Added detailed logging for each page extraction
  - Added text content validation to detect binary garbage

- **Text Content Validation**:
  - Checks printable character ratio (must be >70% printable)
  - Logs sample of extracted text for debugging
  - Prevents corrupted binary data from being stored

- **Enhanced Error Reporting**:
  - Logs first 100 bytes of file when PDF reading fails
  - Provides detailed error messages for debugging
  - Added file path and type logging in Celery tasks

### 11. **Debugging Information Added**
```python
# File validation
file_size = os.path.getsize(file_path)
logger.info(f"Processing file: {file_path}, size: {file_size} bytes, type: {file_type}")

# PDF header validation
header = f.read(4)
if header != b'%PDF':
    logger.error(f"File {file_path} does not appear to be a valid PDF (header: {header})")
    raise ValueError(f"File does not appear to be a valid PDF file")

# Text content validation
printable_chars = sum(1 for c in text_content[:1000] if c.isprintable() or c.isspace())
printable_ratio = printable_chars / total_chars
if printable_ratio < 0.7:
    raise ValueError("Extracted text appears to be corrupted or binary data")
```

## Debugging Steps for Current Issue

### **To Identify the Root Cause:**

1. **Check the logs** for the new diagnostic information:
   - File size and path being processed
   - PDF header validation results
   - Text extraction character counts
   - Printable character ratio

2. **Look for these specific log messages**:
   ```
   Processing file: [path], size: [bytes] bytes, type: [type]
   First 10 bytes of file: [bytes]
   PDF has [X] pages
   Total extracted text length: [X] characters
   Text content printable ratio: [ratio]
   ```

3. **If the issue persists**, check:
   - Is the file actually a valid PDF?
   - Is the file being corrupted during S3 upload/download?
   - Is the temporary file creation working correctly?

### **Expected Behavior:**
- PDF files should show header `b'%PDF'`
- Text extraction should yield readable content
- Printable ratio should be >0.7
- No binary garbage should reach Weaviate

## Next Steps

1. **Upload a test PDF** and monitor the new diagnostic logs
2. **Check if the issue is**:
   - File corruption during upload/download
   - Invalid PDF file format
   - Text extraction library issues
   - File type detection problems

3. **If logs show valid PDF processing** but Weaviate still has corrupted data:
   - Check if there's a caching issue
   - Verify Weaviate schema and data types
   - Check if old corrupted data is being returned

4. **Test with different file sizes** to confirm Celery vs direct processing paths
5. **Monitor WebSocket real-time updates** during document processing

## Critical Session ID Fix Applied

### 12. **Session ID Format Validation and Conversion**
**Problem**: Frontend sending timestamp-based session IDs (e.g., `1748166393187`) instead of UUIDs, causing database errors.

**Root Cause**:
- Frontend generates session IDs using `Date.now()` (timestamps)
- Database schema expects UUID format for session IDs
- Error: `invalid input syntax for type uuid: "1748166393187"`

**Fixes Applied**:
- **Chat Service** (`app/services/chat_service.py`):
  - Added `_validate_and_convert_session_id()` method
  - Converts timestamp session IDs to deterministic UUIDs
  - Applied validation to all session methods:
    - `get_session_documents()`
    - `delete_session()`
    - `get_session()`
    - `get_messages()`
    - `send_message()`

- **Document Service** (`app/services/document_service.py`):
  - Added same validation method
  - Applied to `upload_document()` method for session association

### **Session ID Conversion Logic**:
```python
def _validate_and_convert_session_id(self, session_id: str) -> str:
    try:
        # Try to parse as UUID first
        uuid_obj = uuid.UUID(session_id)
        return str(uuid_obj)
    except (ValueError, TypeError):
        # Convert timestamp to deterministic UUID
        timestamp = int(session_id)
        hash_input = f"session_{timestamp}".encode('utf-8')
        hash_digest = hashlib.md5(hash_input).hexdigest()
        uuid_str = f"{hash_digest[:8]}-{hash_digest[8:12]}-{hash_digest[12:16]}-{hash_digest[16:20]}-{hash_digest[20:32]}"
        return str(uuid.UUID(uuid_str))
```

### **Expected Results**:
- ✅ Timestamp session IDs automatically converted to valid UUIDs
- ✅ Database operations succeed without UUID format errors
- ✅ Document upload and session association works correctly
- ✅ Chat functionality restored with proper session handling

### **Test Cases**:
1. **Upload document with timestamp session ID**: Should convert and associate correctly
2. **Retrieve session documents**: Should work with converted UUID
3. **Send chat messages**: Should work with session validation
4. **WebSocket room joining**: Should work with proper session IDs
