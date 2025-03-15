#!/usr/bin/env python3
"""
Model Optimization Script for LLM Service
This script converts Hugging Face Transformer models to ONNX format and optimizes them with TensorRT
"""

import os
import argparse
import logging
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def convert_to_onnx(model_name, output_dir, quantize=False):
    """
    Convert a Hugging Face model to ONNX format
    
    Args:
        model_name: Name or path of the Hugging Face model
        output_dir: Directory to save the ONNX model
        quantize: Whether to quantize the model to INT8
    """
    logger.info(f"Loading model: {model_name}")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    
    # Fix: Set padding token
    tokenizer.pad_token = tokenizer.eos_token
    model.config.pad_token_id = tokenizer.eos_token_id
    
    # Disable past key values usage during export
    model.config.use_cache = False
    
    # Set the model to evaluation mode
    model.eval()
    
    # Create dummy input with padding
    dummy_input = tokenizer(
        "Hello, how are you?", 
        return_tensors="pt", 
        padding=True,
        truncation=True,
        max_length=50
    )
    input_ids = dummy_input["input_ids"]
    attention_mask = dummy_input["attention_mask"]
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Set dynamic axes for ONNX export
    dynamic_axes = {
        'input_ids': {0: 'batch_size', 1: 'sequence'},
        'attention_mask': {0: 'batch_size', 1: 'sequence'},
        'output': {0: 'batch_size', 1: 'sequence_length', 2: 'vocab_size'}
    }
    
    # Export to ONNX
    output_path = os.path.join(output_dir, "model.onnx")
    logger.info(f"Exporting model to ONNX format at {output_path}...")
    
    # Define a custom forward function to use during export
    def forward_with_return_dict(input_ids, attention_mask):
        outputs = model(input_ids=input_ids, attention_mask=attention_mask)
        return outputs.logits
    
    torch.onnx.export(
        forward_with_return_dict,
        (input_ids, attention_mask),
        output_path,
        input_names=['input_ids', 'attention_mask'],
        output_names=['output'],
        dynamic_axes=dynamic_axes,
        do_constant_folding=True,
        opset_version=13
    )
    
    logger.info("Model exported to ONNX format successfully!")
    
    # Quantize the model if requested
    if quantize:
        try:
            import onnxruntime as ort
            from onnxruntime.quantization import quantize_dynamic
            
            logger.info("Quantizing the model...")
            quantized_output_path = os.path.join(output_dir, "model_quantized.onnx")
            quantize_dynamic(
                output_path,
                quantized_output_path,
                weight_type=torch.qint8
            )
            logger.info("Model quantized successfully!")
        except ImportError:
            logger.error("Warning: onnxruntime not installed. Skipping quantization.")
    
    # Create Triton model repository structure
    triton_model_dir = os.path.join(output_dir, "triton_models", "llm_model", "1")
    os.makedirs(triton_model_dir, exist_ok=True)
    
    # Copy ONNX model to Triton model repository
    if quantize:
        import shutil
        shutil.copy(quantized_output_path, os.path.join(triton_model_dir, "model.onnx"))
    else:
        import shutil
        shutil.copy(output_path, os.path.join(triton_model_dir, "model.onnx"))
    
    # Create Triton model configuration
    config_path = os.path.join(output_dir, "triton_models", "llm_model", "config.pbtxt")
    with open(config_path, "w") as f:
        f.write("""
name: "llm_model"
platform: "onnxruntime_onnx"
max_batch_size: 8
input [
  {
    name: "input_ids"
    data_type: TYPE_INT64
    dims: [ -1 ]
  },
  {
    name: "attention_mask"
    data_type: TYPE_INT64
    dims: [ -1 ]
  }
]
output [
  {
    name: "logits"
    data_type: TYPE_FP32
    dims: [ -1, -1 ]
  }
]
instance_group [
  {
    count: 1
    kind: KIND_GPU
  }
]
""")
    
    logger.info(f"Triton model configuration created at: {config_path}")
    logger.info(f"Model optimization completed. Triton model repository: {os.path.join(output_dir, 'triton_models')}")
    
    # Save tokenizer for later use
    tokenizer_path = os.path.join(output_dir, "tokenizer")
    tokenizer.save_pretrained(tokenizer_path)
    logger.info(f"Tokenizer saved to: {tokenizer_path}")

def optimize_with_tensorrt(onnx_model_path, output_dir):
    """
    Optimize an ONNX model with TensorRT
    
    Args:
        onnx_model_path: Path to the ONNX model
        output_dir: Directory to save the TensorRT engine
    """
    try:
        import tensorrt as trt
        import numpy as np
        from cuda import cuda
        
        logger.info(f"Optimizing ONNX model with TensorRT: {onnx_model_path}")
        
        TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        builder = trt.Builder(TRT_LOGGER)
        network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
        parser = trt.OnnxParser(network, TRT_LOGGER)
        
        with open(onnx_model_path, "rb") as f:
            if not parser.parse(f.read()):
                for error in range(parser.num_errors):
                    logger.error(f"TensorRT ONNX parser error: {parser.get_error(error)}")
                raise RuntimeError("Failed to parse ONNX model")
        
        config = builder.create_builder_config()
        config.max_workspace_size = 1 << 30  # 1GB
        
        # Set FP16 mode if GPU supports it
        if builder.platform_has_fast_fp16:
            logger.info("Enabling FP16 mode")
            config.set_flag(trt.BuilderFlag.FP16)
        
        # Build and save TensorRT engine
        engine_path = os.path.join(output_dir, "model.engine")
        engine = builder.build_engine(network, config)
        
        with open(engine_path, "wb") as f:
            f.write(engine.serialize())
        
        logger.info(f"TensorRT engine saved to: {engine_path}")
        
    except ImportError:
        logger.error("TensorRT is required for optimization. Please install TensorRT.")

def create_tensorflow_lite_model(model_name, output_dir):
    """
    Create a TensorFlow Lite model for edge deployment
    
    Args:
        model_name: Name or path of the Hugging Face model
        output_dir: Directory to save the TFLite model
    """
    try:
        import tensorflow as tf
        from transformers import TFAutoModelForCausalLM
        
        logger.info(f"Creating TensorFlow Lite model from: {model_name}")
        
        # Load model with TensorFlow
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = TFAutoModelForCausalLM.from_pretrained(model_name, from_pt=True)
        
        # Create a concrete function
        @tf.function(input_signature=[
            tf.TensorSpec([1, None], tf.int32, name="input_ids"),
            tf.TensorSpec([1, None], tf.int32, name="attention_mask")
        ])
        def serving_fn(input_ids, attention_mask):
            return model(input_ids=input_ids, attention_mask=attention_mask)
        
        # Get the concrete function
        concrete_func = serving_fn.get_concrete_function()
        
        # Convert to TensorFlow Lite model
        converter = tf.lite.TFLiteConverter.from_concrete_functions([concrete_func])
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        tflite_model = converter.convert()
        
        # Save the TFLite model
        os.makedirs(output_dir, exist_ok=True)
        tflite_path = os.path.join(output_dir, "model.tflite")
        with open(tflite_path, "wb") as f:
            f.write(tflite_model)
        
        # Save tokenizer for later use
        tokenizer_path = os.path.join(output_dir, "tokenizer")
        tokenizer.save_pretrained(tokenizer_path)
        
        logger.info(f"TensorFlow Lite model saved to: {tflite_path}")
        logger.info(f"Tokenizer saved to: {tokenizer_path}")
        
    except ImportError:
        logger.error("TensorFlow is required for TFLite conversion. Install with: pip install tensorflow")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize LLM models for deployment")
    parser.add_argument("--model", type=str, default="distilgpt2", help="Hugging Face model name or path")
    parser.add_argument("--output-dir", type=str, default="optimized_models", help="Output directory for optimized models")
    parser.add_argument("--quantize", action="store_true", help="Quantize the ONNX model to INT8")
    parser.add_argument("--tensorrt", action="store_true", help="Optimize with TensorRT")
    parser.add_argument("--tflite", action="store_true", help="Create TensorFlow Lite model for edge deployment")
    
    args = parser.parse_args()
    
    # Convert to ONNX
    convert_to_onnx(args.model, args.output_dir, args.quantize)
    
    # Optimize with TensorRT if requested
    if args.tensorrt:
        onnx_path = os.path.join(args.output_dir, "model.onnx")
        if args.quantize:
            onnx_path = os.path.join(args.output_dir, "model_quantized.onnx")
        optimize_with_tensorrt(onnx_path, args.output_dir)
    
    # Create TensorFlow Lite model if requested
    if args.tflite:
        tflite_dir = os.path.join(args.output_dir, "tflite")
        create_tensorflow_lite_model(args.model, tflite_dir) 