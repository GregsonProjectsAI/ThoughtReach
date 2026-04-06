import json
import os
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.services.search import search_chunks
from app.models.models import Base

def load_evaluation_dataset(filepath):
    """Loads the search evaluation dataset from a JSON file."""
    if not os.path.exists(filepath):
        print(f"Error: Evaluation dataset not found at {filepath}")
        return None
    
    with open(filepath, 'r') as f:
        return json.load(f)

async def run_evaluation(dataset_obj):
    """Iterates over the evaluation entries, executes live searches, and records results."""
    print("--- ThoughtReach Search Evaluation Runner ---")
    print("Executing live searches against local database...\n")
    
    # Database Setup
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/thoughtreach")
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    version = dataset_obj.get('dataset_version', 'unknown')
    entries = dataset_obj.get('entries', [])
    
    print(f"Dataset Version: {version}")
    
    real_entries = [entry for entry in entries if entry.get('query_id', '').startswith('EVAL-')]
    real_entries.sort(key=lambda x: x.get('query_id', ''))
    
    # Pre-count occurrences for hygiene check
    query_id_counts = {}
    target_id_counts = {}
    query_text_counts = {}
    notes_text_counts = {}
    description_counts = {}
    source_title_counts = {}
    source_date_counts = {}
    project_text_counts = {}
    conv_title_text_counts = {}
    import_title_text_counts = {}

    for entry in real_entries:
        qid = entry.get('query_id')
        if qid and str(qid).strip():
            norm_qid = str(qid).strip()
            query_id_counts[norm_qid] = query_id_counts.get(norm_qid, 0) + 1
        
        prec_mode_val = str(entry.get('expected_precision')).strip().lower()
        if prec_mode_val == 'exact':
            tid = entry.get('expected_target_identifier')
            if tid and str(tid).strip():
                norm_tid = str(tid).strip()
                target_id_counts[norm_tid] = target_id_counts.get(norm_tid, 0) + 1

        query_val = entry.get('query_text')
        if query_val and str(query_val).strip():
            norm_q = " ".join(str(query_val).strip().lower().split())
            query_text_counts[norm_q] = query_text_counts.get(norm_q, 0) + 1

        notes_val = entry.get('notes')
        if notes_val and str(notes_val).strip():
            norm_n = " ".join(str(notes_val).strip().lower().split())
            notes_text_counts[norm_n] = notes_text_counts.get(norm_n, 0) + 1

        desc_val = entry.get('expected_target_description')
        if desc_val and str(desc_val).strip():
            norm_d = " ".join(str(desc_val).strip().lower().split())
            description_counts[norm_d] = description_counts.get(norm_d, 0) + 1

        title_val = entry.get('expected_source_title')
        if title_val and str(title_val).strip():
            norm_t = " ".join(str(title_val).strip().lower().split())
            source_title_counts[norm_t] = source_title_counts.get(norm_t, 0) + 1

        esd_val = entry.get('expected_source_date')
        if esd_val and str(esd_val).strip():
            date_str = str(esd_val).strip()
            source_date_counts[date_str] = source_date_counts.get(date_str, 0) + 1

        project_val = entry.get('expected_project')
        if project_val and str(project_val).strip():
            norm_p = " ".join(str(project_val).strip().lower().split())
            project_text_counts[norm_p] = project_text_counts.get(norm_p, 0) + 1

        conv_val = entry.get('expected_conversation_title')
        if conv_val and str(conv_val).strip():
            norm_c = " ".join(str(conv_val).strip().lower().split())
            conv_title_text_counts[norm_c] = conv_title_text_counts.get(norm_c, 0) + 1

        import_val = entry.get('expected_import_title')
        if import_val and str(import_val).strip():
            norm_i = " ".join(str(import_val).strip().lower().split())
            import_title_text_counts[norm_i] = import_title_text_counts.get(norm_i, 0) + 1

    # Calculation Summary and Validation
    summary = {
        "total_real_entries": len(real_entries),
        "expected_target_complete_count": 0,
        "expected_target_incomplete_count": 0,
        "category_counts": {},
        "difficulty_counts": {},
        "expected_precision_counts": {}
    }
    warnings = []

    for entry in real_entries:
        query_text = entry.get('query_text')
        is_complete = bool(entry.get('expected_target_description')) and bool(entry.get('expected_target_identifier'))
        if is_complete:
            summary["expected_target_complete_count"] += 1
        else:
            summary["expected_target_incomplete_count"] += 1

        cat = entry.get('category', 'unknown')
        diff = entry.get('difficulty', 'unknown')
        prec = entry.get('expected_precision', 'unknown')
        summary['category_counts'][cat] = summary['category_counts'].get(cat, 0) + 1
        summary['difficulty_counts'][diff] = summary['difficulty_counts'].get(diff, 0) + 1
        summary['expected_precision_counts'][prec] = summary['expected_precision_counts'].get(prec, 0) + 1

        issues = []
        # Hygiene checks
        if not is_complete: issues.append("expected_target_incomplete")
        if query_id_counts.get(str(entry.get('query_id')).strip(), 0) > 1: issues.append("duplicate_query_id")
        
        # Live Search Execution
        actual_results = []
        evaluation_status = "executed"
        async with async_session() as db:
            try:
                results = await search_chunks(query_text, db, limit=10)
                for res in results:
                    actual_results.append({
                        "conversation_id": str(res.get("conversation_id")),
                        "conversation_title": res.get("conversation_title"),
                        "similarity_score": res.get("similarity_score")
                    })
            except Exception as e:
                evaluation_status = f"execution_failed: {str(e)}"
                issues.append("search_execution_error")

        print(f"[{entry.get('query_id')}] Query: {query_text}")
        print(f"Results Count: {len(actual_results)}")
        print(f"Status:        {evaluation_status}")
        print("-" * 40)

        entry["actual_results"] = actual_results
        entry["evaluation_status"] = evaluation_status
        entry["expected_target_complete"] = is_complete

        if issues:
            warnings.append({"query_id": entry.get('query_id'), "issues": issues})

    # Coverage Checks
    required_categories = ["lookup", "recall", "navigation", "collection", "synthesis_preparation"]
    existing_categories = set(summary["category_counts"].keys())
    missing = sorted([c for c in required_categories if c not in existing_categories])
    summary["category_coverage_complete"] = (len(missing) == 0)
    summary["missing_categories"] = missing

    summary["dataset_ready_for_execution"] = (
        summary["expected_target_incomplete_count"] == 0 and
        summary["category_coverage_complete"] and
        len(warnings) == 0
    )

    reasons = []
    if summary["expected_target_incomplete_count"] > 0: reasons.append("expected_targets_incomplete")
    if not summary["category_coverage_complete"]: reasons.append("category_coverage_incomplete")
    if len(warnings) > 0: reasons.append("warnings_present")
    summary["readiness_failure_reasons"] = reasons

    print("\n--- Evaluation Summary ---")
    print(json.dumps({"summary": summary}, indent=2))
    
    output_data = {
        "dataset_version": version,
        "entries": real_entries,
        "summary": summary,
        "warnings": warnings
    }
    output_path = 'search_evaluation_output.json'
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    print(f"\nEvaluation output persisted to {output_path}")

if __name__ == "__main__":
    dataset_path = 'search_evaluation_dataset.json'
    dataset = load_evaluation_dataset(dataset_path)
    if dataset:
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # For environments where an event loop is already active (IPython, etc.)
                asyncio.ensure_future(run_evaluation(dataset))
            else:
                loop.run_until_complete(run_evaluation(dataset))
        except RuntimeError:
            # Fallback if get_event_loop() fails or isn't appropriate
            asyncio.run(run_evaluation(dataset))
