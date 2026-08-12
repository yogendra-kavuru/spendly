"use client";

import { X } from "lucide-react";
import { useEffect, useId, useRef } from "react";

import { formatCurrency, formatTransactionDate, formatTransactionTime } from "@/lib/format";
import type { Transaction } from "@/lib/types";
import styles from "./transaction-drawer.module.css";

type TransactionDrawerProps = {
  transaction: Transaction | null;
  onClose: () => void;
};

function statusClass(status: Transaction["status"]): string {
  if (status === "SUCCESS") return styles.success;
  if (status === "FAILED") return styles.failed;
  return styles.pending;
}

export function TransactionDrawer({ transaction, onClose }: TransactionDrawerProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const titleId = useId();

  useEffect(() => {
    if (!transaction) {
      return;
    }

    const previouslyFocusedElement = document.activeElement;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const focusTimer = window.setTimeout(() => closeButtonRef.current?.focus(), 0);
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
      }
    };

    window.addEventListener("keydown", handleKeyDown);

    return () => {
      window.clearTimeout(focusTimer);
      window.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = originalOverflow;
      if (previouslyFocusedElement instanceof HTMLElement) {
        previouslyFocusedElement.focus();
      }
    };
  }, [onClose, transaction]);

  if (!transaction) {
    return null;
  }

  return (
    <div
      className={styles.backdrop}
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
    >
      <aside
        className={styles.drawer}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
      >
        <header className={styles.header}>
          <h2 id={titleId}>Transaction details</h2>
          <button ref={closeButtonRef} type="button" onClick={onClose} aria-label="Close transaction details">
            <X size={20} aria-hidden="true" />
          </button>
        </header>

        <div className={styles.content}>
          <div className={styles.summary}>
            <p className={styles.merchant}>{transaction.merchant}</p>
            <p className={styles.amount}>{formatCurrency(transaction.amount)}</p>
            <span className={`${styles.status} ${statusClass(transaction.status)}`}>{transaction.status}</span>
          </div>

          <dl className={styles.details}>
            <div>
              <dt>Transaction ID</dt>
              <dd>{transaction.transaction_id}</dd>
            </div>
            <div>
              <dt>Date</dt>
              <dd>{formatTransactionDate(transaction.transaction_at)}</dd>
            </div>
            <div>
              <dt>Time</dt>
              <dd>{formatTransactionTime(transaction.transaction_at)}</dd>
            </div>
            <div>
              <dt>Category</dt>
              <dd>{transaction.category}</dd>
            </div>
            <div>
              <dt>Payment method</dt>
              <dd>{transaction.payment_method}</dd>
            </div>
            <div>
              <dt>Currency</dt>
              <dd>{transaction.currency}</dd>
            </div>
          </dl>
        </div>
      </aside>
    </div>
  );
}
