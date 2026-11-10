import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './styles/index.css'

async function start() {
  // Design preview without a backend. Only in builds made with VITE_DEMO=true;
  // in every other build this branch and the sample data are removed.
  if (import.meta.env.VITE_DEMO === 'true') {
    const { installDemo } = await import('./demo/installDemo');
    installDemo();
  }

  const rootElement = document.getElementById('root')!;
  const root = ReactDOM.createRoot(rootElement);

  root.render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
}

start();
