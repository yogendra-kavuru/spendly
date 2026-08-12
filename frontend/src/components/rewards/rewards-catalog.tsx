"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Coins, Gift, LockKeyhole, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { getRewards, redeemReward } from "@/lib/api";
import { formatNumber } from "@/lib/format";
import type { Reward, RewardBalanceResponse, RewardRedemptionResponse } from "@/lib/types";
import styles from "./rewards-catalog.module.css";

type RewardsCatalogProps = {
  balance: number | undefined;
  isBalanceLoading: boolean;
  isBalanceError: boolean;
};

function rewardErrorMessage(error: Error): string {
  if (error.message.includes("Insufficient reward balance")) {
    return "You don't have enough coins to redeem this reward.";
  }
  return "Unable to redeem this reward. Please try again.";
}

function RewardListSkeleton() {
  return (
    <div className={styles.skeletonList} aria-label="Loading rewards">
      <span />
      <span />
      <span />
    </div>
  );
}

export function RewardsCatalog({
  balance,
  isBalanceLoading,
  isBalanceError,
}: RewardsCatalogProps) {
  const queryClient = useQueryClient();
  const [selectedReward, setSelectedReward] = useState<Reward | null>(null);
  const [redemptionResult, setRedemptionResult] =
    useState<RewardRedemptionResponse | null>(null);
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const rewardsQuery = useQuery({ queryKey: ["rewards"], queryFn: getRewards });
  const redemptionMutation = useMutation({
    mutationFn: redeemReward,
    onSuccess: (result) => {
      queryClient.setQueryData<RewardBalanceResponse>(["reward-balance"], {
        balance: result.balance,
      });
      setRedemptionResult(result);
    },
    onError: () => {
      queryClient.invalidateQueries({ queryKey: ["reward-balance"] });
    },
  });

  const dialogOpen = selectedReward !== null || redemptionResult !== null;

  useEffect(() => {
    if (!dialogOpen) {
      return;
    }

    const previouslyFocusedElement = document.activeElement;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const focusTimer = window.setTimeout(() => closeButtonRef.current?.focus(), 0);

    return () => {
      window.clearTimeout(focusTimer);
      document.body.style.overflow = originalOverflow;
      if (previouslyFocusedElement instanceof HTMLElement) {
        previouslyFocusedElement.focus();
      }
    };
  }, [dialogOpen]);

  useEffect(() => {
    if (!dialogOpen) {
      return;
    }

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape" && !redemptionMutation.isPending) {
        setSelectedReward(null);
        setRedemptionResult(null);
        redemptionMutation.reset();
      }
    };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [dialogOpen, redemptionMutation]);

  const closeDialog = () => {
    if (redemptionMutation.isPending) {
      return;
    }
    setSelectedReward(null);
    setRedemptionResult(null);
    redemptionMutation.reset();
  };

  const currentBalance = balance ?? 0;

  return (
    <article className={styles.card} aria-labelledby="rewards-heading">
      <header className={styles.header}>
        <div>
          <h2 id="rewards-heading">Rewards</h2>
          <p>Redeem your coins</p>
        </div>
        <div className={styles.availableBalance}>
          <Coins size={15} aria-hidden="true" />
          {isBalanceLoading ? "Loading…" : isBalanceError ? "Balance unavailable" : `${formatNumber(currentBalance)} available`}
        </div>
      </header>

      {rewardsQuery.isPending ? (
        <RewardListSkeleton />
      ) : rewardsQuery.isError ? (
        <div className={styles.state}>
          <p>Unable to load rewards.</p>
          <button type="button" onClick={() => rewardsQuery.refetch()}>
            Try again
          </button>
        </div>
      ) : rewardsQuery.data.items.length === 0 ? (
        <div className={styles.state}>
          <h3>No rewards available</h3>
          <p>Check back later for new rewards.</p>
        </div>
      ) : (
        <div className={styles.rewardList}>
          {rewardsQuery.data.items.map((reward) => {
            const affordable = !isBalanceLoading && !isBalanceError && currentBalance >= reward.coin_cost;
            const coinsNeeded = reward.coin_cost - currentBalance;
            return (
              <section className={styles.rewardItem} key={reward.id}>
                <div className={styles.rewardCopy}>
                  <div className={styles.rewardTitleRow}>
                    <Gift size={16} aria-hidden="true" />
                    <h3>{reward.name}</h3>
                  </div>
                  <p>{reward.description}</p>
                  <span className={styles.rewardType}>{reward.reward_type}</span>
                </div>
                <div className={styles.rewardAction}>
                  <strong>{formatNumber(reward.coin_cost)} coins</strong>
                  {affordable ? (
                    <button type="button" onClick={() => setSelectedReward(reward)}>
                      Redeem
                    </button>
                  ) : (
                    <>
                      <span className={styles.needCoins}>
                        <LockKeyhole size={13} aria-hidden="true" />
                        {isBalanceLoading || isBalanceError
                          ? "Balance required"
                          : `Need ${formatNumber(coinsNeeded)} more coins`}
                      </span>
                      <button type="button" disabled aria-label={`Redeem ${reward.name}`}>
                        Redeem
                      </button>
                    </>
                  )}
                </div>
              </section>
            );
          })}
        </div>
      )}

      {dialogOpen && (
        <div className={styles.overlay} role="presentation" onMouseDown={closeDialog}>
          <section
            className={styles.dialog}
            role="dialog"
            aria-modal="true"
            aria-labelledby="redeem-dialog-title"
            onMouseDown={(event) => event.stopPropagation()}
          >
            <button
              ref={closeButtonRef}
              className={styles.closeButton}
              type="button"
              onClick={closeDialog}
              disabled={redemptionMutation.isPending}
              aria-label="Close reward redemption dialog"
            >
              <X size={18} aria-hidden="true" />
            </button>

            {redemptionResult ? (
              <div className={styles.successState}>
                <CheckCircle2 size={36} aria-hidden="true" />
                <h3 id="redeem-dialog-title">Reward redeemed</h3>
                <p>{redemptionResult.reward_name}</p>
                <strong>{formatNumber(redemptionResult.coins_spent)} coins used</strong>
                <span>{formatNumber(redemptionResult.balance)} coins remaining</span>
                <button type="button" onClick={closeDialog}>Done</button>
              </div>
            ) : selectedReward ? (
              <>
                <p className={styles.dialogEyebrow}>Confirm redemption</p>
                <h3 id="redeem-dialog-title">Redeem {selectedReward.name}?</h3>
                <div className={styles.costSummary}>
                  <span>Cost <strong>{formatNumber(selectedReward.coin_cost)} coins</strong></span>
                  <span>Current balance <strong>{formatNumber(currentBalance)} coins</strong></span>
                  <span>Balance after <strong>{formatNumber(currentBalance - selectedReward.coin_cost)} coins</strong></span>
                </div>
                {redemptionMutation.isError && (
                  <p className={styles.dialogError} role="alert">
                    {rewardErrorMessage(redemptionMutation.error)}
                  </p>
                )}
                <div className={styles.dialogActions}>
                  <button type="button" onClick={closeDialog} disabled={redemptionMutation.isPending}>
                    Cancel
                  </button>
                  <button
                    className={styles.confirmButton}
                    type="button"
                    disabled={redemptionMutation.isPending}
                    onClick={() => redemptionMutation.mutate(selectedReward.id)}
                  >
                    {redemptionMutation.isPending ? "Redeeming…" : "Confirm redemption"}
                  </button>
                </div>
              </>
            ) : null}
          </section>
        </div>
      )}
    </article>
  );
}
