import type {
  CategoryAnalytics,
  PaginatedTransactions,
  RewardBalanceResponse,
  RewardListResponse,
  RewardRedemptionResponse,
  TransactionMetadata,
  TransactionQueryParams,
} from "@/lib/types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");

function buildUrl(path: string, params?: URLSearchParams): string {
  if (!apiBaseUrl) {
    throw new Error("NEXT_PUBLIC_API_BASE_URL is not configured");
  }

  const url = new URL(path, `${apiBaseUrl}/`);
  if (params) {
    url.search = params.toString();
  }
  return url.toString();
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  params?: URLSearchParams,
): Promise<T> {
  const response = await fetch(buildUrl(path, params), {
    ...options,
    headers: {
      Accept: "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body: unknown = await response.json();
      if (
        typeof body === "object" &&
        body !== null &&
        "detail" in body &&
        typeof body.detail === "string"
      ) {
        detail = body.detail;
      }
    } catch {
      // Keep the HTTP status text when an error response is not JSON.
    }
    throw new Error(`API request failed (${response.status}): ${detail}`);
  }

  return response.json() as Promise<T>;
}

export function getTransactions(
  query: TransactionQueryParams = {},
): Promise<PaginatedTransactions> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  }
  return request<PaginatedTransactions>("/api/transactions", {}, params);
}

export function getTransactionMetadata(): Promise<TransactionMetadata> {
  return request<TransactionMetadata>("/api/transactions/metadata");
}

export function getCategoryAnalytics(month: string): Promise<CategoryAnalytics> {
  const params = new URLSearchParams({ month });
  return request<CategoryAnalytics>("/api/analytics/categories", {}, params);
}

export function getRewards(): Promise<RewardListResponse> {
  return request<RewardListResponse>("/api/rewards");
}

export function getRewardBalance(): Promise<RewardBalanceResponse> {
  return request<RewardBalanceResponse>("/api/rewards/balance");
}

export function redeemReward(rewardId: number): Promise<RewardRedemptionResponse> {
  return request<RewardRedemptionResponse>(`/api/rewards/${rewardId}/redeem`, {
    method: "POST",
  });
}
