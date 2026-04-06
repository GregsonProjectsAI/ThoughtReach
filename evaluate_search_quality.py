import json
import os

def load_evaluation_dataset(filepath):
    """Loads the search evaluation dataset from a JSON file."""
    if not os.path.exists(filepath):
        print(f"Error: Evaluation dataset not found at {filepath}")
        return None
    
    with open(filepath, 'r') as f:
        return json.load(f)

def run_evaluation_skeleton(dataset_obj):
    """Iterates over the evaluation entries and prints a structured summary."""
    print("--- ThoughtReach Search Evaluation Runner (Skeleton) ---")
    print("NOTE: Live search execution and scoring are not yet implemented.\n")
    
    version = dataset_obj.get('dataset_version', 'unknown')
    entries = dataset_obj.get('entries', [])
    
    print(f"Dataset Version: {version}")
    
    real_entries = [entry for entry in entries if entry.get('query_id', '').startswith('EVAL-')]
    real_entries.sort(key=lambda x: x.get('query_id', ''))
    
    # Count query_id occurrences to identify duplicates
    query_id_counts = {}
    target_id_counts = {}
    for entry in real_entries:
        qid = entry.get('query_id')
        if qid and str(qid).strip():
            norm_qid = str(qid).strip()
            query_id_counts[norm_qid] = query_id_counts.get(norm_qid, 0) + 1
        
        # Only track unique target IDs for 'exact' precision entries after normalization
        prec_mode_val = str(entry.get('expected_precision')).strip().lower()
        if prec_mode_val == 'exact':
            tid = entry.get('expected_target_identifier')
            if tid and str(tid).strip():
                norm_tid = str(tid).strip()
                target_id_counts[norm_tid] = target_id_counts.get(norm_tid, 0) + 1
    
    # Count normalized query text to identify duplicates
    query_text_counts = {}
    for entry in real_entries:
        query_val = entry.get('query_text')
        if query_val and str(query_val).strip():
            # Normalized: trim, case-insensitive, collapse internal whitespace
            norm_q = " ".join(str(query_val).strip().lower().split())
            query_text_counts[norm_q] = query_text_counts.get(norm_q, 0) + 1
    
    # Count normalized notes to identify duplicates
    notes_text_counts = {}
    for entry in real_entries:
        notes_val = entry.get('notes')
        if notes_val and str(notes_val).strip():
            # Normalized: trim, case-insensitive, collapse internal whitespace
            norm_n = " ".join(str(notes_val).strip().lower().split())
            notes_text_counts[norm_n] = notes_text_counts.get(norm_n, 0) + 1
    
    # Count normalized target descriptions to identify duplicates
    description_counts = {}
    for entry in real_entries:
        desc_val = entry.get('expected_target_description')
        if desc_val and str(desc_val).strip():
            # Normalized: trim, case-insensitive, collapse internal whitespace
            norm_d = " ".join(str(desc_val).strip().lower().split())
            description_counts[norm_d] = description_counts.get(norm_d, 0) + 1
    
    # Count normalized tag sets to identify cross-entry duplicates
    tag_set_counts = {}
    for entry in real_entries:
        tags = entry.get('tags')
        if isinstance(tags, list):
            usable = sorted(list(set([t.strip().lower() for t in tags if isinstance(t, str) and t.strip()])))
            if usable:
                tag_set_str = "|".join(usable)
                tag_set_counts[tag_set_str] = tag_set_counts.get(tag_set_str, 0) + 1
    
    # Count normalized source titles to identify duplicates
    source_title_counts = {}
    for entry in real_entries:
        title_val = entry.get('expected_source_title')
        if title_val and str(title_val).strip():
            # Normalized: trim, case-insensitive, collapse internal whitespace
            norm_t = " ".join(str(title_val).strip().lower().split())
            source_title_counts[norm_t] = source_title_counts.get(norm_t, 0) + 1
    
    # Count normalized expected source dates to identify duplicates
    source_date_counts = {}
    for entry in real_entries:
        esd_val = entry.get('expected_source_date')
        if esd_val and str(esd_val).strip():
            date_str = str(esd_val).strip()
            source_date_counts[date_str] = source_date_counts.get(date_str, 0) + 1
    
    # Count normalized projects to identify duplicates
    project_text_counts = {}
    for entry in real_entries:
        project_val = entry.get('expected_project')
        if project_val and str(project_val).strip():
            # Normalized: trim, case-insensitive, collapse internal whitespace
            norm_p = " ".join(str(project_val).strip().lower().split())
            project_text_counts[norm_p] = project_text_counts.get(norm_p, 0) + 1
            
    # Count normalized conversation titles to identify duplicates
    conv_title_text_counts = {}
    for entry in real_entries:
        conv_val = entry.get('expected_conversation_title')
        if conv_val and str(conv_val).strip():
            # Normalized: trim, case-insensitive, collapse internal whitespace
            norm_c = " ".join(str(conv_val).strip().lower().split())
            conv_title_text_counts[norm_c] = conv_title_text_counts.get(norm_c, 0) + 1
            
    # Count normalized import titles to identify duplicates
    import_title_text_counts = {}
    for entry in real_entries:
        import_val = entry.get('expected_import_title')
        if import_val and str(import_val).strip():
            # Normalized: trim, case-insensitive, collapse internal whitespace
            norm_i = " ".join(str(import_val).strip().lower().split())
            import_title_text_counts[norm_i] = import_title_text_counts.get(norm_i, 0) + 1
    
    for entry in real_entries:
        # Stub fields for future expansion
        actual_results = []
        evaluation_status = "not_yet_executed"
        
        # Check if basic target evidence is complete
        has_description = bool(entry.get('expected_target_description'))
        has_identifier = bool(entry.get('expected_target_identifier'))
        expected_target_complete = has_description and has_identifier

        print(f"Query ID:   {entry.get('query_id')}")
        print(f"Text:       {entry.get('query_text')}")
        print(f"Category:   {entry.get('category')}")
        print(f"Difficulty: {entry.get('difficulty')}")
        print(f"Precision:  {entry.get('expected_precision')}")
        print(f"Min Results:{entry.get('expected_min_results')}")
        print(f"Target Complete: {expected_target_complete}")
        print(f"Live Results: {actual_results}")
        print(f"Status:      {evaluation_status}")
        print("-" * 40)
    
    # Calculate summary
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
        # Check completeness
        is_complete = bool(entry.get('expected_target_description')) and bool(entry.get('expected_target_identifier'))
        if is_complete:
            summary["expected_target_complete_count"] += 1
        else:
            summary["expected_target_incomplete_count"] += 1

        cat = entry.get('category', 'unknown')
        diff = entry.get('difficulty', 'unknown')
        prec = entry.get('expected_precision', 'unknown')
        min_res = entry.get('expected_min_results')

        summary['category_counts'][cat] = summary['category_counts'].get(cat, 0) + 1
        summary['difficulty_counts'][diff] = summary['difficulty_counts'].get(diff, 0) + 1
        summary['expected_precision_counts'][prec] = summary['expected_precision_counts'].get(prec, 0) + 1
        
        # Validation for warnings
        issues = []
        if not is_complete:
            issues.append("expected_target_incomplete")
        if entry.get('difficulty') not in ['easy', 'medium', 'hard']:
            issues.append("invalid_or_missing_difficulty")
        if entry.get('expected_precision') not in ['exact', 'narrow_set', 'broad_set']:
            issues.append("invalid_or_missing_expected_precision")
        if not isinstance(min_res, int) or min_res <= 0:
            issues.append("invalid_or_missing_expected_min_results")
        
        # Consistency check for precision vs min results
        if isinstance(min_res, int):
            prec = entry.get('expected_precision')
            if prec == 'exact' and min_res != 1:
                issues.append("expected_precision_min_results_mismatch")
            elif prec == 'narrow_set' and min_res < 2:
                issues.append("expected_precision_min_results_mismatch")
            elif prec == 'broad_set' and min_res < 5:
                issues.append("expected_precision_min_results_mismatch")
        
        # Check for missing query text
        query_val = entry.get('query_text')
        if not query_val or not str(query_val).strip():
            issues.append("missing_query_text")
        
        # Check for missing category
        cat_val = entry.get('category')
        if not cat_val or not str(cat_val).strip():
            issues.append("missing_category")
        
        # Check for invalid category
        allowed_cats = ['factual', 'exploratory', 'navigational', 'known_item', 'broad_discovery']
        if cat_val and str(cat_val).strip() and str(cat_val).strip().lower() not in allowed_cats:
            issues.append("invalid_category")
        
        # Check for missing expected precision
        prec_val = entry.get('expected_precision')
        if not prec_val or not str(prec_val).strip():
            issues.append("missing_expected_precision")
        
        # Check for invalid expected precision
        allowed_precs = ['exact', 'narrow_set', 'broad_set']
        if prec_val and str(prec_val).strip() and str(prec_val).strip().lower() not in allowed_precs:
            issues.append("invalid_expected_precision")
        
        # Check for missing description
        desc_val = entry.get('expected_target_description')
        if not desc_val or not str(desc_val).strip():
            issues.append("missing_description")
        
        # Check for duplicate description
        if desc_val and str(desc_val).strip():
            norm_d = " ".join(str(desc_val).strip().lower().split())
            if description_counts.get(norm_d, 0) > 1:
                issues.append("duplicate_description")
        
        # Check for missing difficulty
        diff_val = entry.get('difficulty')
        if not diff_val or not str(diff_val).strip():
            issues.append("missing_difficulty")
        
        # Check for invalid difficulty
        allowed_diffs = ['easy', 'medium', 'hard']
        if diff_val and str(diff_val).strip() and str(diff_val).strip().lower() not in allowed_diffs:
            issues.append("invalid_difficulty")
        
        # Check for missing tags
        if 'tags' not in entry:
            issues.append("missing_tags")
            
        # Check for invalid tags type
        if 'tags' in entry and not isinstance(entry.get('tags'), list):
            issues.append("invalid_tags_type")
            
        # Check for empty tags
        tags_val = entry.get('tags')
        if isinstance(tags_val, list) and len(tags_val) == 0:
            issues.append("empty_tags")
            
        # Check for invalid tag item type
        if isinstance(tags_val, list) and any(not isinstance(t, str) for t in tags_val):
            issues.append("invalid_tag_item_type")
            
        # Check for empty tag string
        if isinstance(tags_val, list) and any(isinstance(t, str) and not t.strip() for t in tags_val):
            issues.append("empty_tag_string")
            
        # Check for duplicate tags
        if isinstance(tags_val, list):
            # Normalization rules for duplicate comparison:
            # - trim, collapse internal whitespace, case-insensitive
            normalized_tags = []
            for t in tags_val:
                if isinstance(t, str) and t.strip():
                    norm_t = " ".join(t.strip().lower().split())
                    normalized_tags.append(norm_t)
            if len(normalized_tags) != len(set(normalized_tags)):
                issues.append("duplicate_tags")
        
        # Check for missing notes
        notes_val = entry.get('notes')
        if not notes_val or not str(notes_val).strip():
            issues.append("missing_notes")
        
        # Check for duplicate notes
        if notes_val and str(notes_val).strip():
            norm_n = " ".join(str(notes_val).strip().lower().split())
            if notes_text_counts.get(norm_n, 0) > 1:
                issues.append("duplicate_notes")
        
        # Check for missing source type
        st_val = entry.get('source_type')
        if not st_val or not str(st_val).strip():
            issues.append("missing_source_type")
        
        # Check for invalid source type value
        allowed_sources = ['conversation', 'import']
        if st_val and str(st_val).strip() and str(st_val).strip() not in allowed_sources:
            issues.append("invalid_source_type_value")
        
        # Check for missing expected source type
        est_type_val = entry.get('expected_source_type')
        if not est_type_val or not str(est_type_val).strip():
            issues.append("missing_expected_source_type")
        
        # Check for invalid expected source type
        allowed_expected_sources = ['conversation', 'import']
        if est_type_val and str(est_type_val).strip() and str(est_type_val).strip().lower() not in allowed_expected_sources:
            issues.append("invalid_expected_source_type")
            
        # Check for expected source type mismatch
        st_trimmed = str(st_val).strip() if st_val else None
        est_type_trimmed = str(est_type_val).strip() if est_type_val else None
        if st_trimmed in allowed_sources and est_type_trimmed in allowed_expected_sources:
            if st_trimmed != est_type_trimmed:
                issues.append("expected_source_type_mismatch")
        
        # Check for missing expected source title
        est_val = entry.get('expected_source_title')
        if not est_val or not str(est_val).strip():
            issues.append("missing_expected_source_title")
        
        # Check for duplicate expected source title
        if est_val and str(est_val).strip():
            norm_t = " ".join(str(est_val).strip().lower().split())
            if source_title_counts.get(norm_t, 0) > 1:
                issues.append("duplicate_expected_source_title")
        
        # Check for missing expected date
        esd_val = entry.get('expected_source_date')
        if not esd_val or not str(esd_val).strip():
            issues.append("missing_expected_date")
        
        # Check for invalid expected date format
        if esd_val and str(esd_val).strip():
            import datetime
            try:
                datetime.datetime.strptime(str(esd_val).strip(), '%Y-%m-%d')
            except ValueError:
                issues.append("invalid_expected_date_format")
        
        # Check for duplicate expected date
        if esd_val and str(esd_val).strip():
            date_str = str(esd_val).strip()
            if source_date_counts.get(date_str, 0) > 1:
                issues.append("duplicate_expected_date")
        
        # Check for missing expected project
        ep_val = entry.get('expected_project')
        if not ep_val or not str(ep_val).strip():
            issues.append("missing_expected_project")
            
        # Check for duplicate expected project
        if ep_val and str(ep_val).strip():
            norm_p = " ".join(str(ep_val).strip().lower().split())
            if project_text_counts.get(norm_p, 0) > 1:
                issues.append("duplicate_expected_project")
        
        # Check for missing expected conversation title
        if str(entry.get('expected_source_type')).strip().lower() == 'conversation':
            ect_val = entry.get('expected_conversation_title')
            if not ect_val or not str(ect_val).strip():
                issues.append("missing_expected_conversation_title")
            
        # Check for duplicate expected conversation title
        if ect_val and str(ect_val).strip():
            norm_c = " ".join(str(ect_val).strip().lower().split())
            if conv_title_text_counts.get(norm_c, 0) > 1:
                issues.append("duplicate_expected_conversation_title")
        
        # Check for unexpected conversation title for import entries
        if str(entry.get('expected_source_type')).strip().lower() == 'import':
            ect_val = entry.get('expected_conversation_title')
            if ect_val and str(ect_val).strip():
                issues.append("unexpected_expected_conversation_title_for_import")
        
        # Check for missing expected import title
        eit_val = entry.get('expected_import_title')
        if not eit_val or not str(eit_val).strip():
            issues.append("missing_expected_import_title")
            
        # Check for duplicate expected import title
        if eit_val and str(eit_val).strip():
            norm_i = " ".join(str(eit_val).strip().lower().split())
            if import_title_text_counts.get(norm_i, 0) > 1:
                issues.append("duplicate_expected_import_title")
        
        # Check for unexpected import title for conversation entries
        if str(entry.get('expected_source_type')).strip() == 'conversation':
            eit_val = entry.get('expected_import_title')
            if eit_val and str(eit_val).strip():
                issues.append("unexpected_expected_import_title_for_conversation")
        
        # Check for missing expected minimum results
        min_res_val = entry.get('expected_min_results')
        if min_res_val is None or not str(min_res_val).strip():
            issues.append("missing_expected_min_results")
        
        # Check for invalid expected minimum results type
        if min_res_val is not None and not isinstance(min_res_val, int):
            if str(min_res_val).strip():
                issues.append("invalid_expected_min_results_type")
        
        # Check for invalid expected minimum results range
        if isinstance(min_res_val, int) and min_res_val < 1:
            issues.append("invalid_expected_min_results_range")
        
        # Check for missing identifier for exact-precision entries
        prec_mode = str(entry.get('expected_precision')).strip().lower()
        if prec_mode == 'exact':
            tid_val = entry.get('expected_target_identifier')
            if not tid_val or not str(tid_val).strip():
                issues.append("missing_expected_target_identifier")
        
        # Check for unexpected identifier for non-exact entries
        if prec_mode in ['narrow_set', 'broad_set']:
            tid_val = entry.get('expected_target_identifier')
            if tid_val and str(tid_val).strip():
                issues.append("unexpected_expected_target_identifier_for_non_exact")

        # Check for duplicate query_id
        qid_val = entry.get('query_id')
        if qid_val and str(qid_val).strip():
            norm_qid = str(qid_val).strip()
            if query_id_counts.get(norm_qid, 0) > 1:
                issues.append("duplicate_query_id")
            
        # Check for missing query id
        qid_val = entry.get('query_id')
        if not qid_val or not str(qid_val).strip():
            issues.append("missing_query_id")
            
        # Check for invalid query id format
        if qid_val and str(qid_val).strip():
            import re
            if not re.match(r'^q[0-9]+$', str(qid_val).strip()):
                issues.append("invalid_query_id_format")
        
        # Check for duplicate query text
        q_val = entry.get('query_text')
        if q_val and str(q_val).strip():
            norm_q = " ".join(str(q_val).strip().lower().split())
            if query_text_counts.get(norm_q, 0) > 1:
                issues.append("duplicate_query_text")
            
        # Check for duplicate target identifier among exact entries
        tid_val = entry.get('expected_target_identifier')
        if prec_mode == 'exact' and tid_val and str(tid_val).strip():
            norm_tid = str(tid_val).strip()
            if target_id_counts.get(norm_tid, 0) > 1:
                issues.append("duplicate_expected_target_identifier")
            
        if issues:
            warnings.append({
                "query_id": entry.get('query_id'),
                "issues": issues
            })

    # Category Coverage Check
    required_categories = ["lookup", "recall", "navigation", "collection", "synthesis_preparation"]
    existing_categories = set(summary["category_counts"].keys())
    missing = sorted([c for c in required_categories if c not in existing_categories])
    summary["category_coverage_complete"] = (len(missing) == 0)
    summary["missing_categories"] = missing

    # Difficulty Coverage Check
    required_difficulties = ["easy", "medium", "hard"]
    existing_difficulties = set(summary["difficulty_counts"].keys())
    missing_diffs = sorted([d for d in required_difficulties if d not in existing_difficulties])
    summary["difficulty_coverage_complete"] = (len(missing_diffs) == 0)
    summary["missing_difficulties"] = missing_diffs

    # Expected Precision Coverage Check
    required_precisions = ["exact", "narrow_set", "broad_set"]
    existing_precisions = set(summary["expected_precision_counts"].keys())
    missing_precs = sorted([p for p in required_precisions if p not in existing_precisions])
    summary["expected_precision_coverage_complete"] = (len(missing_precs) == 0)
    summary["missing_expected_precisions"] = missing_precs

    # Overall Dataset Readiness Flag
    summary["dataset_ready_for_execution"] = (
        summary["expected_target_incomplete_count"] == 0 and
        summary["category_coverage_complete"] and
        summary["difficulty_coverage_complete"] and
        summary["expected_precision_coverage_complete"] and
        len(warnings) == 0
    )

    # Ordered Readiness Failure Reasons
    reasons = []
    if summary["expected_target_incomplete_count"] > 0:
        reasons.append("expected_targets_incomplete")
    if not summary["category_coverage_complete"]:
        reasons.append("category_coverage_incomplete")
    if not summary["difficulty_coverage_complete"]:
        reasons.append("difficulty_coverage_incomplete")
    if not summary["expected_precision_coverage_complete"]:
        reasons.append("expected_precision_coverage_incomplete")
    if len(warnings) > 0:
        reasons.append("warnings_present")
    
    summary["readiness_failure_reasons"] = reasons

    print("\n--- Evaluation Summary ---")
    print(json.dumps({"summary": summary}, indent=2))
    
    if warnings:
        print("\n--- Validation Warnings ---")
        print(json.dumps({"warnings": warnings}, indent=2))
    
    # Persist complete deterministic output to file
    output_data = {
        "dataset_version": version,
        "entries": [
            {
                **entry, 
                "actual_results": [], 
                "evaluation_status": "not_yet_executed",
                "expected_target_complete": bool(entry.get('expected_target_description')) and bool(entry.get('expected_target_identifier'))
            }
            for entry in real_entries
        ],
        "summary": summary,
        "warnings": warnings
    }
    
    output_path = 'search_evaluation_output.json'
    with open(output_path, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nEvaluation output persisted to {output_path}")
    print("\nSearch execution and scoring logic will be implemented in a future step.")

if __name__ == "__main__":
    dataset_path = 'search_evaluation_dataset.json'
    dataset = load_evaluation_dataset(dataset_path)
    if dataset:
        run_evaluation_skeleton(dataset)
