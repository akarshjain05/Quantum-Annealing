import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("treasury@demo-bank.com");
  const [password, setPassword] = useState("DemoPassword123!");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(err.response?.data?.detail || "Sign in failed. Check the API is running.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="font-display text-3xl font-semibold tracking-tight">
            Nostro<span className="text-teal">Q</span>
          </div>
          <div className="text-sm text-muted mt-1.5">
            Quantum-ready liquidity intelligence for cross-border corridors
          </div>
        </div>

        <form onSubmit={handleSubmit} className="card p-6 space-y-4">
          <div>
            <label className="block text-xs text-muted mb-1.5 font-mono uppercase tracking-wide">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-raised border border-border rounded-md px-3 py-2 text-sm text-text focus:border-teal outline-none"
              required
            />
          </div>
          <div>
            <label className="block text-xs text-muted mb-1.5 font-mono uppercase tracking-wide">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-raised border border-border rounded-md px-3 py-2 text-sm text-text focus:border-teal outline-none"
              required
            />
          </div>
          {error && <div className="text-red text-xs">{error}</div>}
          <button
            type="submit"
            disabled={loading}
            className="w-full bg-teal text-bg font-medium text-sm rounded-md py-2.5 hover:bg-teal/90 transition-colors disabled:opacity-60"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
          <div className="text-[11px] text-faint text-center pt-1">
            Synthetic demo account only - not a real bank credential.
          </div>
        </form>
      </div>
    </div>
  );
}
