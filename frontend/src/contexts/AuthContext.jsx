/**
 * contexts/AuthContext.jsx — Context + Provider Pattern
 *
 * Design Pattern: Context + Provider
 * Global auth state without prop-drilling. Hides localStorage storage.
 * Components consume via useAuth() hook.
 */

import { createContext, useContext, useState, useEffect } from "react";
import { getMe } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("hf_token"));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (token) {
      getMe(token)
        .then(setUser)
        .catch(() => {
          localStorage.removeItem("hf_token");
          setToken(null);
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, [token]);

  function loginUser(rawToken, userData) {
    localStorage.setItem("hf_token", rawToken);
    setToken(rawToken);
    setUser(userData);
  }

  function logoutUser() {
    localStorage.removeItem("hf_token");
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ token, user, loading, loginUser, logoutUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
