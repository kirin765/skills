// IG Audience & Content Intelligence — Cypher metrics over Osintgraph's Neo4j graph
//
// Verified schema (Osintgraph 0.1.1, neo4j 5.x):
//   (:Person {id, username, fullname, is_verified, followers, followees, mediacount,
//             is_business_account, business_category_name, bio, external_url,
//             _followers_complete, _followees_complete, _posts_complete, ...})
//   (:Post   {id, shortcode, caption, caption_hashtags(list), caption_mentions(list),
//             likes, comments, is_video, video_view_count, date_utc, is_sponsored, is_pinned})
//   (:Comment {id, text, likes_count, created_at_utc})
//   FOLLOW EDGE DIRECTION (verified from source):  (follower)-[:FOLLOWS]->(followee)
//   (:Person)-[:POSTED]->(:Post)   (:Person)-[:COMMENTED]->(:Comment)-[:ON]->(:Post)   (:Person)-[:LIKED]->(:Post|:Comment)
//
// Stub caveat: followers/followees of a seed are written as STUBS holding only
//   id, username, fullname, profile_pic_url, is_verified — no bio/counts/posts —
//   until that account is itself `discover`-ed (e.g. via `explore`). So follower-count
//   ranking of neighbours is unavailable in discover-only mode; we rank by graph signal
//   (how many seeds touch them) and is_verified instead.
//
// Params (run_intel.py injects these; for manual Neo4j Browser use, set first):
//   :param seeds => ["competitor_a", "competitor_b", "competitor_c"]
//   :param min_seeds => 2
//   :param top => 100
//
// run_intel.py splits this file on the "// name:" markers and runs each block with the params above.

// name: seed_profile
// Seeds themselves + coverage flags. Use to confirm each seed was actually scraped
// (followers_scraped / followees_scraped / posts_scraped should be true) before trusting the rest.
MATCH (s:Person)
WHERE s.username IN $seeds
RETURN s.username AS username, s.fullname AS fullname, coalesce(s.is_verified, false) AS is_verified,
       s.followers AS followers, s.followees AS followees, s.mediacount AS posts,
       coalesce(s.is_business_account, false) AS is_business, s.business_category_name AS category,
       left(coalesce(s.bio, ''), 200) AS bio_snippet, s.external_url AS external_url,
       coalesce(s._followers_complete, false) AS followers_scraped,
       coalesce(s._followees_complete, false) AS followees_scraped,
       coalesce(s._posts_complete, false)     AS posts_scraped
ORDER BY followers DESC;

// name: core_audience
// (1) CORE AUDIENCE OVERLAP — accounts that follow >= min_seeds of the seeds.
// These people opted into multiple accounts in your niche = your highest-intent target segment.
MATCH (a:Person)-[:FOLLOWS]->(s:Person)
WHERE s.username IN $seeds AND NOT a.username IN $seeds
WITH a, count(DISTINCT s) AS seed_hits, collect(DISTINCT s.username) AS follows_seeds
WHERE seed_hits >= $min_seeds
RETURN a.username AS username, a.fullname AS fullname, coalesce(a.is_verified, false) AS is_verified,
       seed_hits, follows_seeds
ORDER BY seed_hits DESC, a.username
LIMIT $top;

// name: audience_overlap_matrix
// (1b) Pairwise audience overlap between seeds — how much two seeds share followers.
// High overlap = direct competitors / audience cannibalisation; low = adjacent niches.
MATCH (a:Person)-[:FOLLOWS]->(s1:Person), (a)-[:FOLLOWS]->(s2:Person)
WHERE s1.username IN $seeds AND s2.username IN $seeds AND s1.username < s2.username
RETURN s1.username AS seed_a, s2.username AS seed_b, count(DISTINCT a) AS shared_followers
ORDER BY shared_followers DESC;

// name: shared_interests
// (2) SHARED INTERESTS / COMMUNITIES — accounts that >= min_seeds of the seeds FOLLOW.
// What the niche's own accounts collectively pay attention to = content themes, brands,
// communities, and collab/where-to-post targets. The content-strategy goldmine.
MATCH (s:Person)-[:FOLLOWS]->(t:Person)
WHERE s.username IN $seeds AND NOT t.username IN $seeds
WITH t, count(DISTINCT s) AS followed_by_seeds, collect(DISTINCT s.username) AS seeds_following
WHERE followed_by_seeds >= $min_seeds
RETURN t.username AS username, t.fullname AS fullname, coalesce(t.is_verified, false) AS is_verified,
       t.business_category_name AS category, left(coalesce(t.bio, ''), 120) AS bio_snippet,
       followed_by_seeds, seeds_following
ORDER BY followed_by_seeds DESC, is_verified DESC, t.username
LIMIT $top;
// category/bio_snippet are null for accounts only seen as stubs (followee not itself discover-ed);
// they populate once that account is fully discover-ed (e.g. via --explore). Group §2 by category.

// name: top_mentions
// (2b) COLLAB SHORTLIST — accounts the seeds @-mention in captions = explicit partners / UGC creators /
// repost sources / co-promos. The most direct collab-target signal (cleaner than FOLLOWS). Discover-only OK.
MATCH (s:Person)-[:POSTED]->(p:Post)
WHERE s.username IN $seeds AND p.caption_mentions IS NOT NULL
UNWIND p.caption_mentions AS raw_handle
WITH toLower(raw_handle) AS handle, count(*) AS mentions, count(DISTINCT s) AS by_seeds,
     sum(coalesce(p.likes, 0)) AS total_likes
WHERE NOT handle IN [x IN $seeds | toLower(x)]
RETURN handle, mentions, by_seeds, total_likes
ORDER BY by_seeds DESC, mentions DESC
LIMIT $top;

// name: hub_centrality
// (3) HUB / CENTRALITY — most-followed accounts inside the collected subgraph (FOLLOWS in-degree).
// EXPLORE-ONLY: in discover-only mode this is just the seeds' followees ranked by in-degree =
// near-identical to shared_interests, so run_intel.py SKIPS it unless --explore is set. With
// `explore` the audience's/neighbours' own follow edges fill in and true niche gatekeepers surface.
MATCH (t:Person)<-[:FOLLOWS]-(:Person)
WHERE NOT t.username IN $seeds
WITH t, count(*) AS in_degree
RETURN t.username AS username, t.fullname AS fullname, coalesce(t.is_verified, false) AS is_verified, in_degree
ORDER BY in_degree DESC
LIMIT $top;

// name: top_hashtags
// (4a) CONTENT SIGNAL — hashtags the seeds actually use, ranked by frequency and total likes.
// Seeds for your own hashtag set. (likes are partial per Instagram's limits — use directionally.)
MATCH (s:Person)-[:POSTED]->(p:Post)
WHERE s.username IN $seeds AND p.caption_hashtags IS NOT NULL
UNWIND p.caption_hashtags AS raw_tag
WITH toLower(raw_tag) AS tag, count(*) AS uses, sum(coalesce(p.likes, 0)) AS total_likes
RETURN tag, uses, total_likes, round(total_likes * 1.0 / uses, 1) AS avg_likes_per_use
ORDER BY uses DESC, total_likes DESC
LIMIT $top;

// name: top_posts
// (4b) CONTENT SIGNAL — seed posts ranked by engagement (likes + comments). Read the
// captions/format of the winners to reverse-engineer what resonates with the niche.
MATCH (s:Person)-[:POSTED]->(p:Post)
WHERE s.username IN $seeds
RETURN s.username AS seed, p.shortcode AS shortcode, toString(p.date_utc) AS date_utc,
       coalesce(p.is_video, false) AS is_video, coalesce(p.likes, 0) AS likes,
       coalesce(p.comments, 0) AS comments, coalesce(p.is_sponsored, false) AS is_sponsored,
       left(coalesce(p.caption, ''), 240) AS caption_snippet, p.caption_hashtags AS hashtags
ORDER BY (coalesce(p.likes, 0) + coalesce(p.comments, 0)) DESC
LIMIT $top;

// name: seed_content_profile
// (4c) CONTENT SIGNAL — per-seed posting profile: volume, video share, avg engagement, date span.
// Tells you cadence and format mix that the niche runs.
MATCH (s:Person)-[:POSTED]->(p:Post)
WHERE s.username IN $seeds
RETURN s.username AS seed, count(p) AS posts,
       sum(CASE WHEN p.is_video THEN 1 ELSE 0 END) AS videos,
       sum(CASE WHEN NOT coalesce(p.is_sponsored, false) THEN 1 ELSE 0 END) AS organic_posts,
       round(avg(coalesce(p.likes, 0)), 1) AS avg_likes,
       round(avg(CASE WHEN NOT coalesce(p.is_sponsored, false) THEN coalesce(p.likes, 0) END), 1) AS avg_likes_organic,
       round(avg(coalesce(p.comments, 0)), 1) AS avg_comments,
       min(toString(p.date_utc)) AS earliest_post, max(toString(p.date_utc)) AS latest_post
ORDER BY avg_likes_organic DESC;

// name: posting_times
// (4d) WHEN TO POST — hour-of-day (UTC) distribution of seed posts, ranked by avg engagement.
// date_utc is a Neo4j datetime so .hour works directly. Times are UTC — shift to your TZ (KST = UTC+9).
MATCH (s:Person)-[:POSTED]->(p:Post)
WHERE s.username IN $seeds AND p.date_utc IS NOT NULL
RETURN p.date_utc.hour AS hour_utc, count(*) AS posts,
       round(avg(coalesce(p.likes, 0)), 1) AS avg_likes,
       round(avg(coalesce(p.comments, 0)), 1) AS avg_comments
ORDER BY avg_likes DESC;
