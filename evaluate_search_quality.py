import json
import os
import re
import traceback
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
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
    engine = create_async_engine(DATABASE_URL, echo=False, connect_args={"ssl": False})
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
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
        "evaluation_pass_count": 0,
        "evaluation_fail_count": 0,
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
                evaluation_status = f"execution_failed: {str(e)}\n{traceback.format_exc()}"
                issues.append("search_execution_error")

        print(f"[{entry.get('query_id')}] Query: {query_text}")
        print(f"Results Count: {len(actual_results)}")
        print(f"Status:        {evaluation_status}")

        # Scoring Layer
        evaluation_pass = False
        evaluation_reason = "Skipped"
        matched_rank = None
        distinct_result_count = None
        
        if is_complete and evaluation_status == "executed":
            def slugify(text):
                text = str(text).lower()
                text = re.sub(r'[^a-z0-9\s-]', '', text)
                return re.sub(r'[-\s]+', '-', text).strip('-')

            prec = entry.get("expected_precision", "")
            if prec == "exact":
                target_id = entry.get("expected_target_identifier", "")
                expected_slug = target_id.replace("conv:", "").replace("topic:", "").strip()
                
                # Check top 3
                for idx, res in enumerate(actual_results[:3]):
                    res_slug = slugify(res.get("conversation_title", ""))
                    if res_slug == expected_slug:
                        matched_rank = idx + 1
                        evaluation_pass = True
                        break
                
                if evaluation_pass:
                    evaluation_reason = f"Expected target found at rank {matched_rank}"
                else:
                    evaluation_reason = "Expected target not found in top 3 results"
            
            elif prec in ["narrow_set", "broad_set"]:
                min_res = entry.get("expected_min_results", 1)
                # Count distinct conversations in top 10
                distinct_convs = set(res.get("conversation_id") for res in actual_results[:10])
                distinct_result_count = len(distinct_convs)
                
                if distinct_result_count >= min_res:
                    evaluation_pass = True
                    evaluation_reason = f"Found {distinct_result_count} distinct conversations, meeting minimum of {min_res}"
                else:
                    evaluation_pass = False
                    evaluation_reason = f"Found only {distinct_result_count} distinct conversations, needed {min_res}"
            
            if evaluation_pass:
                summary["evaluation_pass_count"] += 1
            else:
                summary["evaluation_fail_count"] += 1

        print(f"Pass:          {evaluation_pass}")
        print(f"Reason:        {evaluation_reason}")
        print("-" * 40)

        entry["actual_results"] = actual_results
        entry["evaluation_status"] = evaluation_status
        entry["expected_target_complete"] = is_complete
        entry["evaluation_pass"] = evaluation_pass
        entry["evaluation_reason"] = evaluation_reason
        if matched_rank is not None:
            entry["matched_rank"] = matched_rank
        if distinct_result_count is not None:
            entry["distinct_result_count"] = distinct_result_count

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
        asyncio.run(run_evaluation(dataset))
