/**
 * pages/Property.jsx — Listing Detail Page
 *
 * Shows full property information, favourite toggle,
 * bid form, inquiry form, and viewing request.
 */

import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import HeartButton from "../components/HeartButton";
import * as api from "../api/client";
import toast from "react-hot-toast";

export default function Property() {
  const { id } = useParams();
  const { token, user } = useAuth();
  const [listing, setListing] = useState(null);
  const [error, setError] = useState(false);
  const [bidAmount, setBidAmount] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    setError(false);
    api.getListingDetail(id)
      .then(data => {
        setListing(data);
      })
      .catch(err => {
        console.error("Detail fetch error:", err);
        setError(true);
      });
  }, [id]);

  async function handleBid(e) {
    e.preventDefault();
    if (!token) return toast.error("Please sign in");
    try {
      await api.placeBid(token, Number(id), Number(bidAmount));
      toast.success("Bid placed successfully");
      setBidAmount("");
    } catch (err) { toast.error(err?.detail || "Bid failed"); }
  }

  async function handleInquiry(e) {
    e.preventDefault();
    if (!token) return toast.error("Please sign in");
    try {
      await api.sendMessage(token, Number(id), message);
      toast.success("Inquiry sent");
      setMessage("");
    } catch (err) { toast.error(err?.detail || "Could not send"); }
  }

  async function handleViewing() {
    if (!token) return toast.error("Please sign in");
    try {
      const viewingAt = new Date(Date.now() + 3 * 86400000).toISOString();
      await api.requestViewing(token, Number(id), viewingAt);
      toast.success("Viewing requested");
    } catch (err) { toast.error(err?.detail || "Could not request viewing"); }
  }

  // Error state
  if (error) {
    return (
      <div className="text-center py-16">
        <p className="text-xl text-red-500 mb-4">Property not found</p>
        <Link to="/" className="text-blue-600 underline">Back to Browse</Link>
      </div>
    );
  }

  // Loading state
  if (!listing) {
    return <p className="text-center py-16 text-slate-400 text-lg">Loading property details...</p>;
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Back link */}
      <Link to="/" className="text-sm text-slate-500 hover:text-blue-600 mb-4 inline-block">&larr; Back to Browse</Link>

      {/* Header row: category + status + heart */}
      <div className="flex items-center justify-between mb-2">
        <div>
          <span className="text-xs uppercase font-semibold text-blue-600 bg-blue-50 px-2 py-1 rounded">{listing.category}</span>
          <span className={`ml-2 text-xs px-2 py-1 rounded font-medium ${
            listing.status === "active" ? "bg-green-100 text-green-700" :
            listing.status === "sold" ? "bg-red-100 text-red-700" :
            "bg-slate-100 text-slate-600"
          }`}>{listing.status}</span>
        </div>
        <HeartButton listingId={listing.id} size="text-2xl" />
      </div>

      {/* Address + Price */}
      <h1 className="text-2xl font-bold mt-2">{listing.address}</h1>
      <p className="text-3xl font-bold text-blue-700 mt-2">&euro;{Number(listing.price).toLocaleString()}</p>

      {/* Details grid */}
      <div className="grid grid-cols-2 gap-4 mt-4 p-4 bg-slate-50 rounded-lg">
        {listing.bedrooms != null && (
          <div>
            <p className="text-xs text-slate-500 uppercase">Bedrooms</p>
            <p className="text-lg font-semibold">{listing.bedrooms}</p>
          </div>
        )}
        <div>
          <p className="text-xs text-slate-500 uppercase">Category</p>
          <p className="text-lg font-semibold capitalize">{listing.category}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500 uppercase">Listed</p>
          <p className="text-sm">{new Date(listing.created_at).toLocaleDateString()}</p>
        </div>
        <div>
          <p className="text-xs text-slate-500 uppercase">Property ID</p>
          <p className="text-sm">#{listing.id}</p>
        </div>
      </div>

      {/* Amenities */}
      {listing.amenities && listing.amenities.length > 0 && (
        <div className="mt-4">
          <p className="text-xs text-slate-500 uppercase mb-2">Amenities</p>
          <div className="flex flex-wrap gap-2">
            {listing.amenities.map((a, i) => (
              <span key={i} className="text-sm bg-blue-50 text-blue-700 px-3 py-1 rounded-full">{a}</span>
            ))}
          </div>
        </div>
      )}

      {/* Action buttons */}
      {user && listing.status === "active" && (
        <>
          <div className="mt-6 flex flex-wrap gap-3">
            <button onClick={handleViewing}
              className="bg-teal-600 text-white px-5 py-2 rounded hover:bg-teal-700 text-sm font-medium">
              Request Viewing
            </button>
          </div>

          {/* Bid + Inquiry forms */}
          <div className="mt-6 grid sm:grid-cols-2 gap-6">
            <form onSubmit={handleBid} className="p-4 border rounded-lg space-y-3">
              <h2 className="font-semibold">Place a Bid</h2>
              <input type="number" placeholder="Amount (€)" value={bidAmount}
                onChange={e => setBidAmount(e.target.value)}
                required min="1" className="w-full border rounded px-3 py-2" />
              <button className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700">Submit Bid</button>
            </form>
            <form onSubmit={handleInquiry} className="p-4 border rounded-lg space-y-3">
              <h2 className="font-semibold">Send Inquiry</h2>
              <textarea placeholder="Your message" value={message}
                onChange={e => setMessage(e.target.value)}
                required rows={3} className="w-full border rounded px-3 py-2" />
              <button className="w-full bg-slate-700 text-white py-2 rounded hover:bg-slate-800">Send</button>
            </form>
          </div>
        </>
      )}

      {!user && (
        <p className="mt-6 text-slate-500 text-sm">
          <Link to="/login" className="text-blue-600 underline">Sign in</Link> to place bids, send inquiries, or request viewings.
        </p>
      )}
    </div>
  );
}
