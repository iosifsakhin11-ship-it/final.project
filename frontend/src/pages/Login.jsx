/**
 * pages/Login.jsx — Two-Factor Authentication State Machine
 *
 * Three phases: CREDENTIALS -> OTP -> DONE
 * Handles unverified-account 403 with one-click resend.
 */

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import * as api from "../api/client";
import toast from "react-hot-toast";

export default function Login() {
  const { loginUser } = useAuth();
  const nav = useNavigate();

  const [phase, setPhase] = useState("CREDENTIALS"); // CREDENTIALS | REGISTER | OTP
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [otp, setOtp] = useState("");
  const [loading, setLoading] = useState(false);
  const [unverified, setUnverified] = useState(false);

  async function handleLogin(e) {
    e.preventDefault();
    setLoading(true);
    setUnverified(false);
    try {
      await api.login(email, password);
      toast.success("OTP sent to your email");
      setPhase("OTP");
    } catch (err) {
      const detail = err?.detail || "Login failed";
      if (detail.includes("verify your email")) {
        setUnverified(true);
      }
      toast.error(detail);
    } finally { setLoading(false); }
  }

  async function handleOtp(e) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await api.verifyOtp(email, otp);
      loginUser(data.token, data.user);
      toast.success(data.message);
      nav("/");
    } catch (err) {
      toast.error(err?.detail || "OTP verification failed");
    } finally { setLoading(false); }
  }

  async function handleRegister(e) {
    e.preventDefault();
    setLoading(true);
    try {
      await api.register(username, email, password);
      toast.success("Account created — check your email for verification link");
      setPhase("CREDENTIALS");
    } catch (err) {
      toast.error(err?.detail || "Registration failed");
    } finally { setLoading(false); }
  }

  async function handleResend() {
    try {
      await api.resendVerification(email);
      toast.success("Verification email resent");
    } catch (err) {
      toast.error(err?.detail || "Could not resend");
    }
  }

  return (
    <div className="max-w-md mx-auto mt-16">
      <h1 className="text-2xl font-bold mb-6 text-center">
        {phase === "REGISTER" ? "Create Account" : phase === "OTP" ? "Enter Verification Code" : "Sign In"}
      </h1>

      {phase === "CREDENTIALS" && (
        <form onSubmit={handleLogin} className="space-y-4">
          <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required
            className="w-full border rounded px-3 py-2" />
          <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required
            className="w-full border rounded px-3 py-2" />
          <button disabled={loading} className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50">
            {loading ? "Signing in..." : "Sign In"}
          </button>
          {unverified && (
            <button type="button" onClick={handleResend} className="w-full text-blue-600 underline text-sm">
              Resend verification email
            </button>
          )}
          <p className="text-center text-sm text-slate-500">
            No account?{" "}
            <button type="button" onClick={() => setPhase("REGISTER")} className="text-blue-600 underline">
              Register
            </button>
          </p>
        </form>
      )}

      {phase === "REGISTER" && (
        <form onSubmit={handleRegister} className="space-y-4">
          <input type="text" placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} required
            className="w-full border rounded px-3 py-2" />
          <input type="email" placeholder="Email" value={email} onChange={e => setEmail(e.target.value)} required
            className="w-full border rounded px-3 py-2" />
          <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required
            className="w-full border rounded px-3 py-2" />
          <button disabled={loading} className="w-full bg-green-600 text-white py-2 rounded hover:bg-green-700 disabled:opacity-50">
            {loading ? "Creating..." : "Create Account"}
          </button>
          <p className="text-center text-sm text-slate-500">
            Already have an account?{" "}
            <button type="button" onClick={() => setPhase("CREDENTIALS")} className="text-blue-600 underline">
              Sign in
            </button>
          </p>
        </form>
      )}

      {phase === "OTP" && (
        <form onSubmit={handleOtp} className="space-y-4">
          <p className="text-sm text-slate-600 text-center">
            A 6-digit code was sent to <strong>{email}</strong>. It expires in 30 seconds.
          </p>
          <input type="text" placeholder="6-digit code" value={otp} onChange={e => setOtp(e.target.value)}
            maxLength={6} required className="w-full border rounded px-3 py-2 text-center text-2xl tracking-widest" />
          <button disabled={loading} className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50">
            {loading ? "Verifying..." : "Verify"}
          </button>
          <button type="button" onClick={() => setPhase("CREDENTIALS")}
            className="w-full text-sm text-slate-500 underline">
            Use a different account
          </button>
        </form>
      )}
    </div>
  );
}
