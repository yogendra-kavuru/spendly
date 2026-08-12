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
export function isValidMonthValue(value: string): boolean {
  return MONTH_VALUE_PATTERN.test(value);
}
const MONTH_VALUE_PATTERN = /^\d{4}-(0[1-9]|1[0-2])$/;

export function formatNumber(value: number): string {
  return new Intl.NumberFormat("en-IN").format(value);
}
