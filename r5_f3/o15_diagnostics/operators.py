"""Eight explicitly scoped documentary operators; no universal orbit oracle."""
from __future__ import annotations

import copy
import time

from .evidence import (InputError, PreconditionError, binding, canonical, encoded,
                       json_documents, profile_custody, seal_profile, sha256, validate_fixed_profile)
from .reference import (POLICIES, RECORDS, Violation, evaluate_files, exact_value,
                        metadata, pointer_value, resolve)

VERSION = "R5-F3-O15-OPERATORS-1"
SPECS = {
    "T01": ("Object member reordering", "INVARIANCE", {"order_independent"}),
    "T02": ("Coherent alias renaming", "DECLARED_CONVENTION_INVARIANCE", {"renames", "invariance_conventions"}),
    "T03": ("Full-token qualification with lexical target selection", "SEMANTIC_CONTRAST", {"selection", "relation_mode", "invariance_conventions"}),
    "T04": ("Bare alias keys", "CONVENTION_CONDITIONED", set()),
    "T05": ("Finite unambiguous alias-chain repair", "REPAIR", {"mode", "max_hops"}),
    "T06": ("RFC6901 pointer probe", "POINTER_CONTRAST", {"claim_id", "target_pointer"}),
    "T07": ("Equal value with different metadata", "METADATA_CONTRAST", {"claim_id", "target_pointer", "comparison_convention"}),
    "T08": ("Co-permutation under fixed row-local eligibility", "SCOPED_ROW_LOCAL_INVARIANCE", {"permutation", "eligibility_model"}),
}


def require(condition, message, checks):
    checks.append({"condition": message, "passed": bool(condition)})
    if not condition:
        raise PreconditionError(message)


def reverse_objects(value):
    if type(value) is dict:
        return {k: reverse_objects(value[k]) for k in reversed(list(value))}
    if type(value) is list:
        return [reverse_objects(x) for x in value]
    return value


def selected_claim(claims, claim_id, checks):
    matches = [c for c in claims if c.get("claim_id") == claim_id]
    require(len(matches) == 1, "exactly one claim has the supplied claim_id", checks)
    return matches[0]


def used_names(claims, checks):
    sources = [c.get("source_pointer") for c in claims]
    require(all(type(s) is str and s for s in sources), "all claim source tokens are nonempty strings", checks)
    names = sorted({s[6:] for s in sources if s.startswith("alias:")})
    # The resolver admits opaque nested names. These renaming/qualification
    # operators deliberately exclude overlapping literal/suffix namespaces.
    require(all(n and not n.startswith("alias:") for n in names),
            "operator alias names are nonempty and have no overlapping alias prefix", checks)
    return names


def invariance_policies(parameters, checks):
    policies = parameters.get("invariance_conventions")
    require(type(policies) is list and bool(policies) and all(type(p) is str and p in POLICIES for p in policies)
            and len(set(policies)) == len(policies),
            "invariance_conventions explicitly names distinct supported conventions", checks)
    return policies


def rows_at(docs, path, checks):
    value = docs.get(path)
    require(type(value) is dict and type(value.get("rows")) is list,
            "row record exists: " + path, checks)
    rows = value["rows"]
    require(all(type(r) is dict and type(r.get("id")) is str and r["id"] for r in rows),
            "nonempty stable IDs: " + path, checks)
    ids = [r["id"] for r in rows]
    require(len(ids) == len(set(ids)), "unique stable IDs: " + path, checks)
    return rows, ids


def permute_rows(docs, params, profile, checks, trace):
    require(profile is not None, "T08 has the explicit fixed native profile", checks)
    generation = validate_fixed_profile(profile)
    require(params.get("eligibility_model") == "NSC-CORE-ROW-LOCAL-1",
            "only the implemented fixed-profile row-local eligibility model is admitted", checks)
    data, ids = rows_at(docs, "data/rows.json", checks)
    states, state_ids = rows_at(docs, "data/states_or_change_facts.json", checks)
    require(ids == state_ids, "data and state rows have the same ordered stable IDs", checks)
    order = params.get("permutation")
    require(type(order) is list and all(type(i) is int for i in order)
            and sorted(order) == list(range(len(ids))), "permutation is a bijection of source positions", checks)
    receipt = docs.get("records/R05_alignment_receipt.json", {})
    require(type(receipt) is dict and receipt.get("data_ids") == receipt.get("state_ids") == ids,
            "recorded alignment agrees before transformation", checks)
    header = docs.get("bundle.json")
    require(type(header) is dict and header.get("workflow") in ("W1", "W2"),
            "bundle declares a supported workflow", checks)
    workflow = header["workflow"]
    if workflow == "W1":
        require(all(s.get("state") in profile["response_states"] for s in states),
                "W1 states belong to the declared vocabulary", checks)
        expected = {"eligible": {d["id"] for d, s in zip(data, states)
                                if s["state"] == "observed" and d.get("readiness") in profile["category_order"]}}
    elif workflow == "W2":
        require(all(s.get(k) in profile["input_states"] for s in states
                    for k in ("staff_input", "turnover_input")), "W2 input states are declared", checks)
        expected = {"staff_available": {s["id"] for s in states if s["staff_input"] == "available"},
                    "turnover_available": {s["id"] for s in states if s["turnover_input"] == "available"},
                    "staff_imputation": {s["id"] for s in states if s["staff_input"] == "missing" and s["turnover_input"] == "available"}}
    else:
        raise PreconditionError("unsupported row-local workflow")
    materialisation = docs.get("records/R06_materialisation.json")
    require(type(materialisation) is dict, "materialisation record is an object", checks)
    pops = materialisation.get("populations")
    require(type(pops) is list and all(type(p) is dict and type(p.get("population_id")) is str for p in pops)
            and len(pops) == len(expected) and {p["population_id"] for p in pops} == set(expected),
            "the declared populations match the row-local model", checks)
    for pop in pops:
        pid, pop_ids, positions = pop["population_id"], pop.get("ids"), pop.get("local_to_source_positions")
        require(type(pop_ids) is list and all(type(i) is str for i in pop_ids)
                and type(positions) is list and len(pop_ids) == len(positions)
                and set(pop_ids) == expected[pid] and len(pop_ids) == len(set(pop_ids))
                and all(type(j) is int and 0 <= j < len(ids) and ids[j] == i
                        for i, j in zip(pop_ids, positions)),
                "population membership and original source map are correct: " + pid, checks)
    claims, edges = docs[RECORDS["claims"]]["claims"], docs[RECORDS["edges"]]
    for claim in claims:
        pointer = resolve("suffix_only" if generation == "P5" else "literal_only", claim["source_pointer"], edges["aliases"])
        require(pointer.startswith("/values/"), "T08 claims use order-independent retained result values", checks)
    require(type(docs[RECORDS["result"]].get("values")) is dict,
            "retained result values are an object", checks)
    old_values = copy.deepcopy(docs[RECORDS["result"]]["values"])
    for path in ("data/rows.json", "data/states_or_change_facts.json", "data/output_rows.json"):
        rows, row_ids = rows_at(docs, path, checks)
        require(set(row_ids) == set(ids), "co-permuted record has the same stable-ID domain: " + path, checks)
        keyed = dict(zip(row_ids, rows))
        docs[path]["rows"] = [keyed[ids[j]] for j in order]
    new_ids = [ids[j] for j in order]
    receipt["data_ids"] = receipt["state_ids"] = new_ids
    new_positions = {identifier: i for i, identifier in enumerate(new_ids)}
    for pop in pops:
        pop["local_to_source_positions"] = [new_positions[i] for i in pop["ids"]]
    if workflow == "W2":
        operand_record = docs[RECORDS["result"]].get("operands")
        require(type(operand_record) is dict and type(operand_record.get("rows")) is list,
                "retained W2 operands contain a row list", checks)
        operands = operand_record["rows"]
        require(all(type(r) is dict and type(r.get("id")) is str for r in operands)
                and len(operands) == len(ids) and {r["id"] for r in operands} == set(ids),
                "retained W2 operands have the same unique stable-ID domain", checks)
        keyed = {r["id"]: r for r in operands}
        docs[RECORDS["result"]]["operands"]["rows"] = [keyed[i] for i in new_ids]
    require(docs[RECORDS["result"]]["values"] == old_values,
            "retained summary values are unchanged", checks)
    trace.append({"old_order": ids, "new_order": new_ids,
                  "eligible_stable_ids": {k: sorted(v) for k, v in expected.items()},
                  "scope": "Appendix A row-local membership; no producer authentication or original-pairing claim"})


def transform(files, case_id, operator, parameters, *, profile=None):
    start = time.monotonic()
    if type(operator) is not str or operator not in SPECS:
        raise InputError("UNKNOWN_OPERATOR")
    if type(parameters) is not dict or set(parameters) - SPECS[operator][2]:
        raise InputError("INVALID_OR_UNKNOWN_OPERATOR_PARAMETERS")
    before = evaluate_files(files, case_id)
    checks, trace = [], []
    report = {"schema": "nsc-r5-f3-o15-transform/1", "operator_id": operator,
              "operator_version": VERSION, "operator_name": SPECS[operator][0],
              "case_id": case_id, "parameters": parameters,
              "input_binding": binding(files), "reference_before": before,
              "preconditions": checks, "evidence_trace": trace,
              "relation_type": SPECS[operator][1], "actual_checker_execution": False}
    if before["status"] == "INPUT_ERROR":
        report.update(status="INPUT_ERROR", output_binding=None, reference_after=None,
                      relations={}, semantic_verdict_assigned=False, failure=before["error"])
        return None, {**report, "generation_seconds": time.monotonic() - start}
    try:
        require(before["status"] == "COMPLETED", "documentary JSON is unambiguous and admitted for parsing", checks)
        docs = json_documents(files)
        require(all(p in docs and type(docs[p]) is dict for p in RECORDS.values()),
                "all three O15 documents are present as objects", checks)
        if "inventory.json" in files:
            require(profile is not None, "a complete bundle transformation supplies its fixed profile", checks)
            custody = profile_custody(files, profile)
            require(custody["status"] == "PASS", "input custody is current: " + ",".join(custody["issues"]), checks)
        claims = docs[RECORDS["claims"]].get("claims")
        edges, result = docs[RECORDS["edges"]], docs[RECORDS["result"]]
        require(type(claims) is list and bool(claims) and all(type(c) is dict for c in claims), "claims are a nonempty object array", checks)
        require(all(type(c.get("claim_id")) is str and c["claim_id"] for c in claims), "claims have nonempty textual IDs", checks)
        require(len({c["claim_id"] for c in claims}) == len(claims), "claim identifiers are unique", checks)
        require(all(type(c.get("source_pointer")) is str and c["source_pointer"] for c in claims),
                "claim source tokens are nonempty strings", checks)
        require(type(edges.get("aliases")) is dict and all(type(v) is str for v in edges["aliases"].values())
                and type(edges.get("field_metadata")) is dict, "aliases and field metadata have declared types", checks)
        aliases = edges["aliases"]
        asserted = []
        if operator == "T01":
            require(parameters.get("order_independent") is True, "object-order independence is explicitly declared", checks)
            original = canonical(docs)
            docs = {p: reverse_objects(value) for p, value in docs.items()}
            require(canonical(docs) == original, "the logical JSON documents are identical", checks)
            asserted = list(POLICIES)
        elif operator == "T02":
            names = used_names(claims, checks)
            renames = parameters.get("renames")
            require(type(renames) is dict and bool(renames) and set(renames) <= set(names),
                    "renaming domain is a nonempty subset of used logical aliases", checks)
            require(all(type(v) is str and v and not v.startswith("alias:") for v in renames.values())
                    and len(set(renames.values())) == len(renames), "renaming is a prefix-preserving injection", checks)
            key_map = {k: ("alias:" if k.startswith("alias:") else "") + renames.get(k[6:] if k.startswith("alias:") else k,
                         k[6:] if k.startswith("alias:") else k) for k in aliases}
            require(len(set(key_map.values())) == len(key_map), "renaming has no key collision, including unused keys", checks)
            asserted = invariance_policies(parameters, checks)
            old_pointers = {(p, c["claim_id"]): resolve(p, c["source_pointer"], aliases) for p in asserted for c in claims}
            for name in renames:
                require(all(v.startswith("/") for k, v in aliases.items() if k in (name, "alias:" + name)),
                        "renamed used mappings remain single-hop pointers", checks)
            edges["aliases"] = {key_map[k]: v for k, v in aliases.items()}
            for c in claims:
                if c["source_pointer"].startswith("alias:") and c["source_pointer"][6:] in renames:
                    c["source_pointer"] = "alias:" + renames[c["source_pointer"][6:]]
            require(all(resolve(p, c["source_pointer"], edges["aliases"]) == old_pointers[(p, c["claim_id"])]
                        for p in asserted for c in claims), "effective targets are preserved under each declared convention", checks)
            trace.append({"alias_key_renaming": key_map})
        elif operator in ("T03", "T04"):
            names = used_names(claims, checks)
            require(bool(names), "at least one alias is used", checks)
            if operator == "T03":
                require(parameters.get("selection") in ("min", "max"), "lexical selection is explicitly min or max", checks)
                mode = parameters.get("relation_mode", "contrast")
                require(mode in ("contrast", "preserve"), "relation mode is explicit contrast or preserve", checks)
                if mode == "preserve":
                    asserted = invariance_policies(parameters, checks)
                    report["relation_type"] = "DECLARED_CONVENTION_INVARIANCE"
            for name in names:
                keys = [k for k in (name, "alias:" + name) if k in aliases]
                targets = sorted({aliases[k] for k in keys})
                require(bool(targets), "used alias has at least one mapping: " + name, checks)
                if operator == "T04" or parameters.get("relation_mode") == "preserve":
                    require(len(targets) == 1, "no collision between distinct targets: " + name, checks)
                for target in targets:
                    pointer_value(result, target)
                    require(target in edges["field_metadata"], "candidate target metadata are present: " + target, checks)
                    metadata(edges["field_metadata"][target])
                chosen = targets[-1] if parameters.get("selection") == "max" else targets[0]
                for key in keys:
                    del aliases[key]
                new_key = "alias:" + name if operator == "T03" else name
                aliases[new_key] = chosen
                trace.append({"logical_alias": name, "candidate_targets": targets,
                              "selected_target": chosen, "output_key": new_key,
                              "interpretation": "contrast" if len(targets) > 1 else "convention-conditioned representation"})
            if asserted:
                old_docs = json_documents(files)
                old_aliases = old_docs[RECORDS["edges"]]["aliases"]
                require(all(resolve(p, c["source_pointer"], old_aliases) == resolve(p, c["source_pointer"], aliases)
                            for p in asserted for c in claims), "the output key form preserves the declared convention's target", checks)
        elif operator == "T05":
            require(parameters.get("mode") == "repair", "single-hop profile permits repair, not chain invariance", checks)
            max_hops = parameters.get("max_hops", 32)
            require(type(max_hops) is int and 1 <= max_hops <= 128, "bounded positive unfolding depth", checks)
            require(bool(used_names(claims, checks)), "repair has a used alias", checks)
            old_aliases = dict(aliases)
            repaired = 0
            for c in claims:
                source = c["source_pointer"]
                if not source.startswith("alias:"):
                    continue
                token, seen, path = source, set(), []
                for _ in range(max_hops):
                    if token.startswith("/"):
                        break
                    require(token.startswith("alias:") and bool(token[6:]), "each chain edge is an explicit nonempty alias", checks)
                    require(token not in seen, "alias chain is acyclic", checks)
                    seen.add(token)
                    choices = {old_aliases[k] for k in (token[6:], token) if k in old_aliases}
                    require(len(choices) == 1, "every chain link has one unambiguous target", checks)
                    next_token = next(iter(choices))
                    path.append({"source": token, "target": next_token})
                    token = next_token
                require(token.startswith("/"), "chain reaches a pointer within the declared depth", checks)
                pointer_value(result, token)
                require(token in edges["field_metadata"], "repaired target has field metadata", checks)
                metadata(edges["field_metadata"][token])
                for key in (source[6:], source):
                    if key in aliases:
                        aliases[key] = token
                repaired += int(len(path) > 1)
                trace.append({"claim_id": c["claim_id"], "chain": path, "repaired_pointer": token})
            require(repaired > 0, "at least one used multi-hop chain is repaired", checks)
        elif operator in ("T06", "T07"):
            claim = selected_claim(claims, parameters.get("claim_id"), checks)
            pointer = parameters.get("target_pointer")
            require(type(pointer) is str and pointer.startswith("/"), "probe supplies a direct pointer token", checks)
            old = claim["source_pointer"]
            if operator == "T07":
                policy = parameters.get("comparison_convention")
                require(policy in POLICIES, "metadata comparison convention is explicit", checks)
                require(before["policies"][policy]["verdict"] == "S", "the original reference is satisfied under the comparison convention", checks)
                initial = resolve(policy, old, aliases)
                require(initial != pointer, "metadata contrast uses a different result location", checks)
                require(exact_value(pointer_value(result, initial)) == exact_value(pointer_value(result, pointer)),
                        "the two target values are exactly equal", checks)
                require(pointer in edges["field_metadata"], "new target metadata are present", checks)
                require(metadata(edges["field_metadata"][initial]) != metadata(edges["field_metadata"][pointer]),
                        "target metadata differ", checks)
                trace.append({"comparison_convention": policy, "old_pointer": initial,
                              "new_pointer": pointer, "equal_value": True, "different_metadata": True})
            claim["source_pointer"] = pointer
            trace.append({"claim_id": claim["claim_id"], "source_before": old, "source_after": pointer})
        elif operator == "T08":
            permute_rows(docs, parameters, profile, checks, trace)
            asserted = list(POLICIES)
        output = dict(files)
        for p, document in docs.items():
            output[p] = encoded(document, pretty=operator == "T01")
        if "inventory.json" in files:
            output = seal_profile(output, profile)
            report["custody"] = {"status": "RECOMMITTED_" + validate_fixed_profile(profile), "profile_id": profile["profile_id"],
                                  "profile_canonical_sha256": sha256(canonical(profile))}
        else:
            report["custody"] = {"status": "DOCUMENTARY_ONLY", "profile_id": None}
        after = evaluate_files(output, case_id + ":" + operator)
        require(after["status"] == "COMPLETED", "transformed documentary input parses unambiguously", checks)
        relations = {}
        for policy in POLICIES:
            b, a = before["policies"][policy]["verdict"], after["policies"][policy]["verdict"]
            relations[policy] = {"before": b, "after": a, "changed": b != a,
                                "required_relation": "EQUAL_VERDICT_AND_TARGET" if policy in asserted else SPECS[operator][1],
                                "result": ("HOLDS" if a == b else "VIOLATED") if policy in asserted else "CONTRAST_RECORDED_NO_INVARIANCE_CLAIM"}
        report.update(status="TRANSFORMED", output_binding=binding(output), reference_after=after,
                      relations=relations, asserted_invariance_conventions=asserted)
        return output, {**report, "generation_seconds": time.monotonic() - start}
    except InputError as exc:
        report.update(status="INPUT_ERROR", output_binding=None, reference_after=None,
                      relations={}, semantic_verdict_assigned=False,
                      failure={"type": type(exc).__name__, "message": str(exc)})
        return None, {**report, "generation_seconds": time.monotonic() - start}
    except (PreconditionError, Violation) as exc:
        report.update(status="PRECONDITION_FAILED", output_binding=None, reference_after=None,
                      relations={}, failure={"type": type(exc).__name__, "message": str(exc)})
        return None, {**report, "generation_seconds": time.monotonic() - start}
