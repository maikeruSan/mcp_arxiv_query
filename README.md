# ArXiv Query MCP Server

The ArXiv Query MCP Server is a Model Context Protocol (MCP) implementation that provides AI assistants with capabilities to search, download, and extract text from academic papers on arXiv.

## Features

- **Comprehensive Search Options**: Search arXiv papers by ID, author, category, title, abstract, or date range
- **Paper Downloads**: Download papers as PDF files with automatic caching
- **Text Extraction**: Convert downloaded PDFs to text with support for Mistral OCR API or local processing
- **Rate Limiting**: Smart rate limiting to respect arXiv API usage policies

## Installation

### Prerequisites

- Docker
- Python 3.9+
- Pip package manager

### Docker Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-arxiv-query.git
cd mcp-arxiv-query

# Build the Docker image
docker build -t mcp-arxiv-query .

# Test the server
echo '{"jsonrpc":"2.0","id":1,"method":"list_tools","params":{}}' | \
  docker run --rm -i mcp-arxiv-query
```

### Local Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/mcp-arxiv-query.git
cd mcp-arxiv-query

# Install dependencies with uv (recommended)
uv pip install .

# Or install with pip
pip install .

# Run the server
python -m mcp_arxiv_query
```

## Usage with Claude Desktop

Add the ArXiv Query MCP server to your Claude Desktop configuration file.

### Basic Configuration

```json
{
  "mcp_servers": {
    "arxiv-query": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-v",
        "$HOME/Downloads:/app/Downloads",
        "mcp-arxiv-query"
      ]
    }
  }
}
```

### Advanced Configuration with OCR Support

```json
{
  "mcp_servers": {
    "arxiv-query": {
      "command": "docker",
      "args": [
        "run",
        "--rm",
        "-i",
        "-e", "MISTRAL_OCR_API_KEY=your_api_key_here",
        "-e", "ARXIV_MAX_CALLS_PER_MINUTE=30",
        "-e", "ARXIV_MAX_CALLS_PER_DAY=2000",
        "-e", "LOG_LEVEL=INFO",
        "-v",
        "$HOME/Downloads:/app/Downloads",
        "mcp-arxiv-query"
      ]
    }
  }
}
```

## Environment Variables

| Variable                   | Description                                          | Default    |
|----------------------------|------------------------------------------------------|------------|
| `DOWNLOAD_DIR`             | Directory for PDF downloads                          | /app/Downloads |
| `MISTRAL_OCR_API_KEY`      | API key for Mistral OCR (optional)                   | None       |
| `ARXIV_MAX_CALLS_PER_MINUTE` | Maximum arXiv API calls per minute                 | 30         |
| `ARXIV_MAX_CALLS_PER_DAY`  | Maximum arXiv API calls per day                      | 2000       |
| `ARXIV_MIN_INTERVAL_SECONDS` | Minimum time between API calls in seconds          | 1.0        |
| `LOG_LEVEL`                | Logging level (DEBUG, INFO, WARNING, ERROR)          | INFO       |
| `LOG_FORMAT`               | Set to "json" for JSON-formatted logs                | standard   |

## Claude Integration

This MCP server is designed to be used with Claude. For a seamless experience, we recommend adding the following instructions to your Claude preferences:

```
When I type "@aq <query>", please use the arxiv-query tools to search for academic papers related to my query.
For example, "@aq Capturing Semantic Flow of ML-based Systems" means search for relevant papers on this topic.

When I type "@ax <arxiv-id>", please: 
1. Download the paper using the download_paper tool
2. Extract its text content using the pdf_to_text tool
3. Be ready to answer my questions about the paper

Examples: "@ax 2503.13415" or "@ax 2503.13415v2"
```

### Usage Examples

Here are some examples of how to interact with Claude using the ArXiv Query tools:

#### Search for Papers

```
User: @aq transformer architecture in NLP

Claude: Searching for papers about "transformer architecture in NLP"...
[Claude would use search_arxiv tool and show results]

I found several relevant papers on transformer architecture in NLP:
1. "Attention Is All You Need" by Vaswani et al.
2. "BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding" by Devlin et al.
3. ...
```

#### Category-Specific Search

```
User: @aq category:cs.CL language models

Claude: Searching for language models papers in the Computation and Language category...
[Claude would use search_by_category tool]

Here are the most recent papers about language models in the cs.CL category:
1. ...
2. ...
```

#### Author Search

```
User: @aq author:Hinton recent work

Claude: Searching for recent papers by Geoffrey Hinton...
[Claude would use search_by_author tool]

Here are Geoffrey Hinton's recent publications:
1. ...
2. ...
```

#### Download and Analyze a Paper

```
User: @ax 2203.02155

Claude: I'll download and process the paper with ID 2203.02155 for you.
[Claude would download the PDF and extract text]

I've downloaded and processed the paper "Training language models to follow instructions with human feedback" by Ouyang et al.

This paper introduces InstructGPT, which is trained to follow human instructions. The key findings are:
1. ...
2. ...

Would you like me to analyze any specific section in more detail?
```

#### Date Range Search

```
User: @aq diffusion models date:2023-01-01 to:2023-06-30

Claude: Searching for papers about diffusion models published between January and June 2023...
[Claude would use search_by_date_range tool]

I found 15 papers about diffusion models published in the first half of 2023:
1. ...
2. ...
```

#### Multiple Questions About a Paper

```
User: @ax 2307.09288

Claude: I'll download and process the paper with ID 2307.09288 for you.
[Claude would download and process the paper]

I've downloaded and processed the paper "GPT-4 Technical Report" by OpenAI.

User: What methodology did they use for evaluation?

Claude: In the GPT-4 Technical Report, the evaluation methodology includes:
1. Benchmark testing across multiple domains including...
2. ...
```

These examples demonstrate how to leverage the ArXiv Query tools for academic research through Claude's interface using the recommended shortcuts.

## Available Tools

The server provides the following tools:

- `search_arxiv` - Flexible search interface with multiple parameters
- `download_paper` - Download papers as PDF files
- `search_by_category` - Search papers by arXiv category
- `search_by_author` - Search papers by author name
- `search_by_id` - Search for a specific paper by ID
- `search_by_date_range` - Search papers within a date range
- `pdf_to_text` - Convert PDF files to text
- `get_rate_limiter_stats` - View API usage statistics

## Mistral OCR API Support

The service supports using the Mistral OCR API for PDF text extraction, which provides superior accuracy compared to standard PDF extractors, especially for complex academic papers.

To enable:
1. Obtain an API key from Mistral AI (https://console.mistral.ai/)
2. Set the API key as the environment variable `MISTRAL_OCR_API_KEY`

Key features:
- **Intelligent Processing**: The system automatically extracts arXiv IDs from filenames and prioritizes using arXiv PDF URLs for processing, eliminating local file transfers
- **Fallback Options**: If an arXiv ID cannot be identified, the system processes the local PDF file
- **Automatic Degradation**: If Mistral OCR API fails, the system automatically falls back to PyPDF2

Notes:
- When using URL mode, the system relies on arXiv's public PDF URL format
- When using local file mode, PDF size must be less than 20MB
- The program uses the official `mistral-ocr-latest` model
- Without setting `MISTRAL_OCR_API_KEY`, the system automatically uses PyPDF2 for local processing

## Troubleshooting

### PDF Download Issues

If you encounter problems downloading PDFs:

1. Ensure your download directory has appropriate permissions
2. Verify Docker volume mounting is correct
3. Run the `build_and_test.sh` script to test download functionality
4. Check logs for detailed error messages

Common issues:

- **File Not Found**: Ensure the arXiv ID format is correct, e.g., "2303.08774"
- **Cannot Write File**: Check download directory permissions, ensure the container user has write access
- **Docker Mount Issues**: Ensure the `-v` parameter is correct, format should be `-v host_path:/app/Downloads`
- **Mistral API Errors**: Check if the API key is correct and if the PDF file exceeds the size limit (20MB)
- **arXiv ID Extraction Problems**: Ensure the PDF file is named with a standard arXiv ID, e.g., "2303.08774.pdf"

### Manual Download Testing

You can manually test the PDF download functionality with the following command:

```bash
docker run --rm -i \
  -v "$HOME/Downloads:/app/Downloads" \
  mcp-arxiv-query python -c "from mcp_arxiv_query.downloader import ArxivDownloader; downloader = ArxivDownloader('/app/Downloads'); result = downloader.download_paper('2303.08774'); print(result)"
```

## Development

This service is built on the MCP protocol and the `arxiv_query_fluent` Python library.

### Directory Structure

- `src/mcp_arxiv_query/`: Source code
  - `__init__.py`: Package initialization
  - `__main__.py`: Entry point
  - `server.py`: MCP server implementation
  - `pdf_utils.py`: PDF text extraction tools
  - `arxiv_service.py`: arXiv API service wrapper
  - `rate_limiter.py`: API rate limiting
  - `tools.py`: Tool definitions
  - `logger.py`: Logging configuration

## License

This project is licensed under the [MIT License](LICENSE).
