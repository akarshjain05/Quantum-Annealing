import React, { useState } from 'react';
import client from '../api/client';

export default function Login() {
  const [email, setEmail] = useState('treasury@demo-bank.com');
  const [password, setPassword] = useState('DemoPassword123!');
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      const res = await client.post('/api/auth/login', { email, password });
      localStorage.setItem('token', res.data.access_token);
      window.location.href = '/';
    } catch (err) {
      setError('Invalid credentials');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg font-sans">
      <div className="w-full max-w-md p-8 card">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded bg-primary/10 text-primary mb-4">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <h1 className="font-display text-2xl font-semibold">NostroQ Quantum Core</h1>
          <p className="text-sm text-muted mt-2">Treasury Liquidity Optimization Engine</p>
        </div>
        {error && <div className="text-red-500 text-sm mb-4 text-center">{error}</div>}
        <form className="space-y-4" onSubmit={handleLogin}>
          <div>
            <label className="block text-xs font-medium text-muted uppercase tracking-wide mb-1">SSO ID / Email</label>
            <input type="text" value={email} onChange={e => setEmail(e.target.value)} className="w-full bg-subtle border border-border rounded px-3 py-2 text-sm focus:outline-none focus:border-primary" />
          </div>
          <div>
            <label className="block text-xs font-medium text-muted uppercase tracking-wide mb-1">Hardware Token</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} className="w-full bg-subtle border border-border rounded px-3 py-2 text-sm focus:outline-none focus:border-primary" />
          </div>
          <button type="submit" className="w-full bg-primary text-bg font-medium text-sm rounded px-4 py-2 mt-4 hover:bg-primary/90 transition-colors">
            Authenticate & Connect
          </button>
        </form>
      </div>
    </div>
  );
}
