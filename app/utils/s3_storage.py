"""
S3 storage utility for Wasabi integration.
"""
import os
import boto3
from botocore.client import Config
from typing import BinaryIO, Optional, Dict, Any
import logging
from fastapi import UploadFile

from config.config import settings

# Configure logging
logger = logging.getLogger(__name__)

class S3Storage:
    """S3 storage utility for Wasabi integration."""
    
    def __init__(self):
        """Initialize the S3 storage utility."""
        self.endpoint_url = settings.S3_ENDPOINT
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY
        self.bucket_name = settings.S3_BUCKET_NAME
        self.region = settings.S3_REGION
        
        # Initialize S3 client
        self.s3_client = None
        if all([self.endpoint_url, self.access_key, self.secret_key, self.bucket_name]):
            try:
                self.s3_client = boto3.client(
                    's3',
                    endpoint_url=self.endpoint_url,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    region_name=self.region,
                    config=Config(signature_version='s3v4')
                )
                logger.info(f"Connected to S3 storage at {self.endpoint_url}")
            except Exception as e:
                logger.error(f"Error connecting to S3 storage: {str(e)}")
    
    def is_available(self) -> bool:
        """Check if S3 storage is available."""
        return self.s3_client is not None
    
    async def upload_file(self, file: UploadFile, key: str) -> Dict[str, Any]:
        """
        Upload a file to S3 storage.
        
        Args:
            file: The file to upload
            key: The S3 key (path in the bucket)
            
        Returns:
            Dictionary with upload details
        """
        if not self.is_available():
            raise ValueError("S3 storage is not available")
        
        try:
            # Read file content
            file_content = await file.read()
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=file_content,
                ContentType=file.content_type
            )
            
            # Generate URL for the file
            file_url = f"{self.endpoint_url}/{self.bucket_name}/{key}"
            
            # Reset file position for potential further use
            file.file.seek(0)
            
            return {
                "key": key,
                "url": file_url,
                "size": len(file_content),
                "content_type": file.content_type
            }
        
        except Exception as e:
            logger.error(f"Error uploading file to S3: {str(e)}")
            raise
    
    def upload_bytes(self, content: bytes, key: str, content_type: str = "application/octet-stream") -> Dict[str, Any]:
        """
        Upload bytes to S3 storage.
        
        Args:
            content: The content to upload
            key: The S3 key (path in the bucket)
            content_type: The content type
            
        Returns:
            Dictionary with upload details
        """
        if not self.is_available():
            raise ValueError("S3 storage is not available")
        
        try:
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                ContentType=content_type
            )
            
            # Generate URL for the file
            file_url = f"{self.endpoint_url}/{self.bucket_name}/{key}"
            
            return {
                "key": key,
                "url": file_url,
                "size": len(content),
                "content_type": content_type
            }
        
        except Exception as e:
            logger.error(f"Error uploading bytes to S3: {str(e)}")
            raise
    
    def download_file(self, key: str) -> bytes:
        """
        Download a file from S3 storage.
        
        Args:
            key: The S3 key (path in the bucket)
            
        Returns:
            File content as bytes
        """
        if not self.is_available():
            raise ValueError("S3 storage is not available")
        
        try:
            # Download from S3
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            # Read content
            content = response['Body'].read()
            
            return content
        
        except Exception as e:
            logger.error(f"Error downloading file from S3: {str(e)}")
            raise
    
    def delete_file(self, key: str) -> bool:
        """
        Delete a file from S3 storage.
        
        Args:
            key: The S3 key (path in the bucket)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_available():
            raise ValueError("S3 storage is not available")
        
        try:
            # Delete from S3
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=key
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error deleting file from S3: {str(e)}")
            return False
    
    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """
        Generate a presigned URL for a file.
        
        Args:
            key: The S3 key (path in the bucket)
            expiration: URL expiration time in seconds
            
        Returns:
            Presigned URL
        """
        if not self.is_available():
            raise ValueError("S3 storage is not available")
        
        try:
            # Generate presigned URL
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key
                },
                ExpiresIn=expiration
            )
            
            return url
        
        except Exception as e:
            logger.error(f"Error generating presigned URL: {str(e)}")
            raise

# Create a singleton instance
s3_storage = S3Storage()
