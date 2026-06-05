# AI-Based E-Commerce Recommendation System

A hybrid recommendation engine for an e-commerce platform using Django and machine learning.

## Features
- Collaborative Filtering (Surprise SVD)
- Content-Based Filtering (TF-IDF + Cosine Similarity)
- Hybrid Engine
- Precomputed Models

## Setup
1. Clone the repository.
2. Create a virtual environment.
3. Install dependencies: `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and configure it.
5. Run migrations: `python manage.py migrate`.
6. Load sample data or train models.
