/*
 * Wardrobe — what the player owns, and dressing the bear with it.
 *
 * TZ sections 5 and 17 keep the wardrobe and the avatar as separate ideas, but
 * on a phone they are one screen: you look at the bear and tap things onto it.
 * Splitting them would mean tapping an item, going back, checking, going
 * forward again.
 *
 * Equipping is optimistic in feel but not in fact — the avatar re-renders from
 * the server's answer, because the server is what decides which slot an item
 * lands in and what it replaces.
 */
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { useEquip, useMyAvatar, useWardrobe } from "../api/queries";
import AvatarView, { ItemThumb } from "../components/AvatarView";
import { Button, Card, EmptyState, ErrorState, Skeleton, Tabs } from "../components/ui";
import { haptic } from "../platform/telegram";

const SLOT_LABELS = {
  hair: "Причёски",
  hat: "Головные уборы",
  top: "Верх",
  bottom: "Низ",
  shoes: "Обувь",
  accessory: "Аксессуары",
};

export default function Wardrobe() {
  const [slot, setSlot] = useState(null);
  const wardrobe = useWardrobe();
  const { data: avatar } = useMyAvatar();
  const equip = useEquip();

  // Which wardrobe entry is currently worn, per slot. The avatar reports the
  // ITEM it wears, so the lookup goes item -> wardrobe entry to know what to
  // send to the unequip endpoint.
  const wornItemIds = useMemo(() => {
    const ids = new Set();
    for (const entry of Object.values(avatar?.equipment ?? {})) {
      if (entry?.item) ids.add(entry.item.item_id);
    }
    return ids;
  }, [avatar]);

  const entries = wardrobe.data?.items ?? [];
  const slots = useMemo(() => {
    const present = new Set(entries.map((entry) => entry.item.category.slot));
    return [...present].map((value) => ({ value, label: SLOT_LABELS[value] ?? value }));
  }, [entries]);

  const visible = entries.filter((entry) => slot === null || entry.item.category.slot === slot);

  async function toggle(entry) {
    const worn = wornItemIds.has(entry.item.item_id);
    try {
      await equip.mutateAsync({ wardrobeId: entry.wardrobe_id, equip: !worn });
      haptic.success();
    } catch {
      haptic.error();
    }
  }

  if (wardrobe.isError) {
    return <ErrorState error={wardrobe.error} onRetry={wardrobe.refetch} />;
  }

  return (
    <div className="screen wardrobe">
      <Card className="wardrobe-avatar">
        <AvatarView equipment={avatar?.equipment} size="170px" />
      </Card>

      {wardrobe.isLoading ? (
        <div className="grid">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} height={120} radius={14} />
          ))}
        </div>
      ) : entries.length === 0 ? (
        <EmptyState
          icon="🎽"
          title="Гардероб пуст"
          hint="Активируй код с крышки, чтобы получить монеты, и загляни в магазин."
          action={
            <Link to="/shop">
              <Button variant="ghost">В магазин</Button>
            </Link>
          }
        />
      ) : (
        <>
          <Tabs
            value={slot}
            onChange={setSlot}
            options={[{ value: null, label: "Всё" }, ...slots]}
          />
          <div className="grid">
            {visible.map((entry) => {
              const worn = wornItemIds.has(entry.item.item_id);
              return (
                <button
                  key={entry.wardrobe_id}
                  className={`tile ${worn ? "is-worn" : ""}`}
                  onClick={() => toggle(entry)}
                  disabled={equip.isPending}
                >
                  <ItemThumb item={entry.item} />
                  <span className="tile-name">{entry.item.name}</span>
                  <span className="tile-price">{worn ? "Снять" : "Надеть"}</span>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
