"""TMDB helpers adapted from notebooks/Film_Assistant.ipynb."""

from __future__ import annotations

import json
import os
import urllib.parse

import requests

API_PREFIX = "https://api.themoviedb.org/3"


def _tmdb_api_key() -> str:
    key = os.getenv("TMDB_API_KEY")
    if not key:
        raise RuntimeError("TMDB_API_KEY is not set.")
    return key


def fetch(endpoint: str, params: dict | None = None) -> dict | None:
    params = params or {}
    url = f"{API_PREFIX}{endpoint}"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    try:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def search_movie_id_tmdb(movie_title: str) -> dict | None:
    search_results = fetch(
        "/search/movie",
        params={
            "api_key": _tmdb_api_key(),
            "query": movie_title,
            "include_adult": True,
        },
    )
    if search_results and search_results.get("results"):
        first_result = search_results["results"][0]
        release_date = first_result.get("release_date")
        year = release_date.split("-")[0] if release_date else ""
        return {
            "id": first_result.get("id"),
            "title": first_result.get("title"),
            "year": year,
            "original_title": first_result.get("original_title"),
        }
    return None


def get_movie_details_tmdb(movie_title: str) -> str:
    movie_search_info = search_movie_id_tmdb(movie_title)
    if not movie_search_info or not movie_search_info.get("id"):
        return json.dumps({"error": f"not found movie: {movie_title}"})

    movie_id = movie_search_info["id"]
    movie_details = fetch(
        f"/movie/{movie_id}",
        params={"api_key": _tmdb_api_key()},
    )
    if not movie_details:
        return json.dumps({"error": f"can't get information of film: {movie_title}"})

    title = movie_details.get("title")
    original_title = movie_details.get("original_title")
    release_date = movie_details.get("release_date")
    genres = ", ".join([g["name"] for g in movie_details.get("genres", [])])
    overview = movie_details.get("overview")
    vote_average = movie_details.get("vote_average")
    vote_count = movie_details.get("vote_count")
    runtime = movie_details.get("runtime")

    credits_data = fetch(
        f"/movie/{movie_id}/credits",
        params={"api_key": _tmdb_api_key()},
    )
    director = "Unknown"
    if credits_data and credits_data.get("crew"):
        for crew_member in credits_data["crew"]:
            if crew_member.get("job") == "Director":
                director = crew_member.get("name")
                break

    details_summary = f"film name: {title} ({original_title})\n"
    details_summary += f"director: {director}\n"
    details_summary += f"release date: {release_date}\n"
    details_summary += f"type: {genres}\n"
    if runtime:
        details_summary += f":runtime: {runtime} min\n"
    if vote_average and vote_count:
        details_summary += f"TMDB vote: {vote_average:.1f}/10 ({vote_count} 票)\n"
    details_summary += f"\nplot sommary:\n{overview}\n"
    return json.dumps({"details": details_summary})


TMDB_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_movie_details_tmdb",
        "description": (
            "Gets the details of the specified film, including director, starring actor, "
            "genre, synopsis, rating, and so on. If also need to discuss the details of a "
            "specific film, call this function to get the information."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "movie_title": {
                    "type": "string",
                    "description": "The name of the film for query film details.",
                }
            },
            "required": ["movie_title"],
        },
    },
}

AVAILABLE_FUNCTIONS = {
    "get_movie_details_tmdb": get_movie_details_tmdb,
}
