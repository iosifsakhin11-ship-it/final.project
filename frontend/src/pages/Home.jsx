import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getListings } from "../api/client";
import { useAuth } from "../contexts/AuthContext";
import PropertyCard from "../components/PropertyCard";

export default function Home() {
  const { user } = useAuth();
  const [listings, setListings] = useState([]);
  const [category, setCategory] = useState("");
  const [minPrice, setMinPrice] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [bedrooms, setBedrooms] = useState("");
  const [location, setLocation] = useState("");
  const [amenities, setAmenities] = useState("");

  useEffect(() => { fetchListings(); }, []);

  async function fetchListings() {
    try {
      const filters = {};
      if (category) filters.category = category;
      if (minPrice) filters.min_price = minPrice;
      if (maxPrice) filters.max_price = maxPrice;
      if (bedrooms) filters.bedrooms = bedrooms;
      if (location) filters.location = location;
      if (amenities) filters.amenities = amenities;
      const data = await getListings(filters);
      setListings(data.items || data.listings || []);
    } catch { setListings([]); }
  }

  function handleFilter(e) {
    e.preventDefault();
    fetchListings();
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Browse Properties</h1>

      <form onSubmit={handleFilter} className="flex flex-wrap gap-3 mb-6 p-4 bg-slate-50 rounded-lg">
        <input type="text" placeholder="Location" value={location} onChange={e => setLocation(e.target.value)}
          className="border rounded px-3 py-2 text-sm w-36" />
        <select value={category} onChange={e => setCategory(e.target.value)}
          className="border rounded px-3 py-2 text-sm">
          <option value="">All Categories</option>
          <option value="residential">Residential</option>
          <option value="commercial">Commercial</option>
          <option value="rental">Rental</option>
        </select>
        <input type="number" placeholder="Min price" value={minPrice} onChange={e => setMinPrice(e.target.value)}
          className="border rounded px-3 py-2 text-sm w-28" />
        <input type="number" placeholder="Max price" value={maxPrice} onChange={e => setMaxPrice(e.target.value)}
          className="border rounded px-3 py-2 text-sm w-28" />
        <input type="number" placeholder="Bedrooms" value={bedrooms} onChange={e => setBedrooms(e.target.value)}
          className="border rounded px-3 py-2 text-sm w-24" />
        <input type="text" placeholder="Amenities (pool,garden)" value={amenities} onChange={e => setAmenities(e.target.value)}
          className="border rounded px-3 py-2 text-sm w-44" />
        <button className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
          Search
        </button>
      </form>

      {listings.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-slate-500 text-lg mb-4">No properties found.</p>
          {user && user.type === "user" && (
            <Link to="/add-property"
              className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700">
              Add the first property
            </Link>
          )}
          {!user && (
            <p className="text-sm text-slate-400">
              <Link to="/login" className="text-blue-600 underline">Sign in</Link> to list a property.
            </p>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {listings.map(l => <PropertyCard key={l.id} listing={l} />)}
        </div>
      )}
    </div>
  );
}
