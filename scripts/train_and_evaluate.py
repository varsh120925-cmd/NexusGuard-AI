"""
NexusGuard Training Execution Script
"""
import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ml.model_trainer import train_and_evaluate_models

if __name__ == "__main__":
    train_and_evaluate_models()
