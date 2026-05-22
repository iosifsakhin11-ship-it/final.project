/**
 * pages/Admin.jsx — Admin Dashboard
 *
 * RBAC-gated via require_admin on the backend.
 * Shows user list and listing management.
 * Only visible to users with type=admin.
 */

import { useState, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { Navigate } from "react-router-dom";
import toast from "react-hot-toast";

const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export default function Admin() {
  const { token, user } = useAuth();
  const [tab, setTab] = useState("users");
  const [users, setUsers] = useState([]);
  const [listings, setListings] = useState([]);

  useEffect(() => {
    if (token && user?.type === "admin") {
      fetchUsers();
      fetchListings();
    }
  }, [token, user]);

  if (!user) return <Navigate to="/login" />;
  if (user.type !== "admin") return <p className="text-center py-10 text-red-600">Access denied. Admin role required.</p>;

  async function fetchUsers() {
    try {
      const res = await fetch(`${BASE}/admin/users?token=${token}`);
      if (res.ok) { const d = await res.json(); setUsers(d.users || []); }
    } catch {}
  }

  async function fetchListings() {
    try {
      const res = await fetch(`${BASE}/admin/listings?token=${token}`);
      if (res.ok) { const d = await res.json(); setListings(d.listings || []); }
    } catch {}
  }

  async function toggleBan(uid, currentlyBanned) {
    try {
      const res = await fetch(`${BASE}/admin/users/${uid}?token=${token}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_banned: !currentlyBanned }),
      });
      if (res.ok) { toast.success(currentlyBanned ? "Unbanned" : "Banned"); fetchUsers(); }
      else { const e = await res.json(); toast.error(e.detail || "Error"); }
    } catch { toast.error("Network error"); }
  }

  async function deleteListing(lid) {
    try {
      const res = await fetch(`${BASE}/admin/listings/${lid}?token=${token}`, { method: "DELETE" });
      if (res.ok) { toast.success("Listing removed"); fetchListings(); }
      else { const e = await res.json(); toast.error(e.detail || "Error"); }
    } catch { toast.error("Network error"); }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Admin Dashboard</h1>
      <div className="flex gap-2 mb-6">
        <button onClick={() => setTab("users")}
          className={`px-4 py-2 rounded text-sm ${tab === "users" ? "bg-slate-800 text-white" : "bg-slate-100"}`}>
          Users ({users.length})
        </button>
        <button onClick={() => setTab("listings")}
          className={`px-4 py-2 rounded text-sm ${tab === "listings" ? "bg-slate-800 text-white" : "bg-slate-100"}`}>
          Listings ({listings.length})
        </button>
      </div>

      {tab === "users" && (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="bg-slate-100 text-left">
              <th className="p-2 border">ID</th>
              <th className="p-2 border">Username</th>
              <th className="p-2 border">Email</th>
              <th className="p-2 border">Type</th>
              <th className="p-2 border">Verified</th>
              <th className="p-2 border">Banned</th>
              <th className="p-2 border">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map(u => (
              <tr key={u.id} className="hover:bg-slate-50">
                <td className="p-2 border">{u.id}</td>
                <td className="p-2 border">{u.username}</td>
                <td className="p-2 border">{u.email}</td>
                <td className="p-2 border">{u.type}</td>
                <td className="p-2 border">{u.is_verified ? "Yes" : "No"}</td>
                <td className="p-2 border">{u.is_banned ? "Yes" : "No"}</td>
                <td className="p-2 border">
                  <button onClick={() => toggleBan(u.id, u.is_banned)}
                    className={`text-xs px-2 py-1 rounded ${u.is_banned ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>
                    {u.is_banned ? "Unban" : "Ban"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {tab === "listings" && (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="bg-slate-100 text-left">
              <th className="p-2 border">ID</th>
              <th className="p-2 border">Address</th>
              <th className="p-2 border">Category</th>
              <th className="p-2 border">Price</th>
              <th className="p-2 border">Status</th>
              <th className="p-2 border">Actions</th>
            </tr>
          </thead>
          <tbody>
            {listings.map(l => (
              <tr key={l.id} className="hover:bg-slate-50">
                <td className="p-2 border">{l.id}</td>
                <td className="p-2 border">{l.address}</td>
                <td className="p-2 border">{l.category}</td>
                <td className="p-2 border">&euro;{Number(l.price).toLocaleString()}</td>
                <td className="p-2 border">{l.status}</td>
                <td className="p-2 border">
                  <button onClick={() => deleteListing(l.id)}
                    className="text-xs px-2 py-1 rounded bg-red-100 text-red-700">
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
