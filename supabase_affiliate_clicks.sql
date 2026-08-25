CREATE TABLE IF NOT EXISTS affiliate_ad_clicks (
  ad_id TEXT PRIMARY KEY,
  click_count BIGINT NOT NULL DEFAULT 0,
  home_click_count BIGINT NOT NULL DEFAULT 0,
  chapter_click_count BIGINT NOT NULL DEFAULT 0,
  last_clicked_at TIMESTAMP WITH TIME ZONE
);

ALTER TABLE affiliate_ad_clicks ENABLE ROW LEVEL SECURITY;

CREATE OR REPLACE FUNCTION increment_affiliate_click(
  target_ad_id TEXT,
  target_placement TEXT DEFAULT 'unknown'
)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  next_count BIGINT;
BEGIN
  INSERT INTO affiliate_ad_clicks (
    ad_id,
    click_count,
    home_click_count,
    chapter_click_count,
    last_clicked_at
  )
  VALUES (
    target_ad_id,
    1,
    CASE WHEN target_placement = 'home' THEN 1 ELSE 0 END,
    CASE WHEN target_placement = 'chapter' THEN 1 ELSE 0 END,
    TIMEZONE('utc'::text, NOW())
  )
  ON CONFLICT (ad_id)
  DO UPDATE SET
    click_count = affiliate_ad_clicks.click_count + 1,
    home_click_count = affiliate_ad_clicks.home_click_count
      + CASE WHEN target_placement = 'home' THEN 1 ELSE 0 END,
    chapter_click_count = affiliate_ad_clicks.chapter_click_count
      + CASE WHEN target_placement = 'chapter' THEN 1 ELSE 0 END,
    last_clicked_at = TIMEZONE('utc'::text, NOW())
  RETURNING click_count INTO next_count;

  RETURN COALESCE(next_count, 0);
END;
$$;

GRANT EXECUTE ON FUNCTION increment_affiliate_click(TEXT, TEXT) TO anon;
GRANT EXECUTE ON FUNCTION increment_affiliate_click(TEXT, TEXT) TO authenticated;

CREATE OR REPLACE FUNCTION get_affiliate_click_count(target_ad_id TEXT)
RETURNS BIGINT
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT COALESCE(
    (
      SELECT click_count
      FROM affiliate_ad_clicks
      WHERE ad_id = target_ad_id
      LIMIT 1
    ),
    0
  );
$$;

GRANT EXECUTE ON FUNCTION get_affiliate_click_count(TEXT) TO anon;
GRANT EXECUTE ON FUNCTION get_affiliate_click_count(TEXT) TO authenticated;
