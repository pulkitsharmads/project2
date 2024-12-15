# -*- coding: utf-8 -*-

"""
Dependencies:
1. os - For handling file operations like checking file existence.
2. pandas (pd) - For data manipulation and analysis.
3. numpy (np) - For numerical computations.
4. matplotlib.pyplot (plt) - For creating visualizations.
5. seaborn (sns) - For advanced statistical visualizations.
6. httpx - For making HTTP requests to external APIs.
7. time - For managing delays, particularly in retry logic.
8. argparse - For parsing command-line arguments.
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import httpx
import time
import argparse

# Global Variables
data = None
analysis = None
visualizations = []

# Constants for API
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

def load_data(filepath):
    """
    Load the dataset from a given file path.
    """
    if not os.path.exists(filepath):
        print(f"Error: File '{filepath}' does not exist.")
        return None

    try:
        data = pd.read_csv(filepath)
        print(f"Successfully loaded '{filepath}' with {data.shape[0]} rows and {data.shape[1]} columns.")
        return data
    except Exception as e:
        print(f"Error loading the file: {e}")
        return None

def analyze_data(data):
    """
    Perform basic analysis on the dataset and return a summary.
    """
    analysis = {}

    # Dataset shape
    analysis["shape"] = data.shape

    # Data types and counts
    analysis["data_types"] = data.dtypes.to_dict()

    # Summary statistics
    analysis["summary_statistics"] = data.describe(include="all").to_dict()

    # Count missing values per column
    analysis["missing_values"] = data.isnull().sum().to_dict()

    # Preview of the data
    analysis["data_preview"] = data.head(5).to_dict(orient="records")

    return analysis

def create_visualizations(data, output_prefix="analysis"):
    """
    Create basic visualizations for the dataset.
    """
    visualizations = []

    # Missing values heatmap
    plt.figure(figsize=(10, 6))
    sns.heatmap(data.isnull(), cbar=False, cmap="viridis")
    missing_values_file = f"{output_prefix}_missing_values.png"
    plt.title("Missing Values Heatmap")
    plt.savefig(missing_values_file)
    plt.close()
    visualizations.append(missing_values_file)

    # Pairplot for numeric data (if feasible)
    numeric_cols = data.select_dtypes(include=["number"]).columns
    if len(numeric_cols) > 1:
        sns.pairplot(data[numeric_cols].dropna())
        pairplot_file = f"{output_prefix}_pairplot.png"
        plt.savefig(pairplot_file)
        plt.close()
        visualizations.append(pairplot_file)

    # Correlation heatmap (if numeric columns exist)
    if len(numeric_cols) > 1:
        plt.figure(figsize=(10, 6))
        correlation_matrix = data[numeric_cols].corr()
        sns.heatmap(correlation_matrix, annot=True, cmap="coolwarm", fmt=".2f")
        correlation_file = f"{output_prefix}_correlation.png"
        plt.title("Correlation Heatmap")
        plt.savefig(correlation_file)
        plt.close()
        visualizations.append(correlation_file)

    return visualizations

def query_llm_with_httpx(prompt, model="gpt-4o-mini", max_retries=5, retry_delay=30):
    """
    Query the LLM using the AI Proxy with httpx, with retry logic for rate limiting.
    """
    print("Generating response using LLM...")  # Debugging line
    try:
        # Get the AIPROXY_TOKEN from the environment variable
        token = os.environ.get("AIPROXY_TOKEN")
        if not token:
            print("Error: AIPROXY_TOKEN environment variable is not set.")
            return None

        # Prepare headers and payload
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful data analysis assistant."},
                {"role": "user", "content": prompt},
            ],
        }

        # Retry logic for handling rate limits
        for attempt in range(max_retries):
            try:
                response = httpx.post(API_URL, headers=headers, json=payload, timeout=30.0)
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    print(f"Rate limit exceeded. Retrying in {retry_delay} seconds... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    print(f"HTTP error occurred: {e}")
                    break
            except httpx.RequestError as e:
                print(f"Request error occurred: {e}")
                break
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                break

    except KeyError as e:
        print(f"Missing environment variable: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return None

def generate_markdown_story(analysis, visualizations):
    """
    Use the LLM to generate a Markdown story summarizing the analysis and insights.
    """
    if not analysis or not isinstance(visualizations, list) or len(visualizations) == 0:
        print("Error: Invalid analysis or visualizations provided.")
        return None

    # Prepare a concise summary to send to the LLM
    summary = f"""
    Dataset Shape: {analysis['shape']}
    Data Types: {analysis['data_types']}
    Missing Values: {analysis['missing_values']}
    Summary Statistics:
    {pd.DataFrame(analysis['summary_statistics']).to_string()}

    Visualizations:
    - Missing Values Heatmap: {visualizations[0] if len(visualizations) > 0 else 'Not Available'}
    """
    if len(visualizations) > 1:
        summary += f"\n- Pairplot: {visualizations[1]}"
    if len(visualizations) > 2:
        summary += f"\n- Correlation Heatmap: {visualizations[2]}"

    prompt = f"""
    Analyze the following dataset summary and visualizations:
    {summary}

    Write a Markdown narrative that:
    1. Describes the dataset briefly.
    2. Explains the analyses performed.
    3. Highlights key insights.
    4. Suggests implications or next steps based on the findings.
    Include references to the visualizations in your narrative.
    """
    return query_llm_with_httpx(prompt)

def save_markdown_story(markdown_story, output_file="README.md"):
    """
    Save the generated Markdown story to a file.
    """
    try:
        with open(output_file, "w") as f:
            f.write(markdown_story)
        print(f"Markdown story saved to {output_file}.")
    except Exception as e:
        print(f"Error saving Markdown story to file: {e}")

if __name__ == "__main__":
    # Argument parsing
    parser = argparse.ArgumentParser(description="Automated Data Analysis Script")
    parser.add_argument("filepath", help="Path to the input CSV file")
    args = parser.parse_args()

    # Step 1: Load data
    data = load_data(args.filepath)
    if data is None:
        exit(1)

    # Step 2: Analyze data
    analysis = analyze_data(data)

    # Step 3: Create visualizations
    visualizations = create_visualizations(data)

    # Step 4: Generate Markdown story
    markdown_story = generate_markdown_story(analysis, visualizations)
    if markdown_story:
        save_markdown_story(markdown_story)
