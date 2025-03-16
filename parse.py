from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
import re

# Simplified template focused on structured information extraction
template = """
You are an expert at extracting specific information from text content. 
Below is text extracted from a website:

```
{text_content}
```

Task: {parse_description}

Guidelines:
1. Focus ONLY on extracting what was requested
2. Format your response in a clean, structured way
3. If information is not found, indicate with "Not found"
4. Return only the extracted information without additional commentary
"""

def initialize_model(model_name="llama3.2"):
    """Initialize the Ollama model with the given name."""
    try:
        return OllamaLLM(model=model_name)
    except Exception as e:
        print(f"Error initializing Ollama model '{model_name}': {e}")
        print("Falling back to default model")
        return OllamaLLM(model="llama3")

def parse_with_ollama(text_chunks, parse_description, model_name="llama3.2"):
    """Parse text content using Ollama LLM."""
    print(f"Initializing Ollama with model: {model_name}")
    
    # Initialize model just once
    model = initialize_model(model_name)
    
    # Create prompt template and chain
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | model
    
    parsed_results = []
    
    # Process each chunk
    total_chunks = len(text_chunks)
    
    # If there are too many chunks, only process the first few
    if total_chunks > 3:
        print(f"Limiting processing to first 3 of {total_chunks} chunks for efficiency")
        processing_chunks = text_chunks[:3]
    else:
        processing_chunks = text_chunks
    
    for i, chunk in enumerate(processing_chunks, start=1):
        try:
            # Clean and trim the chunk for faster processing
            cleaned_chunk = clean_text_chunk(chunk)
            
            print(f"Processing chunk {i} of {len(processing_chunks)} (size: {len(cleaned_chunk)} chars)")
            
            # Invoke the model
            response = chain.invoke({
                "text_content": cleaned_chunk,
                "parse_description": parse_description
            })
            
            print(f"Parsed chunk {i} successfully")
            
            # Only add non-empty responses
            if response and len(response.strip()) > 0:
                parsed_results.append(response)
        except Exception as e:
            print(f"Error parsing chunk {i}: {e}")
            # Don't add error messages to results to keep output clean
    
    # Combine results
    if not parsed_results:
        return "No relevant information found in the content."
    
    # Combine and clean results
    combined_results = "\n\n".join(parsed_results)
    cleaned_results = clean_parsed_results(combined_results)
    
    return cleaned_results

def clean_text_chunk(chunk):
    """Clean a text chunk to make it more processable by the LLM."""
    # Trim excessively long chunks
    if len(chunk) > 4000:
        chunk = chunk[:4000]
    
    # Remove excessive whitespace to speed up processing
    chunk = re.sub(r'\s+', ' ', chunk)
    
    # Remove any remaining HTML tags
    chunk = re.sub(r'<[^>]*>', '', chunk)
    
    # Clean up unicode characters
    chunk = chunk.replace('\u00a0', ' ')
    
    return chunk.strip()

def clean_parsed_results(results):
    """Clean up and format the parsed results."""
    # Remove repeated "```" blocks
    results = re.sub(r'```[^`]*```\s*', '', results)
    
    # Remove any starting meta-commentary
    results = re.sub(r'^(I found|Here is|The extracted|Based on the content).*?:\s*', '', results, flags=re.MULTILINE)
    
    # Remove any trailing instructions or explanations
    results = re.sub(r'\n(Note|Please note|I hope|If you need).*?$', '', results, flags=re.MULTILINE|re.DOTALL)
    
    return results.strip()