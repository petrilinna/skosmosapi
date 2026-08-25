import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

FUSEKI_ENDPOINT = os.environ.get(
    "FUSEKI_ENDPOINT",
    "https://fuseki-skosmos.2.rahtiapp.fi/ds/sparql"
)

@app.get("/")
def root():
    return {
        "service": "Skosmos API",
        "version": "1.0",
        "endpoints": [
            "/health",
            "/search?term=wheat"
        ]
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/search")
def search():
    term = request.args.get("term", "").strip()

    if not term:
        return jsonify({"error": "Missing required query parameter: term"}), 400

    query = f"""
    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
    PREFIX dct: <http://purl.org/dc/terms/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

    SELECT DISTINCT
      ?uri
      ?label
      ?label_language
      ?graph
      ?definition
      ?definition_language
    WHERE {{
      GRAPH ?graph {{
        ?uri skos:prefLabel ?label .

        OPTIONAL {{
          ?uri skos:definition ?def1 .
        }}

        OPTIONAL {{
          ?uri skos:scopeNote ?def2 .
        }}

        OPTIONAL {{
          ?uri dct:description ?def3 .
        }}

        OPTIONAL {{
          ?uri rdfs:comment ?def4 .
        }}

        BIND(LANG(?label) AS ?label_language)
        BIND(COALESCE(?def1, ?def2, ?def3, ?def4) AS ?definition)
        BIND(LANG(?definition) AS ?definition_language)

        FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{term}")))
      }}
    }}
    LIMIT 50
    """

    r = requests.get(
        FUSEKI_ENDPOINT,
        params={"query": query},
        headers={"Accept": "application/sparql-results+json"},
        timeout=30
    )
    r.raise_for_status()

    data = r.json()
    results = []

    for row in data["results"]["bindings"]:
        results.append({
            "uri": row["uri"]["value"],
            "label": row["label"]["value"],
            "label_language": row.get(
                "label_language", {}
            ).get("value"),
            "graph": row["graph"]["value"],
            "definition": row.get(
                "definition", {}
            ).get("value"),
            "definition_language": row.get(
                "definition_language", {}
            ).get("value")
        })

    return jsonify(results)
