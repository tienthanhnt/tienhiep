import { NextResponse } from "next/server";

const VALID_PLACEMENTS = new Set(["home", "chapter"]);

function getSupabaseConfig() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  return { url, key };
}

function isValidAdId(adId: string) {
  return /^[a-z0-9-]{1,80}$/.test(adId);
}

export async function GET(
  _request: Request,
  { params }: { params: { adId: string } }
) {
  const adId = decodeURIComponent(params.adId || "").trim();
  const { url, key } = getSupabaseConfig();

  if (!isValidAdId(adId)) {
    return NextResponse.json({ error: "Invalid ad id" }, { status: 400 });
  }

  if (!url || !key) {
    return NextResponse.json({ error: "Missing Supabase config" }, { status: 500 });
  }

  try {
    const response = await fetch(`${url}/rest/v1/rpc/get_affiliate_click_count`, {
      method: "POST",
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ target_ad_id: adId }),
      next: { revalidate: 60 },
    });

    if (!response.ok) {
      return NextResponse.json({ clickCount: 0 }, { status: 200 });
    }

    const clickCount = await response.json();
    return NextResponse.json({ clickCount: Number(clickCount) || 0 });
  } catch {
    return NextResponse.json({ clickCount: 0 }, { status: 200 });
  }
}

export async function POST(
  request: Request,
  { params }: { params: { adId: string } }
) {
  const adId = decodeURIComponent(params.adId || "").trim();
  const { url, key } = getSupabaseConfig();

  if (!isValidAdId(adId)) {
    return NextResponse.json({ error: "Invalid ad id" }, { status: 400 });
  }

  if (!url || !key) {
    return NextResponse.json({ error: "Missing Supabase config" }, { status: 500 });
  }

  let placement = "unknown";
  try {
    const body = await request.json();
    if (typeof body?.placement === "string" && VALID_PLACEMENTS.has(body.placement)) {
      placement = body.placement;
    }
  } catch {
    // sendBeacon may send an empty or non-JSON body in some browsers.
  }

  try {
    const response = await fetch(`${url}/rest/v1/rpc/increment_affiliate_click`, {
      method: "POST",
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        target_ad_id: adId,
        target_placement: placement,
      }),
      cache: "no-store",
    });

    if (!response.ok) {
      return NextResponse.json({ error: "Could not record click" }, { status: 502 });
    }

    const clickCount = await response.json();
    return NextResponse.json({ clickCount });
  } catch {
    return NextResponse.json({ error: "Could not record click" }, { status: 502 });
  }
}
