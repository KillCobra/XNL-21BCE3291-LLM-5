import json
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the parent directory to the path so we can import the app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

class TestLLMService(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
        
    def test_health_check(self):
        """Test the health check endpoint"""
        response = self.app.get('/health')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'healthy')
        
    def test_model_info(self):
        """Test the model info endpoint"""
        response = self.app.get('/model-info')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('model_name', data)
        self.assertIn('model_config', data)
        
    @patch('app.model')
    @patch('app.tokenizer')
    def test_generate_text(self, mock_tokenizer, mock_model):
        """Test the text generation endpoint"""
        # Mock the tokenizer and model
        mock_tokenizer.return_value = {
            "input_ids": MagicMock(),
            "attention_mask": MagicMock()
        }
        mock_model.generate.return_value = [MagicMock()]
        mock_tokenizer.decode.return_value = "This is a generated response."
        
        # Test request
        request_data = {
            'prompt': 'Hello, how are you?',
            'max_length': 50
        }
        
        response = self.app.post('/generate', 
                               json=request_data,
                               content_type='application/json')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['prompt'], 'Hello, how are you?')
        self.assertEqual(data['generated_text'], 'This is a generated response.')
        self.assertIn('model', data)
        self.assertEqual(data['status'], 'success')
        
    def test_generate_text_missing_prompt(self):
        """Test the text generation endpoint with missing prompt"""
        # Test request with missing prompt
        request_data = {
            'max_length': 50
        }
        
        response = self.app.post('/generate', 
                               json=request_data,
                               content_type='application/json')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', data)
        self.assertEqual(data['status'], 'error')

if __name__ == '__main__':
    unittest.main() 