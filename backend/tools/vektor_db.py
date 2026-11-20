from pathlib import Path
from langchain_qdrant import QdrantVectorStore
from langchain_core.documents import Document
from langchain_huggingface.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import (
    UnstructuredWordDocumentLoader,
    PyPDFLoader,
    TextLoader,
    UnstructuredExcelLoader,
    CSVLoader,
    UnstructuredPowerPointLoader,
)
from langchain.tools import tool
from langchain_text_splitters import RecursiveCharacterTextSplitter

QDRANT_URL = "http://localhost:6333"

EMBEDDING_MODEL = "BAAI/bge-m3"

embeddings = HuggingFaceEmbeddings(
    model_name=EMBEDDING_MODEL
)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=100
)


def _read_file_documents(file_path: str):
    """
    Internal helper function for reading supported document files.
    Returns LangChain Document objects.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    file_type = path.suffix.lower()

    if file_type == ".txt":
        reader = TextLoader(
            file_path=str(path),
            encoding="utf-8"
        )

    elif file_type in [".doc", ".docx"]:
        reader = UnstructuredWordDocumentLoader(
            file_path=str(path)
        )

    elif file_type == ".pdf":
        reader = PyPDFLoader(
            file_path=str(path)
        )

    elif file_type in [".xls", ".xlsx"]:
        reader = UnstructuredExcelLoader(
            file_path=str(path)
        )

    elif file_type == ".csv":
        reader = CSVLoader(
            file_path=str(path),
            encoding="utf-8"
        )

    elif file_type in [".ppt", ".pptx"]:
        reader = UnstructuredPowerPointLoader(
            file_path=str(path)
        )

    else:
        raise ValueError(
            f"Unsupported file format: {file_type}"
        )

    return reader.load()


def _get_vector_store(collection_name: str):
    """
    Internal helper function for connecting to an existing
    Qdrant collection.
    """

    return QdrantVectorStore.from_existing_collection(
        embedding=embeddings,
        collection_name=collection_name,
        url=QDRANT_URL
    )


@tool()
def file_reader(file_path: str):
    """
    Read and extract text content from a document file.

    This tool opens a document and extracts its textual content.
    It allows the AI agent to read, understand, analyze, summarize,
    and answer questions about the information stored inside files.

    Supported file formats:
    - PDF: .pdf
    - Microsoft Word: .doc, .docx
    - Microsoft Excel: .xls, .xlsx
    - CSV: .csv
    - Microsoft PowerPoint: .ppt, .pptx
    - Plain text: .txt

    When to use this tool:
    - When the user asks to read a document.
    - When the user wants to summarize a file.
    - When the agent needs to extract information from a document.
    - When the user asks questions about file contents.
    - When document content needs to be prepared for a RAG system.

    Args:
        file_path (str): The absolute or relative path of the file.
            The file must exist and have a supported extension.

    Returns:
        list[Document]: Extracted document content with metadata
            such as source file and page information when available.

        dict: An error message if the file cannot be read.

    Important:
        Always provide the actual file path.
        Do not provide only a filename unless it exists in
        the current working directory.
    """

    try:
        documents = _read_file_documents(file_path)

        return documents

    except Exception as e:
        return {
            "error": str(e)
        }


@tool()
def saved_doc_vector_db(
        file_path: str,
        collection_name: str
):
    """
    Read a document, split its content into smaller text chunks,
    generate vector embeddings, and store them in a Qdrant
    vector database collection.

    This tool creates or populates a RAG knowledge base from
    supported documents.

    Processing steps:
    1. Read the document using the internal file reader.
    2. Split the extracted content into smaller chunks.
    3. Use RecursiveCharacterTextSplitter with chunk_size=500
       and chunk_overlap=100.
    4. Generate embeddings using the BAAI/bge-m3 model.
    5. Connect to the Qdrant vector database.
    6. Store document chunks, embeddings, and metadata
       in the specified collection.

    When to use this tool:
    - When the user wants to upload a document into a RAG system.
    - When a new document needs to be indexed.
    - When creating a searchable knowledge base.
    - When document information needs to be stored for future
      semantic retrieval.
    - When preparing PDF, Word, Excel, CSV, PowerPoint,
      or TXT documents for vector search.

    Args:
        file_path (str): The absolute or relative path of the
            document that needs to be processed.

        collection_name (str): The name of the Qdrant collection
            where the document chunks and embeddings will be stored.

    Returns:
        dict: A dictionary containing:
            - message: A success or error message.
            - collection_name: The name of the target collection.
            - total_chunks: The number of document chunks stored.
            - source: The original document path.

    Important:
        Use a meaningful collection name.
        Remember the collection_name because the same collection
        must be used when searching for the stored information.

        This tool stores document content in Qdrant.
        Do not use it when the user only wants to read a file
        without saving it into a vector database.
    """

    try:
        documents = _read_file_documents(file_path)

        if not documents:
            return {
                "message": "No document content was found.",
                "collection_name": collection_name
            }

        split_documents = splitter.split_documents(documents)

        if not split_documents:
            return {
                "message": "Document splitting returned no chunks.",
                "collection_name": collection_name
            }

        QdrantVectorStore.from_documents(
            embedding=embeddings,
            documents=split_documents,
            url=QDRANT_URL,
            collection_name=collection_name
        )

        return {
            "message": "Successfully saved document vectors to Qdrant.",
            "collection_name": collection_name,
            "total_chunks": len(split_documents),
            "source": file_path
        }

    except Exception as e:
        return {
            "message": "Failed to save document to Qdrant.",
            "error": str(e)
        }


@tool()
def search_vc_db_smiltary_search(
        query: str,
        k: int,
        collection_name: str
):
    """
    Search for semantically similar document chunks inside
    an existing Qdrant vector database collection.

    This tool converts the user's query into an embedding
    and compares it with stored document embeddings.

    It retrieves the top K most similar document chunks
    based on semantic meaning rather than exact keyword matching.

    When to use this tool:
    - When the user asks questions about indexed documents.
    - When retrieving relevant context for a RAG application.
    - When searching for information based on semantic meaning.
    - When the agent needs the most similar document chunks.
    - When similarity scores are not required.

    Args:
        query (str): The user's question or search text.
            It will be converted into an embedding.

        k (int): The maximum number of document chunks to retrieve.
            For example, k=5 retrieves up to five matching chunks.

        collection_name (str): The name of the existing Qdrant
            collection containing document embeddings.

    Returns:
        dict: A dictionary containing:
            - results: A list of LangChain Document objects.
              Each document contains retrieved text and metadata.

        dict: An error message if the search operation fails.

    Important:
        Use the same collection_name that was used when
        storing the documents.

        This method returns documents without similarity scores.
        Use search_vc_db_similtary_search_score when scores
        are also needed.
    """

    try:
        vector_db = _get_vector_store(collection_name)

        result = vector_db.similarity_search(
            query=query,
            k=k
        )

        return {
            "results": result
        }

    except Exception as e:
        return {
            "error": str(e)
        }


@tool()
def search_vc_db_similtary_search_score(
        query: str,
        k: int,
        collection_name: str,
        score: float
):
    """
    Search for semantically similar document chunks in Qdrant
    and return both the retrieved documents and their similarity scores.

    This tool uses similarity_search_with_score to retrieve
    matching document chunks together with their scores.

    It helps the AI agent evaluate how closely retrieved documents
    match the user's search query.

    When to use this tool:
    - When the agent needs similarity scores.
    - When evaluating document relevance.
    - When retrieving context for RAG with score information.
    - When comparing the matching strength of retrieved documents.
    - When score-based filtering is required.

    Args:
        query (str): The user's question or search text.

        k (int): The maximum number of document chunks to retrieve.

        collection_name (str): The existing Qdrant collection
            containing indexed document vectors.

        score (float): The similarity score threshold.
            Only results satisfying the configured Qdrant
            score threshold are returned.

    Returns:
        dict: A dictionary containing:
            - results: A list of tuples containing Document objects
              and their corresponding similarity scores.

        dict: An error message if the search operation fails.

    Important:
        The score interpretation depends on the configured
        Qdrant distance metric.

        Do not assume that a higher score always means a better match.
        For cosine similarity, higher scores generally indicate
        greater similarity.
    """

    try:
        vector_db = _get_vector_store(collection_name)

        result = vector_db.similarity_search_with_score(
            query=query,
            k=k,
            score_threshold=score
        )

        return {
            "results": result
        }

    except Exception as e:
        return {
            "error": str(e)
        }


@tool()
def search_vector_db(
        query: str,
        k: int,
        collection_name: str,
        search_type: str,
        score: float
):
    """
    Perform a configurable search operation in a Qdrant vector
    database using LangChain's search interface.

    This tool allows the AI agent to select a retrieval strategy
    according to the user's search requirements.

    Supported search types:

    1. similarity:
       Retrieves the most semantically similar document chunks.
       Use this when ordinary semantic search is required.

    2. similarity_score_threshold:
       Retrieves relevant documents while applying a minimum
       similarity score threshold.
       Use this when low-relevance results should be excluded.

    3. mmr:
       Maximum Marginal Relevance search.
       Retrieves relevant but less repetitive document chunks.
       Use this when diverse information is more important
       than returning several nearly identical chunks.

    When to use this tool:
    - When the agent needs to choose a search strategy dynamically.
    - When ordinary similarity search is insufficient.
    - When diverse results are required.
    - When relevance threshold filtering is needed.
    - When implementing flexible RAG retrieval.

    Args:
        query (str): The user's search question or text.

        k (int): The maximum number of document chunks to retrieve.

        collection_name (str): The existing Qdrant collection
            containing the indexed document embeddings.

        search_type (str): The retrieval strategy.
            Allowed values:
            - similarity
            - similarity_score_threshold
            - mmr

        score (float): The score threshold used by the
            similarity_score_threshold strategy.
            It is not used by ordinary similarity or MMR search.

    Returns:
        dict: A dictionary containing:
            - results: The retrieved document results.

        dict: An error message if the search operation fails.

    Important:
        Choose the search_type according to the retrieval objective.

        Use similarity for ordinary semantic retrieval.
        Use similarity_score_threshold to filter by relevance.
        Use mmr to retrieve more diverse and less repetitive results.

        The score parameter only applies to search types
        that support score_threshold.
    """

    try:
        vector_db = _get_vector_store(collection_name)

        search_kwargs = {
            "query": query,
            "search_type": search_type,
            "k": k
        }

        if search_type == "similarity_score_threshold":
            search_kwargs["score_threshold"] = score

        elif search_type == "mmr":
            search_kwargs["fetch_k"] = max(k * 4, 20)

        elif search_type != "similarity":
            return {
                "error": (
                    "Unsupported search_type. "
                    "Use similarity, similarity_score_threshold, or mmr."
                )
            }

        result = vector_db.search(**search_kwargs)

        return {
            "results": result,
            "search_type": search_type
        }

    except Exception as e:
        return {
            "error": str(e)
        }


@tool()
async def search_vectior_db_asinxron(
        query: str,
        k: int,
        collection_name: str,
        search_type: str,
        score: float
):
    """
    Perform an asynchronous configurable search operation
    in a Qdrant vector database using LangChain's asearch method.

    This tool is designed for asynchronous RAG applications.
    It allows the event loop to perform other asynchronous tasks
    while waiting for the vector database search operation.

    Supported search types:

    1. similarity:
       Retrieves the most semantically similar document chunks.

    2. similarity_score_threshold:
       Retrieves relevant documents using a score threshold.

    3. mmr:
       Maximum Marginal Relevance search.
       Retrieves relevant and diverse document chunks.

    When to use this tool:
    - When working with asynchronous AI agents.
    - When multiple independent vector searches need to run concurrently.
    - When building asynchronous FastAPI endpoints.
    - When implementing parallel document retrieval.
    - When the application needs non-blocking database operations.

    Args:
        query (str): The user's question or search text.

        k (int): The maximum number of document chunks to retrieve.

        collection_name (str): The existing Qdrant collection
            containing indexed document embeddings.

        search_type (str): The retrieval strategy.
            Allowed values:
            - similarity
            - similarity_score_threshold
            - mmr

        score (float): The score threshold for
            similarity_score_threshold search.
            It is not used by ordinary similarity or MMR search.

    Returns:
        dict: A dictionary containing:
            - results: The retrieved document chunks.
            - search_type: The selected search strategy.

        dict: An error message if asynchronous retrieval fails.

    Important:
        This tool uses the asynchronous asearch interface.

        Use it inside an asynchronous application.
        Await the operation when calling it directly from Python.

        Asynchronous execution is especially useful when
        database operations involve network waiting time.
    """

    try:
        vector_db = _get_vector_store(collection_name)

        search_kwargs = {
            "query": query,
            "search_type": search_type,
            "k": k
        }

        if search_type == "similarity_score_threshold":
            search_kwargs["score_threshold"] = score

        elif search_type == "mmr":
            search_kwargs["fetch_k"] = max(k * 4, 20)

        elif search_type != "similarity":
            return {
                "error": (
                    "Unsupported search_type. "
                    "Use similarity, similarity_score_threshold, or mmr."
                )
            }

        result = await vector_db.asearch(**search_kwargs)

        return {
            "results": result,
            "search_type": search_type
        }

    except Exception as e:
        return {
            "error": str(e)
        }


@tool()
async def search_vector_db_similtary_asinxron(
        collection_name: str,
        query: str,
        k: int
):
    """
    Perform an asynchronous semantic similarity search
    in an existing Qdrant vector database collection.

    This tool uses LangChain's asimilarity_search method
    to retrieve the top K most semantically similar document chunks.

    It converts the user's query into an embedding and compares
    it with the stored document vectors.

    The operation is asynchronous and allows the application
    to perform other asynchronous tasks while waiting for
    the search operation to complete.

    When to use this tool:
    - When an asynchronous agent needs document retrieval.
    - When building asynchronous RAG applications.
    - When multiple independent searches need to run concurrently.
    - When implementing asynchronous FastAPI or LangGraph workflows.
    - When similarity scores are not required.

    Args:
        collection_name (str): The existing Qdrant collection
            containing document embeddings.

        query (str): The user's question or search text.

        k (int): The maximum number of similar document chunks
            to retrieve.

    Returns:
        dict: A dictionary containing:
            - results: A list of LangChain Document objects
              containing retrieved text and metadata.

        dict: An error message if the asynchronous search fails.

    Important:
        This tool returns documents without similarity scores.

        Use search_vector_db_similtary_asinxron_score when
        similarity scores are also required.

        Await this operation when calling it directly
        from Python asynchronous code.
    """

    try:
        vector_db = _get_vector_store(collection_name)

        result = await vector_db.asimilarity_search(
            query=query,
            k=k
        )

        return {
            "results": result
        }

    except Exception as e:
        return {
            "error": str(e)
        }


@tool()
async def search_vector_db_similtary_asinxron_score(
        collection_name: str,
        query: str,
        k: int,
        score: float
):
    """
    Perform an asynchronous semantic similarity search
    in a Qdrant vector database and return retrieved documents
    together with their similarity scores.

    This tool uses LangChain's asimilarity_search_with_score method.

    It allows an asynchronous RAG agent to retrieve relevant
    document chunks and evaluate their similarity to the query.

    When to use this tool:
    - When asynchronous document retrieval requires similarity scores.
    - When evaluating relevance in an asynchronous RAG system.
    - When comparing the similarity of retrieved document chunks.
    - When implementing parallel vector database searches.
    - When low-relevance results should be filtered using a threshold.

    Args:
        collection_name (str): The existing Qdrant collection
            containing indexed document embeddings.

        query (str): The user's question or search text.

        k (int): The maximum number of document chunks to retrieve.

        score (float): The similarity score threshold used
            to filter search results. Its interpretation depends
            on the configured Qdrant distance metric.

    Returns:
        dict: A dictionary containing:
            - results: A list of tuples containing Document objects
              and their corresponding similarity scores.

        dict: An error message if the asynchronous search fails.

    Important:
        This tool returns both documents and their similarity scores.

        Use it when relevance evaluation is required
        in an asynchronous RAG workflow.

        Await this operation when calling it directly
        from Python asynchronous code.
    """

    try:
        vector_db = _get_vector_store(collection_name)

        result = await vector_db.asimilarity_search_with_score(
            query=query,
            k=k,
            score_threshold=score
        )

        return {
            "results": result
        }

    except Exception as e:
        return {
            "error": str(e)
        }


def saved_text_vector_db(text: str, metadate: dict | None, collection_name: str):
    """    Save plain text information directly into a Qdrant vector database.

    This tool stores text without requiring a PDF, Word, Excel,
    PowerPoint, or any other document file.

    It converts the provided text into vector embeddings using
    the configured embedding model and saves the text, vector,
    and optional metadata in the specified Qdrant collection.

    When to use this tool:
    - When the user wants to save a simple text or sentence.
    - When the user provides information that should be remembered
      and retrieved later through semantic search.
    - When storing question-answer pairs.
    - When adding facts, notes, descriptions, or knowledge
      directly to a RAG knowledge base.
    - When the information does not exist in a document file.

    Args:
        text (str): The actual text or information that needs
            to be stored in the vector database.

        collection_name (str): The name of the Qdrant collection
            where the text and its embedding will be saved.

        metadata (dict, optional): Additional information about
            the text, such as category, topic, author, date,
            source, or document type.

    Returns:
        dict: A dictionary containing the storage status,
        collection name, and stored text information.

    Important:
        Use this tool when storing individual text information
        without uploading a document file.
        Use the same collection name later when searching
        for this information.
        """
    try:
        doc = Document(
            page_content=text,
            metadate=metadate or {}
        )
        vector_db = QdrantVectorStore.from_documents(
            documents=[doc],
            collection_name=collection_name,
            url=QDRANT_URL,
            embedding=embeddings
        )
        return {"message": "Successfully saved text information", "collection": collection_name, "text": text}

    except Exception as e:
        return {"error": str(e)}


def delete_vector_db_collection_name(collection_name: str):
    """
    Delete the Qdrant collection name.
    :param collection_name:
    :return:
    """
    try:
        vector_db = QdrantVectorStore.from_existing_collection(
            embedding=embeddings,
            url=QDRANT_URL,
            collection_name=collection_name
        )
        vector_db.client.delete_collection(collection_name=collection_name)
        return {"message": "Successfully deleted Qdrant collection name", "collection": collection_name}
    except Exception as e:
        return {"error": str(e)}


def get_all_collections(collection_name: str):
    """
    Get all Qdrant collection names.
    :param collection_name:
    :return:
    """
    try:
        vector_db = QdrantVectorStore.from_existing_collection(
            embedding=embeddings,
            url=QDRANT_URL,
            collection_name=collection_name

        )
        all_collections = vector_db.client.get_collections()
        return {"collections": all_collections}
    except Exception as e:
        return {"error": str(e)}


RAG_TOOLS = [
    file_reader,
    delete_vector_db_collection_name,
    get_all_collections,
    saved_text_vector_db,
    saved_doc_vector_db,
    search_vc_db_smiltary_search,
    search_vc_db_similtary_search_score,
    search_vector_db,
    search_vectior_db_asinxron,
    search_vector_db_similtary_asinxron,
    search_vector_db_similtary_asinxron_score
]
