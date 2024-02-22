from openai import OpenAI
import tiktoken
import os
from pinecone import Pinecone, ServerlessSpec
from decouple import config
from lesson_plans.models import Persona, Philosophy, Voice, Tone, OutputFormat, PineconeDocument, Tag

# Load API keys from environment
OPENAI_API_KEY = config('OPENAI_API_KEY')
PINECONE_KEY = config('PINECONE_API_KEY')
PINECONE_ENV = os.getenv("yourpeak-gpt", "us-east-1")
PINECONE_INDEX = "yourpeak-gpt"

# Initialize OpenAI client
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_KEY)

# Create index if it doesn't exist
if PINECONE_INDEX not in pc.list_indexes().names():
    pc.create_index(
        name=PINECONE_INDEX,
        dimension=3072,
        metric='cosine',
        spec=ServerlessSpec(cloud='aws', region='us-east-1')
    )
index = pc.Index(PINECONE_INDEX)

# Get tokenizer for the model
tokenizer = tiktoken.encoding_for_model("text-embedding-3-large")

def chunk_text(text, max_tokens=500):
    tokens = tokenizer.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + max_tokens, len(tokens))
        chunk = tokens[start:end]
        chunks.append(tokenizer.decode(chunk))
        start = end
    return chunks

def embed_text_chunks(chunks):
    embeddings = []
    for chunk in chunks:
        response = openai_client.embeddings.create(
            model="text-embedding-3-large",
            input=chunk
        )
        embedding = response.data[0].embedding
        embeddings.append((chunk, embedding))
    return embeddings

def store_document_in_pinecone(document):
    text = document.content
    chunks = chunk_text(text)

    try:
        embedded_chunks = embed_text_chunks(chunks)
    except Exception as e:
        raise

    tags = [tag.name for tag in document.tags.all()]
    vector_ids = []  # ✅ Track uploaded vector IDs

    for i, (chunk, embedding) in enumerate(embedded_chunks):
        vector_id = f"{document.id}-{i}"
        vector_ids.append(vector_id)  # ✅ Store it

        try:
            print("Uploading document:", document.title)
            index.upsert(vectors=[{
                "id": vector_id,
                "values": embedding,
                "metadata": {
                    "document_id": str(document.id),
                    "document_title": document.title,
                    "chunk_index": i,
                    "tags": tags,
                    "text": chunk
                }
            }])
        except Exception as e:
            raise

    # ✅ Save metadata locally
    PineconeDocument.objects.create(
        document=document,
        title=document.title,
        tag_names=tags,
        vector_ids=vector_ids,
        chunk_count=len(vector_ids)
    )



def extract_text_from_file(uploaded_file):
    name = uploaded_file.name
    ext = os.path.splitext(name)[-1].lower()

    if ext == '.txt':
        return uploaded_file.read().decode('utf-8', errors='ignore')

    elif ext == '.docx':
        import docx
        from io import BytesIO
        doc = docx.Document(BytesIO(uploaded_file.read()))
        return '\n'.join([p.text for p in doc.paragraphs])

    elif ext == '.pdf':
        import PyPDF2
        from io import BytesIO
        reader = PyPDF2.PdfReader(BytesIO(uploaded_file.read()))
        return "\n".join(page.extract_text() or '' for page in reader.pages)

    else:
        raise ValueError("Unsupported file type.")




def search_similar_chunks(query, top_k=5, use_gpt=False, model="gpt-4o-mini-2024-07-18", philosophy_ids=None, persona_ids=None, voice_id=None, tone_ids=None, outputformat_id=None):

    persona_ids = persona_ids or []
    philosophy_ids = philosophy_ids or []
    tone_ids = tone_ids or []


    system_message = """
    You are a deep-reasoning, high-clarity model.
    Your core behavior is to reason slowly, carefully, and systematically through all tasks and questions before producing any output.

    Thinking Process:
    • Before forming a response, conduct an internal structured reasoning chain.
    • Identify all key variables, relationships, assumptions, and potential edge cases.
    • Examine possible ambiguities or missing information without rushing to fill gaps.
    • Cross-reference related concepts or principles when relevant to deepen your analysis.
    • Privately work through the logic step-by-step to reach the clearest, most defensible conclusion.

    Priorities:
    • Prioritize careful reasoning and depth of understanding over speed.
    • Avoid skipping critical steps in thought processes, even when tasks seem simple.
    • Prefer thorough internal evaluation before presenting final outputs.

    Output Style:
    • Remain neutral and flexible.
    • Output tone, style, structure, or brevity will be determined externally by user settings or instructions.
    • Do not modify your behavior based on stylistic preferences unless explicitly directed in the input.

    Final Mindset Reminder:
    You are optimized for maximum reasoning depth and precision.
    You act with deliberate, thoughtful intelligence in all tasks, modeling the behavior of the most careful and rigorous version of GPT-4.
    """.strip()

    query_embedding = embed_text_chunks([query])[0][1]

    search_results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        include_values=False
    )

    similar_chunks = [
        {
            "text": match["metadata"].get("text", "[NO TEXT FOUND]"),
            "score": match.get("score")
        }
        for match in search_results.get("matches", [])
    ]


    TOP_CHUNK_THRESHOLD_X = 0.65      
    MINIMAL_RELEVANCE_THRESHOLD_Z = 0.45 
    MIN_REQUIRED_CHUNKS_N = 2

    top_chunk_score = 0.0 
    number_of_chunks_above_Z = 0
    if similar_chunks:
        top_chunk_score = similar_chunks[0]["score"] 

        for chunk in similar_chunks:
            if chunk["score"] >= MINIMAL_RELEVANCE_THRESHOLD_Z:
                number_of_chunks_above_Z += 1

    # Step 4: Honest Mode – no strong matches based on Option B

    if not similar_chunks or \
       (top_chunk_score < TOP_CHUNK_THRESHOLD_X and \
        number_of_chunks_above_Z < MIN_REQUIRED_CHUNKS_N):
        return {
            "answer": "🤖 I have no information about this topic. Please try rephrasing your query or asking about a different topic. For best results, use more specific keywords related to lesson planning.",
            "chunks": []
        }

    if use_gpt:
        context = "\n\n".join([f"- {chunk['text']}" for chunk in similar_chunks])

        injected_texts = []

        def read_file(model_instance):
            try:
                with model_instance.file.open("r") as f:
                    return f.read().strip()
            except Exception as e:
                return ""

        for philosophy in Philosophy.objects.filter(id__in=philosophy_ids):
            injected_texts.append(f"[PHILOSOPHY]\n{read_file(philosophy)}")

        for persona in Persona.objects.filter(id__in=persona_ids):
            injected_texts.append(f"[PERSONA]\n{read_file(persona)}")

        if voice_id:
            injected_texts.append(f"[VOICE]\n{read_file(Voice.objects.get(id=voice_id))}")

        for tone in Tone.objects.filter(id__in=tone_ids):
            injected_texts.append(f"[TONE]\n{read_file(tone)}")

        if outputformat_id:
            injected_texts.append(f"[OUTPUTFORMAT]\n{read_file(OutputFormat.objects.get(id=outputformat_id))}")

        final_prompt = build_dynamic_prompt(user_query=query, context=context, injected_blocks="\n\n".join(injected_texts))

        try:
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": final_prompt.strip()}
                ],
                temperature=0.5,
                max_tokens=1000
            )
            answer = response.choices[0].message.content.strip()

            return {
                "answer": answer,
                "chunks": similar_chunks
            }

        except Exception as e:
            return {
                "answer": "⚠️ Sorry, I couldn't generate a refined response at the moment.",
                "chunks": similar_chunks
            }

    return similar_chunks


def build_dynamic_prompt(user_query: str, context: str, injected_blocks: str = "") -> str:
    lower_query = user_query.lower()
    format_keywords = ["slide", "quiz", "bullet", "assignment", "speaker note", "ppt", "presentation", "pdf", "format", "document", "lesson plan", "blog", "email" ,  "activity", "reflection", "ethical note", "detailed", "structured", "overview", "summary", "tone" , "voice", "formatting", "formatting hints"]

    if any(word in lower_query for word in format_keywords):
        # Let GPT follow user-specific formatting hints
        return f"""

{injected_blocks}
Use the context below to answer the user's query while maintaining the original topic. If the user mentions a specific tone or voice (e.g., 'in Zig Ziglar tone'), emulate that tone/style in your writing — **do not change the topic** to focus on the tone or person.

Respond in the structure or format the user has requested.

If the query is illogical, impossible, or out of domain, even if context is provided, respond with:
"I have no information about this topic. 🤖"

Avoid using any markdown formatting like **bold** or _italic_ in your response.


User query: {user_query}

Context:
{context}

Answer:"""

    return f"""
{injected_blocks}

You are an academic AI assistant that generates concise, well-structured lessons in well-structured format.
If the query is illogical, impossible, or out of domain, even if context is provided, respond with:
"I have no information about this topic. 🤖" else Create a lesson using this structure:

---
• Key Concept 1
• Key Concept 2
• Supporting Detail
• Real-World Application
• Bonus Insight or Caution

Wrap up with a brief summary.
Remove all markdown formatting like **bold** or _italic_ in the response

User topic: {user_query}

Context:
{context}

Answer:"""

# touched on 2025-06-13T18:50:08.928700Z
# touched on 2025-06-13T18:50:40.620329Z
# touched on 2025-06-13T18:50:49.332746Z