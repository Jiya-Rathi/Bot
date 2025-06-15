import os
import requests
import tempfile
import shutil
from pathlib import Path
from typing import Optional
import hashlib
import mimetypes


class FileManager:
    """Handles secure file download, storage, and cleanup for CSV processing."""
    
    def __init__(self, base_temp_dir: str = None):
        self.base_temp_dir = base_temp_dir or tempfile.gettempdir()
        self.app_temp_dir = os.path.join(self.base_temp_dir, "finny_bot_uploads")
        
        # Create app temp directory if it doesn't exist
        os.makedirs(self.app_temp_dir, exist_ok=True)
    
    def generate_user_id_hash(self, user_identifier: str) -> str:
        """Generate a secure hash for user identification."""
        return hashlib.md5(user_identifier.encode()).hexdigest()[:10]
    
    def create_user_temp_directory(self, user_id: str) -> str:
        """Create isolated temporary directory for user files."""
        user_hash = self.generate_user_id_hash(user_id)
        user_dir = os.path.join(self.app_temp_dir, f"user_{user_hash}")
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def download_csv_from_twilio(self, media_url: str, user_id: str, twilio_auth: tuple = None) -> dict:
        """
        Download CSV file from Twilio MediaUrl.
        
        Args:
            media_url: Twilio media URL
            user_id: User identifier (phone number or session ID)
            twilio_auth: (account_sid, auth_token) for Twilio authentication
            
        Returns:
            dict: {'success': bool, 'file_path': str, 'error': str}
        """
        try:
            # Create user directory
            user_dir = self.create_user_temp_directory(user_id)
            
            # Download file with Twilio authentication if provided
            headers = {'User-Agent': 'FinnyBot/1.0'}
            if twilio_auth:
                response = requests.get(media_url, auth=twilio_auth, headers=headers, timeout=30)
            else:
                response = requests.get(media_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'Failed to download file. Status code: {response.status_code}'
                }
            
            # Generate filename with timestamp
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"transactions_{timestamp}.csv"
            file_path = os.path.join(user_dir, filename)
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            # Validate file type
            if not self.validate_file_type(file_path):
                os.remove(file_path)
                return {
                    'success': False,
                    'error': 'File is not a valid CSV format'
                }
            
            return {
                'success': True,
                'file_path': file_path,
                'file_size': len(response.content)
            }
            
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'Network error downloading file: {str(e)}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Error processing file: {str(e)}'
            }
    
    def validate_file_type(self, file_path: str) -> bool:
        """Validate that the file is actually a CSV."""
        try:
            # Check file extension
            print(file_path.lower()+"12")
            if not file_path.strip().lower().endswith('.csv'):
                return False
            
            # Check MIME type
            
            #mime_type, _ = mimetypes.guess_type(file_path)
            #print(mime_type)
            #if mime_type and mime_type not in ['text/csv', 'text/plain']:
                #return False
            
            # Try to read first few lines as CSV
            import csv
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Try to detect if it's CSV-like
                sample = f.read(1024)
                sniffer = csv.Sniffer()
                try:
                    sniffer.sniff(sample)
                    return True
                except csv.Error:
                    # Try common CSV patterns
                    print("sniff failed")
                    if ',' in sample or ';' in sample or '\t' in sample:
                        return True
                    print("not found in sample")
                    return False
                    
        except Exception:
            return False
    
    def get_file_info(self, file_path: str) -> dict:
        """Get basic information about the file."""
        try:
            stat = os.stat(file_path)
            return {
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'modified': stat.st_mtime,
                'exists': True
            }
        except Exception as e:
            return {
                'exists': False,
                'error': str(e)
            }
    
    def cleanup_user_files(self, user_id: str) -> dict:
        """Remove all temporary files for a user."""
        try:
            user_hash = self.generate_user_id_hash(user_id)
            user_dir = os.path.join(self.app_temp_dir, f"user_{user_hash}")
            
            if os.path.exists(user_dir):
                shutil.rmtree(user_dir)
                return {'success': True, 'message': f'Cleaned up files for user {user_hash}'}
            else:
                return {'success': True, 'message': 'No files to clean up'}
                
        except Exception as e:
            return {'success': False, 'error': f'Error cleaning up files: {str(e)}'}
    
    def cleanup_old_files(self, max_age_hours: int = 24) -> dict:
        """Clean up files older than specified hours."""
        try:
            import time
            current_time = time.time()
            max_age_seconds = max_age_hours * 3600
            cleaned_count = 0
            
            for user_dir in os.listdir(self.app_temp_dir):
                user_path = os.path.join(self.app_temp_dir, user_dir)
                if os.path.isdir(user_path):
                    # Check if directory is old enough
                    dir_age = current_time - os.path.getmtime(user_path)
                    if dir_age > max_age_seconds:
                        shutil.rmtree(user_path)
                        cleaned_count += 1
            
            return {
                'success': True,
                'cleaned_directories': cleaned_count,
                'message': f'Cleaned {cleaned_count} old user directories'
            }
            
        except Exception as e:
            return {'success': False, 'error': f'Error cleaning old files: {str(e)}'}


# Helper function for easy import
def get_file_manager() -> FileManager:
    """Get a configured FileManager instance."""
    return FileManager()