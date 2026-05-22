/**
 * pages/CreateListing.jsx — Add Property Form
 *
 * Calls POST /listings with: category, address, price, bedrooms, amenities.
 * Only accessible to authenticated users with type=user.
 * Redirects to Home after successful creation.
 */

import { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { createListing } from "../api/client";
import toast from "react-hot-toast";

export default function CreateListing() {
  const { token, user } = useAuth();
  const nav = useNavigate();

  const [category, setCategory] = useState("residential");
  const [address, setAddress] = useState("");
  const [price, setPrice] = useState("");
  const [bedrooms, setBedrooms] = useState("");
  const [amenitiesText, setAmenitiesText] = useState("");
  const [loading, setLoading] = useState(false);

  if (!user) return <Navigate to="/login" />;

  async function handleSubmit(e) {
    e.preventDefault();

    if (!address.trim()) return toast.error("Address is required");
    if (!price || Number(price) <= 0) return toast.error("Enter a valid price");

    const amenities = amenitiesText
      .split(",")
      .map(a => a.trim())
      .filter(a => a.length > 0);

    const data = {
      category,
      address: address.trim(),
      price: Number(price),
      bedrooms: bedrooms ? Number(bedrooms) : null,
      amenities: amenities.length > 0 ? amenities : [],
    };

    setLoading(true);
    try {
      await createListing(token, data);
      toast.success("Property listed successfully!");
      nav("/");
    } catch (err) {
      toast.error(err?.detail || "Failed to create listing");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl mx-auto mt-8">
      <h1 className="text-2xl font-bold mb-6">Add Property</h1>

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Category */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Property Type</label>
          <select value={category} onChange={e => setCategory(e.target.value)}
            className="w-full border rounded px-3 py-2">
            <option value="residential">Residential</option>
            <option value="commercial">Commercial</option>
            <option value="rental">Rental</option>
          </select>
        </div>

        {/* Address / Location */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Address / Location</label>
          <input type="text" value={address} onChange={e => setAddress(e.target.value)}
            placeholder="e.g. 123 Athens Central, Greece"
            required className="w-full border rounded px-3 py-2" />
        </div>

        {/* Price */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Price (€)</label>
          <input type="number" value={price} onChange={e => setPrice(e.target.value)}
            placeholder="250000" min="1" step="1"
            required className="w-full border rounded px-3 py-2" />
        </div>

        {/* Bedrooms */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Bedrooms</label>
          <input type="number" value={bedrooms} onChange={e => setBedrooms(e.target.value)}
            placeholder="3" min="0" max="50"
            className="w-full border rounded px-3 py-2" />
        </div>

        {/* Amenities */}
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Amenities</label>
          <input type="text" value={amenitiesText} onChange={e => setAmenitiesText(e.target.value)}
            placeholder="pool, garden, parking, gym"
            className="w-full border rounded px-3 py-2" />
          <p className="text-xs text-slate-400 mt-1">Separate with commas</p>
        </div>

        {/* Submit */}
        <button type="submit" disabled={loading}
          className="w-full bg-blue-600 text-white py-3 rounded-lg text-lg font-medium hover:bg-blue-700 disabled:opacity-50">
          {loading ? "Creating..." : "List Property"}
        </button>
      </form>
    </div>
  );
}
