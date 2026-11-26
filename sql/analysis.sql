-- 1. Most common labels (labels are repository taxonomy, not inferred pain points).
SELECT label, count(*) AS issue_count
FROM issue_labels GROUP BY label ORDER BY issue_count DESC, label LIMIT 20;

-- 2. Longest-open issues. Age does not establish severity or continuous user impact.
SELECT title, source_url, date_diff('day', created_at, current_timestamp) AS age_days
FROM issues WHERE state = 'open' ORDER BY age_days DESC LIMIT 20;

-- 3. Label counts by creation month within the sampled corpus.
-- Updated-order sampling cannot support unbiased growth estimates.
SELECT date_trunc('month', i.created_at) AS created_month, l.label, count(*) AS issue_count
FROM issues i JOIN issue_labels l USING (issue_id)
GROUP BY created_month, l.label ORDER BY created_month, l.label;
