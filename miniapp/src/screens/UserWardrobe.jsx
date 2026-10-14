/*
 * Somebody else's wardrobe, read-only.
 *
 * Separate from the player's own wardrobe on purpose: that screen is about
 * dressing the bear, and every tile there is a button. Reusing it would mean
 * carrying an `isMine` flag through the whole component and hoping nobody
 * forgets it, which is how you end up letting one player undress another.
 *
 * The owner may have this switched off (TZ section 8), in which case the API
 * answers 403 and the screen says so plainly.
 */
import { useParams } from "react-router-dom";

import { useProfile, useUserWardrobe } from "../api/queries";
import { ItemThumb } from "../components/AvatarView";
import { Card, EmptyState, ErrorState, Skeleton } from "../components/ui";
import { useT } from "../i18n";

export default function UserWardrobe() {
  const t = useT();
  const { userId } = useParams();
  const profile = useProfile(userId);
  const wardrobe = useUserWardrobe(userId);

  if (wardrobe.error?.status === 403) {
    return (
      <EmptyState
        icon="🔒"
        title={t("wardrobe.hidden")}
        hint={t("wardrobe.hidden_hint")}
      />
    );
  }
  if (wardrobe.isError) return <ErrorState error={wardrobe.error} onRetry={wardrobe.refetch} />;

  const items = wardrobe.data?.items ?? [];

  return (
    <div className="screen wardrobe">
      <h1 className="screen-title">
        {t("wardrobe.of", { username: profile.data?.username ?? "" })}
      </h1>

      {wardrobe.isLoading ? (
        <div className="grid">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} height={120} radius={14} />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState icon="🎽" title={t("wardrobe.empty_other")} />
      ) : (
        <div className="grid">
          {items.map((entry) => (
            <Card key={entry.wardrobe_id} className="tile is-static">
              <ItemThumb item={entry.item} />
              <span className="tile-name">{entry.item.name}</span>
              <span className="tile-price">{entry.item.price} 🪙</span>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
