"""
Improved Database Setup for Movie Recommendation System
Works with MovieLens 100k dataset and creates sample users dynamically
"""

from neo4j import GraphDatabase
import random
import os

class MovieRecommendationDB:
    """
    Handles connection and operations for the Neo4j Movie Recommendation database.
    """
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password="Ramahire0618"):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.driver.verify_connectivity()
            print("✅ Connected to Neo4j successfully!")
        except Exception as e:
            print(f"❌ Failed to connect to Neo4j: {e}")
            raise
    
    def close(self):
        """Closes the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            print("Database connection closed.")
    
    def clear_database(self):
        """Clears all nodes and relationships in the database."""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("🗑️  Database cleared!")
    
    def load_movie_metadata(self):
        """
        Loads Movie, Genre, Actor, and Director data from dataset.csv.
        The file MUST be in the Neo4j import folder.
        """
        with self.driver.session() as session:
            try:
                result = session.run("""
                    LOAD CSV WITH HEADERS FROM 'file:///dataset.csv' AS row
                    WITH row WHERE row.title IS NOT NULL AND row.movie_id IS NOT NULL
                    
                    // Create Movie node
                    MERGE (m:Movie {movie_id: toString(row.movie_id)})
                    ON CREATE SET 
                        m.title = row.title, 
                        m.year = toInteger(row.year),
                        m.created_at = timestamp()
                    
                    // Create Genres and relationships
                    WITH m, row WHERE row.genres IS NOT NULL AND row.genres <> ''
                    UNWIND split(row.genres, '|') AS genre_name
                    WITH m, TRIM(genre_name) as clean_genre
                    WHERE clean_genre <> ''
                    MERGE (g:Genre {name: clean_genre})
                    MERGE (m)-[:BELONGS_TO]->(g)
                    
                    RETURN count(DISTINCT m) as movies_loaded
                """)
                
                record = result.single()
                if record:
                    print(f"✅ Loaded {record['movies_loaded']} movies with genres!")
                
                # Load actors if available
                session.run("""
                    LOAD CSV WITH HEADERS FROM 'file:///dataset.csv' AS row
                    WITH row WHERE row.movie_id IS NOT NULL AND row.actors IS NOT NULL AND row.actors <> ''
                    
                    MATCH (m:Movie {movie_id: toString(row.movie_id)})
                    UNWIND split(row.actors, ',') AS actor_name
                    WITH m, TRIM(actor_name) as clean_actor
                    WHERE clean_actor <> ''
                    MERGE (a:Actor {name: clean_actor})
                    MERGE (a)-[:ACTED_IN]->(m)
                """)
                print("✅ Loaded actors!")
                
                # Load directors if available
                session.run("""
                    LOAD CSV WITH HEADERS FROM 'file:///dataset.csv' AS row
                    WITH row WHERE row.movie_id IS NOT NULL AND row.directors IS NOT NULL AND row.directors <> ''
                    
                    MATCH (m:Movie {movie_id: toString(row.movie_id)})
                    UNWIND split(row.directors, ',') AS director_name
                    WITH m, TRIM(director_name) as clean_director
                    WHERE clean_director <> ''
                    MERGE (d:Director {name: clean_director})
                    MERGE (d)-[:DIRECTED]->(m)
                """)
                print("✅ Loaded directors!")
                
            except Exception as e:
                print(f"⚠️  Error loading metadata: {e}")
                raise

    def create_sample_users_and_ratings(self):
        """
        Creates sample users and assigns them ratings on actual movies from the database.
        Dynamically selects movies that exist in the current dataset.
        """
        with self.driver.session() as session:
            # First, check if we have movies in the database
            movie_count = session.run("MATCH (m:Movie) RETURN count(m) as count").single()
            
            if movie_count['count'] == 0:
                print("⚠️  No movies found in database! Load dataset first.")
                return
            
            print(f"📊 Found {movie_count['count']} movies in database")
            
            # Get a diverse set of movies with genres (for better recommendations)
            result = session.run("""
                MATCH (m:Movie)-[:BELONGS_TO]->(g:Genre)
                WITH m, COLLECT(DISTINCT g.name) as genres
                WHERE SIZE(genres) > 0
                WITH m, genres, rand() as r
                ORDER BY r
                LIMIT 50
                RETURN m.title as title, m.year as year, genres
            """)
            
            available_movies = [dict(record) for record in result]
            
            if len(available_movies) < 10:
                print("⚠️  Not enough movies with genres. Need at least 10 movies.")
                return
            
            print(f"✅ Selected {len(available_movies)} diverse movies for rating")
            
            # Create sample users
            users = ["Alice", "Bob", "Charlie", "David", "Emma", "Frank", "Grace", "Henry"]
            
            total_ratings = 0
            for user_name in users:
                # Create user
                session.run("MERGE (u:User {name: $name})", name=user_name)
                
                # Each user rates 8-15 random movies
                num_ratings = random.randint(8, 15)
                movies_to_rate = random.sample(available_movies, min(num_ratings, len(available_movies)))
                
                ratings_batch = []
                for movie in movies_to_rate:
                    # Generate realistic ratings (more 4s and 5s, fewer low ratings)
                    rating = random.choices([3, 4, 5], weights=[0.2, 0.4, 0.4])[0]
                    ratings_batch.append({
                        'title': movie['title'],
                        'rating': rating
                    })
                
                # Batch insert all ratings for this user
                if ratings_batch:
                    session.run("""
                        MATCH (u:User {name: $username})
                        UNWIND $ratings as r
                        MATCH (m:Movie {title: r.title})
                        MERGE (u)-[rel:RATED]->(m)
                        SET rel.rating = r.rating, rel.timestamp = timestamp()
                    """, username=user_name, ratings=ratings_batch)
                    
                    total_ratings += len(ratings_batch)
                    print(f"  ✓ {user_name}: {len(ratings_batch)} ratings")
            
            print(f"\n✅ Created {len(users)} users with {total_ratings} total ratings!")
    
    def create_indexes(self):
        """Creates indexes for better database performance."""
        indexes = [
            ("movie_id_idx", "CREATE INDEX movie_id_idx IF NOT EXISTS FOR (m:Movie) ON (m.movie_id)"),
            ("movie_title_idx", "CREATE INDEX movie_title_idx IF NOT EXISTS FOR (m:Movie) ON (m.title)"),
            ("user_name_idx", "CREATE INDEX user_name_idx IF NOT EXISTS FOR (u:User) ON (u.name)"),
            ("genre_name_idx", "CREATE INDEX genre_name_idx IF NOT EXISTS FOR (g:Genre) ON (g.name)"),
            ("actor_name_idx", "CREATE INDEX actor_name_idx IF NOT EXISTS FOR (a:Actor) ON (a.name)"),
            ("director_name_idx", "CREATE INDEX director_name_idx IF NOT EXISTS FOR (d:Director) ON (d.name)")
        ]
        
        with self.driver.session() as session:
            for idx_name, idx_query in indexes:
                try:
                    session.run(idx_query)
                except Exception as e:
                    # Index might already exist, that's okay
                    pass
        
        print("✅ Indexes created/verified!")
    
    def verify_setup(self):
        """Verify that the database is set up correctly - FAST version."""
        print("\n" + "="*60)
        print("🔍 DATABASE VERIFICATION")
        print("="*60)
        
        with self.driver.session() as session:
            # Quick count queries (separate for speed)
            try:
                movie_count = session.run("MATCH (m:Movie) RETURN count(m) as count").single()['count']
                print(f"\n📊 Database Statistics:")
                print(f"   Movies:  {movie_count}")
            except Exception as e:
                print(f"   ❌ Error counting movies: {e}")
                movie_count = 0
            
            try:
                user_count = session.run("MATCH (u:User) RETURN count(u) as count").single()['count']
                print(f"   Users:   {user_count}")
            except Exception as e:
                print(f"   ❌ Error counting users: {e}")
                user_count = 0
            
            try:
                genre_count = session.run("MATCH (g:Genre) RETURN count(g) as count").single()['count']
                print(f"   Genres:  {genre_count}")
            except Exception as e:
                print(f"   ❌ Error counting genres: {e}")
                genre_count = 0
            
            try:
                rating_count = session.run("MATCH ()-[r:RATED]->() RETURN count(r) as count").single()['count']
                print(f"   Ratings: {rating_count}")
            except Exception as e:
                print(f"   ❌ Error counting ratings: {e}")
                rating_count = 0
            
            # Sample users (quick)
            try:
                users = session.run("""
                    MATCH (u:User)-[r:RATED]->()
                    WITH u.name as name, count(r) as rating_count
                    RETURN name, rating_count
                    ORDER BY name
                    LIMIT 5
                """)
                
                print(f"\n👥 Sample Users:")
                for user in users:
                    print(f"   {user['name']}: {user['rating_count']} ratings")
            except Exception as e:
                print(f"   ⚠️  Could not fetch user details: {e}")
            
            # Simple validation
            print(f"\n✅ Validation:")
            if movie_count == 0:
                print("   ❌ No movies found!")
            elif user_count == 0:
                print("   ❌ No users found!")
            elif rating_count == 0:
                print("   ❌ No ratings found!")
            else:
                print("   ✅ Database setup looks good!")
        
        print("="*60 + "\n")


# --- Execution Block ---
if __name__ == "__main__":
    print("=" * 60)
    print("🎬 Movie Recommendation System - Database Setup")
    print("=" * 60)
    print("\nThis will:")
    print("1. Clear the existing database")
    print("2. Load movie data from dataset.csv")
    print("3. Create sample users (Alice, Bob, etc.)")
    print("4. Generate realistic ratings")
    print("5. Create performance indexes")
    print("\n" + "=" * 60)
    
    # Quick setup option
    print("\nSetup options:")
    print("  1. Full setup with verification (slower)")
    print("  2. Quick setup (skip verification)")
    
    option = input("\nChoose option (1 or 2, default=2): ").strip() or "2"
    skip_verification = (option == "2")
    
    # Prompt for confirmation
    response = input("\nProceed with setup? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("Setup cancelled.")
        exit()
    
    NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "Ramahire0618") 
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    
    db = MovieRecommendationDB(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)
    
    try:
        print("\n Starting database setup...\n")
        
        # Step 1: Clear existing data
        db.clear_database()
        
        # Step 2: Load movie metadata
        print("\n Loading movie metadata from CSV...")
        db.load_movie_metadata()
        
        # Step 3: Create sample users and ratings
        print("\n Creating sample users...")
        db.create_sample_users_and_ratings()
        
        # Step 4: Create indexes
        print("\n Creating performance indexes...")
        db.create_indexes()
        
        # Step 5: Verify setup (optional)
        if not skip_verification:
            db.verify_setup()
        else:
            print("\n Skipping verification (quick mode)")
        
        print("\n" + "=" * 60)
        print("DATABASE SETUP COMPLETE!")
        print("=" * 60)
        print("\n Next steps:")
        print("   1. Run: python Recommendation_system.py  (to test)")
        print("   2. Run: python app.py  (to start web interface)")
        print("\n" + "=" * 60 + "\n")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(" DATABASE SETUP FAILED!")
        print("=" * 60)
        print(f"\nError: {e}")
        print("\n Common issues:")
        print("   1. Is Neo4j running? Check: http://localhost:7474")
        print("   2. Is dataset.csv in Neo4j import folder?")
        print("      Location: [Neo4j Directory]/import/dataset.csv")
        print("   3. Is the password c2" \
        "correct? Default: 'Ramahire0618'")
        print("\n" + "=" * 60 + "\n")
        
    finally:
        db.close()