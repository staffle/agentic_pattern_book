#!/usr/bin/env python3
"""
Configuration file for book compilation.
Contains book-specific settings that can be easily modified.
"""

# Default book configuration for Agentic Design Patterns
AGENTIC_DESIGN_PATTERNS_CONFIG = {
    "title": "Agentic Design Patterns",
    "description": "Compile the Agentic Design Patterns book",
    "default_output": "Agentic_Design_Patterns_compiled.pdf",
    "default_workdir": "_agentic_build",
    "default_index": "index.pdf",
    "default_cover": "cover.jpeg",
    
    # Predefined table of contents structure
    "predefined_headings": [
        "Dedication",
        "Acknowledgment",
        "Foreword",
        "A Thought Leader's Perspective: Power and Responsibility",
        "Introduction",
        "What makes an AI system an \"agent\"?",
        "Part One",
        "Chapter 1: Prompt Chaining ",
        "Chapter 2: Routing ",
        "Chapter 3: Parallelization ",
        "Chapter 4: Reflection ",
        "Chapter 5: Tool Use ",
        "Chapter 6: Planning ",
        "Chapter 7: Multi-Agent ",
        "Part Two",
        "Chapter 8: Memory Management ",
        "Chapter 9: Learning and Adaptation ",
        "Chapter 10: Model Context Protocol (MCP) ",
        "Chapter 11: Goal Setting and Monitoring ",
        "Part Three",
        "Chapter 12: Exception Handling and Recovery ",
        "Chapter 13: Human-in-the-Loop ",
        "Chapter 14: Knowledge Retrieval (RAG) ",
        "Part Four",
        "Chapter 15: Inter-Agent Communication (A2A) ",
        "Chapter 16: Resource-Aware Optimization ",
        "Chapter 17: Reasoning Techniques ",
        "Chapter 18: Guardrails/Safety Patterns ",
        "Chapter 19: Evaluation and Monitoring ",
        "Chapter 20: Prioritization ",
        "Chapter 21: Exploration and Discovery ",
        "Appendix",
        "Appendix A: Advanced Prompting Techniques",
        "Appendix B - AI Agentic ....: From GUI to Real world environment",
        "Appendix C - Quick overview of Agentic Frameworks",
        "Appendix D - Building an Agent with AgentSpace (on-line only)",
        "Appendix E - AI Agents on the CLI (online)",
        "Appendix F - Under the Hood: An Inside Look at the Agents' Reasoning Engines",
        "Appendix G - Coding agents",
        "Conclusion",
        "Glossary",
        "Index of Terms"
    ],
    
    # Fallback headings if predefined ones are not available
    "fallback_headings": [
        "Agentic Design Patterns", 
        "Introduction", 
        "Core Concepts", 
        "Implementation Guide"
    ]
}

# You can add more book configurations here
# ANOTHER_BOOK_CONFIG = {
#     "title": "Another Book",
#     "description": "Compile another book",
#     "default_output": "another_book_compiled.pdf",
#     "default_workdir": "_another_build",
#     "default_index": "index.pdf",
#     "default_cover": "cover.png",
#     "predefined_headings": ["Chapter 1", "Chapter 2", "Conclusion"],
#     "fallback_headings": ["Introduction", "Main Content", "Conclusion"]
# }

# Available configurations
BOOK_CONFIGS = {
    "agentic": AGENTIC_DESIGN_PATTERNS_CONFIG,
    # "another": ANOTHER_BOOK_CONFIG,
}

# Default configuration (can be changed to switch between different books)
DEFAULT_CONFIG = AGENTIC_DESIGN_PATTERNS_CONFIG

def get_config(book_name=None):
    """Get configuration for a specific book."""
    if book_name and book_name in BOOK_CONFIGS:
        return BOOK_CONFIGS[book_name]
    return DEFAULT_CONFIG
