from app.extract_text import clean_text,extract_text_from_image,extract_images_and_text,extract_tables
import faiss
import numpy as np
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException, Request,APIRouter
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import spacy
import networkx as nx
from typing import Any, List, Dict, Tuple

# Initialize FastAPI app
router = APIRouter()

# Load SentenceTransformer model for embedding generation
model = SentenceTransformer('all-MiniLM-L6-v2')

dimension = 384  # Dimension of the SentenceTransformer embeddings
index = faiss.IndexFlatL2(dimension)  # L2 distance-based FAISS index

file_metadata = []  # To store metadata like filenames

# Initialize a directed graph for the knowledge graph
knowledge_graph = nx.DiGraph()

# Load spaCy model for entity recognition
nlp = spacy.load("en_core_web_sm")


# Function to generate embeddings from text
def generate_embeddings(text: str) -> np.ndarray:
    return model.encode([text])[0]

# Function to extract entities and relationships from text
def extract_entities_and_relationships(text: str) -> List[Tuple[str, str]]:
    doc = nlp(text)
    entities = [(ent.text, ent.label_) for ent in doc.ents]
    return entities

# Function to update the knowledge graph
def update_knowledge_graph(text: str, filename: str):
    entities = extract_entities_and_relationships(text)
    for ent, label in entities:
        knowledge_graph.add_node(ent, label=label)
        # Add an edge from the file (document) to the entity
        knowledge_graph.add_edge(filename, ent)

@router.post("/process-file/")
async def process_file(file: UploadFile = File(...)):
    content_type = file.content_type
    file_bytes = await file.read()

    # Check if the file is HTML or XML
    if content_type == "text/html" or file.filename.endswith(".html"):
        soup = BeautifulSoup(file_bytes, "html.parser")
    elif content_type == "text/xml" or file.filename.endswith(".xml"):
        soup = BeautifulSoup(file_bytes, "lxml-xml")
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload an HTML or XML file.")

    # Extract cleaned text
    cleaned_text = clean_text(soup.get_text())

    # Extract text from images using OCR
    image_text = extract_images_and_text(soup)

    # Extract tables from HTML/XML
    tables = extract_tables(soup)

    # Combine text from all sources
    combined_text = cleaned_text + "\n\n" + image_text
    for table in tables:
        combined_text += "\n\n" + str(table)

    # Generate embeddings for combined text
    embeddings = generate_embeddings(combined_text)

    # Store the embeddings in FAISS
    index.add(np.array([embeddings]))
    
    # Store the metadata about the file
    file_metadata.append({"filename": file.filename, "text": combined_text})
    
    # Update the knowledge graph
    update_knowledge_graph(combined_text, file.filename)

    return {"message": f"File '{file.filename}' processed and stored successfully."}

def convert_numpy_types(data: Any) -> Any:
    if isinstance(data, dict):
        return {key: convert_numpy_types(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_numpy_types(item) for item in data]
    elif isinstance(data, (np.float32, np.float64)):
        return float(data)
    return data

def extract_relevant_snippet(text, query):
    query_words = query.lower().split()  # Break query into words
    for word in query_words:
        if word in text.lower():
            start_index = text.lower().find(word)
            end_index = start_index + 200  # Capture the surrounding context (e.g., 200 chars)
            return text[start_index:end_index]  # Return the snippet of relevant text
    return "No relevant information found."


@router.post("/faiss/search/")
async def search_in_faiss(query: str):

    global index 

    # Check if metadata exists
    if len(file_metadata) == 0:
        return {"error": "No metadata available. Please store a file first."}

    # Generate embeddings for the query
    query_embedding = generate_embeddings(query)
    print("Query Embedding:", query_embedding)

    # Search in FAISS index
    distances, indices = index.search(np.array([query_embedding]), k=5)  # Get top 5 results
    print("Distances:", distances)
    print("Indices:", indices)

    # Ensure indices returned by FAISS are valid and within the range of `file_metadata`
    top_results = []
    for distance, index in zip(distances[0], indices[0]):
        if index < len(file_metadata):  # Check if index is within bounds
            text_content = file_metadata[index]["text"]
            print("text_content",text_content)
            relevant_text = extract_relevant_snippet(text_content, query)
            print("relevant_text",relevant_text)
            top_results.append({
                "filename": file_metadata[index]["filename"],
                "text": relevant_text,  # Retrieve the original text
                "distance": distance
            })

    # Re-ranking results based on the knowledge graph
    ranked_results = re_rank_results(top_results, query)

    response = {"results": convert_numpy_types(ranked_results)}

    return response

# Function to re-rank results based on the knowledge graph
def re_rank_results(results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    query_entities = extract_entities_and_relationships(query)
    entity_scores = {ent: 0 for ent, _ in query_entities}

    # Calculate scores based on knowledge graph relationships
    for result in results:
        for ent in query_entities:
            if knowledge_graph.has_node(ent[0]):
                if knowledge_graph.has_edge(result['filename'], ent[0]):
                    entity_scores[ent[0]] += 1  # Increment score for each direct connection

    # Sort results based on scores
    results_with_scores = [(result, sum(entity_scores.values())) for result in results]
    sorted_results = sorted(results_with_scores, key=lambda x: x[1], reverse=True)

    return [result[0] for result in sorted_results]


