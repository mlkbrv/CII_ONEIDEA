/*
 * Every server call the app makes, in one place.
 *
 * Screens import a hook from here rather than calling fetch, so the cache keys
 * and — more importantly — the invalidation rules live together. Getting those
 * wrong is what makes a game like this feel broken: buy a hat and the coin
 * balance in the header must drop immediately, vote and the score must move.
 * Each mutation below states exactly what it makes stale.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";

const qs = (params) => {
  const search = new URLSearchParams(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "")
  ).toString();
  return search ? `?${search}` : "";
};

// --- Reads -----------------------------------------------------------------

export function useMe() {
  return useQuery({ queryKey: ["me"], queryFn: () => api("/users/me") });
}

export function useCoins() {
  return useQuery({ queryKey: ["coins"], queryFn: () => api("/users/me/coins") });
}

export function useMyAvatar() {
  return useQuery({ queryKey: ["avatar"], queryFn: () => api("/avatar") });
}

export function useWardrobe() {
  return useQuery({
    queryKey: ["wardrobe"],
    queryFn: () => api("/wardrobe?limit=100"),
  });
}

export function useShop(categoryId) {
  return useQuery({
    queryKey: ["shop", categoryId ?? "all"],
    queryFn: () => api(`/clothing${qs({ limit: 100, category_id: categoryId })}`),
  });
}

export function useProfile(userId) {
  return useQuery({
    queryKey: ["profile", userId],
    queryFn: () => api(`/users/${userId}`),
    enabled: Boolean(userId),
  });
}

export function useFollowers(userId, kind = "followers") {
  return useQuery({
    queryKey: ["follows", userId, kind],
    queryFn: () => api(`/users/${userId}/${kind}?limit=100`),
    enabled: Boolean(userId),
  });
}

export function useUserWardrobe(userId) {
  return useQuery({
    queryKey: ["user-wardrobe", userId],
    queryFn: () => api(`/users/${userId}/wardrobe?limit=100`),
    enabled: Boolean(userId),
    // A private wardrobe answers 403 and will keep answering 403; retrying is
    // just three more requests before the same "hidden" message.
    retry: false,
  });
}

export function useSearch(term) {
  return useQuery({
    queryKey: ["search", term],
    queryFn: () => api(`/users/search${qs({ q: term, limit: 20 })}`),
    // Below two characters the result is everyone, which is not a search.
    enabled: term.trim().length >= 2,
  });
}

export function useMyCompetitions(status) {
  return useQuery({
    queryKey: ["competitions", status ?? "all"],
    queryFn: () => api(`/competitions${qs({ status, limit: 50 })}`),
    // A battle's score moves while the user is looking at it.
    refetchInterval: 15_000,
  });
}

export function useDiscover(scope = "following") {
  return useQuery({
    queryKey: ["discover", scope],
    queryFn: () => api(`/competitions/discover${qs({ scope, limit: 50 })}`),
    refetchInterval: 30_000,
  });
}

export function useCompetition(competitionId) {
  return useQuery({
    queryKey: ["competition", competitionId],
    queryFn: () => api(`/competitions/${competitionId}`),
    enabled: Boolean(competitionId),
    refetchInterval: 10_000,
  });
}

export function useRequests(direction) {
  return useQuery({
    queryKey: ["requests", direction],
    queryFn: () => api(`/competition-requests/${direction}`),
  });
}

export function useLeaderboard(metric = "streak") {
  return useQuery({
    queryKey: ["leaderboard", metric],
    queryFn: () => api(`/leaderboard${qs({ metric, limit: 50 })}`),
  });
}

export function useNotifications() {
  return useQuery({
    queryKey: ["notifications"],
    queryFn: () => api("/notifications?limit=50"),
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: ["unread"],
    queryFn: () => api("/notifications/unread-count"),
    refetchInterval: 30_000,
  });
}

// --- Writes ----------------------------------------------------------------

export function useRedeemCode() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (code) => api("/qr/redeem", { method: "POST", body: { code } }),
    // Coins changed, so anything that shows a balance or a purchase history is
    // now wrong. The shop is included because affordability is drawn per item.
    onSuccess: () => invalidate(client, ["coins", "me", "shop", "transactions"]),
  });
}

export function usePurchase() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (itemId) => api(`/clothing/${itemId}/purchase`, { method: "POST" }),
    onSuccess: () => invalidate(client, ["coins", "me", "shop", "wardrobe"]),
  });
}

export function useEquip() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ wardrobeId, equip }) =>
      api(`/wardrobe/${wardrobeId}/equip`, { method: equip ? "POST" : "DELETE" }),
    // The avatar is rendered on the profile and on both sides of a battle.
    onSuccess: () => invalidate(client, ["avatar", "wardrobe", "profile"]),
  });
}

export function useFollow() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ userId, follow }) =>
      api(`/users/${userId}/follow`, { method: follow ? "POST" : "DELETE" }),
    // Following changes whose battles appear in the "other battles" feed.
    onSuccess: () => invalidate(client, ["profile", "follows", "search", "discover"]),
  });
}

export function useChallenge() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ opponentId, durationMinutes }) =>
      api("/competition-requests", {
        method: "POST",
        body: { opponent_id: opponentId, duration_minutes: durationMinutes },
      }),
    onSuccess: () => invalidate(client, ["requests", "competitions", "profile"]),
  });
}

export function useRespondToRequest() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ requestId, action }) =>
      api(`/competition-requests/${requestId}/${action}`, { method: "POST" }),
    // Accepting creates a battle and cancels conflicting requests, so both
    // lists and the profile's "in a battle right now" badge are stale.
    onSuccess: () => invalidate(client, ["requests", "competitions", "profile", "discover"]),
  });
}

export function useVote() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ competitionId, votedForUserId }) =>
      api(`/competitions/${competitionId}/votes`, {
        method: "POST",
        body: { voted_for_user_id: votedForUserId },
      }),
    // A vote costs a coin and grows the prize pool: the score, the balance and
    // every list showing that battle all move together.
    onSuccess: () => invalidate(client, ["competition", "competitions", "discover", "coins", "me"]),
  });
}

export function useMarkAllRead() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => api("/notifications/read-all", { method: "POST" }),
    onSuccess: () => invalidate(client, ["notifications", "unread"]),
  });
}

function invalidate(client, prefixes) {
  for (const prefix of prefixes) {
    client.invalidateQueries({ queryKey: [prefix] });
  }
}
