"""
Tests with realistic, messy data
"""
import pytest

class TestDirtyData:
    def test_users_with_missing_fields(self):
        """Test handling of users with missing required fields"""
        users = [
            {"id": "user1"},  # Missing email
            {"email": "user2@ibm.com"},  # Missing id
            {"id": "", "email": ""},  # Empty strings
            {"id": None, "email": None}  # Null values
        ]
        # Test that system handles gracefully
    
    def test_invalid_email_formats(self):
        """Test handling of invalid email formats"""
        users = [
            {"id": "user1", "email": "not-an-email"},
            {"id": "user2", "email": "@ibm.com"},
            {"id": "user3", "email": "user@"},
        ]
    
    def test_unicode_and_special_chars(self):
        """Test handling of Unicode and special characters"""
        users = [
            {"id": "用户1@ibm.com"},  # Chinese
            {"id": "user😀@ibm.com"},  # Emoji
            {"id": "user'OR'1'='1@ibm.com"}  # SQL injection attempt
        ]
    
    def test_duplicate_user_ids(self):
        """Test handling of duplicate user IDs"""
        users = [
            {"id": "user1@ibm.com", "email": "user1@ibm.com"},
            {"id": "user1@ibm.com", "email": "user1@ibm.com"},  # Duplicate
        ]
    
    def test_very_long_strings(self):
        """Test handling of very long strings (buffer overflow)"""
        long_email = "a" * 10000 + "@ibm.com"
        users = [{"id": long_email, "email": long_email}]
