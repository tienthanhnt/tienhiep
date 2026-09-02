const D1_CACHE_SECONDS = 1800;

interface D1Response<T> {
  success: boolean;
  result?: Array<{
    success: boolean;
    results?: T[];
  }>;
  errors?: unknown[];
}

function getD1Config() {
  const accountId = process.env.CLOUDFLARE_ACCOUNT_ID;
  const databaseId = process.env.D1_DATABASE_ID;
  const token = process.env.CLOUDFLARE_API_TOKEN;

  if (!accountId || !databaseId || !token) return null;
  return { accountId, databaseId, token };
}

export function isNewBookIdentifier(identifier: string) {
  return /^new-\d+(?:-|$)/.test(identifier);
}

export function getNewBookPublicId(identifier: string) {
  const match = identifier.match(/^(new-\d+)(?:-|$)/);
  return match?.[1] || null;
}

export async function queryD1<T>(
  sql: string,
  params: Array<string | number | null> = [],
  revalidate = D1_CACHE_SECONDS,
): Promise<T[]> {
  const config = getD1Config();
  if (!config) return [];

  try {
    const response = await fetch(
      `https://api.cloudflare.com/client/v4/accounts/${config.accountId}/d1/database/${config.databaseId}/query`,
      {
        method: "POST",
        headers: {
          Authorization: `Bearer ${config.token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ sql, params }),
        next: { revalidate },
      },
    );

    if (!response.ok) return [];

    const data = await response.json() as D1Response<T>;
    const result = data.result?.[0];
    if (!data.success || !result?.success) return [];

    return result.results || [];
  } catch {
    return [];
  }
}
