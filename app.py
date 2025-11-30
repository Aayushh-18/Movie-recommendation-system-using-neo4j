"""
Flask Web Application for Movie Recommendation System
PickAMovieForMe.com inspired design with movie poster grid background.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from Recommendation_system import MovieRecommender
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize recommender
try:
    recommender = MovieRecommender(uri="bolt://localhost:7687", user="neo4j", password="Ramahire0618")
    logger.info("✅ Connected to Neo4j and ready to serve recommendations!")
except Exception as e:
    logger.error(f"❌ Failed to connect to Neo4j: {e}")
    recommender = None

@app.route('/')
def index():
    if not recommender:
        return "Error: Could not connect to database", 500
    
    users = recommender.get_all_users()
    return render_template('index.html', users=users)

@app.route('/new-user')
def new_user():
    if not recommender:
        return "Error: Could not connect to database", 500
    
    movies = recommender.get_random_movies_for_rating(10)
    return render_template('new_user.html', movies=movies)

@app.route('/submit-ratings', methods=['POST'])
def submit_ratings():
    if not recommender:
        return "Error: Could not connect to database", 500
    
    username = request.form.get('username')
    ratings = {}
    
    for key, value in request.form.items():
        if key.startswith('rating_'):
            movie_title = key.replace('rating_', '')
            if value and int(value) in range(1, 6):
                ratings[movie_title] = int(value)
    
    if not username or len(ratings) < 3:
        return "Please provide a username and rate at least 3 movies!", 400
    
    recommender.create_new_user(username, ratings)
    return redirect(url_for('recommendations', username=username))

@app.route('/recommendations/<username>')
def recommendations(username):
    if not recommender:
        return "Error: Could not connect to database", 500
    
    try:
        stats = recommender.get_user_stats(username)
        content = recommender.content_based_filtering(username)
        graph = recommender.graph_based_recommendations(username)
        hybrid = recommender.hybrid_recommendations(username)
        
        return render_template(
            'recommendations.html',
            username=username,
            stats=stats,
            content=content,
            graph=graph,
            hybrid=hybrid
        )
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return f"Error getting recommendations: {str(e)}", 500

@app.route('/api/recommendations/<username>/<algorithm>')
def api_recommendations(username, algorithm):
    if not recommender:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        if algorithm == 'content':
            results = recommender.content_based_filtering(username)
        elif algorithm == 'graph':
            results = recommender.graph_based_recommendations(username)
        elif algorithm == 'hybrid':
            results = recommender.hybrid_recommendations(username)
        else:
            return jsonify({'error': 'Invalid algorithm. Choose content, graph, or hybrid.'}), 400
        
        return jsonify(results)
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({'error': str(e)}), 500

# ============= NEW API ENDPOINTS FOR GRAPH VISUALIZATION =============

@app.route('/api/user-movies/<username>')
def api_user_movies(username):
    """Get user's rated movies with genres"""
    if not recommender:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        with recommender.driver.session() as session:
            result = session.run("""
                MATCH (u:User {name: $username})-[r:RATED]->(m:Movie)
                OPTIONAL MATCH (m)-[:BELONGS_TO]->(g:Genre)
                RETURN m.title as title, 
                       m.year as year,
                       r.rating as rating,
                       collect(g.name) as genres
                ORDER BY r.rating DESC
            """, username=username)
            
            movies = []
            for record in result:
                movies.append({
                    'title': record['title'],
                    'year': record['year'],
                    'rating': record['rating'],
                    'genres': [g for g in record['genres'] if g]
                })
            
            return jsonify(movies)
    except Exception as e:
        logger.error(f"Error fetching user movies: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/recommendations/<username>')
def api_user_recommendations(username):
    """Get recommendations for visualization"""
    if not recommender:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Get hybrid recommendations
        recommendations = recommender.hybrid_recommendations(username)
        
        # Format for visualization
        result = []
        for movie in recommendations[:10]:  # Limit to 10
            result.append({
                'title': movie.get('title'),
                'year': movie.get('year'),
                'score': movie.get('hybrid_score', 0),
                'genres': movie.get('genres', [])
            })
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error fetching recommendations: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/graph-query', methods=['POST'])
def graph_query():
    """Execute a custom Cypher query"""
    if not recommender:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        data = request.get_json()
        query = data.get('query')
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        with recommender.driver.session() as session:
            result = session.run(query)
            
            records = []
            for record in result:
                records.append(dict(record))
            
            return jsonify(records)
    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return jsonify({'error': str(e)}), 500

# ============= GRAPH VISUALIZATION ROUTES =============

@app.route('/graph-visualization/<username>')
def graph_visualization(username):
    """Render the graph visualization page"""
    if not recommender:
        return "Error: Could not connect to database", 500
    return render_template('graph_visualization.html', username=username)


@app.route('/api/graph-data/<username>/<viz_type>')
def graph_data(username, viz_type):
    """API endpoint to fetch graph data from Neo4j"""
    if not recommender:
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        with recommender.driver.session() as session:
            nodes = []
            edges = []
            node_ids = set()
            
            if viz_type == 'user-movies':
                # Get user's rated movies with genres
                result = session.run("""
                    MATCH (u:User {name: $username})-[r:RATED]->(m:Movie)
                    OPTIONAL MATCH (m)-[:BELONGS_TO]->(g:Genre)
                    RETURN u, m, collect(distinct g) as genres, r.rating as rating
                    LIMIT 50
                """, username=username)
                
                for record in result:
                    user_node = record['u']
                    movie_node = record['m']
                    genre_nodes = record['genres']
                    rating = record['rating']
                    
                    # Add user node
                    user_id = f"user_{user_node['name']}"
                    if user_id not in node_ids:
                        nodes.append({
                            'id': user_id,
                            'label': user_node['name'],
                            'type': 'User'
                        })
                        node_ids.add(user_id)
                    
                    # Add movie node
                    movie_id = f"movie_{movie_node['title']}"
                    if movie_id not in node_ids:
                        nodes.append({
                            'id': movie_id,
                            'label': movie_node['title'],
                            'type': 'Movie',
                            'year': movie_node.get('year', 'N/A'),
                            'rating': rating
                        })
                        node_ids.add(movie_id)
                    
                    # Add RATED edge
                    edges.append({
                        'source': user_id,
                        'target': movie_id,
                        'type': 'RATED',
                        'rating': rating
                    })
                    
                    # Add genre nodes and edges
                    for genre_node in genre_nodes:
                        if genre_node:
                            genre_id = f"genre_{genre_node['name']}"
                            if genre_id not in node_ids:
                                nodes.append({
                                    'id': genre_id,
                                    'label': genre_node['name'],
                                    'type': 'Genre'
                                })
                                node_ids.add(genre_id)
                            
                            edges.append({
                                'source': movie_id,
                                'target': genre_id,
                                'type': 'BELONGS_TO'
                            })
            
            elif viz_type == 'recommendations':
                # Show recommendation path: user -> liked movies -> shared genres -> recommended movies
                result = session.run("""
                    // Get user's highly rated movies
                    MATCH (u:User {name: $username})-[r1:RATED]->(liked:Movie)-[:BELONGS_TO]->(g:Genre)
                    WHERE r1.rating >= 4
                    
                    // Find recommended movies through shared genres
                    MATCH (rec:Movie)-[:BELONGS_TO]->(g)
                    WHERE NOT EXISTS((u)-[:RATED]->(rec))
                    
                    RETURN u, liked, g, rec
                    LIMIT 30
                """, username=username)
                
                for record in result:
                    user_node = record['u']
                    liked_movie = record['liked']
                    genre_node = record['g']
                    rec_movie = record['rec']
                    
                    # Add user
                    user_id = f"user_{user_node['name']}"
                    if user_id not in node_ids:
                        nodes.append({
                            'id': user_id,
                            'label': user_node['name'],
                            'type': 'User'
                        })
                        node_ids.add(user_id)
                    
                    # Add liked movie
                    liked_id = f"movie_{liked_movie['title']}"
                    if liked_id not in node_ids:
                        nodes.append({
                            'id': liked_id,
                            'label': liked_movie['title'],
                            'type': 'Movie',
                            'year': liked_movie.get('year', 'N/A')
                        })
                        node_ids.add(liked_id)
                        
                        edges.append({
                            'source': user_id,
                            'target': liked_id,
                            'type': 'RATED'
                        })
                    
                    # Add genre
                    genre_id = f"genre_{genre_node['name']}"
                    if genre_id not in node_ids:
                        nodes.append({
                            'id': genre_id,
                            'label': genre_node['name'],
                            'type': 'Genre'
                        })
                        node_ids.add(genre_id)
                    
                    # Add edges to genre
                    if {'source': liked_id, 'target': genre_id, 'type': 'BELONGS_TO'} not in edges:
                        edges.append({
                            'source': liked_id,
                            'target': genre_id,
                            'type': 'BELONGS_TO'
                        })
                    
                    # Add recommended movie
                    rec_id = f"movie_{rec_movie['title']}"
                    if rec_id not in node_ids:
                        nodes.append({
                            'id': rec_id,
                            'label': rec_movie['title'],
                            'type': 'Movie',
                            'year': rec_movie.get('year', 'N/A'),
                            'recommended': True
                        })
                        node_ids.add(rec_id)
                    
                    # Add edge from genre to recommended movie
                    if {'source': rec_id, 'target': genre_id, 'type': 'BELONGS_TO'} not in edges:
                        edges.append({
                            'source': rec_id,
                            'target': genre_id,
                            'type': 'BELONGS_TO'
                        })
            
            elif viz_type == 'genre-network':
                # Show genre network with movies
                result = session.run("""
                    MATCH (m:Movie)-[:BELONGS_TO]->(g:Genre)
                    WITH g, collect(m)[0..5] as movies
                    UNWIND movies as movie
                    RETURN g, movie
                    LIMIT 50
                """)
                
                for record in result:
                    genre_node = record['g']
                    movie_node = record['movie']
                    
                    # Add genre
                    genre_id = f"genre_{genre_node['name']}"
                    if genre_id not in node_ids:
                        nodes.append({
                            'id': genre_id,
                            'label': genre_node['name'],
                            'type': 'Genre'
                        })
                        node_ids.add(genre_id)
                    
                    # Add movie
                    movie_id = f"movie_{movie_node['title']}"
                    if movie_id not in node_ids:
                        nodes.append({
                            'id': movie_id,
                            'label': movie_node['title'],
                            'type': 'Movie',
                            'year': movie_node.get('year', 'N/A')
                        })
                        node_ids.add(movie_id)
                    
                    edges.append({
                        'source': movie_id,
                        'target': genre_id,
                        'type': 'BELONGS_TO'
                    })
            
            logger.info(f"Graph data: {len(nodes)} nodes, {len(edges)} edges for {username} ({viz_type})")
            return jsonify({'nodes': nodes, 'edges': edges})
            
    except Exception as e:
        logger.error(f"Graph data error: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("\n" + "="*60)
    print(" MOVIE RECOMMENDATION WEB APP")
    print("="*60)
    print("\n Server starting...")
    print(f"📡 Open your browser and go to: http://localhost:5000")
    print(f"🕸️  Graph visualization: http://localhost:5000/graph-visualization/Alice")
    print("="*60 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)