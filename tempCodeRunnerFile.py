recommendation_engine.py


from neo4j import GraphDatabase

class MovieRecommender:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="password"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def collaborative_filtering(self, user_name, limit=5):
        """
        Collaborative Filtering: Find users with similar tastes
        and recommend movies they liked
        """
        with self.driver.session() as session:
            result = session.run("""
                // Find users who rated similar movies highly
                MATCH (u:User {name: $user})-[r1:RATED]->(m:Movie)<-[r2:RATED]-(other:User)
                WHERE r1.rating >= 4 AND r2.rating >= 4 AND u <> other
                
                // Find movies that similar users liked but target user hasn't seen
                WITH other, count(DISTINCT m) as commonMovies
                ORDER BY commonMovies DESC
                LIMIT 5
                
                MATCH (other)-[r:RATED]->(rec:Movie)
                WHERE r.rating >= 4 
                AND NOT EXISTS((u)-[:RATED]->(rec))
                
                WITH rec, avg(r.rating) as avgRating, count(DISTINCT other) as recommenders
                ORDER BY recommenders DESC, avgRating DESC
                LIMIT $limit
                
                RETURN rec.title as title, rec.year as year, rec.rating as movieRating, 
                       avgRating, recommenders
            """, user=user_name, limit=limit)
            
            recommendations = []
            for record in result:
                recommendations.append({
                    'title': record['title'],
                    'year': record['year'],
                    'rating': record['movieRating'],
                    'reason': f"Recommended by {record['recommenders']} similar users (avg rating: {record['avgRating']:.1f})"
                })
            
            return recommendations
    
    def content_based_filtering(self, user_name, limit=5):
        """
        Content-Based Filtering: Recommend movies similar to user's favorites
        based on genres, actors, and directors
        """
        with self.driver.session() as session:
            result = session.run("""
                // Find movies user liked
                MATCH (u:User {name: $user})-[r:RATED]->(liked:Movie)
                WHERE r.rating >= 4
                
                // Find similar movies through genres
                MATCH (liked)-[:BELONGS_TO]->(g:Genre)<-[:BELONGS_TO]-(rec:Movie)
                WHERE NOT EXISTS((u)-[:RATED]->(rec))
                
                // Also consider same director
                OPTIONAL MATCH (liked)<-[:DIRECTED]-(d:Director)-[:DIRECTED]->(rec)
                
                // And same actors
                OPTIONAL MATCH (liked)<-[:ACTED_IN]-(a:Actor)-[:ACTED_IN]->(rec)
                
                WITH rec, 
                     count(DISTINCT g) as sharedGenres,
                     count(DISTINCT d) as sameDirector,
                     count(DISTINCT a) as sharedActors,
                     collect(DISTINCT liked.title) as basedOn
                
                WITH rec, sharedGenres, sameDirector, sharedActors, basedOn,
                     (sharedGenres * 1.0 + sameDirector * 2.0 + sharedActors * 1.5) as similarity
                
                ORDER BY similarity DESC, rec.rating DESC
                LIMIT $limit
                
                RETURN rec.title as title, rec.year as year, rec.rating as rating,
                       sharedGenres, sameDirector, sharedActors, basedOn[0..2] as basedOn
            """, user=user_name, limit=limit)
            
            recommendations = []
            for record in result:
                reason_parts = []
                if record['sharedGenres'] > 0:
                    reason_parts.append(f"{record['sharedGenres']} shared genres")
                if record['sameDirector'] > 0:
                    reason_parts.append("same director")
                if record['sharedActors'] > 0:
                    reason_parts.append(f"{record['sharedActors']} shared actors")
                
                reason = f"Similar content ({', '.join(reason_parts)})"
                
                recommendations.append({
                    'title': record['title'],
                    'year': record['year'],
                    'rating': record['rating'],
                    'reason': reason
                })
            
            return recommendations
    
    def graph_based_recommendations(self, user_name, limit=5):
        """
        Graph-Based: Use path analysis to find connected movies
        """
        with self.driver.session() as session:
            result = session.run("""
                // Find movies user liked
                MATCH (u:User {name: $user})-[r:RATED]->(liked:Movie)
                WHERE r.rating >= 4
                
                // Find movies connected through various paths (1-2 hops)
                MATCH path = (liked)-[*1..2]-(rec:Movie)
                WHERE NOT EXISTS((u)-[:RATED]->(rec))
                AND rec <> liked
                
                WITH rec, count(DISTINCT path) as pathCount,
                     collect(DISTINCT [n in nodes(path) | labels(n)[0]]) as pathTypes
                
                ORDER BY pathCount DESC, rec.rating DESC
                LIMIT $limit
                
                RETURN rec.title as title, rec.year as year, rec.rating as rating,
                       pathCount
            """, user=user_name, limit=limit)
            
            recommendations = []
            for record in result:
                recommendations.append({
                    'title': record['title'],
                    'year': record['year'],
                    'rating': record['rating'],
                    'reason': f"Found through {record['pathCount']} connection paths"
                })
            
            return recommendations
    
    def hybrid_recommendations(self, user_name, limit=5):
        """
        Hybrid Approach: Combine multiple algorithms with weighted scoring
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (u:User {name: $user})-[r:RATED]->(liked:Movie)
                WHERE r.rating >= 4
                
                // Content-based score (genres, directors, actors)
                MATCH (liked)-[:BELONGS_TO]->(g:Genre)<-[:BELONGS_TO]-(rec:Movie)
                WHERE NOT EXISTS((u)-[:RATED]->(rec))
                
                OPTIONAL MATCH (liked)<-[:DIRECTED]-(d:Director)-[:DIRECTED]->(rec)
                OPTIONAL MATCH (liked)<-[:ACTED_IN]-(a:Actor)-[:ACTED_IN]->(rec)
                
                WITH rec, 
                     count(DISTINCT g) as genres,
                     count(DISTINCT d) as directors,
                     count(DISTINCT a) as actors
                
                // Collaborative score
                OPTIONAL MATCH (u)-[r1:RATED]->(m:Movie)<-[r2:RATED]-(other:User)-[r3:RATED]->(rec)
                WHERE r1.rating >= 4 AND r2.rating >= 4 AND r3.rating >= 4
                
                WITH rec, genres, directors, actors,
                     count(DISTINCT other) as collaborativeScore,
                     avg(r3.rating) as avgCollaborativeRating
                
                // Calculate hybrid score
                WITH rec,
                     (genres * 1.0 + directors * 2.0 + actors * 1.5) as contentScore,
                     (collaborativeScore * 2.0) as collabScore,
                     coalesce(avgCollaborativeRating, 0) as collabRating
                
                WITH rec, contentScore, collabScore, collabRating,
                     (contentScore * 0.4 + collabScore * 0.6 + rec.rating * 0.2) as hybridScore
                
                ORDER BY hybridScore DESC, rec.rating DESC
                LIMIT $limit
                
                RETURN rec.title as title, rec.year as year, rec.rating as rating,
                       hybridScore, contentScore, collabScore
            """, user=user_name, limit=limit)
            
            recommendations = []
            for record in result:
                recommendations.append({
                    'title': record['title'],
                    'year': record['year'],
                    'rating': record['rating'],
                    'reason': f"Hybrid score: {record['hybridScore']:.2f} (content + collaborative)"
                })
            
            return recommendations
    
    def get_user_stats(self, user_name):
        """Get statistics about a user's viewing history"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (u:User {name: $user})-[r:RATED]->(m:Movie)
                WITH u, count(m) as moviesWatched, avg(r.rating) as avgRating
                
                MATCH (u)-[r:RATED]->(m:Movie)-[:BELONGS_TO]->(g:Genre)
                WHERE r.rating >= 4
                WITH u, moviesWatched, avgRating, g.name as genre, count(*) as genreCount
                ORDER BY genreCount DESC
                LIMIT 3
                
                RETURN moviesWatched, avgRating, collect(genre) as favoriteGenres
            """, user=user_name)
            
            record = result.single()
            if record:
                return {
                    'movies_watched': record['moviesWatched'],
                    'avg_rating': round(record['avgRating'], 2),
                    'favorite_genres': record['favoriteGenres']
                }
            return None
    
    def get_all_users(self):
        """Get list of all users"""
        with self.driver.session() as session:
            result = session.run("MATCH (u:User) RETURN u.name as name ORDER BY name")
            return [record['name'] for record in result]


def print_recommendations(title, recommendations):
    """Pretty print recommendations"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")
    
    if not recommendations:
        print("  No recommendations found.")
        return
    
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['title']} ({rec['year']})")
        print(f"   Rating: {rec['rating']}/10")
        print(f"   Why: {rec['reason']}")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("  MOVIE RECOMMENDATION ENGINE - TEST RUN")
    print("="*70)
    
    recommender = MovieRecommender()
    
    try:
        # Get all users
        users = recommender.get_all_users()
        print(f"\nAvailable users: {', '.join(users)}")
        
        # Test with Alice
        test_user = "Alice"
        print(f"\n\n🎬 RECOMMENDATIONS FOR: {test_user}")
        print("="*70)
        
        # Get user stats
        stats = recommender.get_user_stats(test_user)
        if stats:
            print(f"\n📊 User Statistics:")
            print(f"   Movies watched: {stats['movies_watched']}")
            print(f"   Average rating: {stats['avg_rating']}/5")
            print(f"   Favorite genres: {', '.join(stats['favorite_genres'])}")
        
        # Test all algorithms
        print_recommendations(
            "1️⃣  COLLABORATIVE FILTERING",
            recommender.collaborative_filtering(test_user)
        )
        
        print_recommendations(
            "2️⃣  CONTENT-BASED FILTERING",
            recommender.content_based_filtering(test_user)
        )
        
        print_recommendations(
            "3️⃣  GRAPH-BASED RECOMMENDATIONS",
            recommender.graph_based_recommendations(test_user)
        )
        
        print_recommendations(
            "4️⃣  HYBRID APPROACH",
            recommender.hybrid_recommendations(test_user)
        )
        
        print("\n" + "="*70)
        print("✅ All algorithms tested successfully!")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Make sure Neo4j is running and database is set up.")
    
    finally:
        recommender.close()