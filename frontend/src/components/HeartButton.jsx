/**
 * components/HeartButton.jsx — Favourite toggle (heart icon)
 *
 * Reusable across PropertyCard and Property detail page.
 * Checks current favourite state on mount, toggles on click.
 */

import { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { getFavorites, addFavorite, removeFavorite } from "../api/client";
import toast from "react-hot-toast";

export default function HeartButton({ listingId, size = "text-xl" }) {
  const { token, user } = useAuth();
  const [isFav, setIsFav] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) return;
    getFavorites(token)
      .then(d => {
        const items = d.items || d.favorites || [];
        setIsFav(items.some(f => f.listing_id === Number(listingId)));
      })
      .catch(() => {});
  }, [token, listingId]);

  async function toggle(e) {
    e.preventDefault();   // prevent Link navigation on PropertyCard
    e.stopPropagation();  // prevent card click
    if (!user) return toast.error("Sign in to save favourites");
    setLoading(true);
    try {
      if (isFav) {
        await removeFavorite(token, listingId);
        setIsFav(false);
        toast.success("Removed from favourites");
      } else {
        await addFavorite(token, listingId);
        setIsFav(true);
        toast.success("Saved to favourites");
      }
    } catch (err) {
      toast.error(err?.detail || "Could not update favourite");
    } finally {
      setLoading(false);
    }
  }

  if (!user) return null;

  return (
    <button
      onClick={toggle}
      disabled={loading}
      className={`${size} transition-transform hover:scale-110 disabled:opacity-50`}
      title={isFav ? "Remove from favourites" : "Save to favourites"}
    >
      {isFav ? "❤️" : "🤍"}
    </button>
  );
}
