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
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    
    SELECT
      ?uri
      ?label
      ?label_language
      ?graph
      (SAMPLE(?definition) AS ?definition)
      (SAMPLE(?definition_language) AS ?definition_language)
    WHERE {{
      GRAPH ?graph {{
        ?uri skos:prefLabel ?label .
    
        FILTER(LANGMATCHES(LANG(?label), "en"))
    
        OPTIONAL {{
          ?uri skos:definition ?defNode .
    
          OPTIONAL {{
            ?defNode rdf:value ?defText .
            FILTER(LANGMATCHES(LANG(?defText), "en"))
          }}
    
          BIND(
            IF(
              isLiteral(?defNode) &&
              LANGMATCHES(LANG(?defNode), "en"),
              ?defNode,
              ?defText
            )
            AS ?definition
          )
    
          BIND(
            LANG(?definition)
            AS ?definition_language
          )
        }}
    
        BIND(
          LANG(?label)
          AS ?label_language
        )
    
        FILTER(
          CONTAINS(
            LCASE(STR(?label)),
            LCASE("{term}")
          )
        )
      }}
    }}
    GROUP BY
      ?uri
      ?label
      ?label_language
      ?graph
    LIMIT 50
    """
    
    response = requests.get(
        FUSEKI_ENDPOINT,
        params={"query": query},
        headers={"Accept": "application/sparql-results+json"},
        timeout=30
    )
    
    response.raise_for_status()
    
    data = response.json()
    results = []
    
    for row in data["results"]["bindings"]:
        item = {
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
        }
    
        term_lower = term.lower()
        label_lower = item["label"].lower()
    
        score = 0
        match_type = "partial"
    
        # Lexical match
        if label_lower == term_lower:
            score = 100
            match_type = "exact"
    
        elif label_lower.startswith(term_lower):
            score = 80
            match_type = "starts_with"
    
        elif term_lower in label_lower:
            score = 60
            match_type = "contains"
    
        # Vocabulary priority
        graph = item["graph"]
    
        if graph == "http://aims.fao.org/aos/agrovoc/":
            score += 10
    
        elif graph == "https://lod.nal.usda.gov/nalt":
            score += 5
    
        elif graph == "http://www.yso.fi/onto/yso":
            score += 2
    
        item["score"] = score
        item["match_type"] = match_type
    
        results.append(item)
    
    # Highest score first
    results.sort(
        key=lambda x: x["score"],
        reverse=True
    )
    
    return jsonify(results)


