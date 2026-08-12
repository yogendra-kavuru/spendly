"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Cell,
  Pie,
  PieChart,
  type PieSectorDataItem,
  ResponsiveContainer,
  Tooltip,
  type TooltipContentProps,
} from "recharts";

import { getCategoryAnalytics } from "@/lib/api";
import {
  formatCompactCurrency,
  formatCurrency,
  formatMonthLabel,
  isValidMonthValue,
} from "@/lib/format";
import styles from "./spending-by-category.module.css";

const CATEGORY_COLORS = [
  "#3157cf",
  "#7589dc",
  "#23a184",
  "#df8a3d",
  "#a164c7",
  "#dd6262",
  "#2e9fc2",
  "#8492a8",
];

type ChartDatum = {
  category: string;
  amount: number;
  transactionCount: number;
  color: string;
};

type SpendingByCategoryProps = {
  selectedMonth: string | null;
  onCategorySelect?: (category: string) => void;
};

function CategoryTooltip({ active, payload }: TooltipContentProps) {
  if (!active || payload.length === 0) {
    return null;
  }

  const datum = payload[0].payload as ChartDatum;
  return (
    <div className={styles.tooltip}>
      <strong>{datum.category}</strong>
      <span>{formatCurrency(datum.amount)}</span>
      <span>{datum.transactionCount} transactions</span>
    </div>
  );
}

function AnalyticsSkeleton() {
  return (
    <div className={styles.loadingBody} aria-label="Loading spending analytics">
      <span className={styles.totalSkeleton} />
      <div className={styles.loadingGrid}>
        <span className={styles.donutSkeleton} />
        <div className={styles.rowSkeletons}>
          <span />
          <span />
          <span />
          <span />
        </div>
      </div>
    </div>
  );
}

export function SpendingByCategory({
  selectedMonth,
  onCategorySelect,
}: SpendingByCategoryProps) {
  const validSelectedMonth = selectedMonth && isValidMonthValue(selectedMonth)
    ? selectedMonth
    : null;
  const analyticsQuery = useQuery({
    queryKey: ["category-analytics", validSelectedMonth],
    queryFn: () => getCategoryAnalytics(validSelectedMonth ?? ""),
    enabled: Boolean(validSelectedMonth),
  });

  const analytics = analyticsQuery.data;
  const chartData: ChartDatum[] = (analytics?.items ?? []).map((item, index) => ({
    category: item.category,
    amount: Number(item.amount),
    transactionCount: item.transaction_count,
    color: CATEGORY_COLORS[index % CATEGORY_COLORS.length],
  }));
  const hasData = chartData.length > 0;
  const totalSpend = analytics?.total_spend ?? "0";
  const totalSpendNumber = Number(totalSpend);

  return (
    <article className={styles.card} aria-labelledby="spending-heading">
      <header className={styles.header}>
        <div>
          <h2 id="spending-heading">Spending by category</h2>
          <p>{validSelectedMonth ? formatMonthLabel(validSelectedMonth) : "Selected month"}</p>
        </div>
      </header>

      {!validSelectedMonth ? (
        <div className={styles.message}>Select a month to view spending analytics.</div>
      ) : analyticsQuery.isPending ? (
        <AnalyticsSkeleton />
      ) : analyticsQuery.isError ? (
        <div className={styles.message}>
          <p>Unable to load spending analytics.</p>
          <button type="button" onClick={() => analyticsQuery.refetch()}>
            Try again
          </button>
        </div>
      ) : !hasData ? (
        <div className={styles.emptyState}>
          <h3>No spending activity</h3>
          <p>No successful spending was recorded for this month.</p>
          <strong>{formatCurrency(analytics?.total_spend ?? "0")}</strong>
        </div>
      ) : (
        <>
          <div className={styles.total}>
            <strong>{formatCurrency(totalSpend)}</strong>
            <span>Total spend</span>
          </div>
          <div className={styles.analyticsBody}>
            <div className={styles.chartWrap}>
              <ResponsiveContainer width="100%" height={238}>
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="amount"
                    nameKey="category"
                    innerRadius={67}
                    outerRadius={96}
                    paddingAngle={2}
                    stroke="none"
                    cursor={onCategorySelect ? "pointer" : undefined}
                    onClick={(datum: PieSectorDataItem) => {
                      const chartDatum = datum.payload as ChartDatum;
                      onCategorySelect?.(chartDatum.category);
                    }}
                  >
                    {chartData.map((item) => (
                      <Cell key={item.category} fill={item.color} />
                    ))}
                  </Pie>
                  <Tooltip content={CategoryTooltip} />
                  <text x="50%" y="47%" textAnchor="middle" className={styles.centerValue}>
                    {formatCompactCurrency(totalSpend)}
                  </text>
                  <text x="50%" y="58%" textAnchor="middle" className={styles.centerLabel}>
                    Total spend
                  </text>
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className={styles.breakdown} aria-label="Category spending breakdown">
              {chartData.map((item) => {
                const percentage =
                  totalSpendNumber > 0
                    ? (item.amount / totalSpendNumber) * 100
                    : 0;
                return (
                  <button
                    className={styles.categoryRow}
                    key={item.category}
                    type="button"
                    onClick={() => onCategorySelect?.(item.category)}
                  >
                    <span className={styles.categoryName}>
                      <span
                        className={styles.colorDot}
                        style={{ backgroundColor: item.color }}
                        aria-hidden="true"
                      />
                      {item.category}
                    </span>
                    <span className={styles.categoryDetails}>
                      <span>{item.transactionCount} transactions · {percentage.toFixed(1)}%</span>
                      <strong>{formatCurrency(item.amount)}</strong>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </article>
  );
}
