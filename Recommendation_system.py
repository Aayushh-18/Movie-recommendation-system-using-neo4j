
from neo4j import GraphDatabase
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MovieRecommender:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="Ramahire0618"):
        try:
            self.driver = GraphDatabase.driver(
                uri, 
                auth=(user, password),
                max_connection_pool_size=50,
                connection_timeout=30
            )
            # Test connection
            self.driver.verify_connectivity()
            logger.info("Successfully connected to Neo4j")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()
            logger.info("Database connection closed")
    
    def content_based_filtering(self, username, limit=5):
        """
        Fast content-based filtering - finds movies similar to user's favorites
        """
        query = """
        // Step 1: Get user's liked genres (simple and fast)
        MATCH (u:User {name: $username})-[r:RATED]->(m:Movie)-[:BELONGS_TO]->(g:Genre)
        WHERE r.rating >= 4
        WITH u, COLLECT(DISTINCT g.name) as liked_genres
        WHERE SIZE(liked_genres) > 0
        
        // Step 2: Find unwatched movies with matching genres
        MATCH (rec:Movie)-[:BELONGS_TO]->(g:Genre)
        WHERE g.name IN liked_genres
        AND NOT EXISTS((u)-[:RATED]->(rec))
        
        // Step 3: Calculate simple match score
        WITH rec, COUNT(DISTINCT g) as genre_matches
        
        // Step 4: Get movie details
        MATCH (rec)-[:BELONGS_TO]->(genre:Genre)
        
        RETURN rec.title as title,
               rec.year as year,
               COLLECT(DISTINCT genre.name) as genres,
               genre_matches as score
        ORDER BY genre_matches DESC, rec.title
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, username=username, limit=limit)
                recommendations = [dict(record) for record in result]
                logger.info(f"Content-based: Found {len(recommendations)} recommendations for {username}")
                return recommendations
        except Exception as e:
            logger.error(f"Content-based filtering failed: {e}")
            return []
    
    def graph_based_recommendations(self, username, limit=5):
        """
        Fast graph-based - finds movies through shared connections
        """
        query = """
        // Find movies connected through shared genres (2-hop path)
        MATCH (u:User {name: $username})-[r:RATED]->(liked:Movie)-[:BELONGS_TO]->(g:Genre)<-[:BELONGS_TO]-(rec:Movie)
        WHERE r.rating >= 4
        AND NOT EXISTS((u)-[:RATED]->(rec))
        AND liked <> rec
        
        WITH rec, COUNT(DISTINCT g) as shared_connections
        
        // Get genres for display
        MATCH (rec)-[:BELONGS_TO]->(genre:Genre)
        
        RETURN rec.title as title,
               rec.year as year,
               COLLECT(DISTINCT genre.name) as genres,
               shared_connections
        ORDER BY shared_connections DESC, rec.title
        LIMIT $limit
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, username=username, limit=limit)
                recommendations = [dict(record) for record in result]
                logger.info(f"Graph-based: Found {len(recommendations)} recommendations for {username}")
                return recommendations
        except Exception as e:
            logger.error(f"Graph-based filtering failed: {e}")
            return []
    
    def hybrid_recommendations(self, username, limit=5):
        """
        Combines both methods with intelligent scoring
        """
        try:
            # Get recommendations from both methods
            content_recs = self.content_based_filtering(username, limit=limit*2)
            graph_recs = self.graph_based_recommendations(username, limit=limit*2)
            
            if not content_recs and not graph_recs:
                logger.warning(f"No recommendations found for {username}")
                return []
            
            # Combine and score
            combined = {}
            
            # Content-based scores (weight: 0.6)
            for i, movie in enumerate(content_recs):
                title = movie['title']
                score = (len(content_recs) - i) * 0.6
                combined[title] = {
                    'title': title,
                    'year': movie['year'],
                    'genres': movie['genres'],
                    'score': score
                }
            
            # Graph-based scores (weight: 0.4)
            for i, movie in enumerate(graph_recs):
                title = movie['title']
                score = (len(graph_recs) - i) * 0.4
                if title in combined:
                    combined[title]['score'] += score
                else:
                    combined[title] = {
                        'title': title,
                        'year': movie['year'],
                        'genres': movie['genres'],
                        'score': score
                    }
            
            # Sort by combined score
            results = sorted(combined.values(), key=lambda x: x['score'], reverse=True)[:limit]
            
            # Add rounded hybrid score
            for movie in results:
                movie['hybrid_score'] = round(movie['score'], 2)
                del movie['score']
            
            logger.info(f"Hybrid: Returning {len(results)} recommendations for {username}")
            return results
            
        except Exception as e:
            logger.error(f"Hybrid recommendations failed: {e}")
            return []
    
    def get_user_stats(self, username):
        """Get user statistics efficiently"""
        query = """
        MATCH (u:User {name: $username})
        OPTIONAL MATCH (u)-[r:RATED]->(m:Movie)
        OPTIONAL MATCH (m)-[:BELONGS_TO]->(g:Genre)
        
        RETURN COUNT(DISTINCT m) as movies_watched,
               ROUND(AVG(r.rating) * 10) / 10 as avg_rating,
               COLLECT(DISTINCT g.name)[0..5] as favorite_genres
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, username=username)
                record = result.single()
                
                if record and record['movies_watched'] > 0:
                    return dict(record)
                return None
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return None
    
    def get_all_users(self):
        """Get list of all users"""
        query = "MATCH (u:User) RETURN u.name as name ORDER BY name"
        
        try:
            with self.driver.session() as session:
                result = session.run(query)
                users = [record["name"] for record in result]
                logger.info(f"Found {len(users)} users")
                return users
        except Exception as e:
            logger.error(f"Failed to get users: {e}")
            return []
    
    def get_random_movies_for_rating(self, limit=10):
        
        query = """
        MATCH (m:Movie)-[:BELONGS_TO]->(g:Genre)
        WITH m, COLLECT(DISTINCT g.name) as genres, rand() as r
        ORDER BY r
        LIMIT $limit
        RETURN m.title as title, m.year as year, genres
        """
        
        try:
            with self.driver.session() as session:
                result = session.run(query, limit=limit)
                movies = [dict(record) for record in result]
                logger.info(f"Retrieved {len(movies)} random movies")
                return movies
        except Exception as e:
            logger.error(f"Failed to get random movies: {e}")
            return []
    
    def create_new_user(self, username, ratings):
        
        try:
            with self.driver.session() as session:
                # Create user
                session.run("MERGE (u:User {name: $name})", name=username)
                
                # Batch insert ratings
                if ratings:
                    rating_list = [{'title': title, 'rating': score} 
                                 for title, score in ratings.items()]
                    
                    session.run("""
                        MATCH (u:User {name: $username})
                        UNWIND $ratings as r
                        MATCH (m:Movie {title: r.title})
                        MERGE (u)-[rel:RATED]->(m)
                        SET rel.rating = r.rating
                    """, username=username, ratings=rating_list)
                
                logger.info(f"Created user '{username}' with {len(ratings)} ratings")
                return f"User '{username}' created successfully with {len(ratings)} ratings."
                
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return f"Error creating user: {str(e)}"
    
    def setup_indexes(self):
        
        indexes = [
            "CREATE INDEX user_name IF NOT EXISTS FOR (u:User) ON (u.name)",
            "CREATE INDEX movie_title IF NOT EXISTS FOR (m:Movie) ON (m.title)",
            "CREATE INDEX genre_name IF NOT EXISTS FOR (g:Genre) ON (g.name)"
        ]
        
        try:
            with self.driver.session() as session:
                for idx_query in indexes:
                    session.run(idx_query)
            logger.info("Indexes created successfully")
            return "Indexes setup complete"
        except Exception as e:
            logger.error(f"Index creation failed: {e}")
            return f"Index setup failed: {str(e)}"



if __name__ == "__main__":
    recommender = MovieRecommender()
    
    try:
        # Setup indexes (run once)
        print(recommender.setup_indexes())
        
        # Get recommendations
        username = "Alice"
        
        # print(f"\n=== Content-Based Recommendations for {username} ===")
        # content_recs = recommender.content_based_filtering(username, limit=5)
        # for i, movie in enumerate(content_recs, 1):
        #     print(f"{i}. {movie['title']} ({movie['year']}) - {', '.join(movie['genres'])}")
        
        print(f"\n=== Graph-Based Recommendations for {username} ===")
        graph_recs = recommender.graph_based_recommendations(username, limit=5)
        for i, movie in enumerate(graph_recs, 1):
            print(f"{i}. {movie['title']} ({movie['year']}) - {', '.join(movie['genres'])}")
        
        # print(f"\n=== Hybrid Recommendations for {username} ===")
        # hybrid_recs = recommender.hybrid_recommendations(username, limit=5)
        # for i, movie in enumerate(hybrid_recs, 1):
        #     print(f"{i}. {movie['title']} ({movie['year']}) - Score: {movie['hybrid_score']}")
        
    finally:
        recommender.close()