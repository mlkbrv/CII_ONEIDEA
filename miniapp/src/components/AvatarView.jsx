/*
 * Renders an avatar by stacking its equipped layers.
 *
 * This is the payoff of drawing every garment on the same 512x768 canvas
 * (see scripts/generate_assets.py): there is no positioning code here at all.
 * Each layer is an absolutely-positioned image filling the same box, in slot
 * order, and the artwork lands where it belongs because it was drawn there.
 *
 * One component for every place an avatar appears — profile, shop preview,
 * wardrobe, both sides of a battle — so a garment can never sit correctly on
 * one screen and wrong on another.
 */

// Painting order, back to front. Bottoms before tops so a shirt hangs over the
// waistband; hair before hats so a cap sits on the hair; glasses last because
// they belong in front of everything on the face.
const SLOT_ORDER = ["bottom", "top", "shoes", "hair", "hat", "accessory"];

const BASE_BACK = "/media/avatar/base-back.svg";
const BASE = "/media/avatar/base.svg";

/**
 * @param equipment  the `equipment` map from GET /avatar — slot -> { item }
 * @param preview    an extra item to draw on top, for "try before you buy".
 *                   Replaces whatever occupies its slot.
 * @param size       any CSS length; the 2:3 aspect ratio is fixed.
 */
export default function AvatarView({ equipment, preview, size = "100%", className = "" }) {
  const worn = { ...(equipment || {}) };
  // The bear itself is decorative: what matters to a screen reader is which
  // garments are on it, and each of those carries its own name below.

  if (preview) {
    const slot = preview.category?.slot;
    if (slot) worn[slot] = { item: preview };
  }

  return (
    <div className={`avatar ${className}`} style={{ width: size }}>
      <img src={BASE_BACK} alt="" aria-hidden="true" />
      <img src={BASE} alt="" aria-hidden="true" />
      {SLOT_ORDER.map((slot) => {
        const item = worn[slot]?.item;
        if (!item) return null;
        return (
          <img
            key={slot}
            src={item.image_url}
            alt={item.name}
            // A garment whose file is missing must not leave a broken-image
            // icon glued to the bear — better an incomplete outfit.
            onError={(event) => {
              event.currentTarget.style.display = "none";
            }}
          />
        );
      })}
    </div>
  );
}

/** The small square used in shop and wardrobe grids. */
export function ItemThumb({ item, className = "" }) {
  const thumb = item.image_url.replace(/\.svg$/, ".thumb.svg");
  return (
    <img
      className={`thumb ${className}`}
      src={thumb}
      alt={item.name}
      loading="lazy"
      // Fall back to the full layer if a thumbnail is missing: the item will
      // look small in its tile, which beats an empty tile.
      onError={(event) => {
        if (event.currentTarget.src.endsWith(".thumb.svg")) {
          event.currentTarget.src = item.image_url;
        }
      }}
    />
  );
}
