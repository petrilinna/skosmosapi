import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

FUSEKI_ENDPOINT = os.environ.get(
    "FUSEKI_ENDPOINT",
    "https://fuseki-skosmos.2.rahtiapp.fi/ds/sparql"
)

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

    SELECT DISTINCT ?uri ?label ?graph
    WHERE {{
      GRAPH ?graph {{
        ?uri skos:prefLabel ?label .
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
            "graph": row["graph"]["value"]
        })

    return jsonify(results)
