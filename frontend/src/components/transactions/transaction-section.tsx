"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Search } from "lucide-react";
import { useEffect, useState } from "react";

import { getTransactionMetadata, getTransactions } from "@/lib/api";
import {
  formatCurrency,
  formatTransactionDate,
  getMonthDateRange,
  isValidMonthValue,
} from "@/lib/format";
import type { SortOrder, TransactionQueryParams, TransactionSortBy, TransactionStatus } from "@/lib/types";
import styles from "./transaction-section.module.css";

type TransactionSectionProps = {
  selectedMonth: string | null;
  selectedCategory: string;
  onCategoryChange: (category: string) => void;
};

function useDebouncedValue(value: string, delay: number): string {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedValue(value), delay);
    return () => window.clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

function isValidAmountRange(minimum: string, maximum: string): boolean {
  if (!minimum || !maximum) {
    return true;
  }
  return Number.isFinite(Number(minimum)) && Number.isFinite(Number(maximum)) && Number(minimum) <= Number(maximum);
}

function statusClass(status: TransactionStatus): string {
  if (status === "SUCCESS") return styles.success;
  if (status === "FAILED") return styles.failed;
  return styles.pending;
}

export function TransactionSection({
  selectedMonth,
  selectedCategory,
  onCategoryChange,
}: TransactionSectionProps) {
  const monthRange = selectedMonth && isValidMonthValue(selectedMonth)
    ? getMonthDateRange(selectedMonth)
    : null;
  const [searchInput, setSearchInput] = useState("");
  const [status, setStatus] = useState<"" | TransactionStatus>("");
  const [dateFrom, setDateFrom] = useState(monthRange?.from ?? "");
  const [dateTo, setDateTo] = useState(monthRange?.to ?? "");
  const [amountMin, setAmountMin] = useState("");
  const [amountMax, setAmountMax] = useState("");
  const [sortBy, setSortBy] = useState<TransactionSortBy>("date");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const debouncedSearch = useDebouncedValue(searchInput, 300).trim();
  const validDateRange = !dateFrom || !dateTo || dateFrom <= dateTo;
  const validAmountRange = isValidAmountRange(amountMin, amountMax);
  const queryEnabled = Boolean(monthRange) && validDateRange && validAmountRange;
  const metadataQuery = useQuery({
    queryKey: ["transaction-metadata"],
    queryFn: getTransactionMetadata,
  });

  const params: TransactionQueryParams = {
    page,
    page_size: pageSize,
    sort_by: sortBy,
    sort_order: sortOrder,
    ...(debouncedSearch ? { search: debouncedSearch } : {}),
    ...(selectedCategory ? { category: selectedCategory } : {}),
    ...(status ? { status } : {}),
    ...(dateFrom ? { date_from: dateFrom } : {}),
    ...(dateTo ? { date_to: dateTo } : {}),
    ...(amountMin ? { amount_min: amountMin } : {}),
    ...(amountMax ? { amount_max: amountMax } : {}),
  };
  const transactionsQuery = useQuery({
    queryKey: ["transactions", params],
    queryFn: () => getTransactions(params),
    enabled: queryEnabled,
    placeholderData: keepPreviousData,
  });
  const transactions = transactionsQuery.data;

  const changeSort = (nextSort: TransactionSortBy) => {
    setSortOrder(nextSort === sortBy && sortOrder === "desc" ? "asc" : "desc");
    setSortBy(nextSort);
    setPage(1);
  };
  const clearFilters = () => {
    setSearchInput("");
    onCategoryChange("");
    setStatus("");
    setDateFrom(monthRange?.from ?? "");
    setDateTo(monthRange?.to ?? "");
    setAmountMin("");
    setAmountMax("");
    setPage(1);
  };
  const resultsStart = transactions && transactions.total > 0 ? (page - 1) * pageSize + 1 : 0;
  const resultsEnd = transactions ? Math.min(page * pageSize, transactions.total) : 0;

  return (
    <section className={styles.section} aria-labelledby="transactions-heading">
      <div className={styles.sectionHeading}>
        <div>
          <p>Activity</p>
          <h2 id="transactions-heading">Transactions</h2>
        </div>
        {transactionsQuery.isFetching && transactionsQuery.data && <span>Updating…</span>}
      </div>

      <div className={styles.filters}>
        <label className={styles.searchField}>
          <span>Search merchants</span>
          <div>
            <Search size={17} aria-hidden="true" />
            <input
              value={searchInput}
              placeholder="Search merchants…"
              onChange={(event) => { setSearchInput(event.target.value); setPage(1); }}
            />
          </div>
        </label>
        <label>
          <span>Category</span>
          <select
            value={selectedCategory}
            disabled={metadataQuery.isPending || metadataQuery.isError}
            onChange={(event) => { onCategoryChange(event.target.value); setPage(1); }}
          >
            <option value="">{metadataQuery.isError ? "Categories unavailable" : "All categories"}</option>
            {metadataQuery.data?.categories.map((category) => <option key={category} value={category}>{category}</option>)}
          </select>
        </label>
        <label>
          <span>Status</span>
          <select
            value={status}
            disabled={metadataQuery.isPending || metadataQuery.isError}
            onChange={(event) => { setStatus(event.target.value as "" | TransactionStatus); setPage(1); }}
          >
            <option value="">{metadataQuery.isError ? "Statuses unavailable" : "All statuses"}</option>
            {metadataQuery.data?.statuses.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label><span>From</span><input type="date" value={dateFrom} onChange={(event) => { setDateFrom(event.target.value); setPage(1); }} /></label>
        <label><span>To</span><input type="date" value={dateTo} onChange={(event) => { setDateTo(event.target.value); setPage(1); }} /></label>
        <label><span>Min amount</span><input type="number" step="0.01" value={amountMin} onChange={(event) => { setAmountMin(event.target.value); setPage(1); }} /></label>
        <label><span>Max amount</span><input type="number" step="0.01" value={amountMax} onChange={(event) => { setAmountMax(event.target.value); setPage(1); }} /></label>
        <button className={styles.clearButton} type="button" onClick={clearFilters}>Clear filters</button>
      </div>
      {!validDateRange && <p className={styles.validation} role="alert">From date must be before or equal to To date.</p>}
      {!validAmountRange && <p className={styles.validation} role="alert">Min amount must be less than or equal to Max amount.</p>}

      <div className={styles.tableWrap}>
        <table>
          <thead>
            <tr>
              <th scope="col">Merchant</th>
              <th className={styles.optionalColumn} scope="col">Category</th>
              <th scope="col" aria-sort={sortBy === "date" ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}>
                <button type="button" onClick={() => changeSort("date")}>Date {sortBy === "date" && (sortOrder === "asc" ? <ArrowUp size={14} /> : <ArrowDown size={14} />)}</button>
              </th>
              <th className={styles.optionalColumn} scope="col">Method</th>
              <th scope="col">Status</th>
              <th className={styles.amountHeader} scope="col" aria-sort={sortBy === "amount" ? (sortOrder === "asc" ? "ascending" : "descending") : "none"}>
                <button type="button" onClick={() => changeSort("amount")}>Amount {sortBy === "amount" && (sortOrder === "asc" ? <ArrowUp size={14} /> : <ArrowDown size={14} />)}</button>
              </th>
            </tr>
          </thead>
          <tbody>
            {!queryEnabled ? (
              <tr><td className={styles.stateCell} colSpan={6}>Correct the highlighted filter range to load transactions.</td></tr>
            ) : transactionsQuery.isPending ? (
              Array.from({ length: 8 }, (_, index) => <tr key={index} className={styles.skeletonRow}><td colSpan={6}><span /></td></tr>)
            ) : transactionsQuery.isError ? (
              <tr><td className={styles.stateCell} colSpan={6}>Unable to load transactions. <button type="button" onClick={() => transactionsQuery.refetch()}>Retry</button></td></tr>
            ) : transactions?.items.length === 0 ? (
              <tr><td className={styles.stateCell} colSpan={6}><strong>No transactions found</strong><span>Try adjusting your filters.</span></td></tr>
            ) : transactions?.items.map((transaction) => (
              <tr key={transaction.id}>
                <td className={styles.merchant}>{transaction.merchant}</td>
                <td className={styles.optionalColumn}>{transaction.category}</td>
                <td>{formatTransactionDate(transaction.transaction_at)}</td>
                <td className={styles.optionalColumn}>{transaction.payment_method}</td>
                <td><span className={`${styles.status} ${statusClass(transaction.status)}`}>{transaction.status}</span></td>
                <td className={styles.amount}>{formatCurrency(transaction.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <footer className={styles.pagination}>
        <span>Showing {resultsStart}–{resultsEnd} of {transactions?.total ?? 0} transactions</span>
        <label>Rows <select value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setPage(1); }}><option value={25}>25</option><option value={50}>50</option><option value={100}>100</option></select></label>
        <div>
          <button type="button" disabled={page === 1 || !transactions} onClick={() => setPage((current) => current - 1)}>Previous</button>
          <span>Page {transactions?.page ?? page} of {transactions?.total_pages ?? 0}</span>
          <button type="button" disabled={!transactions || page >= transactions.total_pages} onClick={() => setPage((current) => current + 1)}>Next</button>
        </div>
      </footer>
    </section>
  );
}
