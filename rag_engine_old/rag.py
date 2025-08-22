from typing import Tuple
from langchain_core.output_parsers import StrOutputParser
from configs.config import retriever, model, prompt
#from configs.config import LANGSMITH_TRACING, LANGSMITH_ENDPOINT, LANGSMITH_API_KEY, LANGSMITH_PROJECT


def format_docs(docs):
    """Format documents and extract metadata"""
    formatted_content = "\n\n".join(doc.page_content for doc in docs)
    resources = {
        doc.metadata["video_name"] 
        for doc in docs 
        if "video_name" in doc.metadata and doc.metadata["video_name"]
    }
    return formatted_content, resources

def create_qa_chain():
    """Create the QA chain (without retrieval)"""
    chain = (
        {
            "context": lambda x: x["context"],
            "question": lambda x: x["question"]
        }
        | prompt 
        | model 
        | StrOutputParser()
    )
    return chain

def rag_query(question: str) -> Tuple[str, str]:
    """
    Process a query through the RAG chain
    Returns: (response text, question)
    """
    # Step 1: Retrieval and formatting
    docs = retriever.invoke(question)
    context, resources = format_docs(docs)
    
    # Step 2: Question answering
    qa_chain = create_qa_chain()
    response = qa_chain.invoke({
        "context": context,
        "question": question
    })

    
    response +="""\n\nЕсли у Вас остались вопросы, мы можем обсудить эту тему на сессии или в личном разговоре.\n\nЧтобы записаться на сессию, введи команду /booking, либо для того чтобы задать вопрос, используй команду /help."""
    
    # Add sources if available
    #if resources:
    #    source_info = "\n\nИсточники:"
    #    for source in resources:
    #        source_info += f"\n- {source}"
    #    response += source_info
            
    return response, question