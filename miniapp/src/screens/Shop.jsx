/*
 * The shop.
 *
 * TZ section 5 asks for filter, select, preview on the avatar, then buy. The
 * preview is the part that matters: nobody spends 900 coins on a shape in a
 * grid, so tapping an item puts it straight onto the player's own bear, over
 * whatever they are already wearing.
 */
import { useMemo, useState } from "react";

import { useCoins, useMyAvatar, usePurchase, useShop, useWardrobe } from "../api/queries";
import AvatarView, { ItemThumb } from "../components/AvatarView";
import { Button, Card, Coins, ErrorState, Skeleton, Tabs } from "../components/ui";
import { useT } from "../i18n";
import { haptic } from "../platform/telegram";

export default function Shop() {
  const t = useT();
  const [slot, setSlot] = useState(null);
  const [selected, setSelected] = useState(null);
  const [message, setMessage] = useState(null);

  const shop = useShop();
  const { data: avatar } = useMyAvatar();
  const { data: coins } = useCoins();
  const { data: wardrobe } = useWardrobe();
  const purchase = usePurchase();

  // Grouped by avatar SLOT, not by category. Two reasons: category_name comes
  // from the database in English and would stay English in every language,
  // and "hats" is how a player thinks about it anyway — the same grouping the
  // wardrobe uses, so the two screens sort the catalogue the same way.
  const slots = useMemo(() => {
    const present = new Set(
      (shop.data?.items ?? []).map((item) => item.category.slot)
    );
    return [...present].map((value) => ({ value, label: t(`slot.${value}`) }));
  }, [shop.data, t]);

  const owned = useMemo(
    () => new Set((wardrobe?.items ?? []).map((entry) => entry.item.item_id)),
    [wardrobe]
  );

  const items = (shop.data?.items ?? []).filter(
    (item) => slot === null || item.category.slot === slot
  );

  async function buy(item) {
    setMessage(null);
    try {
      const result = await purchase.mutateAsync(item.item_id);
      setMessage({
        ok: true,
        text: t("shop.bought", { item: item.name, balance: result.remaining_balance }),
      });
      haptic.success();
    } catch (err) {
      setMessage({
        ok: false,
        text: t(
          err.status === 400
            ? "shop.err_funds"
            : err.status === 409
              ? "shop.err_owned"
              : "shop.err_generic"
        ),
      });
      haptic.error();
    }
  }

  if (shop.isError) return <ErrorState error={shop.error} onRetry={shop.refetch} />;

  return (
    <div className="screen shop">
      <Card className="shop-preview">
        <AvatarView equipment={avatar?.equipment} preview={selected} size="150px" />
        <div className="shop-preview-info">
          {selected ? (
            <>
              <p className="item-name">{selected.name}</p>
              {selected.description ? (
                <p className="muted small">{selected.description}</p>
              ) : null}
              <p>
                <Coins amount={selected.price} />
              </p>
              {owned.has(selected.item_id) ? (
                <Button variant="ghost" disabled>
                  {t("shop.owned")}
                </Button>
              ) : (
                <Button
                  onClick={() => buy(selected)}
                  disabled={purchase.isPending || (coins?.balance ?? 0) < selected.price}
                >
                  {purchase.isPending
                    ? t("shop.buying")
                    : (coins?.balance ?? 0) < selected.price
                      ? t("shop.not_enough")
                      : t("shop.buy")}
                </Button>
              )}
            </>
          ) : (
            <p className="muted">{t("shop.pick_hint")}</p>
          )}
        </div>
      </Card>

      {message ? (
        <p className={`status ${message.ok ? "status-ok" : "status-err"}`}>{message.text}</p>
      ) : null}

      <Tabs
        value={slot}
        onChange={setSlot}
        options={[{ value: null, label: t("shop.all") }, ...slots]}
      />

      {shop.isLoading ? (
        <div className="grid">
          {Array.from({ length: 6 }, (_, index) => (
            <Skeleton key={index} height={120} radius={14} />
          ))}
        </div>
      ) : (
        <div className="grid">
          {items.map((item) => (
            <button
              key={item.item_id}
              className={`tile ${selected?.item_id === item.item_id ? "is-selected" : ""}`}
              onClick={() => {
                haptic.tap();
                setSelected(item);
              }}
            >
              <ItemThumb item={item} />
              <span className="tile-name">{item.name}</span>
              <span className="tile-price">
                {owned.has(item.item_id) ? t("shop.owned_short") : <Coins amount={item.price} />}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
