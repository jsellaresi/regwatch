from langchain_community.document_loaders import PDFPlumberLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import PGVector

CONNECTION_STRING = "postgresql+psycopg2://user:pass@localhost/regwatch"


def ingest_regulation(pdf_path: str, regulation_name: str,
                      celex: str, source_url: str, version_date: str):
    loader = PDFPlumberLoader(pdf_path)
    raw_docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\nArtículo", "\nArticle", "\n\n", "\n"],
    )
    chunks = splitter.split_documents(raw_docs)

    for chunk in chunks:
        chunk.metadata.update({
            "regulation": regulation_name,
            "celex": celex,
            "source_url": source_url,
            "version_date": version_date,
            "language": "ES",
        })

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    PGVector.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name="regulations",
        connection_string=CONNECTION_STRING,
    )
    print(f"Ingestados {len(chunks)} chunks de {regulation_name} ({celex})")


def main():
    regulations = [
        ("data/CELEX_32016R0679_ES_TXT.pdf", "GDPR", "32016R0679",
         "https://eur-lex.europa.eu/legal-content/ES/TXT/PDF/?uri=CELEX:32016R0679", "2016-05-04"),
        ("data/CELEX_32014L0065_ES_TXT.pdf", "MiFID II", "32014L0065",
         "https://eur-lex.europa.eu/legal-content/ES/TXT/PDF/?uri=CELEX:32014L0065", "2014-05-15"),
        ("data/CELEX_32015L0849_ES_TXT.pdf", "4AMLD", "32015L0849",
         "https://eur-lex.europa.eu/legal-content/ES/TXT/PDF/?uri=CELEX:32015L0849", "2015-05-20"),
        ("data/CELEX_32018L0843_ES_TXT.pdf", "5AMLD", "32018L0843",
         "https://eur-lex.europa.eu/legal-content/ES/TXT/PDF/?uri=CELEX:32018L0843", "2018-05-30"),
        ("data/CELEX_32018L1673_ES_TXT.pdf", "6AMLD", "32018L1673",
         "https://eur-lex.europa.eu/legal-content/ES/TXT/PDF/?uri=CELEX:32018L1673", "2018-10-23"),
    ]
    for args in regulations:
        ingest_regulation(*args)


if __name__ == "__main__":
    main()
