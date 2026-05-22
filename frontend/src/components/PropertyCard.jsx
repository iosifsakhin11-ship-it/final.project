import { Link } from "react-router-dom";
import HeartButton from "./HeartButton";

export default function PropertyCard({ listing }) {
  return (
    <div className="border rounded-lg overflow-hidden hover:shadow-lg transition relative">
      {/* Heart button - top right */}
      <div className="absolute top-2 right-2 z-10 bg-white/80 rounded-full p-1">
        <HeartButton listingId={listing.id} size="text-lg" />
      </div>

      <Link to={`/listings/${listing.id}`}>
        <div className="bg-slate-100 h-40 flex items-center justify-center text-slate-400">
          {listing.photos?.[0]
            ? <img src={`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/listings/photos/${listing.photos[0].url}`} alt="" className="h-full w-full object-cover" />
            : "No Photo"
          }
        </div>
      </Link>

      <div className="p-4">
        <div className="flex justify-between items-start mb-1">
          <span className="text-xs font-medium uppercase text-blue-600">{listing.category}</span>
          <span className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700">{listing.status}</span>
        </div>
        <p className="text-sm text-slate-600 truncate">{listing.address}</p>
        <p className="text-lg font-bold mt-1">&euro;{Number(listing.price).toLocaleString()}</p>
        {listing.bedrooms != null && (
          <p className="text-xs text-slate-500 mt-1">{listing.bedrooms} bedroom{listing.bedrooms !== 1 ? "s" : ""}</p>
        )}

        {/* Amenities preview */}
        {listing.amenities && listing.amenities.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {listing.amenities.slice(0, 3).map((a, i) => (
              <span key={i} className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded">{a}</span>
            ))}
            {listing.amenities.length > 3 && (
              <span className="text-xs text-slate-400">+{listing.amenities.length - 3}</span>
            )}
          </div>
        )}

        <Link to={`/listings/${listing.id}`}
          className="block mt-3 text-center text-sm bg-slate-800 text-white py-2 rounded hover:bg-slate-900">
          View Details
        </Link>
      </div>
    </div>
  );
}
