/**
 * api/client.js — HTTP Facade (Module pattern)
 *
 * Design Pattern: Facade + Module/Namespace
 * Every backend endpoint is hidden behind a named function.
 * Components never call fetch() directly.
 */

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function authParam(token) {
  return token ? `token=${token}` : "";
}

// ---------- Auth ----------
export async function register(username, email, password) {
  const res = await fetch(`${BASE}/users`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, email, password }),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function login(email, password) {
  const res = await fetch(`${BASE}/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function verifyOtp(email, otp) {
  const res = await fetch(`${BASE}/verify-otp`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, otp }),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function resendVerification(email) {
  const res = await fetch(`${BASE}/resend-verification?email=${encodeURIComponent(email)}`, {
    method: "POST",
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function logout(token) {
  const res = await fetch(`${BASE}/logout?${authParam(token)}`, { method: "POST" });
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function getMe(token) {
  const res = await fetch(`${BASE}/users/me?${authParam(token)}`);
  if (!res.ok) throw await res.json();
  return res.json();
}

// ---------- Listings ----------
export async function getListings(filters = {}) {
  const params = new URLSearchParams();
  if (filters.category) params.set("category", filters.category);
  if (filters.min_price) params.set("min_price", filters.min_price);
  if (filters.max_price) params.set("max_price", filters.max_price);
  if (filters.bedrooms) params.set("bedrooms", filters.bedrooms);
  if (filters.location) params.set("location", filters.location);
  if (filters.amenities) params.set("amenities", filters.amenities);
  const res = await fetch(`${BASE}/listings?${params}`);
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function getListingDetail(id) {
  const res = await fetch(`${BASE}/listings/${id}`);
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function createListing(token, data) {
  const res = await fetch(`${BASE}/listings?${authParam(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

// ---------- Favorites ----------
export async function getFavorites(token) {
  const res = await fetch(`${BASE}/favorites?${authParam(token)}`);
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function addFavorite(token, listingId) {
  const res = await fetch(`${BASE}/favorites?listing_id=${listingId}&${authParam(token)}`, {
    method: "POST",
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function removeFavorite(token, listingId) {
  const res = await fetch(`${BASE}/favorites/${listingId}?${authParam(token)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

// ---------- Bids ----------
export async function placeBid(token, listingId, amount) {
  const res = await fetch(`${BASE}/bids?${authParam(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ listing_id: listingId, amount }),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function getMyBids(token) {
  const res = await fetch(`${BASE}/bids/me?${authParam(token)}`);
  if (!res.ok) throw await res.json();
  return res.json();
}

// ---------- Viewings ----------
export async function requestViewing(token, listingId, viewingAt) {
  const res = await fetch(`${BASE}/viewings?${authParam(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ listing_id: listingId, viewing_at: viewingAt }),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

// ---------- Messages ----------
export async function sendMessage(token, listingId, content) {
  const res = await fetch(`${BASE}/messages?${authParam(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ listing_id: listingId, content }),
  });
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function getChats(token) {
  const res = await fetch(`${BASE}/chats?${authParam(token)}`);
  if (!res.ok) throw await res.json();
  return res.json();
}
