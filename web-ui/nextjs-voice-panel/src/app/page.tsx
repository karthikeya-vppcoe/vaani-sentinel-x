'use client';

import dynamic from 'next/dynamic';
import ContentPanel from '@/components/ContentPanel';
import { useState, useEffect } from 'react';

// Dynamically import Auth with SSR disabled
const Auth = dynamic(() => import('@/components/Auth'), { ssr: false });

export default function Home() {
  const [token, setToken] = useState<string | null>(null);

  useEffect(() => {
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      setToken(storedToken);
    }

    // Listen for storage events (e.g., token changes in another tab)
    const handleStorageChange = () => {
      const newToken = localStorage.getItem('token');
      setToken(newToken);
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  return (
    <main className="min-h-screen p-8">
      <h1 className="text-3xl font-bold mb-8">Vaani Sentinel X</h1>
      <Auth setToken={setToken} />
      {token && <ContentPanel />}
    </main>
  );
}
