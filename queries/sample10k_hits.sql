-- Root pages in httparchive.sample_data.requests_10k (script and html responses): whether any
-- body disables an element from script, and, for bodies where an Enter-key check appears within
-- 600 chars before disabling, the script URL, a body fingerprint and a snippet around the match.
WITH bodies AS (
  SELECT client, page, rank, url, type, response_body AS b
  FROM `httparchive.sample_data.requests_10k`
  WHERE is_root_page AND type IN ('script', 'html') AND response_body IS NOT NULL
), flagged AS (
  SELECT client, page, rank, url, type,
    REGEXP_CONTAINS(b, r'\.disabled\s*=\s*(?:true|!0)|\.prop\(\s*["\x27]disabled["\x27]\s*,\s*(?:true|!0)|setAttribute\(\s*["\x27]disabled["\x27]') AS dis,
    REGEXP_EXTRACT(b, r'(?s)([^\x00]{0,300}(?:(?:keyCode|which)\s*===?\s*13\b|\.key\s*===?\s*["\x27]Enter["\x27])[^\x00]{0,600}?(?:\.disabled\s*=\s*(?:true|!0)|\.prop\(\s*["\x27]disabled["\x27]\s*,\s*(?:true|!0)|setAttribute\(\s*["\x27]disabled["\x27])[^\x00]{0,200})') AS enter_snip,
    FARM_FINGERPRINT(b) AS fp
  FROM bodies
)
SELECT client, page, rank,
  LOGICAL_OR(dis) AS dis,
  LOGICAL_OR(enter_snip IS NOT NULL) AS enter_dis,
  ARRAY_AGG(IF(enter_snip IS NULL, NULL, STRUCT(url, type, fp, SUBSTR(enter_snip, 1, 1500) AS snip)) IGNORE NULLS LIMIT 3) AS hits
FROM flagged
GROUP BY client, page, rank
