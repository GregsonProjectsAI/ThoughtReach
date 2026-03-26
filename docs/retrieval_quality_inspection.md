# Retrieval Quality Inspection

This document characterises the current retrieval precision of the ThoughtReach semantic search system based on a small set of representative queries.

## Methodology
- **Source**: Existing `/search` endpoint.
- **Data**: Real ingested conversation data (Treasure Hunt and Japan Travel).
- **Evaluation**: Top 5 results per query classified manually.
- **Categories**:
    - **DIRECT MATCH**: Contains the target content or exactly matches the query's intent.
    - **INDIRECT MATCH**: Related discussion or context but not the primary target.
    - **IRRELEVANT**: No meaningful connection to the query.

---

## Query: "poetry"
*Context: The treasure hunt conversation contains discussions about "rhymes" and "prose".*

1. [IRRELEVANT] "puzzles" (Too broad)
2. [INDIRECT] "About your prose comments" (Related to writing style)
3. [INDIRECT] "Tone consistent (light rhyme, clear action)" (Explicitly mentions rhyme)
4. [INDIRECT] "Then add (non-rhyme, clarity wins)" (Explicitly mentions rhyme)
5. [INDIRECT] "rewrite the FULL prose again" (Related to writing style)

**Analysis**: Strong semantic link to "prose" and "rhyme", but lacks a "DIRECT" block of poetry in the top 5.

---

## Query: "treasure hunt"
*Context: Main topic of the primary conversation.*

1. [DIRECT] "🧭 TREASURE HUNT SYSTEM — CURRENT STATE (END OF SESSION) 🎯 STATUS"
2. [DIRECT] "👉 (Players go to the volcano location) 👉 (They search and find the treasure)"
3. [DIRECT] "collect early fragments and cipher fragments assemble the cipher decode clue to find F4 assemble full map place character cards identify winning location sheet find treasure"
4. [DIRECT] "👉 A modular, reusable treasure hunt engine 👉 That can be reskinned infinitely 👉 With a proven game loop"
5. [INDIRECT] "Track A — Main hunt"

**Analysis**: Excellent precision for the core topic.

---

## Query: "cipher"
*Context: A key subsystem of the treasure hunt.*

1. [DIRECT] "cipher info puzzle logic extra markings"
2. [DIRECT] "1 cipher card"
3. [DIRECT] "Encoded message (cipher puzzle)"
4. [DIRECT] "cipher key symbol reference special card decoder strip"
5. [DIRECT] "Cipher A Cipher B Cipher C Cipher D"

**Analysis**: 100% precision for "cipher" related terms.

---

## Query: "travel itinerary"
*Context: Testing cross-conversation retrieval.*

1. [IRRELEVANT] "assemble map ... identify landmark"
2. [IRRELEVANT] "starting location"
3. [DIRECT] "I'm planning a 10-day trip to Japan in late November. I want to see autumn leaves. Where should I go?"
4. [IRRELEVANT] "to"
5. [IRRELEVANT] "🧭 MAP ASSEMBLY"

**Analysis**: Found the correct travel document, but it was ranked 3rd behind unrelated treasure hunt steps. Shows bias toward the larger "treasure hunt" dataset.

---

## Query: "map fragments"
*Context: Specific items in the game.*

1. [DIRECT] "mini puzzle → reveals fragment location"
2. [DIRECT] "Map fragments upgrade"
3. [DIRECT] "👉 Fragment F4"
4. [DIRECT] "👉 Fragment F2"
5. [DIRECT] "👉 Fragment F3"

**Analysis**: Very high precision for specific game items.

---

## Query: "character cards"
*Context: Player role mechanics.*

1. [DIRECT] "using character cards ✖"
2. [DIRECT] "Right now character cards:"
3. [DIRECT] "👉 Character cards = positioning system only"
4. [DIRECT] "👉 a character card (already in your system)"
5. [DIRECT] "👉 Character cards are already doing a job. Don’t overload them."

**Analysis**: 100% precision for character-related mechanics.

---

## Query: "logic puzzle"
*Context: Broad concept in the game.*

1. [INDIRECT] "puzzles" (Broad)
2. [INDIRECT] "one puzzle each" (Broad)
3. [INDIRECT] "Puzzle Intro" (Broad)
4. [DIRECT] "cipher info puzzle logic extra markings" (Matches "logic")
5. [INDIRECT] "harder puzzles" (Broad)

**Analysis**: High recall for "puzzle", but "logic" specific matches are mixed with general puzzle mentions.

---

## Observed Anomalies & Notes
1. **Dataset Bias**: Queries like "travel itinerary" were heavily diluted by treasure hunt results despite having a perfect match in the DB.
2. **Stop Word Noise**: Small fragments (e.g., "to") occasionally surface as high-similarity results for low-information queries.
3. **Symbol Handling**: Semantic search seems to handle emojis and symbols (👉, 🧭, ✖) well, correctly grouping them with related topics.
