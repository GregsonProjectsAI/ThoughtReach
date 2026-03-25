/**
 * ThoughtReach Retrieval API - Minimal Client Example (JavaScript)
 * 
 * This example demonstrates how to consume the search and category discovery 
 * endpoints using the native Fetch API.
 */

const BASE_URL = 'http://localhost:8000';

/**
 * 1. Global Search Example
 * Performs a semantic search across all conversations.
 */
async function runGlobalSearch(query, limit = 5) {
  console.log(`\n--- Global Search: "${query}" ---`);
  try {
    const response = await fetch(`${BASE_URL}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, limit })
    });
    
    const results = await response.json();
    console.log(`Found ${results.length} results:`);
    results.forEach((r, i) => {
      console.log(`${i+1}. ${r.conversation_title} (Score: ${r.similarity_score.toFixed(4)})`);
    });
    return results;
  } catch (error) {
    console.error('Global search failed:', error.message);
  }
}

/**
 * 2. Category Discovery Example
 * Fetches the list of all available categories.
 */
async function getCategories() {
  console.log('\n--- Category Discovery ---');
  try {
    const response = await fetch(`${BASE_URL}/categories`);
    const categories = await response.json();
    console.log(`Found ${categories.length} categories:`);
    categories.forEach(c => console.log(`- ${c.name} (ID: ${c.id})`));
    return categories;
  } catch (error) {
    console.error('Category discovery failed:', error.message);
  }
}

/**
 * 3. Category-Scoped Search Example
 * Performs a search restricted to a specific category.
 */
async function runScopedSearch(query, categoryId, limit = 5) {
  console.log(`\n--- Scoped Search: "${query}" (Category: ${categoryId}) ---`);
  try {
    const response = await fetch(`${BASE_URL}/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        query, 
        limit, 
        category_id: categoryId 
      })
    });
    
    if (response.status === 404) {
      console.error('Error: Category not found (404)');
      return;
    }
    
    const results = await response.json();
    console.log(`Found ${results.length} results in category:`);
    results.forEach((r, i) => {
      console.log(`${i+1}. ${r.conversation_title} (Score: ${r.similarity_score.toFixed(4)})`);
    });
    return results;
  } catch (error) {
    console.error('Scoped search failed:', error.message);
  }
}

/**
 * Main function to demonstrate usage.
 */
async function main() {
  // 1. Run a global search
  await runGlobalSearch('vector embeddings');

  // 2. Discover categories
  const categories = await getCategories();

  // 3. If categories exist, run a scoped search using the first one
  if (categories && categories.length > 0) {
    const firstCategoryId = categories[0].id;
    await runScopedSearch('vector embeddings', firstCategoryId);
  } else {
    console.log('\n(No categories found to demonstrate scoped search)');
  }
  
  // 4. Demonstrate error handling with a non-existent category ID
  await runScopedSearch('any query', 'ffffffff-ffff-ffff-ffff-ffffffffffff');
}

// To run this in a Node.js environment (for testing):
// main();
