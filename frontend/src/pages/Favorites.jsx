/**
 * pages/Favorites.jsx — User's saved properties
 *
 * Loads favourite IDs, then fetches listing details for each.
 * Heart button allows removing directly from this page.
 */

import { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { getFavorites, removeFavorite, getListingDetail } from "../api/client";
import { Link, Navigate } from "react-router-dom";
import toast from "react-hot-toast";

export default function Favorites() {
  const { token, user } = useAuth();
  const [favListings, setFavListings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    loadFavourites();
  }, [token]);

  async function loadFavourites() {
    setLoading(true);
    try {
      const data = await getFavorites(token);
      const favItems = data.items || data.favorites || [];
      
      // Fetch detail for each favourite
      const details = await Promise.all(
        favItems.map(async (f) => {
          try {
            const listing = await getListingDetail(f.listing_id);
            return { favId: f.id, listingId: f.listing_id, listing };
          } catch {
            return { favId: f.id, listingId: f.listing_id, listing: null };
          }
        })
      );
      setFavListings(details);
    } catch {
      setFavListings([]);
    } finally {
      setLoading(false);
    }
  }

  if (!user) return <Navigate to="/login" />;

  async function handleRemove(listingId) {
    try {
      await removeFavorite(token, listingId);
      setFavListings(prev => prev.filter(f => f.listingId !== listingId));
      toast.success("Removed from favourites");
    } catch (err) {
      toast.error(err?.detail || "Error");
    }
  }

  if (loading) return <p className="text-center py-10 text-slate-400">Loading favourites...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">My Favourites</h1>

      {favListings.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-slate-500 text-lg mb-4">No favourites yet.</p>
          <Link to="/" className="text-blue-600 underline">Browse properties</Link>
        </div>
      ) : (
        <div className="space-y-4">
          {favListings.map(f => (
            <div key={f.favId} className="flex items-center justify-between border rounded-lg p-4 hover:shadow-sm transition">
              <div className="flex-1">
                {f.listing ? (
                  <Link to={`/listings/${f.listingId}`} className="group">
                    <div className="flex items-center gap-3">
                      <span className="text-xs uppercase font-medium text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                        {f.listing.category}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded ${
                        f.listing.status === "active" ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                      }`}>{f.listing.status}</span>
                    </div>
                    <p className="text-lg font-semibold mt-1 group-hover:text-blue-600">{f.listing.address}</p>
                    <p className="text-blue-700 font-bold">&euro;{Number(f.listing.price).toLocaleString()}</p>
                    {f.listing.bedrooms != null && (
                      <p className="text-xs text-slate-500">{f.listing.bedrooms} bedrooms</p>
                    )}
                  </Link>
                ) : (
                  <p className="text-slate-400">Listing #{f.listingId} (unavailable)</p>
                )}
              </div>
              <button onClick={() => handleRemove(f.listingId)}
                className="ml-4 text-2xl hover:scale-110 transition" title="Remove">
                ❤️
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
