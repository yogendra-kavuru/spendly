const MONTH_VALUE_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/;

export function isValidMonthValue(value: string): boolean {
  return MONTH_VALUE_PATTERN.test(value);
}

export function formatCurrency(value: string | number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(Number(value));
}

export function formatCompactCurrency(value: string | number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(Number(value));
}

export function formatMonthLabel(month: string): string {
  if (!isValidMonthValue(month)) {
    return "";
  }

  const [year, monthNumber] = month.split("-").map(Number);
  return new Intl.DateTimeFormat("en-IN", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, monthNumber - 1, 1)));
}

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-IN").format(value);
}

export function getMonthDateRange(month: string): { from: string; to: string } | null {
  if (!isValidMonthValue(month)) {
    return null;
  }

  const [year, monthNumber] = month.split("-").map(Number);
  const lastDay = new Date(Date.UTC(year, monthNumber, 0)).getUTCDate();
  return {
    from: `${month}-01`,
    to: `${month}-${String(lastDay).padStart(2, "0")}`,
  };
}

export function formatTransactionDate(timestamp: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Kolkata",
  }).format(new Date(timestamp));
}

export function formatTransactionTime(timestamp: string): string {
  return new Intl.DateTimeFormat("en-IN", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "Asia/Kolkata",
  }).format(new Date(timestamp));
}
