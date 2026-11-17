class MemoryImageCollection:
    """Doble de pruebas: no establece conexiones MongoDB."""
    def __init__(self):
        self.documents = {}

    def insert_one(self, document):
        self.documents[document['_id']] = document.copy()

    def find_one(self, query, projection=None):
        return self.documents.get(query['_id'])

    def delete_one(self, query):
        self.documents.pop(query['_id'], None)
