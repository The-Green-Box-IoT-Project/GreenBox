import unittest
from unittest.mock import patch, MagicMock

# We need to make sure the adapter is in the python path.
# This is a common way to do it in tests.
import sys
import os
# Add the parent directory of 'greenbox' to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from greenbox.MongoDB.Mongo_DB_adapter import MongoAdapter

class TestMongoAdapter(unittest.TestCase):

    @patch('greenbox.MongoDB.Mongo_DB_adapter.MongoClient')
    def test_retrieve_device_found(self, mock_mongo_client):
        """
        Test that retrieve_device returns a device dictionary when found.
        """
        # Arrange: Set up the mock objects
        mock_db = MagicMock()
        # When MongoClient is called, it returns a client object.
        # We make that client object return our mock_db when the db_name is accessed.
        mock_client_instance = mock_mongo_client.return_value
        mock_client_instance.__getitem__.return_value = mock_db
        
        expected_device = {"device_id": "d1", "name": "TempSensor"}
        mock_db.devices.find_one.return_value = expected_device

        # Act: Instantiate the adapter and call the method
        adapter = MongoAdapter(db_uri="mongodb://fake:27017/", db_name="test_db")
        device = adapter.retrieve_device("d1")

        # Assert: Check if the mocks were called correctly and the result is right
        mock_db.devices.find_one.assert_called_once_with({"device_id": "d1"})
        self.assertEqual(device, expected_device)

    @patch('greenbox.MongoDB.Mongo_DB_adapter.MongoClient')
    def test_retrieve_device_not_found(self, mock_mongo_client):
        """
        Test that retrieve_device returns an empty dictionary when not found.
        """
        # Arrange
        mock_db = MagicMock()
        mock_client_instance = mock_mongo_client.return_value
        mock_client_instance.__getitem__.return_value = mock_db
        mock_db.devices.find_one.return_value = None

        # Act
        adapter = MongoAdapter(db_uri="mongodb://fake:27017/", db_name="test_db")
        device = adapter.retrieve_device("d1_non_existent")

        # Assert
        mock_db.devices.find_one.assert_called_once_with({"device_id": "d1_non_existent"})
        self.assertEqual(device, {})

    @patch('greenbox.MongoDB.Mongo_DB_adapter.MongoClient')
    def test_create_user_success(self, mock_mongo_client):
        """
        Test that create_user successfully inserts a new user.
        """
        # Arrange
        mock_db = MagicMock()
        mock_client_instance = mock_mongo_client.return_value
        mock_client_instance.__getitem__.return_value = mock_db
        
        # Simulate that the user does not exist
        mock_db.users.find_one.return_value = None
        
        user_data = {"user_id": "new_user", "name": "Newbie"}
        
        # Act
        adapter = MongoAdapter(db_uri="mongodb://fake:27017/", db_name="test_db")
        result = adapter.create_user(user_data)

        # Assert
        mock_db.users.find_one.assert_called_once_with({"user_id": "new_user"})
        mock_db.users.insert_one.assert_called_once_with(user_data)
        self.assertTrue(result)

    @patch('greenbox.MongoDB.Mongo_DB_adapter.MongoClient')
    def test_create_user_already_exists(self, mock_mongo_client):
        """
        Test that create_user returns False if the user already exists.
        """
        # Arrange
        mock_db = MagicMock()
        mock_client_instance = mock_mongo_client.return_value
        mock_client_instance.__getitem__.return_value = mock_db
        
        user_data = {"user_id": "existing_user", "name": "Oldie"}
        # Simulate that the user *does* exist
        mock_db.users.find_one.return_value = user_data
        
        # Act
        adapter = MongoAdapter(db_uri="mongodb://fake:27017/", db_name="test_db")
        result = adapter.create_user(user_data)

        # Assert
        mock_db.users.find_one.assert_called_once_with({"user_id": "existing_user"})
        # Ensure insert_one was NOT called
        mock_db.users.insert_one.assert_not_called()
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
