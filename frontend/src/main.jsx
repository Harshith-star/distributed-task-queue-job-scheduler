import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'react-hot-toast';
import App from './App.jsx';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false } },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster position="top-right" toastOptions={{
        duration: 4000,
        style: { background: '#111827', color: '#f3f4f6', border: '1px solid #374151', borderRadius: '10px', fontSize: '14px' },
        success: { iconTheme: { primary: '#10b981', secondary: '#111827' } },
        error:   { iconTheme: { primary: '#ef4444', secondary: '#111827' } },
      }} />
    </QueryClientProvider>
  </React.StrictMode>
);
