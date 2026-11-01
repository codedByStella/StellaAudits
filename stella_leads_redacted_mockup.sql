-- stella_leads sample data
-- All domains, URLs and filenames are fictional (.test is a reserved TLD).
-- Score, grade, finding totals and timestamps come from real runs and are unaltered.
--
-- Removed 11 security-related check findings across 2 rows to protect IP.
-- The complete findings snapshot for one additional row was withheld.
-- total_findings and score still reflect the UNREDACTED runs, so counts will not
-- match the findings shown.
-- Internal check identifiers are replaced with generic ones, and target-specific
-- measurements are omitted from finding titles.
-- The scoring function, weights, grade cutoffs and full check catalog are not
-- represented here. This file is a sample, not a specification of the scorer.

CREATE TABLE audits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT NOT NULL,
    domain TEXT NOT NULL,
    audited_at TEXT NOT NULL,
    score INTEGER,
    grade TEXT,
    total_findings INTEGER,
    pdf_filename TEXT,
    email_draft_filename TEXT,
    status TEXT NOT NULL DEFAULT 'New',
    notes TEXT DEFAULT '',
    error TEXT DEFAULT '',
    findings_snapshot TEXT DEFAULT ''
);

INSERT INTO audits (id,url,domain,audited_at,score,grade,total_findings,pdf_filename,email_draft_filename,status,notes,error,findings_snapshot) VALUES (1,'https://sample-saas.test/','sample-saas.test','2026-07-22T05:11:14.312021+00:00',59,'F',10,'audit-sample-saas.test-20260722-011113.pdf','audit-sample-saas.test-20260722-011113-email.txt','New','','','[]');
INSERT INTO audits (id,url,domain,audited_at,score,grade,total_findings,pdf_filename,email_draft_filename,status,notes,error,findings_snapshot) VALUES (2,'https://sample-saas.test/','sample-saas.test','2026-07-22T05:27:34.484785+00:00',86,'B',10,'audit-sample-saas.test-20260722-012734.pdf','audit-sample-saas.test-20260722-012734-email.txt','New','','','[{"check_key": "finding-001", "severity": "Medium", "title": "Site appears JavaScript-rendered \u2014 some findings may be unreliable"}, {"check_key": "finding-002", "severity": "Low", "title": "Page has no top-level heading (H1)"}, {"check_key": "finding-003", "severity": "Low", "title": "Embedded frame (iframe) missing a title"}, {"check_key": "finding-004", "severity": "Info", "title": "Color contrast not automatically verified"}, {"check_key": "finding-005", "severity": "Low", "title": "Page title length is not ideal"}, {"check_key": "finding-006", "severity": "Low", "title": "No H1 heading for search engines to key off of"}, {"check_key": "finding-007", "severity": "Low", "title": "No LocalBusiness structured data found"}, {"check_key": "finding-008", "severity": "Low", "title": "No phone number found in visible page text"}, {"check_key": "finding-009", "severity": "Low", "title": "No embedded Google Map found"}, {"check_key": "finding-010", "severity": "Info", "title": "Deeper detection (PageSpeed/Lighthouse) not run"}]');
INSERT INTO audits (id,url,domain,audited_at,score,grade,total_findings,pdf_filename,email_draft_filename,status,notes,error,findings_snapshot) VALUES (3,'https://www.example-portal.test/','www.example-portal.test','2026-07-22T05:27:39.720969+00:00',44,'F',17,'audit-www.example-portal.test-20260722-012739.pdf','audit-www.example-portal.test-20260722-012739-email.txt','New','','','[{"check_key": "finding-002", "severity": "Medium", "title": "Page has no top-level heading (H1)"}, {"check_key": "finding-011", "severity": "Medium", "title": "Data table without header cells"}, {"check_key": "finding-004", "severity": "Info", "title": "Color contrast not automatically verified"}, {"check_key": "finding-005", "severity": "Low", "title": "Page title length is not ideal"}, {"check_key": "finding-006", "severity": "Medium", "title": "No H1 heading for search engines to key off of"}, {"check_key": "finding-012", "severity": "Low", "title": "Missing canonical tag"}, {"check_key": "finding-013", "severity": "High", "title": "Missing mobile viewport tag"}, {"check_key": "finding-014", "severity": "Low", "title": "No structured data (schema.org) found"}, {"check_key": "finding-007", "severity": "Low", "title": "No LocalBusiness structured data found"}, {"check_key": "finding-008", "severity": "Low", "title": "No phone number found in visible page text"}, {"check_key": "finding-009", "severity": "Low", "title": "No embedded Google Map found"}, {"check_key": "finding-015", "severity": "Low", "title": "No favicon found"}, {"check_key": "finding-010", "severity": "Info", "title": "Deeper detection (PageSpeed/Lighthouse) not run"}]');
INSERT INTO audits (id,url,domain,audited_at,score,grade,total_findings,pdf_filename,email_draft_filename,status,notes,error,findings_snapshot) VALUES (4,'https://sample-retailer.test/','sample-retailer.test','2026-07-22T05:29:05.571693+00:00',33,'F',20,'audit-sample-retailer.test-20260722-012905.pdf','audit-sample-retailer.test-20260722-012905-email.txt','New','','','[{"check_key": "finding-002", "severity": "Medium", "title": "Page has no top-level heading (H1)"}, {"check_key": "finding-016", "severity": "Low", "title": "Heading levels skip (e.g. H1 straight to H3)"}, {"check_key": "finding-017", "severity": "Low", "title": "Duplicate id attribute(s) found"}, {"check_key": "finding-004", "severity": "Info", "title": "Color contrast not automatically verified"}, {"check_key": "finding-018", "severity": "Medium", "title": "Missing meta description"}, {"check_key": "finding-006", "severity": "Medium", "title": "No H1 heading for search engines to key off of"}, {"check_key": "finding-014", "severity": "Low", "title": "No structured data (schema.org) found"}, {"check_key": "finding-019", "severity": "Medium", "title": "Slow initial server response"}, {"check_key": "finding-020", "severity": "Info", "title": "No robots.txt found"}, {"check_key": "finding-021", "severity": "Low", "title": "No sitemap.xml found"}, {"check_key": "finding-007", "severity": "Low", "title": "No LocalBusiness structured data found"}, {"check_key": "finding-009", "severity": "Low", "title": "No embedded Google Map found"}, {"check_key": "finding-010", "severity": "Info", "title": "Deeper detection (PageSpeed/Lighthouse) not run"}]');
