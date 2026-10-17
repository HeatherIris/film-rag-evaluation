"""Export the film knowledge graph to results/film_graph.ttl and run one sample SPARQL query."""

from __future__ import annotations

import re
import sys
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDFS, XSD

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.graph_build import build_triples  # noqa: E402

FILM = Namespace("http://example.org/film/")
REL = Namespace("http://example.org/film/rel/")
OUTPUT = ROOT / "results" / "film_graph.ttl"


def node(name: str) -> URIRef:
    return FILM[re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")]


def main() -> None:
    graph = Graph()
    graph.bind("film", FILM)
    graph.bind("rel", REL)
    triples = build_triples()
    for triple in triples:
        subject = node(triple.subject)
        graph.add((subject, RDFS.label, Literal(triple.subject)))
        if triple.predicate == "release_year":
            graph.add((subject, REL.release_year, Literal(triple.object, datatype=XSD.gYear)))
            continue
        obj = node(triple.object)
        graph.add((obj, RDFS.label, Literal(triple.object)))
        graph.add((subject, REL[triple.predicate], obj))

    OUTPUT.parent.mkdir(exist_ok=True)
    graph.serialize(OUTPUT, format="turtle")
    print(f"{len(triples)} source triples -> {len(graph)} RDF triples in {OUTPUT.relative_to(ROOT)}")

    query = """
        PREFIX rel: <http://example.org/film/rel/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?name WHERE {
            ?a rdfs:label "Stoker" ; rel:cinematography_by ?p .
            ?b rdfs:label "The Handmaiden" ; rel:cinematography_by ?p .
            ?p rdfs:label ?name .
        }
    """
    print("SPARQL: cinematographer of both Stoker and The Handmaiden ->")
    for row in graph.query(query):
        print(f"  {row.name}")


if __name__ == "__main__":
    main()
