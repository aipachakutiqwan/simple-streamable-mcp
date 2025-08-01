import os
import json
import logging
from typing import List

import arxiv
from mcp.server.fastmcp import FastMCP

from src.log_management.log_management import configure_logger


PAPER_DIR = "papers"
PAPER_INFO_FILE = "papers_info.json"
RUN_LOCALLY = (
    True if os.getenv("RUN_LOCALLY", "True") in [True, "true", "True"] else False
)
if RUN_LOCALLY:
    mcp = FastMCP("research")
else:
    mcp = FastMCP("research", port=int(os.getenv("PORT", 8001)), stateless_http=False)


@mcp.tool()
def search_papers(topic: str, max_results: int = 5) -> List[str]:
    """
    Search for papers on arXiv based on a topic and store their information.
    Args:
        topic: The topic to search for.
        max_results: Maximum number of results to retrieve.
    Returns:
        List of paper IDs found in the search
    """

    client = arxiv.Client()
    search = arxiv.Search(
        query=topic, max_results=max_results, sort_by=arxiv.SortCriterion.Relevance
    )
    papers = client.results(search)
    path = os.path.join(PAPER_DIR, topic.lower().replace(" ", "_"))
    os.makedirs(path, exist_ok=True)
    file_path = os.path.join(path, PAPER_INFO_FILE)
    try:
        with open(file_path, "r") as json_file:
            papers_info = json.load(json_file)
    except FileNotFoundError as ex:
        logging.error(f"File not found: {file_path}: {ex}")
        papers_info = {}
    except json.JSONDecodeError as ex:
        logging.error(f"JSON decode error: {ex}")
        papers_info = {}

    paper_ids = []
    for paper in papers:
        paper_ids.append(paper.get_short_id())
        paper_info = {
            "title": paper.title,
            "authors": [author.name for author in paper.authors],
            "summary": paper.summary,
            "pdf_url": paper.pdf_url,
            "published": str(paper.published.date()),
        }
        papers_info[paper.get_short_id()] = paper_info
    with open(file_path, "w") as json_file:
        json.dump(papers_info, json_file, indent=2)
    logging.info(f"Results are saved in: {file_path}")
    return paper_ids


@mcp.tool()
def extract_info(paper_id: str) -> str:
    """
    Search for information about a specific paper across all topic directories.
    Args:
        paper_id: The ID of the paper to look for.
    Returns:
        JSON string with paper information if found, error message if not found.
    """

    for item in os.listdir(PAPER_DIR):
        item_path = os.path.join(PAPER_DIR, item)
        if os.path.isdir(item_path):
            file_path = os.path.join(item_path, PAPER_INFO_FILE)
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r") as json_file:
                        papers_info = json.load(json_file)
                        if paper_id in papers_info:
                            return json.dumps(papers_info[paper_id], indent=2)
                except (FileNotFoundError, json.JSONDecodeError) as e:
                    logging.info(f"Error reading {file_path}: {str(e)}")
                    continue
    return f"There's no saved information related to paper {paper_id}."


@mcp.resource("papers://folders")
def get_available_folders() -> str:
    """
    List all available topic folders in the papers directory.
    This resource provides a simple list of all available topic folders.
    """
    folders = []
    if os.path.exists(PAPER_DIR):
        for topic_dir in os.listdir(PAPER_DIR):
            topic_path = os.path.join(PAPER_DIR, topic_dir)
            if os.path.isdir(topic_path):
                papers_file = os.path.join(topic_path, PAPER_INFO_FILE)
                if os.path.exists(papers_file):
                    folders.append(topic_dir)
    content = "# Available Topics\n\n"
    if folders:
        for folder in folders:
            content += f"- {folder}\n"
        content += f"\nUse @{folder} to access papers in that topic.\n"
    else:
        content += "No topics found.\n"
    return content


@mcp.resource("papers://{topic}")
def get_topic_papers(topic: str) -> str:
    """
    Get detailed information about papers on a specific topic.
    Args:
        topic: The research topic to retrieve papers for
    """
    topic_dir = topic.lower().replace(" ", "_")
    papers_file = os.path.join(PAPER_DIR, topic_dir, PAPER_INFO_FILE)
    if not os.path.exists(papers_file):
        return f"# No papers found for topic: {topic}\n\nTry searching for papers on this topic first."
    try:
        with open(papers_file, "r") as f:
            papers_data = json.load(f)
        # Create markdown content with paper details
        content = f"# Papers on {topic.replace('_', ' ').title()}\n\n"
        content += f"Total papers: {len(papers_data)}\n\n"
        for paper_id, paper_info in papers_data.items():
            content += f"## {paper_info['title']}\n"
            content += f"- **Paper ID**: {paper_id}\n"
            content += f"- **Authors**: {', '.join(paper_info['authors'])}\n"
            content += f"- **Published**: {paper_info['published']}\n"
            content += (
                f"- **PDF URL**: [{paper_info['pdf_url']}]({paper_info['pdf_url']})\n\n"
            )
            content += f"### Summary\n{paper_info['summary'][:500]}...\n\n"
            content += "---\n\n"
        return content
    except json.JSONDecodeError:
        return f"# Error reading papers data for {topic}\n\nThe papers data file is corrupted."


@mcp.prompt()
def generate_search_prompt(topic: str, num_papers: int = 5) -> str:
    """Generate a prompt for Claude to find and discuss academic papers on a specific topic.
    Args:
        topic: The topic to search for.
        num_papers: The number of papers to search for.
    Returns:
        Prompt string.
    """
    return f""" Search for {num_papers} academic papers about '{topic}' using the search_papers tool.
                Follow these instructions:
                1. First, search for papers using search_papers(topic='{topic}', max_results={num_papers})
                2. For each paper found, extract and organize the following information:
                    - Paper title
                    - Authors
                    - Publication date
                    - Brief summary of the key findings
                    - Main contributions or innovations
                    - Methodologies used
                    - Relevance to the topic '{topic}'
                3. Provide a comprehensive summary that includes:
                    - Overview of the current state of research in '{topic}'
                    - Common themes and trends across the papers
                    - Key research gaps or areas for future investigation
                    - Most impactful or influential papers in this area
                4. Organize your findings in a clear, structured format with headings and bullet points for easy readability.

                Please present both detailed information about each paper and a high-level synthesis of the research landscape in {topic}."""


class ServerLogging:
    def __init__(self):
        """
        Initialize the Server application.
        """
        self.log_config_file = os.getenv("LOG_CONFIG_FILE", "config/log_config.yaml")

    def run(self):
        """
        Run the client application.
        """
        configure_logger(self.log_config_file)
        logging.info("Config is read and logging lib is initialized.")


if __name__ == "__main__":
    # Initialize and run the server
    SERVER_LOG = ServerLogging()
    SERVER_LOG.run()
    logging.info(os.environ)
    if RUN_LOCALLY:
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http")
