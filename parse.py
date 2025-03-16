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
5. If creating a table or list, ensure it's properly formatted
6. For technical content, maintain accuracy of numbers, code, and technical details
7. If the request is ambiguous, interpret it in the most reasonable way based on the content
8. If the content is promotional or marketing text, extract factual elements rather than claims
9. For dates, names, and other specific identifiers, match the exact format from the text
10. Always respond with something useful, even if you need to be creative with limited content
"""

def initialize_model(model_name="llama3.2"):
    """Initialize the Ollama model with the given name."""
    try:
        # Use specific base URL and timeout values
        ollama = OllamaLLM(
            model=model_name,
            base_url="http://localhost:11434",  # Default Ollama URL
            temperature=0.1,  # Low temperature for more factual responses
            timeout=60,  # Increased timeout for larger documents
            num_ctx=4096  # Increase context window
        )
        
        # Test the connection with a simple request
        test_result = ollama.invoke("test connection")
        print(f"Ollama connection successful using model: {model_name}")
        return ollama
    except Exception as e:
        print(f"Error initializing Ollama model '{model_name}': {e}")
        print("Falling back to default model")
        try:
            # Try one more time with the default model
            return OllamaLLM(
                model="llama3",
                base_url="http://localhost:11434",
                temperature=0.1
            )
        except Exception as fallback_error:
            print(f"Critical error connecting to Ollama: {fallback_error}")
            raise ValueError(f"Cannot connect to Ollama. Make sure it's running with 'ollama serve' command. Error: {fallback_error}")

def parse_with_ollama(text_chunks, parse_description, model_name="llama3.2"):
    """Parse text content using Ollama LLM."""
    print(f"Initializing Ollama with model: {model_name}")
    
    # Data validation
    if not text_chunks or len(text_chunks) == 0:
        print("Error: No text chunks provided")
        return "No content to parse. Please scrape a website first."
    
    # Print what we're trying to parse
    print(f"Parse request: '{parse_description}'")
    print(f"Number of text chunks: {len(text_chunks)}")
    print(f"Size of first chunk: {len(text_chunks[0]) if text_chunks else 0} chars")
    
    # Check if any chunks have content
    valid_chunks = [chunk for chunk in text_chunks if chunk and len(chunk.strip()) > 50]
    if not valid_chunks:
        print("Error: No valid content in text chunks")
        return "No significant content found. Please try scraping a different website."
    
    # Initialize model just once
    try:
        model = initialize_model(model_name)
    except Exception as e:
        print(f"Critical error initializing Ollama model: {e}")
        return f"Error connecting to Ollama: {str(e)}. Make sure Ollama is running with 'ollama serve' command."
    
    # Create prompt template and chain
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | model
    
    parsed_results = []
    
    # Process each chunk
    total_chunks = len(valid_chunks)
    print(f"Processing {total_chunks} valid text chunks")
    
    # If there are too many chunks, only process the first few
    if total_chunks > 3:
        print(f"Limiting processing to first 3 of {total_chunks} chunks for efficiency")
        processing_chunks = valid_chunks[:3]
    else:
        processing_chunks = valid_chunks
    
    # Process a single larger chunk first if content isn't too big
    if total_chunks > 0 and len(" ".join(valid_chunks[:2])) < 8000:
        try:
            print("Attempting to process combined chunks for better context...")
            combined_text = " ".join(valid_chunks[:2])
            cleaned_combined = clean_text_chunk(combined_text)
            print(f"Processing combined chunk (size: {len(cleaned_combined)} chars)")
            
            response = chain.invoke({
                "text_content": cleaned_combined,
                "parse_description": parse_description
            })
            
            if response and len(response.strip()) > 0:
                print("Successfully parsed combined chunk")
                return clean_parsed_results(response)
        except Exception as e:
            print(f"Error processing combined chunk: {e}")
            print("Falling back to individual chunk processing...")
    
    # Process individual chunks if combined approach didn't work
    for i, chunk in enumerate(processing_chunks, start=1):
        try:
            # Clean and trim the chunk for faster processing
            cleaned_chunk = clean_text_chunk(chunk)
            
            if not cleaned_chunk or len(cleaned_chunk) < 50:
                print(f"Skipping chunk {i} - too short after cleaning")
                continue
                
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
        print("No results from any chunks - falling back to direct processing")
        # Try once more with a single concatenated chunk (limited size)
        try:
            all_text = " ".join(chunk for chunk in valid_chunks)
            # Limit to 8000 chars (from start and end) to avoid LLM token limits
            if len(all_text) > 8000:
                print(f"Text too long ({len(all_text)} chars), trimming to 8000 chars")
                all_text = all_text[:4000] + "..." + all_text[-4000:]
            
            response = chain.invoke({
                "text_content": all_text,
                "parse_description": parse_description
            })
            
            if response and len(response.strip()) > 0:
                return clean_parsed_results(response)
        except Exception as e:
            print(f"Error in fallback parsing: {e}")
        
        # Final fallback: just return a generic extraction with the most common topics
        try:
            print("Using final fallback extraction method")
            simple_extraction = extract_common_topics(valid_chunks[0], parse_description)
            if simple_extraction:
                return simple_extraction
        except Exception as e:
            print(f"Error in simple extraction: {e}")
        
        return "No relevant information found in the content that matches your request. Try a different query or website."
    
    # Combine and clean results
    combined_results = "\n\n".join(parsed_results)
    cleaned_results = clean_parsed_results(combined_results)
    
    return cleaned_results

def extract_common_topics(text, query):
    """Extract basic information as a fallback when Ollama fails"""
    import re
    
    # Very basic extraction of common elements
    results = []
    
    # Look for potential skill lists if query mentions skills
    if "skill" in query.lower():
        skills = []
        # Look for skills in bullet points
        bullet_matches = re.findall(r'[•\-\*]\s*([A-Za-z0-9][\w\s,&\-\+]+)', text)
        for match in bullet_matches:
            if len(match.strip()) > 3 and len(match.strip()) < 50:
                skills.append(match.strip())
        
        # Look for words that might be skills
        skill_words = [
            "Python", "JavaScript", "HTML", "CSS", "Java", "C\\+\\+", "React", 
            "Node", "SQL", "Database", "API", "Cloud", "AWS", "Azure", "Docker",
            "Kubernetes", "DevOps", "Machine Learning", "AI", "Data Science",
            "Leadership", "Management", "Communication", "Teamwork", "Problem Solving"
        ]
        
        for skill in skill_words:
            if re.search(r'\b' + skill + r'\b', text, re.IGNORECASE):
                if skill not in skills:
                    skills.append(skill)
        
        if skills:
            results.append("## Skills\n" + "\n".join([f"- {skill}" for skill in skills[:10]]))
    
    # Look for contact information if query mentions contact
    if "contact" in query.lower():
        # Find email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        if email_match:
            results.append(f"## Contact\nEmail: {email_match.group(0)}")
        
        # Find phone number
        phone_match = re.search(r'\b(\+\d{1,2}\s)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b', text)
        if phone_match:
            if not results:
                results.append("## Contact")
            results[-1] += f"\nPhone: {phone_match.group(0)}"
    
    # If query mentions table, create a simple table with whatever we found
    if "table" in query.lower() and results:
        table_content = "| Category | Details |\n| --- | --- |\n"
        for result in results:
            parts = result.split("\n", 1)
            if len(parts) > 1:
                category = parts[0].replace("##", "").strip()
                details = parts[1].replace("\n", "<br>")
                table_content += f"| {category} | {details} |\n"
        
        if table_content != "| Category | Details |\n| --- | --- |\n":
            return table_content
    
    if results:
        return "\n\n".join(results)
    
    # Generic fallback if nothing else worked
    return None

def clean_text_chunk(chunk):
    """Clean a text chunk to make it more processable by the LLM."""
    # Sanity check
    if not chunk or not isinstance(chunk, str):
        return ""
    
    # First trim excessively long chunks
    if len(chunk) > 5000:
        chunk = chunk[:5000]
    
    # Remove excessive whitespace to speed up processing
    chunk = re.sub(r'\s+', ' ', chunk)
    
    # Remove any remaining HTML tags
    chunk = re.sub(r'<[^>]*>', '', chunk)
    
    # Clean up unicode characters
    chunk = chunk.replace('\u00a0', ' ')
    
    # Remove multiple spaces
    chunk = re.sub(r' {2,}', ' ', chunk)
    
    # Remove multiple newlines
    chunk = re.sub(r'\n{2,}', '\n\n', chunk)
    
    # Remove very short lines that are likely navigation items
    lines = chunk.split('\n')
    lines = [line for line in lines if len(line.strip()) > 3]
    chunk = '\n'.join(lines)
    
    # Ensure it's returned as a string
    return chunk.strip()

def clean_parsed_results(results):
    """Clean up and format the parsed results."""
    # Sanity check
    if not results or not isinstance(results, str):
        return "No results found."
    
    # Remove repeated "```" blocks that aren't part of code blocks
    results = re.sub(r'```\s*```', '', results)
    
    # Remove any starting meta-commentary
    results = re.sub(r'^(I found|Here is|The extracted|Based on the content).*?:\s*', '', results, flags=re.MULTILINE)
    
    # Remove any trailing instructions or explanations
    results = re.sub(r'\n(Note|Please note|I hope|If you need).*?$', '', results, flags=re.MULTILINE|re.DOTALL)
    
    # Preserve markdown tables and lists
    # Make sure there's a newline before and after tables
    results = re.sub(r'([^\n])\n\|', r'\1\n\n|', results)
    results = re.sub(r'\|\n([^\|])', r'|\n\n\1', results)
    
    # Ensure proper spacing for lists
    results = re.sub(r'([^\n])\n(\d+\.|\*|\-)', r'\1\n\n\2', results)
    
    # Fix any doubled markdown formatting
    results = re.sub(r'\*\*\*\*', '**', results)
    results = re.sub(r'____', '__', results)
    
    return results.strip()