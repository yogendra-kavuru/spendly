"use client";

import { useQuery } from "@tanstack/react-query";
import { CalendarDays, Coins, ReceiptText } from "lucide-react";
import { useState } from "react";

import { getRewardBalance, getTransactions } from "@/lib/api";
import { formatMonthLabel, formatNumber, isValidMonthValue } from "@/lib/format";
import { SpendingByCategory } from "@/components/analytics/spending-by-category";
import { RewardsCatalog } from "@/components/rewards/rewards-catalog";
import styles from "./dashboard-shell.module.css";

function monthFromTransactionTimestamp(timestamp: string): string {
  return timestamp.slice(0, 7);
}

export function DashboardShell() {
  const [selectedMonth, setSelectedMonth] = useState<string | null>(null);
  const [monthInputValue, setMonthInputValue] = useState<string | null>(null);
  const balanceQuery = useQuery({
    queryKey: ["reward-balance"],
    queryFn: getRewardBalance,
  });
  const latestTransactionQuery = useQuery({
    queryKey: [
      "transactions",
      { page: 1, page_size: 1, sort_by: "date", sort_order: "desc" },
    ],
    queryFn: () =>
      getTransactions({
        page: 1,
        page_size: 1,
        sort_by: "date",
        sort_order: "desc",
      }),
  });

  const latestTransaction = latestTransactionQuery.data?.items[0];
  const initialMonth = latestTransaction
    ? monthFromTransactionTimestamp(latestTransaction.transaction_at)
    : null;
  const resolvedMonth = selectedMonth ?? initialMonth;
  const analyticsMonth = resolvedMonth && isValidMonthValue(resolvedMonth)
    ? resolvedMonth
    : null;
  const inputMonth = monthInputValue ?? analyticsMonth ?? "";
  const isInputMonthValid = isValidMonthValue(inputMonth);
  const monthUnavailable =
    latestTransactionQuery.isError ||
    (!latestTransactionQuery.isPending && latestTransaction === undefined);
  const balanceContent = balanceQuery.isPending ? (
    <span className={styles.balanceSkeleton} aria-label="Loading reward balance" />
  ) : balanceQuery.isError ? (
    <span className={styles.balanceError}>Balance unavailable</span>
  ) : (
    <span>{formatNumber(balanceQuery.data.balance)} coins</span>
  );

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <div className={styles.brand}>
            <span className={styles.brandMark} aria-hidden="true">
              S
            </span>
            <div>
              <p className={styles.brandName}>Spendly</p>
              <p className={styles.subtitle}>Personal spending &amp; rewards</p>
            </div>
          </div>

          <div className={styles.balancePill} aria-live="polite">
            <Coins size={18} aria-hidden="true" />
            {balanceContent}
          </div>
        </div>
      </header>

      <main className={styles.main}>
        <section className={styles.intro} aria-labelledby="overview-heading">
          <div>
            <p className={styles.eyebrow}>Dashboard</p>
            <h1 id="overview-heading">Overview</h1>
            <p className={styles.introCopy}>
              A clearer view of your spending and rewards.
            </p>
          </div>

          <div className={styles.monthControl}>
            <label htmlFor="selected-month">Selected month</label>
            <div className={styles.monthInputWrap}>
              <CalendarDays size={18} aria-hidden="true" />
              <input
                id="selected-month"
                type="month"
                value={inputMonth}
                disabled={latestTransactionQuery.isPending || monthUnavailable}
                onChange={(event) => {
                  const nextValue = event.target.value;
                  setMonthInputValue(nextValue);
                  if (isValidMonthValue(nextValue)) {
                    setSelectedMonth(nextValue);
                  }
                }}
              />
            </div>
            {isInputMonthValid ? (
              <p className={styles.monthHint}>{formatMonthLabel(inputMonth)}</p>
            ) : monthInputValue !== null ? (
              <p className={styles.monthHint} aria-live="polite" />
            ) : latestTransactionQuery.isPending ? (
              <p className={styles.monthHint}>Determining latest transaction month…</p>
            ) : (
              <p className={styles.monthError}>
                Unable to determine latest transaction month
              </p>
            )}
          </div>
        </section>

        <section className={styles.overviewGrid} aria-label="Dashboard overview">
          <SpendingByCategory selectedMonth={analyticsMonth} />
          <RewardsCatalog
            balance={balanceQuery.data?.balance}
            isBalanceLoading={balanceQuery.isPending}
            isBalanceError={balanceQuery.isError}
          />
        </section>

        <section className={styles.transactionsPlaceholder} aria-labelledby="transactions-heading">
          <div className={styles.sectionHeading}>
            <div>
              <p className={styles.eyebrow}>Activity</p>
              <h2 id="transactions-heading">Transactions</h2>
            </div>
            <ReceiptText size={22} aria-hidden="true" />
          </div>
          <p>Transaction table coming next.</p>
        </section>
      </main>
    </div>
  );
}
