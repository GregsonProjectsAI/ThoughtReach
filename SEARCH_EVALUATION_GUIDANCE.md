# ThoughtReach Search Evaluation Guidance

This document provides instructions for adding and maintaining evaluation queries in `search_evaluation_dataset.json`.

## Purpose
The search evaluation dataset provides a stable, deterministic set of real-world ThoughtReach search scenarios to measure and improve retrieval quality.

## Category Selection
Entries should be assigned one of the five authority categories:
- **lookup**: Targeting a single, known specific piece of information.
- **recall**: Finding several pieces of context relating to a particular theme.
- **navigation**: Locating a specific historical event or design decision point.
- **collection**: Gathering all available evidence on a broad topic across the archive.
- **synthesis_preparation**: Retrieving a diverse spread of content to support a future summary or decision.

## Metadata Fields
### difficulty
- **easy**: Clear keywords and highly specific targets.
- **medium**: Requires some thematic understanding or handles modest ambiguity.
- **hard**: High ambiguity, generic terminology, or requires gathering distributed evidence.

### expected_precision
- **exact**: One specific target is the only correct answer. Usually `expected_min_results: 1`.
- **narrow_set**: A small, well-defined group of 2-3 results is expected. Usual `expected_min_results: 2-3`.
- **broad_set**: A wide collection of results is expected to cover the topic. Usual `expected_min_results: 5+`.

## Target Completeness
A query is considered **complete** only when both of these are provided:
- **expected_target_description**: A clear human-readable explanation of the ideal result.
- **expected_target_identifier**: A stable identifier (e.g., `conv:TITLE`, `topic:NAME`) that unequivocally names the intended target.

## Grounding
Every evaluation entry MUST be grounded in real ThoughtReach retrieval scenarios—actual searches performed or intended within the project's development history. Do not add arbitrary or speculative queries.
