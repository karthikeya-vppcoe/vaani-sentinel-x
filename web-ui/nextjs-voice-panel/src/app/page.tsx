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

    const handleStorageChange = () => {
      const newToken = localStorage.getItem('token');
      setToken(newToken);
    };

    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-gray-50 to-indigo-100 flex flex-col">
      {/* Header */}
      <header className="bg-white shadow-md py-4 px-6 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">
            Vaani Sentinel X
          </h1>
        </div>
        <nav className="flex space-x-4">
          <a
            href="#"
            className="text-gray-600 hover:text-indigo-600 transition-colors duration-200 text-sm font-medium"
            onClick={(e) => e.preventDefault()}
          >
            About
          </a>
          <a
            href="#"
            className="text-gray-600 hover:text-indigo-600 transition-colors duration-200 text-sm font-medium"
            onClick={(e) => e.preventDefault()}
          >
            Contact
          </a>
        </nav>
      </header>

      {/* Main Content */}
      <main className="flex-1 py-10 px-6 max-w-7xl mx-auto w-full animate-fade-in">
        <div className="mb-10">
          <Auth setToken={setToken} />
        </div>
        {token && (
          <div className="animate-slide-up">
            <ContentPanel />
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-gray-800 py-4 px-6 text-center text-white">
        <p className="text-sm">
          &copy; {new Date().getFullYear()} Vaani Sentinel X. All rights reserved.
        </p>
        <div className="mt-2 flex justify-center space-x-4">
          <a
            href="#"
            className="text-gray-400 hover:text-indigo-400 transition-colors duration-200 text-sm"
            onClick={(e) => e.preventDefault()}
          >
            Privacy Policy
          </a>
          <a
            href="#"
            className="text-gray-400 hover:text-indigo-400 transition-colors duration-200 text-sm"
            onClick={(e) => e.preventDefault()}
          >
            Terms of Service
          </a>
        </div>
      </footer>
    </div>
  );
}
