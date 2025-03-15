from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from prometheus_flask_exporter import PrometheusMetrics
import time

app = Flask(__name__)
metrics = PrometheusMetrics(app)

# Load model and tokenizer
model_name = "distilgpt2"  # Using a smaller model for local testing
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Fix: Set padding token
tokenizer.pad_token = tokenizer.eos_token
model.config.pad_token_id = tokenizer.eos_token_id

# Cache for storing recent responses
response_cache = {}

# Circuit breaker state
circuit_state = {
    "failures": 0,
    "threshold": 5,
    "open": False,
    "last_failure": 0,
    "reset_timeout": 30  # seconds
}

# Add a root endpoint to show the service is running
@app.route('/', methods=['GET'])
def root():
    return jsonify({
        "status": "running",
        "message": "LLM Service is up and running!",
        "model": model_name,
        "endpoints": {
            "generate": "/generate (POST)",
            "health": "/health (GET)",
            "model-info": "/model-info (GET)",
            "metrics": "/metrics (GET)"
        }
    })

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/model-info', methods=['GET'])
def model_info():
    return jsonify({
        "model_name": model_name,
        "model_config": model.config.to_dict()
    })

@app.route('/generate', methods=['POST'])
@metrics.counter('llm_requests_total', 'Number of LLM requests')
def generate():
    # Check circuit breaker
    if circuit_state["open"]:
        # Check if we should reset the circuit breaker
        if time.time() - circuit_state["last_failure"] > circuit_state["reset_timeout"]:
            circuit_state["open"] = False
            circuit_state["failures"] = 0
        else:
            return jsonify({
                "error": "Service temporarily unavailable",
                "status": "error",
                "circuit_open": True
            }), 503
    
    try:
        data = request.get_json()
        
        if not data or 'prompt' not in data:
            return jsonify({
                "error": "Missing prompt in request",
                "status": "error"
            }), 400

        prompt = data['prompt']
        max_length = data.get('max_length', 50)
        
        # Check cache first
        cache_key = f"{prompt}_{max_length}"
        if cache_key in response_cache:
            return jsonify({
                "prompt": prompt,
                "generated_text": response_cache[cache_key],
                "model": model_name,
                "status": "success",
                "cached": True
            })
        
        # Create inputs with padding
        inputs = tokenizer(prompt, 
                         return_tensors="pt", 
                         padding=True, 
                         truncation=True,
                         max_length=max_length)
        
        # Generate text with timeout
        start_time = time.time()
        outputs = model.generate(
            inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            max_length=max_length,
            num_return_sequences=1,
            no_repeat_ngram_size=2,
            pad_token_id=tokenizer.eos_token_id,
            do_sample=True,
            temperature=0.7
        )
        
        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # Cache the response
        response_cache[cache_key] = generated_text
        
        # Limit cache size
        if len(response_cache) > 1000:
            # Remove oldest entries
            for _ in range(100):
                response_cache.pop(next(iter(response_cache)))
        
        # Reset circuit breaker failures on success
        circuit_state["failures"] = 0
        
        return jsonify({
            "prompt": prompt,
            "generated_text": generated_text,
            "model": model_name,
            "status": "success",
            "cached": False,
            "generation_time": time.time() - start_time
        })
    except Exception as e:
        # Update circuit breaker
        circuit_state["failures"] += 1
        circuit_state["last_failure"] = time.time()
        
        if circuit_state["failures"] >= circuit_state["threshold"]:
            circuit_state["open"] = True
            app.logger.warning("Circuit breaker opened due to repeated failures")
        
        return jsonify({
            "error": str(e),
            "status": "error"
        }), 500

if __name__ == "__main__":
    print("Starting LLM Service...")
    print("Model loaded: distilgpt2")
    print("Access the service at http://localhost:8080")
    print("Endpoints:")
    print("  - GET / (Service status)")
    print("  - POST /generate")
    print("  - GET /health")
    print("  - GET /model-info")
    print("  - GET /metrics")
    app.run(host="0.0.0.0", port=8081) 