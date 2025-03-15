import os
import json
import logging
import numpy as np
from flask import Flask, request, jsonify
from transformers import AutoTokenizer

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
model_path = os.environ.get("MODEL_PATH", "/models/tflite_model")
use_tflite = os.environ.get("USE_TFLITE", "true").lower() == "true"
use_onnx = os.environ.get("USE_ONNX", "false").lower() == "true"
environment = os.environ.get("ENVIRONMENT", "edge")

# Global variables for model and tokenizer
model = None
tokenizer = None

def load_tflite_model():
    """Load TensorFlow Lite model"""
    try:
        import tensorflow as tf
        
        # Load TFLite model
        model_file = os.path.join(model_path, "model.tflite")
        logger.info(f"Loading TFLite model from {model_file}")
        
        interpreter = tf.lite.Interpreter(model_path=model_file)
        interpreter.allocate_tensors()
        
        # Get input and output details
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        
        logger.info(f"TFLite model loaded successfully")
        logger.info(f"Input details: {input_details}")
        logger.info(f"Output details: {output_details}")
        
        return interpreter, input_details, output_details
    except Exception as e:
        logger.error(f"Error loading TFLite model: {str(e)}")
        raise

def load_onnx_model():
    """Load ONNX model"""
    try:
        import onnxruntime as ort
        
        # Load ONNX model
        model_file = os.path.join(model_path, "model.onnx")
        logger.info(f"Loading ONNX model from {model_file}")
        
        # Check if GPU is available
        providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if ort.get_device() == 'GPU' else ['CPUExecutionProvider']
        session = ort.InferenceSession(model_file, providers=providers)
        
        logger.info(f"ONNX model loaded successfully")
        logger.info(f"Input names: {session.get_inputs()[0].name}")
        logger.info(f"Output names: {session.get_outputs()[0].name}")
        
        return session
    except Exception as e:
        logger.error(f"Error loading ONNX model: {str(e)}")
        raise

@app.before_first_request
def load_model():
    """Load model and tokenizer before first request"""
    global model, tokenizer
    
    try:
        # Load tokenizer
        tokenizer_path = os.path.join(model_path, "tokenizer")
        logger.info(f"Loading tokenizer from {tokenizer_path}")
        tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
        
        # Load model based on configuration
        if use_tflite:
            model = load_tflite_model()
        elif use_onnx:
            model = load_onnx_model()
        else:
            raise ValueError("Either USE_TFLITE or USE_ONNX must be set to true")
            
        logger.info("Model and tokenizer loaded successfully")
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        raise

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Kubernetes probes"""
    return jsonify({"status": "healthy", "environment": environment})

@app.route("/info", methods=["GET"])
def model_info():
    """Return information about the loaded model"""
    model_type = "TensorFlow Lite" if use_tflite else "ONNX"
    return jsonify({
        "model_path": model_path,
        "model_type": model_type,
        "environment": environment,
    })

@app.route("/generate", methods=["POST"])
def generate_text():
    """Generate text based on the provided prompt"""
    try:
        data = request.get_json()
        
        if not data or "prompt" not in data:
            return jsonify({"error": "Missing prompt in request"}), 400
            
        prompt = data["prompt"]
        max_length = data.get("max_length", 50)
        
        logger.info(f"Generating text for prompt: {prompt[:50]}...")
        
        # Tokenize the prompt
        input_tokens = tokenizer(prompt, return_tensors="np")
        input_ids = input_tokens["input_ids"]
        attention_mask = input_tokens["attention_mask"]
        
        # Generate text based on model type
        if use_tflite:
            generated_text = generate_with_tflite(input_ids, attention_mask, max_length)
        elif use_onnx:
            generated_text = generate_with_onnx(input_ids, attention_mask, max_length)
        
        logger.info(f"Generated text: {generated_text[:50]}...")
        
        return jsonify({
            "prompt": prompt,
            "generated_text": generated_text,
            "model_type": "TensorFlow Lite" if use_tflite else "ONNX",
        })
        
    except Exception as e:
        logger.error(f"Error generating text: {str(e)}")
        return jsonify({"error": str(e)}), 500

def generate_with_tflite(input_ids, attention_mask, max_length):
    """Generate text using TensorFlow Lite model"""
    interpreter, input_details, output_details = model
    
    # Set input tensor
    interpreter.set_tensor(input_details[0]['index'], input_ids)
    interpreter.set_tensor(input_details[1]['index'], attention_mask)
    
    # Run inference
    interpreter.invoke()
    
    # Get output tensor
    logits = interpreter.get_tensor(output_details[0]['index'])
    
    # Simple greedy decoding
    for _ in range(max_length - input_ids.shape[1]):
        # Get the last token's logits
        next_token_logits = logits[0, -1, :]
        
        # Get the token with the highest probability
        next_token = np.argmax(next_token_logits)
        
        # Append the token to input_ids
        input_ids = np.concatenate([input_ids, [[next_token]]], axis=1)
        
        # Update attention mask
        attention_mask = np.concatenate([attention_mask, [[1]]], axis=1)
        
        # Set input tensor
        interpreter.set_tensor(input_details[0]['index'], input_ids)
        interpreter.set_tensor(input_details[1]['index'], attention_mask)
        
        # Run inference
        interpreter.invoke()
        
        # Get output tensor
        logits = interpreter.get_tensor(output_details[0]['index'])
        
        # Stop if we generate the EOS token
        if next_token == tokenizer.eos_token_id:
            break
    
    # Decode the generated tokens
    generated_text = tokenizer.decode(input_ids[0], skip_special_tokens=True)
    return generated_text

def generate_with_onnx(input_ids, attention_mask, max_length):
    """Generate text using ONNX model"""
    session = model
    
    # Simple greedy decoding
    for _ in range(max_length - input_ids.shape[1]):
        # Run inference
        ort_inputs = {
            "input_ids": input_ids,
            "attention_mask": attention_mask
        }
        logits = session.run(None, ort_inputs)[0]
        
        # Get the last token's logits
        next_token_logits = logits[0, -1, :]
        
        # Get the token with the highest probability
        next_token = np.argmax(next_token_logits)
        
        # Append the token to input_ids
        input_ids = np.concatenate([input_ids, [[next_token]]], axis=1)
        
        # Update attention mask
        attention_mask = np.concatenate([attention_mask, [[1]]], axis=1)
        
        # Stop if we generate the EOS token
        if next_token == tokenizer.eos_token_id:
            break
    
    # Decode the generated tokens
    generated_text = tokenizer.decode(input_ids[0], skip_special_tokens=True)
    return generated_text

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port) 