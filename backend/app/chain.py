import logging

from langchain_cohere import ChatCohere
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.config import settings

logger = logging.getLogger(__name__)


# This is the prompt template that gets sent to the LLM.
# {context} = the reranked chunks
# {question} = the user's question
# These placeholders get filled in at runtime
PROMPT_TEMPLATE = ChatPromptTemplate.from_messages([
    ("system", """You are an expert research paper assistant. Answer questions using the provided context chunks from academic papers.

Rules:
- Read ALL chunks carefully before answering.
- If the answer is partially in the context, give the partial answer and note what is missing — do not say you have no information.
- Be specific — use exact numbers, terms, and formulas from the context.
- If a number, dataset, or fact is mentioned anywhere in the chunks, use it in your answer even if it is not in a dedicated section.
- Always mention which paper the information comes from.
- Only say you cannot answer if the topic is completely absent from all provided chunks."""),
    ("human", """Context from research papers:
{context}

Question: {question}

Answer:""")
])


def format_context(documents: list[Document]) -> str:
    """
    Converts a list of Document chunks into a single
    formatted string that gets inserted into the prompt.

    Each chunk is labelled with its source filename
    so the LLM can cite where the information came from.
    """
    if not documents:
        return "No relevant context found."

    formatted_chunks = []
    for i, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source", "unknown")
        formatted_chunks.append(
            f"[Chunk {i} from {source}]\n{doc.page_content}"
        )

    # Join all chunks with a separator
    return "\n\n---\n\n".join(formatted_chunks)


def generate_answer(
    query: str,
    documents: list[Document]
) -> dict:
    """
    Takes reranked documents and generates a final answer.

    Args:
        query:     The user's question
        documents: Reranked relevant chunks

    Returns:
        Dictionary with answer and source information
    """
    logger.info(f"Generating answer for: {query[:50]}...")

    # Step 1: Format chunks into context string
    context = format_context(documents)

    # Step 2: Initialize the LLM
    llm = ChatCohere(
        model=settings.chat_model,
        cohere_api_key=settings.cohere_api_key,
        temperature=0.1,  # low temperature = more factual, less creative
    )

    # Step 3: Build the chain
    # This is LangChain's pipe operator |
    # It means: prompt → llm → parse output as string
    chain = PROMPT_TEMPLATE | llm | StrOutputParser()

    # Step 4: Run the chain
    answer = chain.invoke({
        "context": context,
        "question": query
    })

    logger.info("Answer generated successfully")

    # Step 5: Extract source information for the response
    sources = []
    for doc in documents:
        source = doc.metadata.get("source", "unknown")
        score = doc.metadata.get("relevance_score", 0.0)
        if source not in [s["filename"] for s in sources]:
            sources.append({
                "filename": source,
                "relevance_score": round(float(score), 4)
            })

    return {
        "answer": answer,
        "sources": sources,
        "chunks_used": len(documents)
    }