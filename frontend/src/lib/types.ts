export type TransactionStatus = "SUCCESS" | "FAILED" | "PENDING";
export type TransactionSortBy = "date" | "amount";
export type SortOrder = "asc" | "desc";

export interface Transaction {
  id: number;
  transaction_id: string;
  transaction_at: string;
  merchant: string;
  category: string;
  amount: string;
  currency: string;
  status: TransactionStatus;
  payment_method: string;
}

export interface PaginatedTransactions {
  items: Transaction[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface TransactionMetadata {
  categories: string[];
  statuses: string[];
  payment_methods: string[];
}

export interface CategorySpendItem {
  category: string;
  amount: string;
  transaction_count: number;
}

export interface CategoryAnalytics {
  month: string;
  items: CategorySpendItem[];
  total_spend: string;
}

export interface Reward {
  id: number;
  name: string;
  description: string;
  coin_cost: number;
  reward_type: string;
  reward_value: string | null;
  active: boolean;
}

export interface RewardListResponse {
  items: Reward[];
}

export interface RewardBalanceResponse {
  balance: number;
}

export interface RewardRedemptionResponse {
  redemption_id: number;
  reward_id: number;
  reward_name: string;
  coins_spent: number;
  balance: number;
}

export interface TransactionQueryParams {
  page?: number;
  page_size?: number;
  search?: string;
  category?: string;
  status?: TransactionStatus;
  date_from?: string;
  date_to?: string;
  amount_min?: string;
  amount_max?: string;
  sort_by?: TransactionSortBy;
  sort_order?: SortOrder;
}
