🎬 Movie Recommendation Engine

Neo4j • Flask • Python
A full-stack, graph-driven movie recommendation system developed as an individual project.
The system integrates a hybrid recommendation algorithm with a complete Flask web interface and a Neo4j graph database backend.

📌 Overview

This project builds a personalized movie recommendation engine using:

Graph Database (Neo4j) for movie, genre, actor, and user relationships

Flask for web routing, UI rendering, and REST APIs

Custom recommendation algorithms (content-based, graph-based, hybrid)

Dynamic user creation & rating system

Graph visualization APIs for interactive exploration

The entire pipeline—data ingestion, modeling, algorithm design, backend integration, and UI—has been implemented end-to-end.

🚀 Features
🔎 Recommendation Algorithms

Content-Based Filtering
Uses user-liked genres to find similar movies.

Graph-Based Recommendations
Traverses the Neo4j graph through shared connections.

Hybrid Model
Weighted score combining both approaches for improved accuracy.

🗄️ Database & Modeling

Movie, Genre, Actor, Director, User nodes

RATED, BELONGS_TO, ACTED_IN, DIRECTED relationships

Automatic index creation for optimized performance

Dynamic user/rating creation

🌐 Web Application (Flask)

User homepage

New user rating interface

Personalized recommendation page

REST APIs for all algorithms

Graph visualization endpoints (JSON formatted)

🛠️ Setup Script

Loads dataset into Neo4j

Creates sample users and realistic ratings

Builds indexes

Validates database structure

Fully automated initialization

📂 Project Structure
├── app.py                          # Flask web application
├── Recommendation_system.py        # Core recommendation engine
├── setup.py                        # Database setup & dataset loader
├── templates/                      # HTML templates
├── static/                         # CSS, JS, images
└── README.md

🧠 Architecture Diagram (Conceptual)

User Input → Ratings → Neo4j Graph →
Recommendation Engine →
API Response →
Flask Templates →
Web UI Output

⚙️ Installation & Setup
1️⃣ Install Dependencies
pip install -r requirements.txt

2️⃣ Start Neo4j

Create a database

Place dataset.csv in the Neo4j import directory

Update credentials in setup.py or environment variables

3️⃣ Run Database Setup
python setup.py

4️⃣ Start the Web Server
python app.py

5️⃣ Access the Application
http://localhost:5000

📊 API Endpoints
Recommendations
/api/recommendations/<username>/content
/api/recommendations/<username>/graph
/api/recommendations/<username>/hybrid

Graph Data
/api/graph-data/<username>/user-movies
/api/graph-data/<username>/recommendations
/api/graph-data/<username>/genre-network

User Movie Stats
/api/user-movies/<username>

🧪 Algorithms (High-Level Summary)
Content-Based Filtering

Extracts user-liked genres

Matches unwatched movies with similar attributes

Ranks by genre overlap

Graph-Based Approach

Uses Neo4j for 2-hop traversal

Detects movies linked through shared genres

Prioritizes stronger graph connectivity

Hybrid Model

Assigns weighted scores:

Content: 0.6

Graph: 0.4

Combines, sorts, and returns top results

🎯 Project Purpose

The goal of this project was to explore:

Graph databases in practical recommendation systems

Designing multi-algorithm recommendation engines

Full-stack implementation combining backend + data + visualization

Real-world modeling of movie datasets

👤 Author

Aayush Manoj Thakare
Computer Engineering, IIIT Pune
Backend Developer • Neo4j • Flask • Python

⭐ Future Improvements

Collaborative filtering algorithm

User embeddings with ML

Frontend UI redesign

Deployment on Render / Railway

Dockerized services
