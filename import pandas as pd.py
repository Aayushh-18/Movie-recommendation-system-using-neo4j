import pandas as pd

# Load CSV
df = pd.read_csv("dataset.csv", header=None, names=["movie_id", "title", "year", "director", "cast", "genres"], low_memory=False)

# Handle missing values
df['director'] = df['director'].fillna('')
df['cast'] = df['cast'].fillna('')
df['genres'] = df['genres'].fillna('')

# Split cast and genres into lists
df['cast_list'] = df['cast'].apply(lambda x: [actor.strip() for actor in x.split() if actor.strip()])
df['genres_list'] = df['genres'].apply(lambda x: [genre.strip() for genre in x.split() if genre.strip()])

# Drop old 'cast' and 'genres' columns
df = df.drop(columns=['cast', 'genres'])

# Save cleaned CSV
df.to_csv("cleaned_dataset.csv", index=False)
print("Cleaned dataset saved as cleaned_dataset.csv")
