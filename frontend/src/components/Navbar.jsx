import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { logout as apiLogout } from "../api/client";

export default function Navbar() {
  const { user, token, logoutUser } = useAuth();
  const nav = useNavigate();

  async function handleLogout() {
    try { await apiLogout(token); } catch {}
    logoutUser();
    nav("/");
  }

  return (
    <nav className="bg-slate-800 text-white px-6 py-3 flex items-center justify-between">
      <Link to="/" className="text-xl font-bold tracking-tight">HomeFinder</Link>
      <div className="flex items-center gap-4 text-sm">
        <Link to="/" className="hover:text-blue-300">Browse</Link>
        {user ? (
          <>
            <Link to="/favorites" className="hover:text-blue-300">Favourites</Link>
            {user.type === "user" && (
              <Link to="/add-property" className="hover:text-blue-300">Add Property</Link>
            )}
            {user.type === "admin" && <Link to="/admin" className="hover:text-blue-300">Admin</Link>}
            <span className="text-slate-400">{user.username}</span>
            <button onClick={handleLogout} className="bg-red-600 px-3 py-1 rounded hover:bg-red-700">
              Logout
            </button>
          </>
        ) : (
          <Link to="/login" className="bg-blue-600 px-3 py-1 rounded hover:bg-blue-700">Login</Link>
        )}
      </div>
    </nav>
  );
}
