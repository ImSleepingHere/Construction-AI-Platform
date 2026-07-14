-- The dataset SQL dump inserts explicit ids without advancing Postgres's
-- SERIAL sequences, so every sequence starts stuck at 1 while the tables
-- already have hundreds/thousands of rows. Any ORM insert into a dataset
-- table (e.g. seed_demo_data.py) collides with an existing row until this
-- runs. Safe to re-run any time -- it only ever advances a sequence to
-- MAX(id), never rewinds it.
--
-- Run after loading the dataset dump:
--   docker exec -i construction_ai_postgres psql -U construction_ai -d construction_ai < data/fix_sequences.sql

SELECT setval('change_orders_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM change_orders), 1));
SELECT setval('claim_evidence_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM claim_evidence), 1));
SELECT setval('claims_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM claims), 1));
SELECT setval('correspondence_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM correspondence), 1));
SELECT setval('daily_activities_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM daily_activities), 1));
SELECT setval('documents_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM documents), 1));
SELECT setval('generated_documents_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM generated_documents), 1));
SELECT setval('meetings_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM meetings), 1));
SELECT setval('ncrs_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM ncrs), 1));
SELECT setval('project_decisions_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM project_decisions), 1));
SELECT setval('projects_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM projects), 1));
SELECT setval('purchase_orders_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM purchase_orders), 1));
SELECT setval('purchase_requests_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM purchase_requests), 1));
SELECT setval('safety_events_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM safety_events), 1));
SELECT setval('site_reports_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM site_reports), 1));
SELECT setval('subcontractor_evaluations_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM subcontractor_evaluations), 1));
SELECT setval('subcontractors_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM subcontractors), 1));
SELECT setval('suppliers_id_seq', GREATEST((SELECT COALESCE(MAX(id),1) FROM suppliers), 1));
